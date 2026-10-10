"""
regras.py - Regras de balanceamento, tempo, pontuacao e recorde.

Antes tudo isso eram atributos soltos e contas espalhadas dentro da classe
Jogo (tempo_restante, pontos, bonus_ultimo, ultimo_segundo, recorde...).
Agora cada regra tem dono: Dificuldade, Cronometro, Placar e Recorde.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .contratos import OuvinteDaPartida, RepositorioDeRecorde


@dataclass(frozen=True)
class Dificuldade:
    """Curva de dificuldade - MEXA AQUI para balancear o jogo.

    Objeto de configuracao imutavel, entregue por composicao a FabricaDeFases:
    um "modo facil" seria so outra instancia com outros numeros.
    """

    colunas_iniciais: int = 10
    colunas_maximas: int = 30
    linhas_iniciais: int = 7
    linhas_maximas: int = 20
    fator_tempo_inicial: float = 2.8    # fase 1: tempo = (tempo minimo) x 2.8 ...
    fator_tempo_minimo: float = 1.6     # ... cai a cada fase ate x 1.6
    queda_fator_por_fase: float = 0.1
    tempo_extra: float = 5.0            # segundos de "folga" fixos
    raio_visao_inicial: float = 7.0     # alcance da luz, em tiles ...
    raio_visao_minimo: float = 3.5      # ... diminui a cada fase ate 3.5
    queda_visao_por_fase: float = 0.4

    def tamanho(self, fase: int) -> tuple[int, int]:
        """Quantidade de CELULAS (colunas, linhas) do labirinto da fase."""
        colunas = min(self.colunas_iniciais + (fase - 1), self.colunas_maximas)
        linhas = min(self.linhas_iniciais + (fase - 1) * 2 // 3, self.linhas_maximas)
        return colunas, linhas

    def tempo_limite(self, fase: int, distancia: float, velocidade: float) -> float:
        """Segundos para a fase: tempo do caminho perfeito x fator + folga."""
        tempo_minimo = distancia / velocidade
        fator = max(self.fator_tempo_minimo,
                    self.fator_tempo_inicial - self.queda_fator_por_fase * (fase - 1))
        return tempo_minimo * fator + self.tempo_extra

    def raio_visao(self, fase: int) -> float:
        """Alcance da luz do jogador, em tiles."""
        return max(self.raio_visao_minimo,
                   self.raio_visao_inicial - self.queda_visao_por_fase * (fase - 1))


class Cronometro:
    """Contagem regressiva de uma fase, com alerta a cada segundo final."""

    LIMITE_ALERTA = 10.0  # segundos finais em que cada segundo gera um alerta

    def __init__(self, total: float, limite_alerta: float = LIMITE_ALERTA) -> None:
        self._total = total
        self._restante = total
        self._limite_alerta = limite_alerta
        self._ultimo_segundo = math.inf

    @property
    def total(self) -> float:
        return self._total

    @property
    def restante(self) -> float:
        return max(0.0, self._restante)

    @property
    def fracao_restante(self) -> float:
        return max(0.0, self._restante / self._total)

    @property
    def esgotado(self) -> bool:
        return self._restante <= 0

    def avancar(self, dt: float) -> bool:
        """Desconta `dt` segundos. Devolve True ao entrar em um novo segundo final."""
        self._restante -= dt
        segundo = int(self._restante)
        alerta = 0 < self._restante <= self._limite_alerta and segundo < self._ultimo_segundo
        self._ultimo_segundo = segundo
        return alerta


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
