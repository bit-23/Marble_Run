"""Testes dos itens novos e dos monstros. Rodar na pasta src:  python -m unittest test.test_monstros"""
import math
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from marble_run.dominio.ambiente import (  # noqa: E402
    Ambiente, Condicao, Desejo, Fenomeno, Perigo, TipoDeItem, TipoDeOcorrencia, TipoDePerigo,
)
from marble_run.dominio.biomas import Bioma  # noqa: E402
from marble_run.dominio.caminhos import caminho, linha_de_visao, manhattan, tiles_em_linha  # noqa: E402
from marble_run.dominio.geometria import Vetor2  # noqa: E402
from marble_run.dominio.geradores import GeradorBacktracker  # noqa: E402
from marble_run.dominio.jogador import Direcao, Jogador  # noqa: E402
from marble_run.dominio.labirinto import Coordenada, Labirinto, LabirintoEditavel  # noqa: E402
from marble_run.dominio.monstros import (  # noqa: E402
    CLASSES_DOS_MONSTROS, EstadoDoMonstro, Golpe, Rastro, TipoDeMonstro, criar_monstro,
)
from marble_run.dominio.partida import FabricaDeFases, Fase  # noqa: E402
from marble_run.dominio.regras import Cronometro, Dificuldade, NivelDeDificuldade  # noqa: E402

DT = 1 / 60
CORREDOR = [  # corredor reto comprido na linha 1, parede fina entre as linhas 1 e 3
    "###########",
    "#.........#",
    "#####.#####",
    "#.........#",
    "###########",
]
ABERTO = ["#########", "#.......#", "#.......#", "#.......#", "#.......#", "#.......#", "#########"]


def montar(mapa, entrada=(1, 1), saida=None, editavel=False) -> Labirinto:
    saida = saida or (len(mapa[0]) - 2, len(mapa) - 2)
    classe = LabirintoEditavel if editavel else Labirinto
    return classe([[c == "#" for c in linha] for linha in mapa], Coordenada(*entrada), Coordenada(*saida),
                  distancia_minima=10)


def jogador_em(lab: Labirinto, coluna: int, linha: int) -> Jogador:
    x, y = lab.centro_do_tile(Coordenada(coluna, linha))
    return Jogador(x, y + Jogador.ALTURA_DOS_PES)


def fase_com(lab: Labirinto, jogador: Jogador, ambiente: Ambiente) -> Fase:
    return Fase(1, 0, "teste", lab, jogador, Cronometro(60), 5.0, ambiente)


def andar(fase: Fase, direcao: Vetor2, segundos: float) -> list:
    ocorrencias = []
    for _ in range(round(segundos / DT)):
        fase.avancar(DT, direcao)
        ocorrencias += fase.recolher_ocorrencias()
    return ocorrencias


def tipos(ocorrencias) -> list:
    return [o.tipo for o in ocorrencias]


def simular(amb: Ambiente, jogador: Jogador, segundos: float) -> list:
    ocorrencias = []
    for _ in range(round(segundos / DT)):
        ocorrencias += amb.atualizar(DT, jogador)
    return ocorrencias


def monstro(tipo, lab, coluna, linha, agressivo=False, semente=1):
    return criar_monstro(tipo, Coordenada(coluna, linha), lab, random.Random(semente), agressivo)


# ======================================================================
class TesteCaminhos(unittest.TestCase):
    def test_caminho_linha_de_visao_e_tiles_em_linha(self):
        lab = montar(CORREDOR)
        trajeto = caminho(lab, Coordenada(1, 1), Coordenada(9, 3))
        self.assertEqual(trajeto[0], Coordenada(1, 1))
        self.assertEqual(trajeto[-1], Coordenada(9, 3))
        self.assertIn(Coordenada(5, 2), trajeto, "passa pela unica abertura")
        self.assertEqual(linha_de_visao(lab, Coordenada(1, 1), Coordenada(6, 1), 8), (1, 0))
        self.assertIsNone(linha_de_visao(lab, Coordenada(1, 1), Coordenada(1, 3), 8), "parede no meio")
        self.assertIsNone(linha_de_visao(lab, Coordenada(1, 1), Coordenada(9, 1), 3), "longe demais")
        self.assertEqual(len(tiles_em_linha(lab, Coordenada(1, 1), (1, 0), 99)), 8)


# ======================================================================
class TesteItensNovos(unittest.TestCase):
    def test_extintor_apaga_fogo_e_lava_em_volta(self):
        lab = montar(ABERTO)
        perto = Perigo(TipoDePerigo.FOGO, Coordenada(3, 3), lab.centro_do_tile(Coordenada(3, 3)))
        longe = Perigo(TipoDePerigo.FOGO, Coordenada(7, 5), lab.centro_do_tile(Coordenada(7, 5)))
        amb = Ambiente(lab, perigos=[perto, longe])
        amb.atualizar(DT, jogador_em(lab, 2, 3))
        amb.aplicar_premio(TipoDeItem.EXTINTOR)
        self.assertFalse(perto.ativo)
        self.assertTrue(longe.ativo)
        self.assertIsNotNone(amb.extintor)

    def test_extintor_petrifica_o_magman(self):
        lab = montar(ABERTO)
        magman = monstro(TipoDeMonstro.MAGMAN, lab, 4, 3)
        amb = Ambiente(lab, monstros=[magman])
        amb.atualizar(DT, jogador_em(lab, 2, 3))
        amb.aplicar_premio(TipoDeItem.EXTINTOR)
        self.assertIs(magman.estado, EstadoDoMonstro.APAGADO)

    def test_bota_protege_do_fogo(self):
        lab = montar(CORREDOR)
        for com_bota in (False, True):
            amb = Ambiente(lab, perigos=[Perigo(TipoDePerigo.LAVA, Coordenada(3, 1),
                                                lab.centro_do_tile(Coordenada(3, 1)))])
            if com_bota:
                amb.aplicar_premio(TipoDeItem.BOTA)
            fase = fase_com(lab, jogador_em(lab, 1, 1), amb)
            queimou = TipoDeOcorrencia.QUEIMOU in tipos(andar(fase, Vetor2(1, 0), 0.8))
            self.assertEqual(queimou, not com_bota)

    def test_guarda_chuva_anula_rajada_e_pipa_sopra_para_o_portal(self):
        lab = montar(CORREDOR, entrada=(1, 1), saida=(9, 1))
        jogador = jogador_em(lab, 3, 1)
        amb = Ambiente(lab, fenomeno=Fenomeno.RAJADA, sorteio=random.Random(1))
        while not (amb.ciclo.ativo and amb.ciclo.intensidade >= 1):
            amb.atualizar(DT, jogador)
        amb.aplicar_premio(TipoDeItem.PIPA)
        amb.atualizar(DT, jogador)
        self.assertGreater(amb.locomocao().arrasto.x, 0, "a pipa leva para a saida (direita)")
        amb.aplicar_premio(TipoDeItem.GUARDA_CHUVA)
        self.assertTrue(amb.locomocao().arrasto.eh_nulo)

    def test_broca_quebra_a_parede_de_verdade(self):
        lab = montar(CORREDOR, editavel=True)
        amb = Ambiente(lab)
        amb.aplicar_premio(TipoDeItem.BROCA)
        self.assertEqual(amb.cargas_de_parede, 2)
        fase = fase_com(lab, jogador_em(lab, 2, 1), amb)
        ocorrencias = andar(fase, Vetor2(0, 1), 0.3)
        self.assertIn(TipoDeOcorrencia.COMECOU_A_PERFURAR, tipos(ocorrencias))
        self.assertIsNotNone(amb.perfuracao)
        self.assertTrue(amb.locomocao().travado, "parado enquanto a broca gira")
        ocorrencias = andar(fase, Vetor2(0, 1), 1.4)
        self.assertIn(TipoDeOcorrencia.QUEBROU_PAREDE, tipos(ocorrencias))
        self.assertFalse(lab.eh_parede(2, 2), "a parede virou chao")
        self.assertEqual(amb.cargas_de_parede, 1)
        self.assertEqual(int(fase.jogador.y - Jogador.ALTURA_HITBOX / 2) // lab.tamanho_tile, 3, "passou andando")

    def test_broca_some_da_mao_quando_acaba(self):
        lab = montar(ABERTO.copy(), editavel=True)
        amb = Ambiente(lab)
        amb.aplicar_premio(TipoDeItem.BROCA)
        jogador = jogador_em(lab, 1, 3)
        fase = fase_com(lab, jogador, amb)
        andar(fase, Vetor2(-1, 0), 1.5)  # borda: nao quebra
        self.assertTrue(lab.eh_parede(0, 3))
        self.assertEqual(amb.cargas_de_parede, 2)
        amb._cargas_de_parede = 1  # noqa: SLF001
        lab.colocar_parede(Coordenada(2, 3))
        andar(fase, Vetor2(1, 0), 1.5)
        self.assertFalse(lab.eh_parede(2, 3))
        self.assertFalse(amb.condicao_ativa(Condicao.BROCA), "sem carga, a broca some")

    def test_fenomeno_liga_e_desliga(self):
        lab = montar(ABERTO)
        amb = Ambiente(lab, fenomeno=Fenomeno.TERREMOTO)
        jogador = jogador_em(lab, 3, 3)
        amb.ligar_fenomeno(False)
        self.assertFalse(amb.fenomeno_ligado)
        for _ in range(round(30 / DT)):
            amb.atualizar(DT, jogador)
            self.assertFalse(amb.locomocao().invertido)
        amb.forcar_fenomeno()
        self.assertTrue(amb.fenomeno_ligado, "forcar tambem liga")
        amb.atualizar(0.3, jogador)
        self.assertTrue(amb.locomocao().invertido)

    def test_tapete_flutua_sobre_areia_e_so_uma_parede(self):
        lab = montar(CORREDOR)
        amb = Ambiente(lab, perigos=[Perigo(TipoDePerigo.AREIA_MOVEDICA, Coordenada(2, 1),
                                            lab.centro_do_tile(Coordenada(2, 1)))])
        amb.aplicar_premio(TipoDeItem.TAPETE)
        self.assertEqual(amb.cargas_de_parede, 1)
        amb.atualizar(DT, jogador_em(lab, 2, 1))
        self.assertFalse(amb.na_areia)
        self.assertTrue(amb.golpear(Golpe.VENENO, monstro(TipoDeMonstro.COBRA, lab, 3, 1)) is False)

    def test_capacete_terremoto_nao_inverte(self):
        lab = montar(ABERTO)
        amb = Ambiente(lab, fenomeno=Fenomeno.TERREMOTO)
        jogador = jogador_em(lab, 3, 3)
        while not amb.ciclo.ativo:
            amb.atualizar(DT, jogador)
        amb.atualizar(0.3, jogador)
        self.assertTrue(amb.locomocao().invertido)
        amb.aplicar_premio(TipoDeItem.CAPACETE)
        self.assertFalse(amb.locomocao().invertido)
        self.assertGreater(amb.multiplicador_de_visao(), 1.0)

    def test_genio_tempo_caminho_e_teleporte(self):
        lab = montar(CORREDOR, saida=(9, 3))
        amb = Ambiente(lab)
        fase = fase_com(lab, jogador_em(lab, 1, 1), amb)
        fase.avancar(DT, Vetor2())
        fase.recolher_ocorrencias()
        self.assertIs(amb.aplicar_premio(TipoDeItem.GENIO).item, TipoDeItem.GENIO)

        fase.realizar_desejo(Desejo.TEMPO)
        self.assertEqual(fase.recolher_ocorrencias()[0].segundos, Ambiente.BONUS_DO_GENIO)

        fase.realizar_desejo(Desejo.CAMINHO)
        trajeto = amb.melhor_caminho
        self.assertEqual(trajeto[0], Coordenada(1, 1))
        self.assertEqual(trajeto[-1], Coordenada(9, 3))
        andar(fase, Vetor2(), 4.0)
        self.assertEqual(amb.melhor_caminho, (), "as setas somem depois de 3.5s")

        antes = len(caminho(lab, Coordenada(1, 1), lab.saida))
        fase.realizar_desejo(Desejo.TELEPORTE)
        tile = Coordenada(int(fase.jogador.x) // 56, int(fase.jogador.y - 8) // 56)
        self.assertLess(len(caminho(lab, tile, lab.saida)), antes - 3, "ficou mais perto do portal")

    def test_flauta_faz_os_monstros_dormirem(self):
        lab = montar(ABERTO)
        yeti = monstro(TipoDeMonstro.YETI, lab, 5, 3)
        amb = Ambiente(lab, monstros=[yeti])
        amb.aplicar_premio(TipoDeItem.FLAUTA)
        jogador = jogador_em(lab, 2, 3)
        x = yeti.x
        simular(amb, jogador, 2.0)
        self.assertIs(yeti.estado, EstadoDoMonstro.DORMINDO)
        self.assertEqual(yeti.x, x, "dormindo nao anda")


# ======================================================================
class TesteMonstros(unittest.TestCase):
    def test_aranha_cospe_teia_que_prende(self):
        lab = montar(CORREDOR)
        aranha = monstro(TipoDeMonstro.ARANHA, lab, 8, 1)
        amb = Ambiente(lab, monstros=[aranha], sorteio=random.Random(2))
        jogador = jogador_em(lab, 2, 1)
        ocorrencias = simular(amb, jogador, 8.0)
        self.assertIn(TipoDeOcorrencia.FICOU_PRESO, tipos(ocorrencias))
        self.assertIsNotNone(amb.desafio_da_teia)

    def test_aranha_foge_da_lanterna(self):
        lab = montar(CORREDOR)
        aranha = monstro(TipoDeMonstro.ARANHA, lab, 4, 1)
        amb = Ambiente(lab, monstros=[aranha], sorteio=random.Random(2))
        amb.aplicar_premio(TipoDeItem.LANTERNA)
        jogador = jogador_em(lab, 2, 1)
        ocorrencias = simular(amb, jogador, 3.0)
        self.assertNotIn(TipoDeOcorrencia.FICOU_PRESO, tipos(ocorrencias))
        self.assertTrue(aranha.com_medo or aranha.x > lab.centro_do_tile(Coordenada(4, 1))[0])

    def test_minotauro_investe_machuca_e_fica_tonto(self):
        lab = montar(CORREDOR)
        minotauro = monstro(TipoDeMonstro.MINOTAURO, lab, 8, 1)
        amb = Ambiente(lab, monstros=[minotauro])
        jogador = jogador_em(lab, 3, 1)
        vistos, ocorrencias = set(), []
        for _ in range(round(8 / DT)):
            ocorrencias += amb.atualizar(DT, jogador)
            vistos.add(minotauro.estado)
        self.assertTrue({EstadoDoMonstro.AVISANDO, EstadoDoMonstro.ATACANDO, EstadoDoMonstro.ATORDOADO} <= vistos)
        self.assertTrue(any(o.dano for o in ocorrencias if o.tipo is TipoDeOcorrencia.MONSTRO_ATACOU))

    def test_boneco_de_neve_e_lento_e_congela_em_linha(self):
        lab = montar(CORREDOR)
        boneco = monstro(TipoDeMonstro.BONECO_DE_NEVE, lab, 8, 1)
        amb = Ambiente(lab, monstros=[boneco])
        jogador = jogador_em(lab, 3, 1)
        ocorrencias = simular(amb, jogador, 7.0)
        self.assertIn(TipoDeOcorrencia.CONGELOU, tipos(ocorrencias))
        self.assertLess(boneco.VELOCIDADE, 0.2, "extremamente lento")

    def test_blusa_protege_do_raio_congelante(self):
        lab = montar(CORREDOR)
        amb = Ambiente(lab, monstros=[monstro(TipoDeMonstro.BONECO_DE_NEVE, lab, 8, 1)])
        jogador = jogador_em(lab, 3, 1)
        for _ in range(4):
            amb.aplicar_premio(TipoDeItem.BLUSA)
            ocorrencias = simular(amb, jogador, 2.0)
            self.assertNotIn(TipoDeOcorrencia.CONGELOU, tipos(ocorrencias))

    def test_yeti_cria_placas_de_gelo(self):
        lab = montar(ABERTO)
        amb = Ambiente(lab, monstros=[monstro(TipoDeMonstro.YETI, lab, 5, 3)])
        jogador = jogador_em(lab, 2, 1)
        criou = False
        for _ in range(round(10 / DT)):
            amb.atualizar(DT, jogador)
            if any(p.tipo is TipoDePerigo.GELO for p in amb.rastros):
                criou = True
                break
        self.assertTrue(criou)

    def test_magman_deixa_lava_que_some(self):
        lab = montar(ABERTO)
        magman = monstro(TipoDeMonstro.MAGMAN, lab, 6, 5)
        amb = Ambiente(lab, monstros=[magman])
        jogador = jogador_em(lab, 1, 1)
        simular(amb, jogador, 2.0)
        lavas = [p for p in amb.rastros if p.tipo is TipoDePerigo.LAVA]
        self.assertTrue(lavas)
        for lava in lavas:
            self.assertLessEqual(lava.expira_em - amb.tempo, magman.DURACAO_DA_LAVA)

    def test_fornalha_solta_labareda_e_bota_protege(self):
        lab = montar(CORREDOR)
        for com_bota in (False, True):
            fornalha = monstro(TipoDeMonstro.FORNALHA, lab, 9, 1)
            amb = Ambiente(lab, monstros=[fornalha])
            jogador = jogador_em(lab, 6, 1)
            if com_bota:
                amb.aplicar_premio(TipoDeItem.BOTA)
            ocorrencias = simular(amb, jogador, 6.0 if not com_bota else 7.9)
            self.assertEqual(TipoDeOcorrencia.QUEIMOU in tipos(ocorrencias), not com_bota)

    def test_fornalha_e_solida(self):
        lab = montar(CORREDOR)
        amb = Ambiente(lab, monstros=[monstro(TipoDeMonstro.FORNALHA, lab, 5, 1)])
        fase = fase_com(lab, jogador_em(lab, 2, 1), amb)
        amb.aplicar_premio(TipoDeItem.ESTRELA)
        andar(fase, Vetor2(1, 0), 2.0)
        self.assertLess(fase.jogador.x, lab.centro_do_tile(Coordenada(5, 1))[0] - 20, "nao atravessa")

    def test_aguia_rouba_buff_e_guarda_chuva_protege(self):
        lab = montar(ABERTO)
        for com_guarda_chuva in (False, True):
            aguia = monstro(TipoDeMonstro.AGUIA, lab, 6, 3)
            amb = Ambiente(lab, monstros=[aguia])
            jogador = jogador_em(lab, 3, 3)
            amb.aplicar_premio(TipoDeItem.CAFE)
            if com_guarda_chuva:
                amb.aplicar_premio(TipoDeItem.GUARDA_CHUVA)
            for _ in range(round(7 / DT)):
                amb.aplicar_premio(TipoDeItem.CAFE)
                ocorrencias = amb.atualizar(DT, jogador)
                if any(o.tipo in (TipoDeOcorrencia.ROUBOU_BUFF, TipoDeOcorrencia.GOLPE_BLOQUEADO)
                       for o in ocorrencias):
                    break
            esperado = TipoDeOcorrencia.GOLPE_BLOQUEADO if com_guarda_chuva else TipoDeOcorrencia.ROUBOU_BUFF
            self.assertIn(esperado, tipos(ocorrencias))

    def test_tornado_joga_para_longe_do_portal(self):
        lab = montar(ABERTO, entrada=(1, 1), saida=(7, 5))
        tornado = monstro(TipoDeMonstro.TORNADO, lab, 5, 4)
        amb = Ambiente(lab, monstros=[tornado])
        fase = fase_com(lab, jogador_em(lab, 5, 4), amb)
        antes = len(caminho(lab, Coordenada(5, 4), lab.saida))
        ocorrencias = andar(fase, Vetor2(), 0.2)
        self.assertIn(TipoDeOcorrencia.ARREMESSADO, tipos(ocorrencias))
        self.assertFalse(any(o.dano for o in ocorrencias), "tornado nao da dano")
        andar(fase, Vetor2(), 0.8)
        jogador = fase.jogador
        depois = len(caminho(lab, Coordenada(int(jogador.x) // 56, int(jogador.y - 8) // 56), lab.saida))
        self.assertGreater(depois, antes)
        self.assertTrue(amb.condicao_ativa(Condicao.TONTO))

    def test_toupeira_abre_buraco_e_capacete_protege(self):
        lab = montar(ABERTO)
        for com_capacete in (False, True):
            amb = Ambiente(lab, monstros=[monstro(TipoDeMonstro.TOUPEIRA, lab, 4, 3)])
            jogador = jogador_em(lab, 3, 3)
            if com_capacete:
                amb.aplicar_premio(TipoDeItem.CAPACETE)
            ocorrencias = simular(amb, jogador, 8.0)
            caiu = [o for o in ocorrencias if o.tipo is TipoDeOcorrencia.CAIU_NO_BURACO]
            self.assertEqual(bool(caiu), not com_capacete)
            if caiu:
                self.assertLess(caiu[0].segundos, 0, "perde tempo")
            self.assertTrue(any(p.tipo is TipoDePerigo.BURACO for p in amb.rastros))

    def test_buracos_viram_tunel(self):
        lab = montar(CORREDOR)
        amb = Ambiente(lab)
        jogador = jogador_em(lab, 1, 1)
        amb.atualizar(DT, jogador)
        amb.deixar_rastro(Rastro.BURACO, Coordenada(3, 1), math.inf)
        amb.deixar_rastro(Rastro.BURACO, Coordenada(8, 3), math.inf)
        fase = fase_com(lab, jogador, amb)
        self.assertIn(TipoDeOcorrencia.ATRAVESSOU_TUNEL, tipos(andar(fase, Vetor2(1, 0), 0.8)))
        self.assertEqual(int(jogador.y - 8) // 56, 3)

    def test_golem_onda_de_choque_deixa_tonto_e_depois_cansa(self):
        lab = montar(ABERTO)
        golem = monstro(TipoDeMonstro.GOLEM, lab, 4, 3)
        amb = Ambiente(lab, monstros=[golem])
        jogador = jogador_em(lab, 2, 3)
        ocorrencias = []
        for _ in range(round(8 / DT)):
            ocorrencias += amb.atualizar(DT, jogador)
            if golem.estado is EstadoDoMonstro.ATORDOADO:
                break
        self.assertIn(TipoDeOcorrencia.MONSTRO_ATACOU, tipos(ocorrencias))
        self.assertTrue(amb.condicao_ativa(Condicao.TONTO))
        self.assertFalse(golem.solido, "cansado: da para passar por ele")

    def test_cobra_envenena_e_setas_curam(self):
        lab = montar(CORREDOR)
        amb = Ambiente(lab, monstros=[monstro(TipoDeMonstro.COBRA, lab, 4, 1)], sorteio=random.Random(3))
        jogador = jogador_em(lab, 2, 1)
        ocorrencias = []
        for _ in range(round(6 / DT)):
            ocorrencias += amb.atualizar(DT, jogador)
            if amb.envenenado:
                break
        self.assertIn(TipoDeOcorrencia.ENVENENOU, tipos(ocorrencias))
        for direcao in amb.desafio_da_teia.sequencia:
            ultima = amb.apertar(direcao)
        self.assertIs(ultima.tipo, TipoDeOcorrencia.CUROU_VENENO)
        self.assertFalse(amb.envenenado)

    def test_veneno_sem_cura_tira_coracao(self):
        lab = montar(CORREDOR)
        amb = Ambiente(lab)
        jogador = jogador_em(lab, 2, 1)
        amb.atualizar(DT, jogador)
        self.assertTrue(amb.golpear(Golpe.VENENO, monstro(TipoDeMonstro.COBRA, lab, 3, 1)))
        ocorrencias = simular(amb, jogador, Ambiente.TEMPO_DO_VENENO + 0.2)
        efeito = [o for o in ocorrencias if o.tipo is TipoDeOcorrencia.VENENO_FEZ_EFEITO]
        self.assertEqual(efeito[0].dano, 1)
        self.assertIsNone(amb.desafio_da_teia)

    def test_mumia_puxa_com_o_laco_e_some_na_tempestade(self):
        lab = montar(CORREDOR)
        mumia = monstro(TipoDeMonstro.MUMIA, lab, 6, 1)
        amb = Ambiente(lab, monstros=[mumia], fenomeno=Fenomeno.TEMPESTADE_DE_AREIA)
        jogador = jogador_em(lab, 2, 1)
        ocorrencias = simular(amb, jogador, 6.0)
        self.assertIn(TipoDeOcorrencia.PUXADO, tipos(ocorrencias))
        while not (amb.ciclo.ativo and amb.ciclo.intensidade > 0.5):
            amb.atualizar(DT, jogador)
        amb.atualizar(DT, jogador)
        self.assertFalse(mumia.visivel)

    def test_estrela_ignora_monstros(self):
        lab = montar(CORREDOR)
        amb = Ambiente(lab)
        jogador = jogador_em(lab, 2, 1)
        amb.atualizar(DT, jogador)
        amb.aplicar_premio(TipoDeItem.ESTRELA)
        for golpe in Golpe:
            self.assertFalse(amb.golpear(golpe, monstro(TipoDeMonstro.GOLEM, lab, 3, 1)), golpe)

    def test_monstros_ficam_no_territorio(self):
        """Patrulhando, ninguem se afasta muito de onde nasceu (da para fugir deles)."""
        lab = montar(["#" * 21] + ["#" + "." * 19 + "#"] * 11 + ["#" * 21], saida=(19, 11))
        for tipo in (TipoDeMonstro.MINOTAURO, TipoDeMonstro.TORNADO, TipoDeMonstro.GOLEM, TipoDeMonstro.COBRA,
                     TipoDeMonstro.BONECO_DE_NEVE):
            m = monstro(tipo, lab, 10, 6)
            amb = Ambiente(lab, monstros=[m])
            jogador = jogador_em(lab, 1, 1)
            for _ in range(round(30 / DT)):
                amb.atualizar(DT, jogador)
                self.assertLessEqual(manhattan(m.tile, m.casa), m.RAIO_DO_TERRITORIO + 1, tipo)

    def test_so_yeti_e_mumia_cacam_e_cansam(self):
        cacadores = {t for t in TipoDeMonstro if CLASSES_DOS_MONSTROS[t].ALCANCE_DA_CACA > 0}
        self.assertEqual(cacadores, {TipoDeMonstro.YETI, TipoDeMonstro.MUMIA})
        lab = montar(["#" * 21] + ["#" + "." * 19 + "#"] * 11 + ["#" * 21], saida=(19, 11))
        yeti = monstro(TipoDeMonstro.YETI, lab, 10, 6)
        amb = Ambiente(lab, monstros=[yeti])
        jogador = jogador_em(lab, 13, 6)
        cacou, desistiu = False, False
        for _ in range(round(8 / DT)):
            amb.aplicar_premio(TipoDeItem.ESTRELA)  # so observar, sem levar dano
            amb.atualizar(DT, jogador)
            cacou = cacou or yeti.cacando
            desistiu = desistiu or (cacou and not yeti.cacando)
        self.assertTrue(cacou, "chegou perto: o yeti caca")
        self.assertTrue(desistiu, "o folego acaba e ele desiste")

    def test_quem_patrulha_nao_entra_no_tile_do_jogador(self):
        lab = montar(CORREDOR)
        tornado = monstro(TipoDeMonstro.TORNADO, lab, 4, 1)
        amb = Ambiente(lab, monstros=[tornado])
        jogador = jogador_em(lab, 3, 1)
        amb.atualizar(DT, jogador)
        for _ in range(20):
            self.assertNotEqual(tornado._vagar(amb), Coordenada(3, 1))

    def test_quem_esta_preso_nao_apanha(self):
        """Preso na teia/veneno ou congelado, os monstros esperam (nada de apanhar sem poder fugir)."""
        lab = montar(CORREDOR)
        amb = Ambiente(lab)
        jogador = jogador_em(lab, 2, 1)
        amb.atualizar(DT, jogador)
        cobra = monstro(TipoDeMonstro.COBRA, lab, 3, 1)
        self.assertTrue(amb.golpear(Golpe.VENENO, cobra))
        for golpe in (Golpe.MORDIDA, Golpe.CHIFRADA, Golpe.LACO, Golpe.ARREMESSO, Golpe.TEIA):
            self.assertFalse(amb.golpear(golpe, cobra), golpe)

    def test_dano_de_monstro_tem_folga(self):
        lab = montar(CORREDOR)
        amb = Ambiente(lab)
        jogador = jogador_em(lab, 2, 1)
        amb.atualizar(DT, jogador)
        golem = monstro(TipoDeMonstro.GOLEM, lab, 3, 1)
        self.assertTrue(amb.golpear(Golpe.MORDIDA, golem))
        self.assertFalse(amb.golpear(Golpe.MORDIDA, golem), "invulneravel logo depois")


# ======================================================================
class TesteMonstrosNoMapa(unittest.TestCase):
    def test_quantidade_por_fase_e_dificuldade(self):
        normal = Dificuldade()
        self.assertEqual([normal.monstros(f) for f in (1, 3, 4, 6, 7, 12)], [0, 0, 1, 1, 2, 2])
        facil = Dificuldade.do_nivel(NivelDeDificuldade.FACIL)
        self.assertEqual(facil.monstros(10), 1)
        insano = Dificuldade.do_nivel(NivelDeDificuldade.INSANO)
        self.assertEqual([insano.monstros(f) for f in (1, 2, 3)], [0, 2, 3])
        self.assertTrue(insano.monstros_agressivos)

    def test_cada_mapa_tem_seus_dois_monstros(self):
        esperado = {
            "masmorra": (Bioma.masmorra(), {TipoDeMonstro.ARANHA, TipoDeMonstro.MINOTAURO}),
            "gelo": (Bioma.gelado(), {TipoDeMonstro.BONECO_DE_NEVE, TipoDeMonstro.YETI}),
            "fogo": (Bioma.vulcanico(), {TipoDeMonstro.MAGMAN, TipoDeMonstro.FORNALHA}),
            "vento": (Bioma.ventoso(), {TipoDeMonstro.AGUIA, TipoDeMonstro.TORNADO}),
            "terra": (Bioma.terroso(), {TipoDeMonstro.TOUPEIRA, TipoDeMonstro.GOLEM}),
            "deserto": (Bioma.desertico(), {TipoDeMonstro.COBRA, TipoDeMonstro.MUMIA}),
        }
        for nome, (bioma, monstros) in esperado.items():
            self.assertEqual(set(bioma.monstros), monstros, nome)

    def test_monstros_nascem_longe_da_entrada_e_so_depois_da_fase_3(self):
        for nome, bioma in (("gelo", Bioma.gelado()), ("fogo", Bioma.vulcanico()), ("terra", Bioma.terroso())):
            lab = GeradorBacktracker().gerar(16, 11, random.Random(4))
            self.assertEqual(bioma.criar_ambiente(lab, random.Random(1), fase=3).monstros, ())
            amb = bioma.criar_ambiente(lab, random.Random(1), fase=8)
            self.assertEqual(len(amb.monstros), 2, nome)
            for m in amb.monstros:
                self.assertGreaterEqual(len(caminho(lab, lab.entrada, m.tile)) - 1, bioma.distancia_dos_monstros)

    def test_fornalha_nasce_no_fim_de_um_beco(self):
        for semente in range(6):
            lab = GeradorBacktracker().gerar(16, 11, random.Random(semente))
            amb = Bioma.vulcanico().criar_ambiente(lab, random.Random(semente), fase=8)
            for m in amb.monstros:
                if m.tipo is TipoDeMonstro.FORNALHA:
                    livres = [d for d in ((1, 0), (-1, 0), (0, 1), (0, -1))
                              if not lab.eh_parede(m.tile.coluna + d[0], m.tile.linha + d[1])]
                    self.assertEqual(len(livres), 1)

    def test_vitrine_mostra_os_dois_monstros(self):
        for tema, bioma in (("masmorra", Bioma.masmorra()), ("deserto", Bioma.desertico()),
                            ("vento", Bioma.ventoso())):
            fabrica = FabricaDeFases(GeradorBacktracker(), Dificuldade(), [tema], random.Random(4),
                                     biomas={tema: bioma}, vitrine=True)
            fase = fabrica.criar(1)
            self.assertEqual({m.tipo for m in fase.ambiente.monstros}, set(bioma.monstros), tema)

    def test_partida_longa_com_monstros_nao_quebra(self):
        """Fumaca: todos os mapas, varias fases, jogador andando a esmo por um tempo."""
        biomas = {"gelo": Bioma.gelado(), "fogo": Bioma.vulcanico(), "deserto": Bioma.desertico(),
                  "masmorra": Bioma.masmorra(), "terra": Bioma.terroso(), "vento": Bioma.ventoso()}
        rng = random.Random(9)
        direcoes = [Vetor2(1, 0), Vetor2(-1, 0), Vetor2(0, 1), Vetor2(0, -1)]
        for tema, bioma in biomas.items():
            fabrica = FabricaDeFases(GeradorBacktracker(), Dificuldade.do_nivel(NivelDeDificuldade.INSANO), [tema],
                                     random.Random(2), biomas={tema: bioma})
            fase = fabrica.criar(9)
            direcao = direcoes[0]
            for passo in range(round(25 / DT)):
                if passo % 30 == 0:
                    direcao = rng.choice(direcoes)
                    for item in fase.ambiente.premios:
                        if rng.random() < 0.02 and item is not TipoDeItem.GENIO:
                            fase.aplicar_premio(item)
                    if fase.ambiente.desafio_da_teia is not None:
                        for seta in fase.ambiente.desafio_da_teia.sequencia:
                            fase.apertar(seta)
                fase.avancar(DT, direcao)
                fase.recolher_ocorrencias()
            for m in fase.ambiente.monstros:
                self.assertTrue(0 <= m.x <= fase.labirinto.largura and 0 <= m.y <= fase.labirinto.altura, tema)


if __name__ == "__main__":
    unittest.main()
