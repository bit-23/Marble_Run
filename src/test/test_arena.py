"""Testes da ARENA editavel (teste dos mapas). Rodar na pasta src:  python -m unittest test.test_arena"""
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from marble_run.dominio.ambiente import TipoDeItem, TipoDeOcorrencia, TipoDePerigo  # noqa: E402
from marble_run.dominio.arena import (  # noqa: E402
    FERRAMENTAS, Categoria, EditorDaArena, Especial, ferramentas_da,
)
from marble_run.dominio.biomas import Bioma  # noqa: E402
from marble_run.dominio.geometria import Vetor2  # noqa: E402
from marble_run.dominio.geradores import GeradorArena, GeradorBacktracker  # noqa: E402
from marble_run.dominio.labirinto import Coordenada  # noqa: E402
from marble_run.dominio.monstros import TipoDeMonstro  # noqa: E402
from marble_run.dominio.partida import FabricaDeFases, Partida, SituacaoDaPartida  # noqa: E402
from marble_run.dominio.regras import Dificuldade  # noqa: E402

DT = 1 / 60


def ferramenta(nome: str):
    return next(f for f in FERRAMENTAS if f.nome == nome)


class TesteArena(unittest.TestCase):
    def setUp(self):
        fabrica = FabricaDeFases(GeradorBacktracker(), Dificuldade(), ["gelo"], random.Random(1),
                                 biomas={"gelo": Bioma.gelado()}, vitrine=True, gerador_da_arena=GeradorArena())
        self.partida = Partida(fabrica)
        self.fase = self.partida.fase
        self.lab = self.fase.labirinto
        self.amb = self.fase.ambiente
        self.editor = EditorDaArena(self.lab, self.amb, self.fase.jogador, random.Random(2))

    def test_arena_e_um_quadrado_aberto_e_vazio(self):
        lab = self.lab
        self.assertEqual((lab.colunas, lab.linhas), (30, 20))
        internos = [(c, l) for l in range(1, lab.linhas - 1) for c in range(1, lab.colunas - 1)]
        self.assertFalse(any(lab.eh_parede(c, l) for c, l in internos), "por dentro nao tem parede")
        self.assertTrue(all(lab.eh_parede(c, 0) and lab.eh_parede(c, lab.linhas - 1) for c in range(lab.colunas)))
        self.assertEqual((self.amb.monstros, self.amb.perigos, self.amb.caixas), ((), (), ()))
        self.assertIsNotNone(self.amb.fenomeno, "o fenomeno do mapa continua (F forca)")
        self.assertTrue(self.fase.tempo_ilimitado)

    def test_paleta_tem_tudo(self):
        self.assertEqual({f.monstro for f in ferramentas_da(Categoria.MONSTRO)}, set(TipoDeMonstro))
        self.assertEqual({f.item for f in ferramentas_da(Categoria.ITEM)}, set(TipoDeItem))
        self.assertEqual({f.perigo for f in ferramentas_da(Categoria.PERIGO)}, set(TipoDePerigo))
        self.assertEqual({f.especial for f in ferramentas_da(Categoria.MAPA)}, set(Especial))

    def test_parede_levanta_derruba_e_nunca_prende_o_jogador(self):
        tile = Coordenada(10, 5)
        self.assertTrue(self.editor.aplicar(ferramenta("PAREDE"), tile))
        self.assertTrue(self.lab.eh_parede(*tile))
        self.assertTrue(self.editor.apagar(tile), "clique direito derruba")
        self.assertFalse(self.lab.eh_parede(*tile))
        self.assertFalse(self.editor.aplicar(ferramenta("PAREDE"), self.lab.entrada), "nem em cima do jogador")
        self.assertFalse(self.editor.aplicar(ferramenta("PAREDE"), Coordenada(0, 5)), "borda nao muda")
        self.assertFalse(self.editor.aplicar(ferramenta("PAREDE"), self.lab.saida))

    def test_parede_bloqueia_o_jogador(self):
        entrada = self.lab.entrada
        for linha in range(1, self.lab.linhas - 1):
            self.editor.aplicar(ferramenta("PAREDE"), Coordenada(entrada.coluna + 2, linha))
        for _ in range(round(2 / DT)):
            self.partida.atualizar(DT, Vetor2(1, 0))
        self.assertLess(self.fase.jogador.x, (entrada.coluna + 2) * self.lab.tamanho_tile)

    def test_perigo_monstro_item_e_borracha(self):
        tile = Coordenada(12, 9)
        self.editor.aplicar(ferramenta("FOGO"), tile)
        self.assertEqual([p.tipo for p in self.amb.perigos], [TipoDePerigo.FOGO])
        self.editor.aplicar(ferramenta("LAVA"), tile)
        self.assertEqual([p.tipo for p in self.amb.perigos], [TipoDePerigo.LAVA], "troca o que tinha no tile")
        self.editor.aplicar(ferramenta("YETI"), Coordenada(15, 9))
        self.assertEqual([m.tipo for m in self.amb.monstros], [TipoDeMonstro.YETI])
        self.editor.aplicar(ferramenta("BOTA"), Coordenada(5, 3))
        self.assertIs(self.amb.caixas[0].conteudo, TipoDeItem.BOTA)
        for t in (tile, Coordenada(15, 9), Coordenada(5, 3)):
            self.assertTrue(self.editor.aplicar(ferramenta("BORRACHA"), t))
        self.assertEqual((self.amb.perigos, self.amb.monstros, self.amb.caixas), ((), (), ()))

    def test_item_no_chao_e_pego_sem_roleta(self):
        entrada = self.lab.entrada
        self.editor.aplicar(ferramenta("CAPACETE"), Coordenada(entrada.coluna + 1, entrada.linha))
        ocorrencias = []
        for _ in range(round(0.6 / DT)):
            self.partida.atualizar(DT, Vetor2(1, 0))
            ocorrencias += self.partida.ocorrencias
        pegou = [o for o in ocorrencias if o.item is TipoDeItem.CAPACETE]
        self.assertTrue(pegou)
        self.assertIs(pegou[0].tipo, TipoDeOcorrencia.BUFF_APLICADO)

    def test_portal_muda_de_lugar_e_nao_encerra_a_arena(self):
        entrada = self.lab.entrada
        perto = Coordenada(entrada.coluna + 1, entrada.linha)
        self.assertTrue(self.editor.aplicar(ferramenta("PORTAL"), perto))
        self.assertEqual(self.lab.saida, perto)
        for _ in range(round(0.6 / DT)):
            self.partida.atualizar(DT, Vetor2(1, 0))
        self.assertIs(self.partida.situacao, SituacaoDaPartida.EM_ANDAMENTO, "o que foi montado nao se perde")

    def test_monstro_nao_atravessa_parede_nova(self):
        self.editor.aplicar(ferramenta("TORNADO"), Coordenada(15, 9))
        for linha in range(1, self.lab.linhas - 1):  # muro em volta da coluna 15
            for coluna in (13, 17):
                self.editor.aplicar(ferramenta("PAREDE"), Coordenada(coluna, linha))
        for _ in range(round(15 / DT)):
            self.partida.atualizar(DT, Vetor2())
            self.assertTrue(13 < self.amb.monstros[0].tile.coluna < 17)

    def test_limpar_tudo(self):
        self.editor.aplicar(ferramenta("PAREDE"), Coordenada(8, 8))
        self.editor.aplicar(ferramenta("GOLEM"), Coordenada(9, 9))
        self.editor.aplicar(ferramenta("TEIA"), Coordenada(10, 10))
        self.editor.limpar_tudo()
        self.assertFalse(self.lab.eh_parede(8, 8))
        self.assertEqual((self.amb.monstros, self.amb.perigos), ((), ()))


if __name__ == "__main__":
    unittest.main()
