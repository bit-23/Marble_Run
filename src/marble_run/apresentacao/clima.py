"""
clima.py - Efeitos de atmosfera desenhados por cima da fase.

Polimorfismo: o Cenario so chama `clima.atualizar()` e `clima.desenhar()`.
Ele nao sabe (nem pergunta) se esta nevando - antes havia um
"if tema['neve']" no meio do desenho.
"""
from __future__ import annotations

import math
import random
from abc import ABC, abstractmethod

import pygame

Deslocamento = tuple[int, int]  # canto superior esquerdo da camera, em pixels do mapa


class Clima(ABC):
    @abstractmethod
    def atualizar(self, dt: float) -> None: ...

    @abstractmethod
    def desenhar(self, tela: pygame.Surface, camera: Deslocamento) -> None: ...


class CeuLimpo(Clima):
    """Null Object: tema sem clima nenhum."""

    def atualizar(self, dt: float) -> None:
        pass

    def desenhar(self, tela: pygame.Surface, camera: Deslocamento) -> None:
        pass


class _Floco:
    """Um floco de neve. `profundidade` vai de 0.3 (longe) a 1.0 (perto da tela)."""

    __slots__ = ("_x", "_y", "_profundidade", "_balanco")

    def __init__(self, x: float, y: float, profundidade: float, balanco: float) -> None:
        self._x = x
        self._y = y
        self._profundidade = profundidade
        self._balanco = balanco  # fase do vai-e-vem lateral

    def soprar(self, vento: float, tempo: float, dt: float) -> None:
        prof = self._profundidade
        self._x += (vento + 30 * math.sin(tempo * 2 + self._balanco)) * prof * dt
        self._y += (40 + 110 * prof) * dt

    def desenhar(self, tela: pygame.Surface, camera: Deslocamento, largura: int, altura: int, vento: float) -> None:
        prof = self._profundidade
        # flocos mais perto andam mais quando a camera mexe (efeito de profundidade)
        paralaxe = 1.0 + 0.6 * prof
        sx = int(self._x - camera[0] * paralaxe) % largura
        sy = int(self._y - camera[1] * paralaxe) % altura
        brilho = int(110 + 145 * prof)
        if prof > 0.8:  # rastro: os flocos mais proximos parecem mais rapidos
            rastro = vento * prof * 0.04
            cor_rastro = (brilho // 2, brilho // 2, brilho // 2 + 25)
            pygame.draw.line(tela, cor_rastro, (sx, sy), (sx - rastro, sy - 5), 2)
        pygame.draw.circle(tela, (brilho, brilho, min(255, brilho + 20)), (sx, sy), 1 if prof < 0.6 else 2)


class Nevasca(Clima):
    """Flocos caindo com vento em rajadas - desenhados por cima ate da escuridao."""

    def __init__(self, quantidade: int = 180, aleatorio: random.Random | None = None) -> None:
        self._quantidade = quantidade
        self._aleatorio = aleatorio
        self._flocos: list[_Floco] = []  # criados no 1o desenho (precisa do tamanho da tela)
        self._tempo = 0.0
        self._vento = 0.0

    def atualizar(self, dt: float) -> None:
        self._tempo += dt
        if not self._flocos:
            return
        rajada = 0.5 + 0.5 * math.sin(self._tempo * 0.9) * math.sin(self._tempo * 0.31 + 1.0)
        self._vento = 40 + 260 * rajada
        for floco in self._flocos:
            floco.soprar(self._vento, self._tempo, dt)

    def desenhar(self, tela: pygame.Surface, camera: Deslocamento) -> None:
        largura, altura = tela.get_size()
        if not self._flocos:
            self._flocos = self._criar_flocos(largura, altura)
        for floco in self._flocos:
            floco.desenhar(tela, camera, largura, altura, self._vento)

    def _criar_flocos(self, largura: int, altura: int) -> list[_Floco]:
        rng = self._aleatorio if self._aleatorio is not None else random.Random()
        return [_Floco(rng.uniform(0, largura), rng.uniform(0, altura),
                       rng.uniform(0.3, 1.0), rng.uniform(0, math.tau))
                for _ in range(self._quantidade)]
