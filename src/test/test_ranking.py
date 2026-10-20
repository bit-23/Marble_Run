"""Testes do ranking em SQLite. Rodar na pasta src:  python -m unittest test.test_ranking"""
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from marble_run.dominio.regras import NivelDeDificuldade, PontuacaoDoJogador, ResultadoDaFase  # noqa: E402
from marble_run.infraestrutura.persistencia import PontuacoesEmSQLite  # noqa: E402

FACIL, NORMAL, DIFICIL, INSANO = (NivelDeDificuldade.FACIL, NivelDeDificuldade.NORMAL,
                                  NivelDeDificuldade.DIFICIL, NivelDeDificuldade.INSANO)


class TesteRanking(unittest.TestCase):
    def setUp(self):
        self._pasta = tempfile.TemporaryDirectory()
        self.caminho = Path(self._pasta.name) / "pontuacoes.sqlite3"
        self.repo = PontuacoesEmSQLite(self.caminho)

    def tearDown(self):
        self._pasta.cleanup()

    def test_separado_por_dificuldade_e_ordenado(self):
        self.repo.salvar_melhor("Ana", NORMAL, 500, 3)
        self.repo.salvar_melhor("Bia", NORMAL, 900, 5)
        self.repo.salvar_melhor("Ana", INSANO, 50, 1)
        self.assertEqual([(e.jogador, e.pontos) for e in self.repo.ranking(NORMAL)], [("Bia", 900), ("Ana", 500)])
        self.assertEqual([e.jogador for e in self.repo.ranking(INSANO)], ["Ana"])
        self.assertEqual(self.repo.ranking(FACIL), [])
        self.assertEqual(self.repo.carregar_melhor("ana", NORMAL), (500, 3), "nome sem diferenciar maiusculas")

    def test_so_guarda_se_bater_o_proprio_recorde(self):
        self.repo.salvar_melhor("Ana", NORMAL, 500, 3)
        self.repo.salvar_melhor("Ana", NORMAL, 200, 9)
        self.assertEqual(self.repo.carregar_melhor("Ana", NORMAL), (500, 3))

    def test_top_10(self):
        for i in range(15):
            self.repo.salvar_melhor(f"J{i}", DIFICIL, i * 10, 1)
        ranking = self.repo.ranking(DIFICIL)
        self.assertEqual(len(ranking), 10)
        self.assertEqual(ranking[0].jogador, "J14")

    def test_edicao(self):
        self.repo.salvar_melhor("Ana", NORMAL, 500, 3)
        self.repo.salvar_melhor("Bia", NORMAL, 900, 5)
        self.assertFalse(self.repo.atualizar("Ana", NORMAL, "bia", 1, 1), "nome ja usado por outro")
        self.assertTrue(self.repo.atualizar("Ana", NORMAL, "Carol", 1000, 7))
        self.assertEqual(self.repo.ranking(NORMAL)[0].jogador, "Carol")
        self.assertTrue(self.repo.atualizar("Carol", NORMAL, "CAROL", 1000, 7), "so mudar maiusculas pode")
        self.repo.apagar("Bia", NORMAL)
        self.assertEqual([e.jogador for e in self.repo.ranking(NORMAL)], ["CAROL"])
        self.repo.salvar_melhor("Dani", FACIL, 10, 1)
        self.repo.limpar(NORMAL)
        self.assertEqual(self.repo.ranking(NORMAL), [])
        self.assertEqual(len(self.repo.ranking(FACIL)), 1, "limpar uma aba nao mexe nas outras")

    def test_migra_banco_antigo_para_normal_uma_vez(self):
        antigo = Path(self._pasta.name) / "antigo.sqlite3"
        with sqlite3.connect(antigo) as banco:
            banco.execute("CREATE TABLE pontuacoes (jogador TEXT PRIMARY KEY COLLATE NOCASE, pontos INT, fase INT)")
            banco.execute("INSERT INTO pontuacoes VALUES ('wesley', 1200, 6)")
        banco.close()
        repo = PontuacoesEmSQLite(antigo)
        self.assertEqual(repo.carregar_melhor("Wesley", NORMAL), (1200, 6))
        repo.apagar("wesley", NORMAL)
        self.assertEqual(PontuacoesEmSQLite(antigo).ranking(NORMAL), [], "apagado nao volta ao reabrir")

    def test_pontuacao_do_jogador_salva_na_dificuldade_da_partida(self):
        ouvinte = PontuacaoDoJogador("Ana", INSANO, self.repo)
        ouvinte.ao_concluir_fase(ResultadoDaFase(1, 50, 150))
        ouvinte.ao_concluir_fase(ResultadoDaFase(2, 0, 200))
        self.assertEqual(self.repo.carregar_melhor("Ana", INSANO), (350, 2))
        self.assertEqual(self.repo.carregar_melhor("Ana", NORMAL), (0, 0))


if __name__ == "__main__":
    unittest.main()
