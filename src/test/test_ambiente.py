"""Testes dos buffs/debuffs. Rodar na pasta src:  python -m unittest test.test_ambiente"""
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from marble_run.dominio.ambiente import (  # noqa: E402
    CICLOS_DOS_FENOMENOS, ITENS_COMUNS, Ambiente, CaixaSurpresa, CicloDeEvento, Condicao, Fenomeno, MolaDeParede,
    Ocorrencia, Perigo, TipoDeItem, TipoDeOcorrencia, TipoDePerigo,
)
from marble_run.dominio.biomas import Bioma  # noqa: E402
from marble_run.dominio.contratos import OuvinteDaPartida  # noqa: E402
from marble_run.dominio.geometria import Vetor2  # noqa: E402
from marble_run.dominio.geradores import GeradorBacktracker  # noqa: E402
from marble_run.dominio.jogador import Direcao, Jogador, Locomocao  # noqa: E402
from marble_run.dominio.labirinto import Coordenada, Labirinto  # noqa: E402
from marble_run.dominio.partida import FabricaDeFases, Fase, Partida, SituacaoDaPartida  # noqa: E402
from marble_run.dominio.regras import Cronometro, Dificuldade, NivelDeDificuldade  # noqa: E402

MAPA = [
    "#######",
    "#.#...#",
    "#.#.#.#",
    "#.....#",
    "#######",
]
DT = 1 / 60


def labirinto() -> Labirinto:
    return Labirinto([[c == "#" for c in linha] for linha in MAPA],
                     Coordenada(1, 1), Coordenada(5, 1), distancia_minima=10)


def jogador_em(lab: Labirinto, coluna: int, linha: int) -> Jogador:
    x, y = lab.centro_do_tile(Coordenada(coluna, linha))
    return Jogador(x, y + Jogador.ALTURA_DOS_PES)


def tile_de(jogador: Jogador, lab: Labirinto) -> tuple[int, int]:
    t = lab.tamanho_tile
    return int(jogador.x) // t, int(jogador.y - Jogador.ALTURA_HITBOX / 2) // t


def perigo(lab: Labirinto, tipo: TipoDePerigo, coluna: int, linha: int, defasagem: float = 0.0) -> Perigo:
    tile = Coordenada(coluna, linha)
    return Perigo(tipo, tile, lab.centro_do_tile(tile), defasagem)


def caixa(lab: Labirinto, coluna: int, linha: int) -> CaixaSurpresa:
    tile = Coordenada(coluna, linha)
    return CaixaSurpresa(tile, lab.centro_do_tile(tile))


def andar(fase: Fase, direcao: Vetor2, segundos: float) -> list:
    ocorrencias = []
    for _ in range(round(segundos / DT)):
        fase.avancar(DT, direcao)
        ocorrencias += fase.recolher_ocorrencias()
    return ocorrencias


def tipos(ocorrencias) -> list:
    return [o.tipo for o in ocorrencias]


def criar_fase(lab: Labirinto, jogador: Jogador, ambiente: Ambiente, tempo: float = 60.0) -> Fase:
    return Fase(1, 0, "teste", lab, jogador, Cronometro(tempo), 5.0, ambiente)


def avancar_ate_o_meio_do_fenomeno(amb: Ambiente, jogador: Jogador) -> None:
    intervalo, duracao, _ = CICLOS_DOS_FENOMENOS[amb.fenomeno]
    for _ in range(int((intervalo - duracao / 2) / DT)):
        amb.atualizar(DT, jogador)


class TesteMovimento(unittest.TestCase):
    def test_sem_aderencia_para_na_hora(self):
        lab = labirinto()
        j = jogador_em(lab, 1, 3)
        for _ in range(10):
            j.mover(Vetor2(1, 0), DT, lab)
        x = j.x
        j.mover(Vetor2(), DT, lab)
        self.assertEqual(j.x, x)
        self.assertFalse(j.esta_andando)

    def test_chao_escorregadio_continua_andando_depois_de_soltar(self):
        lab = labirinto()
        j = jogador_em(lab, 1, 3)
        escorregadio = Locomocao(aderencia=3.2)
        for _ in range(30):
            j.mover(Vetor2(1, 0), DT, lab, escorregadio)
        x = j.x
        for _ in range(5):
            j.mover(Vetor2(), DT, lab, escorregadio)
        self.assertGreater(j.x, x + 5)

    def test_terremoto_inverte_controles(self):
        lab = labirinto()
        j = jogador_em(lab, 3, 3)
        x = j.x
        for _ in range(5):
            j.mover(Vetor2(1, 0), DT, lab, Locomocao(invertido=True))
        self.assertLess(j.x, x)

    def test_intencao_forcada_ignora_o_controle(self):
        lab = labirinto()
        j = jogador_em(lab, 3, 3)
        x = j.x
        for _ in range(10):
            j.mover(Vetor2(), DT, lab, Locomocao(intencao_forcada=Vetor2(1, 0)))
        self.assertGreater(j.x, x)

    def test_nunca_atravessa_parede_e_avisa_que_bateu(self):
        lab = labirinto()
        j = jogador_em(lab, 1, 1)
        for _ in range(120):
            j.mover(Vetor2(1, 0), DT, lab, Locomocao(multiplicador=3, arrasto=Vetor2(300, 0)))
        self.assertFalse(lab.colide(j.caixa_de_colisao()))
        self.assertLess(j.x, 2 * lab.tamanho_tile)
        self.assertTrue(j.bateu)

    def test_salto_em_arco_por_cima_da_parede(self):
        lab = labirinto()
        j = jogador_em(lab, 1, 1)
        x, y = lab.centro_do_tile(Coordenada(3, 1))
        self.assertFalse(j.saltar(lab.tamanho_tile * 2 + 28, y, 0.4, lab), "nao pode cair dentro da parede")
        self.assertTrue(j.saltar(x, y + Jogador.ALTURA_DOS_PES, 0.4, lab))
        alturas = []
        for _ in range(30):
            j.mover(Vetor2(-1, 0), DT, lab)  # controle ignorado no ar
            alturas.append(j.altura_do_salto)
        self.assertFalse(j.pulando)
        self.assertGreater(max(alturas), 0.9)
        self.assertEqual(tile_de(j, lab), (3, 1))


class TesteMolaDeParede(unittest.TestCase):
    def ambiente_com_mola(self, lab: Labirinto) -> Ambiente:
        t = lab.tamanho_tile
        molas = [MolaDeParede(Coordenada(1, 1), Direcao.DIREITA, Coordenada(3, 1), t),
                 MolaDeParede(Coordenada(3, 1), Direcao.ESQUERDA, Coordenada(1, 1), t)]
        return Ambiente(lab, molas=molas)

    def test_andar_contra_a_mola_pula_para_o_outro_lado(self):
        lab = labirinto()
        fase = criar_fase(lab, jogador_em(lab, 1, 1), self.ambiente_com_mola(lab))
        ocorrencias = andar(fase, Vetor2(1, 0), 0.4)
        self.assertEqual(tipos(ocorrencias).count(TipoDeOcorrencia.PULOU), 1)
        andar(fase, Vetor2(), 0.6)
        self.assertEqual(tile_de(fase.jogador, lab), (3, 1))

    def test_nao_volta_sozinho_e_da_para_voltar_andando_contra(self):
        lab = labirinto()
        fase = criar_fase(lab, jogador_em(lab, 1, 1), self.ambiente_com_mola(lab))
        andar(fase, Vetor2(1, 0), 0.4)
        andar(fase, Vetor2(), 0.6)
        self.assertEqual(tile_de(fase.jogador, lab), (3, 1), "a mola do outro lado nao dispara sozinha")
        ocorrencias = andar(fase, Vetor2(-1, 0), 0.4)
        self.assertIn(TipoDeOcorrencia.PULOU, tipos(ocorrencias))
        andar(fase, Vetor2(), 0.6)
        self.assertEqual(tile_de(fase.jogador, lab), (1, 1))

    def test_passar_ao_lado_nao_dispara(self):
        lab = labirinto()
        fase = criar_fase(lab, jogador_em(lab, 1, 1), self.ambiente_com_mola(lab))
        self.assertNotIn(TipoDeOcorrencia.PULOU, tipos(andar(fase, Vetor2(0, 1), 0.6)))


class TestePerigos(unittest.TestCase):
    def test_agua_congela_e_blusa_protege(self):
        lab = labirinto()
        amb = Ambiente(lab, perigos=[perigo(lab, TipoDePerigo.AGUA, 1, 2)])
        fase = criar_fase(lab, jogador_em(lab, 1, 1), amb)
        self.assertIn(TipoDeOcorrencia.CONGELOU, tipos(andar(fase, Vetor2(0, 1), 0.5)))
        y = fase.jogador.y
        andar(fase, Vetor2(0, 1), 1.0)
        self.assertEqual(fase.jogador.y, y)  # congelado nao anda

        amb2 = Ambiente(lab, perigos=[perigo(lab, TipoDePerigo.AGUA, 1, 2)])
        amb2.aplicar_premio(TipoDeItem.BLUSA)
        fase2 = criar_fase(lab, jogador_em(lab, 1, 1), amb2)
        self.assertNotIn(TipoDeOcorrencia.CONGELOU, tipos(andar(fase2, Vetor2(0, 1), 0.5)))

    def test_placa_de_gelo_desliza_ate_bater_na_parede(self):
        lab = labirinto()
        amb = Ambiente(lab, perigos=[perigo(lab, TipoDePerigo.GELO, 2, 3)])
        fase = criar_fase(lab, jogador_em(lab, 1, 3), amb)
        ocorrencias = andar(fase, Vetor2(1, 0), 0.3)  # so encosta na placa e solta
        self.assertIn(TipoDeOcorrencia.COMECOU_A_DESLIZAR, tipos(ocorrencias))
        self.assertTrue(amb.deslizando)
        y = fase.jogador.y
        andar(fase, Vetor2(0, -1), 0.1)  # apertar para cima nao adianta enquanto desliza
        self.assertEqual(fase.jogador.y, y)
        andar(fase, Vetor2(), 1.5)
        self.assertFalse(amb.deslizando)
        self.assertEqual(tile_de(fase.jogador, lab), (5, 3))

    def test_blusa_nao_desliza_no_gelo(self):
        lab = labirinto()
        amb = Ambiente(lab, perigos=[perigo(lab, TipoDePerigo.GELO, 2, 3)])
        amb.aplicar_premio(TipoDeItem.BLUSA)
        fase = criar_fase(lab, jogador_em(lab, 1, 3), amb)
        self.assertNotIn(TipoDeOcorrencia.COMECOU_A_DESLIZAR, tipos(andar(fase, Vetor2(1, 0), 0.5)))

    def test_fogo_tira_coracao_e_deixa_descontrolado(self):
        lab = labirinto()
        amb = Ambiente(lab, perigos=[perigo(lab, TipoDePerigo.FOGO, 3, 3)], sorteio=random.Random(3))
        fase = criar_fase(lab, jogador_em(lab, 1, 3), amb, tempo=60)
        ocorrencias = andar(fase, Vetor2(1, 0), 0.6)
        queimaduras = [o for o in ocorrencias if o.tipo is TipoDeOcorrencia.QUEIMOU]
        self.assertEqual(len(queimaduras), 1)
        self.assertEqual(queimaduras[0].dano, 1)
        self.assertTrue(amb.condicao_ativa(Condicao.QUEIMANDO))
        self.assertIsNotNone(amb.locomocao().intencao_forcada)
        posicoes = set()
        for _ in range(40):  # sem apertar nada, ele continua correndo
            fase.avancar(DT, Vetor2())
            posicoes.add((round(fase.jogador.x), round(fase.jogador.y)))
        self.assertGreater(len(posicoes), 10)
        self.assertGreater(fase.tempo_restante, 58, "fogo agora tira coracao, nao tempo")

    def test_flauta_apaga_o_fogo(self):
        lab = labirinto()
        amb = Ambiente(lab, perigos=[perigo(lab, TipoDePerigo.FOGO, 3, 3)])
        amb.aplicar_premio(TipoDeItem.FLAUTA)
        fase = criar_fase(lab, jogador_em(lab, 1, 3), amb)
        self.assertNotIn(TipoDeOcorrencia.QUEIMOU, tipos(andar(fase, Vetor2(1, 0), 1.0)))

    def test_teia_prende_ate_acertar_as_4_setas_em_ordem(self):
        lab = labirinto()
        teia = perigo(lab, TipoDePerigo.TEIA, 2, 3)
        amb = Ambiente(lab, perigos=[teia], sorteio=random.Random(1))
        fase = criar_fase(lab, jogador_em(lab, 1, 3), amb)
        self.assertIn(TipoDeOcorrencia.FICOU_PRESO, tipos(andar(fase, Vetor2(1, 0), 0.4)))
        desafio = amb.desafio_da_teia
        self.assertEqual(len(desafio.sequencia), 4)
        x = fase.jogador.x
        andar(fase, Vetor2(1, 0), 3.0)
        self.assertEqual(fase.jogador.x, x, "sem limite de tempo: continua preso")

        sequencia = desafio.sequencia
        errada = next(d for d in Direcao if d is not sequencia[1])
        fase.apertar(sequencia[0])
        fase.apertar(errada)
        self.assertEqual(desafio.acertos, 0, "errou: volta do comeco")
        self.assertIn(TipoDeOcorrencia.TECLA_ERRADA, tipos(fase.recolher_ocorrencias()))

        for direcao in sequencia:
            fase.apertar(direcao)
        self.assertIn(TipoDeOcorrencia.SOLTOU_DA_TEIA, tipos(fase.recolher_ocorrencias()))
        self.assertIsNone(amb.desafio_da_teia)
        self.assertFalse(amb.travado)
        self.assertFalse(teia.ativo)
        andar(fase, Vetor2(1, 0), 0.3)
        self.assertGreater(fase.jogador.x, x)

    def test_apertar_fora_da_teia_nao_faz_nada(self):
        lab = labirinto()
        fase = criar_fase(lab, jogador_em(lab, 1, 3), Ambiente(lab))
        fase.apertar(Direcao.CIMA)
        self.assertEqual(fase.recolher_ocorrencias(), ())

    def test_areia_movedica_deixa_lento_e_cafe_anula(self):
        lab = labirinto()
        amb = Ambiente(lab, perigos=[perigo(lab, TipoDePerigo.AREIA_MOVEDICA, 1, 3)])
        amb.atualizar(DT, jogador_em(lab, 1, 3))
        self.assertTrue(amb.na_areia)
        self.assertAlmostEqual(amb.locomocao().multiplicador, 0.4)
        amb.aplicar_premio(TipoDeItem.CAFE)
        self.assertGreater(amb.locomocao().multiplicador, 1.0)

    def test_estrela_ignora_tudo(self):
        lab = labirinto()
        amb = Ambiente(lab, perigos=[perigo(lab, TipoDePerigo.TEIA, 2, 3), perigo(lab, TipoDePerigo.FOGO, 3, 3)],
                       fenomeno=Fenomeno.TERREMOTO)
        amb.aplicar_premio(TipoDeItem.ESTRELA)
        fase = criar_fase(lab, jogador_em(lab, 1, 3), amb)
        ocorrencias = tipos(andar(fase, Vetor2(1, 0), 1.0))
        self.assertNotIn(TipoDeOcorrencia.FICOU_PRESO, ocorrencias)
        self.assertNotIn(TipoDeOcorrencia.QUEIMOU, ocorrencias)


class TesteCaixaSurpresa(unittest.TestCase):
    def test_caixa_sorteia_um_premio_do_mapa_e_aplica(self):
        lab = labirinto()
        premios = ((TipoDeItem.CAFE, 1),)
        amb = Ambiente(lab, caixas=[caixa(lab, 2, 3)], premios=premios)
        fase = criar_fase(lab, jogador_em(lab, 1, 3), amb)
        ocorrencias = [o for o in andar(fase, Vetor2(1, 0), 0.4) if o.tipo is TipoDeOcorrencia.CAIXA_ABERTA]
        self.assertEqual(len(ocorrencias), 1, "a caixa abre uma vez so")
        self.assertIs(ocorrencias[0].item, TipoDeItem.CAFE)
        self.assertTrue(amb.condicao_ativa(Condicao.CAFE))
        self.assertTrue(amb.caixas[0].aberta)

    def test_relogio_da_tempo_sem_passar_do_total(self):
        lab = labirinto()
        amb = Ambiente(lab, caixas=[caixa(lab, 1, 3)], premios=((TipoDeItem.RELOGIO, 1),))
        fase = criar_fase(lab, jogador_em(lab, 1, 3), amb, tempo=30)
        andar(fase, Vetor2(), 0.1)
        self.assertGreater(fase.tempo_restante, 29.8)
        self.assertLessEqual(fase.tempo_restante, 30)

    def test_lanterna_aumenta_visao_e_cafe_acelera(self):
        amb = Ambiente(labirinto())
        amb.aplicar_premio(TipoDeItem.LANTERNA)
        amb.aplicar_premio(TipoDeItem.CAFE)
        self.assertAlmostEqual(amb.multiplicador_de_visao(), Ambiente.VISAO_LANTERNA)
        self.assertAlmostEqual(amb.locomocao().multiplicador, Ambiente.VELOCIDADE_CAFE)

    def test_efeito_acaba_com_o_tempo(self):
        lab = labirinto()
        amb = Ambiente(lab)
        amb.aplicar_premio(TipoDeItem.CAFE)
        j = jogador_em(lab, 1, 3)
        for _ in range(int(9 / DT)):
            amb.atualizar(DT, j)
        self.assertFalse(amb.condicao_ativa(Condicao.CAFE))

    def test_itens_comuns_sao_relogio_coracao_e_estrela(self):
        self.assertEqual({tipo for tipo, _ in ITENS_COMUNS},
                         {TipoDeItem.RELOGIO, TipoDeItem.CORACAO, TipoDeItem.ESTRELA})
        self.assertNotIn("BANANA", TipoDeItem.__members__)

    def test_coracao_cura_e_com_vida_cheia_some(self):
        partida = Partida(_FabricaCalma())
        partida.vida.perder(1)
        partida.fase.aplicar_premio(TipoDeItem.CORACAO)
        partida.atualizar(DT, Vetor2())
        self.assertEqual(partida.vida.coracoes, partida.vida.maximo)

        partida.fase.ganhar_tempo(-20)
        antes = partida.fase.tempo_restante
        partida.fase.aplicar_premio(TipoDeItem.CORACAO)
        partida.atualizar(DT, Vetor2())
        self.assertEqual(partida.vida.coracoes, partida.vida.maximo)
        self.assertAlmostEqual(partida.fase.tempo_restante, antes - DT, places=3, msg="vida cheia: nao vira tempo")

    def test_roleta_evita_repetir(self):
        lab = labirinto()
        premios = ((TipoDeItem.RELOGIO, 1), (TipoDeItem.CORACAO, 1), (TipoDeItem.ESTRELA, 1))
        amb = Ambiente(lab, premios=premios, sorteio=random.Random(5))
        sorteados = [amb.sortear_premio() for _ in range(300)]
        repetidos = sum(a is b for a, b in zip(sorteados, sorteados[1:]))
        self.assertLess(repetidos / 299, 0.12, "sem memoria seria ~33% de repeticao seguida")
        self.assertEqual(set(sorteados), {t for t, _ in premios})

    def test_historico_da_roleta_passa_de_uma_fase_para_outra(self):
        fabrica = FabricaDeFases(GeradorBacktracker(), Dificuldade(), ["vento"], random.Random(3),
                                 biomas={"vento": Bioma.ventoso()})
        primeira = fabrica.criar(1).ambiente.sortear_premio()
        self.assertIn(primeira, fabrica.criar(2).ambiente._historico.ultimos)  # noqa: SLF001


class TesteFenomenos(unittest.TestCase):
    def test_ciclo_aviso_ativo_e_calmo(self):
        ciclo = CicloDeEvento(10, 3, 2)
        ciclo.atualizar(5.5)
        self.assertTrue(ciclo.em_aviso)
        self.assertTrue(ciclo.atualizar(1.6))  # comecou agora (t = 7.1)
        self.assertTrue(ciclo.ativo)
        ciclo.atualizar(3.0)  # t = 10.1 -> novo ciclo
        self.assertFalse(ciclo.ativo)

    def test_forcar_fenomeno_comeca_na_hora(self):
        lab = labirinto()
        amb = Ambiente(lab, fenomeno=Fenomeno.TERREMOTO)
        amb.forcar_fenomeno()
        ocorrencias = amb.atualizar(DT, jogador_em(lab, 1, 3))
        self.assertIn(TipoDeOcorrencia.FENOMENO_COMECOU, tipos(ocorrencias))
        self.assertTrue(amb.ciclo.ativo)

    def test_tempestade_deixa_lento_e_apagao_escurece(self):
        lab = labirinto()
        j = jogador_em(lab, 1, 3)
        tempestade = Ambiente(lab, fenomeno=Fenomeno.TEMPESTADE_DE_AREIA)
        apagao = Ambiente(lab, fenomeno=Fenomeno.APAGAO)
        avancar_ate_o_meio_do_fenomeno(tempestade, j)
        avancar_ate_o_meio_do_fenomeno(apagao, j)
        self.assertLess(tempestade.locomocao().multiplicador, 0.6)
        self.assertLess(apagao.multiplicador_de_visao(), 0.5)

    def test_tempestade_de_gelo_deixa_lento_e_cafe_protege(self):
        lab = labirinto()
        j = jogador_em(lab, 1, 3)
        nevasca = Ambiente(lab, fenomeno=Fenomeno.TEMPESTADE_DE_GELO)
        avancar_ate_o_meio_do_fenomeno(nevasca, j)
        self.assertAlmostEqual(nevasca.locomocao().multiplicador, 1 - Ambiente.LENTIDAO_NEVASCA)
        nevasca.aplicar_premio(TipoDeItem.CAFE)
        self.assertTrue(nevasca.fenomeno_neutralizado)
        self.assertAlmostEqual(nevasca.locomocao().multiplicador, Ambiente.VELOCIDADE_CAFE)

    def test_rajada_empurra(self):
        lab = labirinto()
        amb = Ambiente(lab, fenomeno=Fenomeno.RAJADA, sorteio=random.Random(1))
        avancar_ate_o_meio_do_fenomeno(amb, jogador_em(lab, 1, 3))
        self.assertFalse(amb.locomocao().arrasto.eh_nulo)

    def test_fenomenos_mais_espacados_principalmente_a_erupcao(self):
        intervalos = {f: ciclo[0] for f, ciclo in CICLOS_DOS_FENOMENOS.items()}
        self.assertGreaterEqual(intervalos[Fenomeno.ERUPCAO], 11.0)
        self.assertLessEqual(Ambiente.JATOS_DE_LAVA, 3)
        self.assertLessEqual(Ambiente.ALCANCE_DA_ERUPCAO, 3)
        self.assertIn(Fenomeno.TEMPESTADE_DE_GELO, intervalos)


# ======================================================================
class _AmbienteEmChamas(Ambiente):
    """Queima o jogador a cada quadro (para testar os coracoes)."""

    def atualizar(self, dt, jogador):
        return [Ocorrencia(TipoDeOcorrencia.QUEIMOU, dano=1)]


class _FabricaFixa:
    em_arena = False

    def __init__(self, vitrine=False):
        self.vitrine = vitrine
        self.dificuldade = Dificuldade()

    def criar(self, numero):
        lab = labirinto()
        return Fase(numero, 0, "teste", lab, jogador_em(lab, 1, 3), Cronometro(60), 5.0, _AmbienteEmChamas(lab))


class _FabricaCalma(_FabricaFixa):
    def criar(self, numero):
        lab = labirinto()
        return Fase(numero, 0, "teste", lab, jogador_em(lab, 1, 3), Cronometro(60), 5.0, Ambiente(lab))


class _Ouvinte(OuvinteDaPartida):
    def __init__(self):
        self.fim = None

    def ao_perder_todas_as_vidas(self, fase_alcancada):
        self.fim = fase_alcancada


class TesteVida(unittest.TestCase):
    def test_tres_queimaduras_acabam_a_partida(self):
        partida = Partida(_FabricaFixa())
        ouvinte = _Ouvinte()
        partida.inscrever(ouvinte)
        for _ in range(2):
            partida.atualizar(DT, Vetor2())
        self.assertEqual(partida.vida.coracoes, 1)
        self.assertIs(partida.situacao, SituacaoDaPartida.EM_ANDAMENTO)
        partida.atualizar(DT, Vetor2())
        self.assertIs(partida.situacao, SituacaoDaPartida.SEM_VIDA)
        self.assertEqual(ouvinte.fim, 1)

    def test_apresentacao_nunca_acaba(self):
        partida = Partida(_FabricaFixa(vitrine=True))
        for _ in range(10):
            partida.atualizar(DT, Vetor2())
        self.assertIs(partida.situacao, SituacaoDaPartida.EM_ANDAMENTO)
        self.assertGreater(partida.vida.coracoes, 0)


class TesteBiomas(unittest.TestCase):
    def test_mesma_semente_mesmas_coisas_e_nada_na_entrada_ou_saida(self):
        lab = GeradorBacktracker().gerar(12, 8, random.Random(5))
        a = Bioma.gelado().criar_ambiente(lab, random.Random(9))
        b = Bioma.gelado().criar_ambiente(lab, random.Random(9))
        self.assertEqual([c.tile for c in a.caixas], [c.tile for c in b.caixas])
        self.assertEqual([(p.tipo, p.tile) for p in a.perigos], [(p.tipo, p.tile) for p in b.perigos])
        ocupados = [c.tile for c in a.caixas] + [p.tile for p in a.perigos]
        self.assertEqual(len(ocupados), len(set(ocupados)))
        self.assertNotIn(lab.entrada, ocupados)
        self.assertNotIn(lab.saida, ocupados)
        self.assertEqual({p.tipo for p in a.perigos}, {TipoDePerigo.AGUA, TipoDePerigo.GELO})
        self.assertTrue({TipoDeItem.BLUSA, TipoDeItem.CAFE} <= set(a.premios))
        self.assertIsNone(a.locomocao().aderencia, "o gelo nao escorrega mais no mapa inteiro")

    def test_gelo_tem_tempestade_de_gelo(self):
        lab = GeradorBacktracker().gerar(12, 8, random.Random(5))
        self.assertIs(Bioma.gelado().criar_ambiente(lab, random.Random(1), fase=5).fenomeno,
                      Fenomeno.TEMPESTADE_DE_GELO)

    def test_itens_exclusivos_de_cada_mapa(self):
        exclusivos = {"gelo": (Bioma.gelado(), {TipoDeItem.BLUSA, TipoDeItem.CAFE}),
                      "deserto": (Bioma.desertico(), {TipoDeItem.FLAUTA, TipoDeItem.TAPETE, TipoDeItem.GENIO}),
                      "masmorra": (Bioma.masmorra(), {TipoDeItem.LANTERNA, TipoDeItem.BUSSOLA}),
                      "fogo": (Bioma.vulcanico(), {TipoDeItem.EXTINTOR, TipoDeItem.BOTA}),
                      "terra": (Bioma.terroso(), {TipoDeItem.BROCA, TipoDeItem.CAPACETE}),
                      "vento": (Bioma.ventoso(), {TipoDeItem.GUARDA_CHUVA, TipoDeItem.PIPA})}
        comuns = {TipoDeItem.RELOGIO, TipoDeItem.CORACAO, TipoDeItem.ESTRELA}
        for nome, (bioma, proprios) in exclusivos.items():
            self.assertEqual({tipo for tipo, _ in bioma.premios()}, comuns | proprios, nome)

    def test_molas_so_na_masmorra_so_de_ida_e_longe_do_portal(self):
        lab = GeradorBacktracker().gerar(14, 10, random.Random(5))
        for bioma in (Bioma.gelado(), Bioma.desertico(), Bioma.vulcanico(), Bioma.terroso(), Bioma.ventoso()):
            self.assertEqual(bioma.criar_ambiente(lab, random.Random(1), fase=8).molas, ())
        amb = Bioma.masmorra().criar_ambiente(lab, random.Random(1), fase=8)
        self.assertGreaterEqual(len(amb.molas), 1)
        ida = {(m.tile, m.destino) for m in amb.molas}
        saida = lab.saida
        for mola in amb.molas:
            a, b = mola.tile, mola.destino
            meio = ((a.coluna + b.coluna) // 2, (a.linha + b.linha) // 2)
            self.assertFalse(lab.eh_parede(*a))
            self.assertFalse(lab.eh_parede(*b))
            self.assertTrue(lab.eh_parede(*meio))
            self.assertNotIn((b, a), ida, "mola so de ida: nao tem a de volta")
            for tile in (a, b):
                self.assertGreaterEqual(abs(tile.coluna - saida.coluna) + abs(tile.linha - saida.linha),
                                        Bioma.masmorra().distancia_do_portal)

    def test_caixas_bem_distribuidas_e_longe_umas_das_outras(self):
        lab = GeradorBacktracker().gerar(30, 20, random.Random(7))
        bioma = Bioma.ventoso()
        chao = sum(not lab.eh_parede(c, l) for l in range(lab.linhas) for c in range(lab.colunas))
        for semente in range(5):
            caixas = [c.tile for c in bioma.criar_ambiente(lab, random.Random(semente), fase=8).caixas]
            self.assertLessEqual(len(caixas), 2 + chao // bioma.tiles_por_caixa)
            self.assertGreaterEqual(len(caixas), 6, "mapa grande: varias caixas")
            for i, a in enumerate(caixas):
                for b in caixas[i + 1:]:
                    self.assertGreaterEqual(abs(a.coluna - b.coluna) + abs(a.linha - b.linha),
                                            bioma.distancia_entre_caixas)

    def test_placas_de_gelo_espalhadas(self):
        lab = GeradorBacktracker().gerar(30, 20, random.Random(2))
        regra = next(r for r in Bioma.gelado().perigos if r.tipo is TipoDePerigo.GELO)
        amb = Bioma.gelado().criar_ambiente(lab, random.Random(3), fase=12)
        placas = [p.tile for p in amb.perigos if p.tipo is TipoDePerigo.GELO]
        trechos: list[set] = []  # junta placas vizinhas em trechos
        for tile in placas:
            vizinhos = [t for t in trechos if any(abs(tile.coluna - o.coluna) + abs(tile.linha - o.linha) == 1
                                                  for o in t)]
            novo = {tile}.union(*vizinhos)
            trechos = [t for t in trechos if t not in vizinhos] + [novo]
        for i, a in enumerate(trechos):
            self.assertLessEqual(len(a), regra.tamanho_maximo)
            for b in trechos[i + 1:]:
                menor = min(abs(x.coluna - y.coluna) + abs(x.linha - y.linha) for x in a for y in b)
                self.assertGreaterEqual(menor, regra.distancia_minima)

    def test_placas_de_gelo_formam_trechos(self):
        lab = GeradorBacktracker().gerar(20, 14, random.Random(2))
        amb = Bioma.gelado().criar_ambiente(lab, random.Random(3), fase=12)
        placas = {p.tile for p in amb.perigos if p.tipo is TipoDePerigo.GELO}
        vizinhas = [t for t in placas if any(Coordenada(t.coluna + dx, t.linha + dy) in placas
                                             for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))]
        self.assertGreater(len(vizinhas), 0)

    def test_fabrica_usa_o_bioma_do_tema(self):
        biomas = {"deserto": Bioma.desertico(), "fogo": Bioma.vulcanico()}
        deserto = FabricaDeFases(GeradorBacktracker(), Dificuldade(), ["deserto"], random.Random(3), biomas=biomas)
        fase = deserto.criar(5)
        self.assertIs(fase.ambiente.fenomeno, Fenomeno.TEMPESTADE_DE_AREIA)
        self.assertEqual({p.tipo for p in fase.ambiente.perigos}, {TipoDePerigo.AREIA_MOVEDICA})
        self.assertIn(TipoDeItem.FLAUTA, fase.ambiente.premios)
        self.assertAlmostEqual(fase.raio_visao, Dificuldade().raio_visao(5) * 1.25, msg="sol forte: mais luz")

        fogo = FabricaDeFases(GeradorBacktracker(), Dificuldade(), ["fogo"], random.Random(3), biomas=biomas).criar(5)
        self.assertIs(fogo.ambiente.fenomeno, Fenomeno.ERUPCAO)
        self.assertEqual({p.tipo for p in fogo.ambiente.perigos}, {TipoDePerigo.FOGO})
        self.assertNotIn(TipoDeItem.FLAUTA, fogo.ambiente.premios, "a flauta agora e so do deserto")

    def test_vitrine_tudo_perto_da_entrada_e_sem_limite_de_tempo(self):
        for tema, bioma in (("gelo", Bioma.gelado()), ("deserto", Bioma.desertico()), ("fogo", Bioma.vulcanico()),
                            ("masmorra", Bioma.masmorra())):
            fabrica = FabricaDeFases(GeradorBacktracker(), Dificuldade(), [tema], random.Random(4),
                                     biomas={tema: bioma}, vitrine=True)
            fase = fabrica.criar(1)
            self.assertTrue(fase.tempo_ilimitado)
            self.assertFalse(fase.avancar(5.0, Vetor2()))
            self.assertFalse(fase.tempo_esgotado)
            tipos_esperados = {regra.tipo for regra in bioma.perigos}
            self.assertEqual({p.tipo for p in fase.ambiente.perigos}, tipos_esperados)
            entrada = fase.labirinto.entrada
            perto = [abs(p.tile.coluna - entrada.coluna) + abs(p.tile.linha - entrada.linha) for p in fase.ambiente.perigos]
            self.assertLess(min(perto), 6)
            self.assertEqual(len(fase.ambiente.caixas), 3)


class TesteMapaACadaTresFases(unittest.TestCase):
    TEMAS = ["gelo", "fogo", "deserto", "masmorra", "terra", "vento"]

    def test_mapa_so_muda_a_cada_3_fases_e_nunca_repete_o_anterior(self):
        for semente in range(20):
            fabrica = FabricaDeFases(GeradorBacktracker(), Dificuldade(), self.TEMAS, random.Random(semente))
            temas = [fabrica.criar(numero).tema for numero in range(1, 13)]
            blocos = [temas[i:i + 3] for i in range(0, 12, 3)]
            for bloco in blocos:
                self.assertEqual(len(set(bloco)), 1, f"mesmo mapa nas 3 fases: {temas}")
            for anterior, seguinte in zip(blocos, blocos[1:]):
                self.assertNotEqual(anterior[0], seguinte[0], f"o mapa troca a cada bloco: {temas}")

    def test_etapa_no_mapa(self):
        fabrica = FabricaDeFases(GeradorBacktracker(), Dificuldade(), self.TEMAS, random.Random(1))
        fases = [fabrica.criar(numero) for numero in range(1, 8)]
        self.assertEqual([f.etapa_no_mapa for f in fases], [1, 2, 3, 1, 2, 3, 1])
        self.assertEqual([f.ultima_no_mapa for f in fases], [False, False, True, False, False, True, False])

    def test_partida_segue_a_regra_ao_avancar(self):
        partida = Partida(FabricaDeFases(GeradorBacktracker(), Dificuldade(), self.TEMAS, random.Random(5)))
        temas = [partida.fase.tema]
        for _ in range(5):
            partida._concluir_fase()  # noqa: SLF001
            partida.avancar_para_proxima_fase()
            temas.append(partida.fase.tema)
        self.assertEqual(temas[0], temas[1])
        self.assertEqual(temas[1], temas[2])
        self.assertNotEqual(temas[2], temas[3])
        self.assertEqual(temas[3], temas[5])

    def test_com_um_mapa_so_continua_funcionando(self):
        fabrica = FabricaDeFases(GeradorBacktracker(), Dificuldade(), ["gelo"], random.Random(1))
        self.assertEqual({fabrica.criar(n).tema for n in range(1, 8)}, {"gelo"})


class TesteDificuldade(unittest.TestCase):
    def test_tempo_por_nivel_e_insano_sempre_possivel(self):
        niveis = [Dificuldade.do_nivel(n) for n in NivelDeDificuldade]
        tempos = [d.tempo_limite(1, 2000, 200) for d in niveis]
        self.assertEqual(tempos, sorted(tempos, reverse=True))  # facil > normal > dificil > insano
        insano = Dificuldade.do_nivel(NivelDeDificuldade.INSANO)
        for fase in range(1, 40):
            self.assertGreaterEqual(insano.tempo_limite(fase, 2000, 200), 10 * insano.fator_tempo_absoluto)

    def test_normal_igual_ao_padrao(self):
        self.assertEqual(Dificuldade.do_nivel(NivelDeDificuldade.NORMAL), Dificuldade())

    def test_insano_sem_lanterna_na_roleta_e_com_mais_perigos(self):
        lab = GeradorBacktracker().gerar(14, 10, random.Random(2))
        normal = Bioma.masmorra().criar_ambiente(lab, random.Random(4), Dificuldade(), fase=12)
        insano = Bioma.masmorra().criar_ambiente(lab, random.Random(4), Dificuldade.do_nivel(NivelDeDificuldade.INSANO),
                                                 fase=12)
        self.assertGreater(len(insano.perigos), len(normal.perigos))
        self.assertIn(TipoDeItem.LANTERNA, normal.premios)
        self.assertNotIn(TipoDeItem.LANTERNA, insano.premios)


class TesteCurvaDeDificuldade(unittest.TestCase):
    def setUp(self):
        self.d = Dificuldade()

    def folga_por_tile(self, fase: int) -> float:
        """Segundos dados para cada tile do caminho perfeito (quanto maior, mais tranquilo)."""
        return self.d.tempo_limite(fase, 30 * 56, 210) / 30

    def test_primeiras_fases_tranquilas_e_depois_piora_ate_a_fase_10(self):
        folgas = [self.folga_por_tile(f) for f in range(1, 16)]
        self.assertEqual(folgas[0], folgas[2], "fases 1 a 3 com a mesma folga (tranquilas)")
        for anterior, seguinte in zip(folgas[2:10], folgas[3:10]):
            self.assertLess(seguinte, anterior, "da fase 3 a 10 o tempo aperta a cada fase")
        self.assertEqual(folgas[9], folgas[14], "depois da 10 fica no maximo")
        self.assertGreater(folgas[0], 1.6 * folgas[9])

    def test_luz_diminui_e_perigos_aumentam(self):
        self.assertGreater(self.d.raio_visao(1), self.d.raio_visao(6))
        self.assertGreater(self.d.raio_visao(6), self.d.raio_visao(10))
        self.assertLessEqual(self.d.perigos(1), 0.6)
        self.assertGreater(self.d.perigos(10), self.d.perigos(6))

    def test_cada_nivel_e_mais_dificil_que_o_anterior(self):
        niveis = [Dificuldade.do_nivel(n) for n in NivelDeDificuldade]
        for fase in (1, 5, 10):
            tempos = [d.tempo_limite(fase, 30 * 56, 210) for d in niveis]
            self.assertEqual(tempos, sorted(tempos, reverse=True), f"menos tempo a cada nivel (fase {fase})")
            luzes = [d.raio_visao(fase) for d in niveis]
            self.assertEqual(luzes, sorted(luzes, reverse=True), f"menos luz a cada nivel (fase {fase})")
            perigos = [d.perigos(fase) for d in niveis]
            self.assertEqual(perigos, sorted(perigos), f"mais perigos a cada nivel (fase {fase})")
        self.assertEqual([d.monstros(3) for d in niveis], [0, 0, 1, 3], "monstros chegam mais cedo")
        self.assertEqual([d.coracoes for d in niveis], [3, 3, 3, 2])
        self.assertEqual([d.cura_por_fase for d in niveis], [1, 1, 0, 0])
        tamanhos = [d.tamanho(1)[0] * d.tamanho(1)[1] for d in niveis]
        self.assertEqual(tamanhos, sorted(tamanhos), "labirinto comeca maior nos niveis dificeis")

    def test_insano_comeca_com_2_coracoes_e_dificil_nao_cura(self):
        for nivel, coracoes in ((NivelDeDificuldade.INSANO, 2), (NivelDeDificuldade.DIFICIL, 3)):
            fabrica = FabricaDeFases(GeradorBacktracker(), Dificuldade.do_nivel(nivel), ["terra"],
                                     random.Random(1), biomas={"terra": Bioma.terroso()})
            partida = Partida(fabrica)
            self.assertEqual(partida.vida.maximo, coracoes)
            partida.vida.perder(1)
            partida._concluir_fase()  # noqa: SLF001
            partida.avancar_para_proxima_fase()
            self.assertEqual(partida.vida.coracoes, coracoes - 1, "sair do labirinto nao devolve coracao")

    def test_labirinto_comeca_pequeno_e_cresce(self):
        tamanhos = [self.d.tamanho(f) for f in range(1, 40)]
        self.assertLess(tamanhos[0][0] * tamanhos[0][1], 50)
        areas = [c * l for c, l in tamanhos]
        self.assertEqual(areas, sorted(areas))
        self.assertEqual(tamanhos[-1], (30, 20), "chega no tamanho maximo")

    def test_sem_fenomenos_nas_fases_tranquilas_e_cada_vez_mais_frequentes(self):
        lab = GeradorBacktracker().gerar(10, 7, random.Random(1))
        for fase in (1, 2, 3):
            self.assertIsNone(Bioma.terroso().criar_ambiente(lab, random.Random(1), self.d, fase=fase).fenomeno)
        self.assertIs(Bioma.terroso().criar_ambiente(lab, random.Random(1), self.d, fase=4).fenomeno,
                      Fenomeno.TERREMOTO)
        self.assertGreater(self.d.ritmo_dos_fenomenos(4), self.d.ritmo_dos_fenomenos(12))

    def test_insano_tem_luz_fixa_e_facil_mais_luz(self):
        insano = Dificuldade.do_nivel(NivelDeDificuldade.INSANO)
        facil = Dificuldade.do_nivel(NivelDeDificuldade.FACIL)
        self.assertEqual(insano.raio_visao(1), insano.raio_visao(20))
        self.assertGreater(facil.raio_visao(12), self.d.raio_visao(12))


class TesteErupcao(unittest.TestCase):
    MAPA_ABERTO = ["#########", "#.......#", "#.......#", "#.......#", "#.......#", "#.......#", "#########"]

    def preparar(self):
        lab = Labirinto([[c == "#" for c in linha] for linha in self.MAPA_ABERTO],
                        Coordenada(1, 1), Coordenada(7, 5), distancia_minima=10)
        amb = Ambiente(lab, fenomeno=Fenomeno.ERUPCAO, sorteio=random.Random(2))
        jogador = jogador_em(lab, 4, 3)
        return lab, amb, jogador

    def test_marca_tiles_perto_do_jogador_no_aviso(self):
        lab, amb, jogador = self.preparar()
        self.assertEqual(amb.jatos_de_lava, ())
        while not amb.ciclo.em_aviso:
            amb.atualizar(DT, jogador)
        self.assertEqual(len(amb.jatos_de_lava), Ambiente.JATOS_DE_LAVA)
        for tile in amb.jatos_de_lava:
            self.assertFalse(lab.eh_parede(*tile))
            self.assertLessEqual(abs(tile.coluna - 4) + abs(tile.linha - 3), Ambiente.ALCANCE_DA_ERUPCAO)

    def test_lava_queima_quem_ficar_em_cima_e_flauta_protege(self):
        for com_flauta in (False, True):
            lab, amb, jogador = self.preparar()
            while not amb.ciclo.em_aviso:
                amb.atualizar(DT, jogador)
            if com_flauta:
                amb.aplicar_premio(TipoDeItem.FLAUTA)
            alvo = amb.jatos_de_lava[0]
            x, y = lab.centro_do_tile(alvo)
            jogador.posicionar(x, y + Jogador.ALTURA_DOS_PES, lab)
            ocorrencias = []
            for _ in range(int(3.0 / DT)):
                ocorrencias += amb.atualizar(DT, jogador)
            queimou = TipoDeOcorrencia.QUEIMOU in tipos(ocorrencias)
            self.assertEqual(queimou, not com_flauta)

    def test_fora_dos_jatos_nao_queima_e_tiles_somem_depois(self):
        lab, amb, jogador = self.preparar()
        while not amb.ciclo.em_aviso:
            amb.atualizar(DT, jogador)
        livres = [Coordenada(c, l) for l in range(1, 6) for c in range(1, 8)
                  if Coordenada(c, l) not in amb.jatos_de_lava]
        x, y = lab.centro_do_tile(livres[0])
        jogador.posicionar(x, y + Jogador.ALTURA_DOS_PES, lab)
        ocorrencias = []
        for _ in range(int(3.5 / DT)):
            ocorrencias += amb.atualizar(DT, jogador)
        self.assertNotIn(TipoDeOcorrencia.QUEIMOU, tipos(ocorrencias))
        self.assertFalse(amb.ciclo.ativo or amb.ciclo.em_aviso)
        self.assertEqual(amb.jatos_de_lava, ())


if __name__ == "__main__":
    unittest.main()
