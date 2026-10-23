"""
regras.py - Regras de balanceamento, tempo, pontuacao e recorde.

Antes tudo isso eram atributos soltos e contas espalhadas dentro da classe
Jogo (tempo_restante, pontos, bonus_ultimo, ultimo_segundo, recorde...).
Agora cada regra tem dono: Dificuldade, Cronometro, Placar e Recorde.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from .ambiente import TipoDeItem
from .contratos import OuvinteDaPartida, RepositorioDePontuacao, RepositorioDeRecorde


class NivelDeDificuldade(Enum):
    FACIL = "facil"
    NORMAL = "normal"
    DIFICIL = "dificil"
    INSANO = "insano"


@dataclass(frozen=True)
class Dificuldade:
    """Curva de dificuldade - MEXA AQUI para balancear o jogo.

    As fases 1 a `fases_tranquilas` sao calmas (muito tempo, labirinto
    pequeno, bastante luz, poucos perigos e nenhum fenomeno). Dai em diante
    tudo piora aos poucos ate chegar no maximo na `fase_mais_dificil`:

        progresso(fase) = 0 ... 1     (0 = tranquilo, 1 = dificuldade total)
        valor = tranquilo + (final - tranquilo) * progresso

    Objeto imutavel, entregue por composicao a FabricaDeFases: cada nivel
    (facil, normal...) e so outra instancia com outros multiplicadores
    (veja `do_nivel`).
    """

    fases_tranquilas: int = 3
    fase_mais_dificil: int = 10
    colunas_maximas: int = 30
    linhas_maximas: int = 20
    fator_tempo_tranquilo: float = 2.6    # tempo = (tempo do caminho perfeito) x fator ...
    fator_tempo_final: float = 1.35       # ... que cai ate x 1.35
    tempo_extra_tranquilo: float = 12.0   # segundos de folga ...
    tempo_extra_final: float = 4.0        # ... que caem ate 4
    raio_visao_tranquilo: float = 7.0     # alcance da luz, em tiles ...
    raio_visao_final: float = 3.2         # ... que cai ate 3.2
    perigos_tranquilo: float = 0.6        # quantidade de perigos (x o normal do mapa) ...
    perigos_final: float = 1.8            # ... que sobe ate x 1.8
    ritmo_fenomenos_inicial: float = 1.4  # intervalo entre fenomenos (x o normal): raros no comeco ...
    ritmo_fenomenos_final: float = 0.8    # ... e frequentes no fim
    raio_visao_minimo: float = 2.5
    multiplicador_tempo: float = 1.0      # facil da mais tempo, insano bem menos
    fator_tempo_absoluto: float = 1.15    # nunca menos que 15% acima do caminho perfeito
    fator_perigos: float = 1.0            # multiplicador do nivel (facil tem menos perigos)
    ritmo_fenomenos: float = 1.0          # multiplicador do nivel (< 1 = mais frequentes)
    ajuste_visao: float = 0.0             # tiles a mais (facil) ou a menos (dificil) de luz
    visao_fixa: float | None = None       # insano: luz sempre pequena
    itens_vetados: tuple[TipoDeItem, ...] = ()
    fases_com_um_monstro: int = 6         # ate esta fase: 1 monstro; dai em diante 2
    monstros_extras: int = 0              # insano: +1 monstro
    maximo_de_monstros: int | None = None  # facil: no maximo 1
    monstros_agressivos: bool = False     # dificil/insano: atacam mais vezes e andam mais rapido
    coracoes: int = 3                     # vida maxima
    cura_por_fase: int = 1                # coracoes devolvidos ao sair do labirinto
    celulas_extras: int = 0               # labirinto ja comeca maior
    nivel: NivelDeDificuldade = NivelDeDificuldade.NORMAL

    @classmethod
    def do_nivel(cls, nivel: NivelDeDificuldade) -> Dificuldade:
        if nivel is NivelDeDificuldade.FACIL:
            return cls(multiplicador_tempo=1.3, ajuste_visao=1.0, fator_perigos=0.75, ritmo_fenomenos=1.2,
                       maximo_de_monstros=1, nivel=nivel)
        if nivel is NivelDeDificuldade.DIFICIL:  # monstros desde a fase 3, sem cura ao passar de fase
            return cls(multiplicador_tempo=0.8, ajuste_visao=-0.8, fator_perigos=1.35, ritmo_fenomenos=0.8,
                       fator_tempo_absoluto=1.12, fases_tranquilas=2, fases_com_um_monstro=4,
                       monstros_agressivos=True, cura_por_fase=0, celulas_extras=1, nivel=nivel)
        if nivel is NivelDeDificuldade.INSANO:  # 2 coracoes, pouca luz, pouco tempo e monstros desde a fase 2
            return cls(multiplicador_tempo=0.6, visao_fixa=2.4, fator_perigos=1.6, ritmo_fenomenos=0.65,
                       fator_tempo_absoluto=1.08, fases_tranquilas=1, fases_com_um_monstro=2, monstros_extras=1,
                       monstros_agressivos=True, itens_vetados=(TipoDeItem.LANTERNA,), coracoes=2,
                       cura_por_fase=0, celulas_extras=2, nivel=nivel)
        return cls()

    def monstros(self, fase: int) -> int:
        """Quantos monstros aparecem: nenhum nas fases tranquilas, depois 1 e, mais adiante, 2."""
        if fase <= self.fases_tranquilas:
            return 0
        quantidade = (1 if fase <= self.fases_com_um_monstro else 2) + self.monstros_extras
        return min(quantidade, self.maximo_de_monstros) if self.maximo_de_monstros else quantidade

    # ------------------------------------------------------------------
    def progresso(self, fase: int) -> float:
        """0 nas fases tranquilas, 1 a partir da fase mais dificil."""
        rampa = self.fase_mais_dificil - self.fases_tranquilas
        return min(1.0, max(0.0, (fase - self.fases_tranquilas) / rampa))

    def _curva(self, fase: int, tranquilo: float, final: float) -> float:
        return tranquilo + (final - tranquilo) * self.progresso(fase)

    def tamanho(self, fase: int) -> tuple[int, int]:
        """Quantidade de CELULAS (colunas, linhas) do labirinto: pequeno no comeco, cresce mais rapido depois."""
        depois_da_calmaria = max(0, fase - self.fases_tranquilas)
        colunas = min(7 + self.celulas_extras + (fase - 1) + depois_da_calmaria // 2, self.colunas_maximas)
        linhas = min(5 + self.celulas_extras + (fase - 1) * 2 // 3 + depois_da_calmaria // 3, self.linhas_maximas)
        return colunas, linhas

    def tempo_limite(self, fase: int, distancia: float, velocidade: float) -> float:
        """Segundos para a fase: tempo do caminho perfeito x fator + folga."""
        tempo_minimo = distancia / velocidade
        fator = self._curva(fase, self.fator_tempo_tranquilo, self.fator_tempo_final)
        fator = max(self.fator_tempo_absoluto, fator * self.multiplicador_tempo)
        folga = self._curva(fase, self.tempo_extra_tranquilo, self.tempo_extra_final)
        return tempo_minimo * fator + folga * self.multiplicador_tempo

    def raio_visao(self, fase: int) -> float:
        """Alcance da luz do jogador, em tiles."""
        if self.visao_fixa is not None:
            return self.visao_fixa
        raio = self._curva(fase, self.raio_visao_tranquilo, self.raio_visao_final) + self.ajuste_visao
        return max(self.raio_visao_minimo, raio)

    def perigos(self, fase: int) -> float:
        """Multiplicador da quantidade de perigos do mapa nesta fase."""
        return self._curva(fase, self.perigos_tranquilo, self.perigos_final) * self.fator_perigos

    def tem_fenomenos(self, fase: int) -> bool:
        """Nas fases tranquilas nao tem tempestade, terremoto, apagao..."""
        return fase > self.fases_tranquilas

    def ritmo_dos_fenomenos(self, fase: int) -> float:
        """Multiplicador do intervalo entre fenomenos (menor = mais frequente)."""
        return self._curva(fase, self.ritmo_fenomenos_inicial, self.ritmo_fenomenos_final) * self.ritmo_fenomenos


class Cronometro:
    """Contagem regressiva de uma fase, com alerta a cada segundo final."""

    LIMITE_ALERTA = 10.0  # segundos finais em que cada segundo gera um alerta

    def __init__(self, total: float, limite_alerta: float = LIMITE_ALERTA, ilimitado: bool = False) -> None:
        self._total = total
        self._restante = total
        self._limite_alerta = limite_alerta
        self._ultimo_segundo = math.inf
        self._ilimitado = ilimitado

    @classmethod
    def sem_limite(cls) -> Cronometro:
        """Relogio que nunca acaba (modo apresentacao)."""
        return cls(1.0, ilimitado=True)

    @property
    def ilimitado(self) -> bool:
        return self._ilimitado

    @property
    def total(self) -> float:
        return self._total

    @property
    def restante(self) -> float:
        return max(0.0, self._restante)

    @property
    def fracao_restante(self) -> float:
        return min(1.0, max(0.0, self._restante / self._total))

    @property
    def esgotado(self) -> bool:
        return self._restante <= 0

    def ajustar(self, segundos: float) -> None:
        """Ganha (relogio) ou perde tempo. Nunca passa do tempo total da fase."""
        if not self._ilimitado:
            self._restante = min(self._total, self._restante + segundos)

    def avancar(self, dt: float) -> bool:
        """Desconta `dt` segundos. Devolve True ao entrar em um novo segundo final."""
        if self._ilimitado:
            return False
        self._restante -= dt
        segundo = int(self._restante)
        alerta = 0 < self._restante <= self._limite_alerta and segundo < self._ultimo_segundo
        self._ultimo_segundo = segundo
        return alerta


class Vida:
    """Coracoes do jogador durante a partida (o fogo tira, passar de fase devolve 1)."""

    def __init__(self, maximo: int = 3) -> None:
        self._maximo = maximo
        self._coracoes = maximo

    @property
    def coracoes(self) -> int:
        return self._coracoes

    @property
    def maximo(self) -> int:
        return self._maximo

    @property
    def acabou(self) -> bool:
        return self._coracoes <= 0

    def perder(self, quantidade: int = 1) -> None:
        self._coracoes = max(0, self._coracoes - quantidade)

    def recuperar(self, quantidade: int = 1) -> None:
        self._coracoes = min(self._maximo, self._coracoes + quantidade)


@dataclass(frozen=True)
class ResultadoDaFase:
    """Comprovante (imutavel) do que o jogador ganhou ao sair de um labirinto."""

    fase: int
    bonus: int
    pontos_ganhos: int


class Placar:
    """Pontuacao acumulada da partida."""

    PONTOS_POR_FASE = 100   # multiplicado pelo numero da fase
    PONTOS_POR_SEGUNDO = 10  # bonus por segundo que sobrou

    def __init__(self) -> None:
        self._pontos = 0

    @property
    def pontos(self) -> int:
        return self._pontos

    def registrar_conclusao(self, fase: int, segundos_restantes: float) -> ResultadoDaFase:
        bonus = int(segundos_restantes) * self.PONTOS_POR_SEGUNDO
        ganho = self.PONTOS_POR_FASE * fase + bonus
        self._pontos += ganho
        return ResultadoDaFase(fase, bonus, ganho)


class Recorde(OuvinteDaPartida):
    """Melhor fase ja alcancada.

    Depende da ABSTRACAO RepositorioDeRecorde (DIP): nao sabe se o recorde
    vai para um arquivo, um banco ou a memoria (util em testes). Como
    ouvinte da partida, se atualiza sozinho quando o tempo acaba.
    """

    def __init__(self, repositorio: RepositorioDeRecorde) -> None:
        self._repositorio = repositorio
        self._melhor_fase = repositorio.carregar()

    @property
    def melhor_fase(self) -> int:
        return self._melhor_fase

    def registrar(self, fase_alcancada: int) -> None:
        if fase_alcancada > self._melhor_fase:
            self._melhor_fase = fase_alcancada
            self._repositorio.salvar(fase_alcancada)

    def ao_esgotar_tempo(self, fase_alcancada: int) -> None:
        self.registrar(fase_alcancada)

    def ao_perder_todas_as_vidas(self, fase_alcancada: int) -> None:
        self.registrar(fase_alcancada)


class PontuacaoDoJogador(OuvinteDaPartida):
    """Persiste a melhor pontuacao do jogador (no ranking da dificuldade) ao concluir cada fase."""

    def __init__(self, jogador: str, dificuldade: NivelDeDificuldade, repositorio: RepositorioDePontuacao) -> None:
        self._jogador = jogador
        self._dificuldade = dificuldade
        self._repositorio = repositorio
        self._pontos = 0

    def ao_concluir_fase(self, resultado: ResultadoDaFase) -> None:
        self._pontos += resultado.pontos_ganhos
        self._repositorio.salvar_melhor(self._jogador, self._dificuldade, self._pontos, resultado.fase)
