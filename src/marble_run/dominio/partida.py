"""
partida.py - Fase, fabrica de fases e a Partida (corrida estilo roguelike).

Fluxo:  fase 1 -> (achou a saida) -> fase 2 (maior, menos tempo, menos luz)
                -> (tempo acabou)  -> fim da partida; ENTER = REBOOT com
                                      labirinto totalmente novo, de volta a fase 1.
"""
from __future__ import annotations

import random
from enum import Enum, auto
from typing import Callable, Sequence

from .contratos import OuvinteDaPartida
from .geometria import Vetor2
from .geradores import GeradorDeLabirinto
from .jogador import Jogador
from .labirinto import Labirinto
from .regras import Cronometro, Dificuldade, Placar, ResultadoDaFase


class Fase:
    """Um labirinto jogavel: mapa + jogador + cronometro (+ dados para exibir)."""

    def __init__(self, numero: int, semente: int, tema: str, labirinto: Labirinto,
                 jogador: Jogador, cronometro: Cronometro, raio_visao: float) -> None:
        self._numero = numero
        self._semente = semente
        self._tema = tema
        self._labirinto = labirinto
        self._jogador = jogador
        self._cronometro = cronometro
        self._raio_visao = raio_visao

    @property
    def numero(self) -> int:
        return self._numero

    @property
    def semente(self) -> int:
        return self._semente

    @property
    def tema(self) -> str:
        """Nome do tema visual sorteado (o dominio nao sabe como ele e desenhado)."""
        return self._tema

    @property
    def labirinto(self) -> Labirinto:
        return self._labirinto

    @property
    def jogador(self) -> Jogador:
        return self._jogador

    @property
    def raio_visao(self) -> float:
        return self._raio_visao

    @property
    def tempo_restante(self) -> float:
        return self._cronometro.restante

    @property
    def fracao_de_tempo(self) -> float:
        return self._cronometro.fracao_restante

    @property
    def tempo_esgotado(self) -> bool:
        return self._cronometro.esgotado

    def avancar(self, dt: float, intencao: Vetor2) -> bool:
        """Move o jogador e desconta o tempo. Devolve True se for hora de alertar."""
        self._jogador.mover(intencao, dt, self._labirinto)
        return self._cronometro.avancar(dt)

    def jogador_na_saida(self) -> bool:
        return self._jogador.caixa_de_colisao().intersecta(self._labirinto.area_da_saida())


class FabricaDeFases:
    """Factory: monta fases cada vez mais dificeis.

    Composicao: COMO gerar o mapa (GeradorDeLabirinto) e QUANTO dificultar
    (Dificuldade) sao objetos injetados - podem ser trocados sem mexer aqui.
    """

    LIMITE_SEMENTE = 1_000_000
    ALTURA_DOS_PES = 12  # o personagem nasce com os pes um pouco abaixo do centro do tile

    def __init__(self, gerador: GeradorDeLabirinto, dificuldade: Dificuldade,
                 temas: Sequence[str], sorteio: random.Random | None = None) -> None:
        if not temas:
            raise ValueError("informe ao menos um tema")
        self._gerador = gerador
        self._dificuldade = dificuldade
        self._temas = tuple(temas)
        self._sorteio = sorteio if sorteio is not None else random.SystemRandom()

    def criar(self, numero: int) -> Fase:
        semente = self._sorteio.randrange(self.LIMITE_SEMENTE)
        rng = random.Random(semente)  # mesma semente => mesmo labirinto e mesmo tema
        colunas, linhas = self._dificuldade.tamanho(numero)
        labirinto = self._gerador.gerar(colunas, linhas, rng)
        tema = rng.choice(self._temas)

        centro_x, centro_y = labirinto.centro_do_tile(labirinto.entrada)
        jogador = Jogador(centro_x, centro_y + self.ALTURA_DOS_PES)
        distancia = labirinto.distancia_minima * labirinto.tamanho_tile
        tempo = self._dificuldade.tempo_limite(numero, distancia, jogador.velocidade)
        return Fase(numero, semente, tema, labirinto, jogador, Cronometro(tempo),
                    self._dificuldade.raio_visao(numero))


class SituacaoDaPartida(Enum):
    EM_ANDAMENTO = auto()
    FASE_CONCLUIDA = auto()
    TEMPO_ESGOTADO = auto()


class Partida:
    """Uma corrida completa: fase 1, 2, 3... ate o tempo acabar.

    E a raiz do agregado: de fora ninguem mexe no cronometro, no placar ou na
    posicao do jogador. Tudo passa por `atualizar` e `avancar_para_proxima_fase`,
    que garantem as regras (ex.: nao da para pular de fase sem concluir a atual).
    Os acontecimentos sao avisados aos ouvintes (Observer), sem a Partida
    saber se alguem toca som, salva recorde ou mostra conquistas.
    """

    def __init__(self, fabrica: FabricaDeFases, placar: Placar | None = None) -> None:
        self._fabrica = fabrica
        self._placar = placar if placar is not None else Placar()
        self._ouvintes: list[OuvinteDaPartida] = []
        self._fase = fabrica.criar(1)
        self._situacao = SituacaoDaPartida.EM_ANDAMENTO
        self._ultimo_resultado: ResultadoDaFase | None = None

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------
    @property
    def fase(self) -> Fase:
        return self._fase

    @property
    def nivel(self) -> int:
        return self._fase.numero

    @property
    def pontos(self) -> int:
        return self._placar.pontos

    @property
    def situacao(self) -> SituacaoDaPartida:
        return self._situacao

    @property
    def ultimo_resultado(self) -> ResultadoDaFase | None:
        return self._ultimo_resultado

    # ------------------------------------------------------------------
    # Comandos
    # ------------------------------------------------------------------
    def inscrever(self, ouvinte: OuvinteDaPartida) -> None:
        self._ouvintes.append(ouvinte)

    def atualizar(self, dt: float, intencao: Vetor2) -> None:
        if self._situacao is not SituacaoDaPartida.EM_ANDAMENTO:
            return
        if self._fase.avancar(dt, intencao):
            restante = self._fase.tempo_restante
            self._avisar(lambda ouvinte: ouvinte.ao_alertar_tempo(restante))

        if self._fase.jogador_na_saida():
            self._concluir_fase()
        elif self._fase.tempo_esgotado:
            self._encerrar_por_tempo()

    def avancar_para_proxima_fase(self) -> None:
        if self._situacao is not SituacaoDaPartida.FASE_CONCLUIDA:
            raise RuntimeError("so da para avancar depois de concluir a fase atual")
        self._fase = self._fabrica.criar(self._fase.numero + 1)
        self._situacao = SituacaoDaPartida.EM_ANDAMENTO

    # ------------------------------------------------------------------
    def _concluir_fase(self) -> None:
        resultado = self._placar.registrar_conclusao(self._fase.numero, self._fase.tempo_restante)
        self._ultimo_resultado = resultado
        self._situacao = SituacaoDaPartida.FASE_CONCLUIDA
        self._avisar(lambda ouvinte: ouvinte.ao_concluir_fase(resultado))

    def _encerrar_por_tempo(self) -> None:
        self._situacao = SituacaoDaPartida.TEMPO_ESGOTADO
        fase = self._fase.numero
        self._avisar(lambda ouvinte: ouvinte.ao_esgotar_tempo(fase))

    def _avisar(self, evento: Callable[[OuvinteDaPartida], None]) -> None:
        for ouvinte in self._ouvintes:
            evento(ouvinte)
