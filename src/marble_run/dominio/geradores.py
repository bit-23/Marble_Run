"""
geradores.py - Geracao PROCEDURAL de labirintos (padrao Strategy).

Antes eram funcoes soltas dentro de jogo.py. Agora quem cria as fases
depende so da abstracao GeradorDeLabirinto: para usar outro algoritmo
(Prim, Kruskal, salas e corredores...) basta criar outra subclasse e
injeta-la no main.py - nada mais muda (Aberto/Fechado).
"""
from __future__ import annotations

import random
from abc import ABC, abstractmethod
from collections import deque

from .labirinto import Coordenada, Labirinto

VIZINHOS = ((1, 0), (-1, 0), (0, 1), (0, -1))

Grade = list[list[bool]]  # True = parede


class GeradorDeLabirinto(ABC):
    """Contrato de qualquer algoritmo que crie labirintos."""

    @abstractmethod
    def gerar(self, colunas: int, linhas: int, rng: random.Random) -> Labirinto:
        """Cria um labirinto de `colunas` x `linhas` CELULAS usando o sorteador `rng`.

        Receber o `rng` de fora garante: mesma semente => mesmo labirinto.
        """


class GeradorBacktracker(GeradorDeLabirinto):
    """
    "Recursive backtracker" (DFS) + lacos.

    colunas/linhas = quantidade de CELULAS. A grade final tem (2n+1) tiles,
    porque entre duas celulas existe um tile que pode ser parede ou passagem.

      1. DFS: garante que TODAS as celulas estao ligadas -> sempre tem solucao.
      2. Remove algumas paredes ao acaso (lacos) para criar atalhos, deixando
         de ser um labirinto "perfeito" e chato.
      3. Entrada em uma celula aleatoria; saida escolhida entre as celulas mais
         DISTANTES dela (BFS) -> o jogador sempre precisa explorar.
    """

    def __init__(self, proporcao_lacos: float = 0.06) -> None:
        self._proporcao_lacos = proporcao_lacos  # % de paredes removidas para criar atalhos

    def gerar(self, colunas: int, linhas: int, rng: random.Random) -> Labirinto:
        grade, inicio = self._escavar(colunas, linhas, rng)
        self._abrir_lacos(grade, rng)
        entrada = Coordenada(inicio[0] * 2 + 1, inicio[1] * 2 + 1)
        saida, distancia = self._escolher_saida(grade, entrada, rng)
        return Labirinto(grade, entrada, saida, distancia)

    # ------------------------------------------------------------------
    # Etapas do algoritmo
    # ------------------------------------------------------------------
    @staticmethod
    def _escavar(colunas: int, linhas: int, rng: random.Random) -> tuple[Grade, tuple[int, int]]:
        largura, altura = colunas * 2 + 1, linhas * 2 + 1
        grade = [[True] * largura for _ in range(altura)]

        inicio = (rng.randrange(colunas), rng.randrange(linhas))
        grade[inicio[1] * 2 + 1][inicio[0] * 2 + 1] = False
        visitadas = {inicio}
        pilha = [inicio]
        while pilha:
            cx, cy = pilha[-1]
            vizinhas = [(cx + dx, cy + dy, dx, dy) for dx, dy in VIZINHOS
                        if 0 <= cx + dx < colunas and 0 <= cy + dy < linhas
                        and (cx + dx, cy + dy) not in visitadas]
            if not vizinhas:
                pilha.pop()
                continue
            nx, ny, dx, dy = rng.choice(vizinhas)
            grade[cy * 2 + 1 + dy][cx * 2 + 1 + dx] = False  # derruba a parede entre as duas
            grade[ny * 2 + 1][nx * 2 + 1] = False
            visitadas.add((nx, ny))
            pilha.append((nx, ny))
        return grade, inicio

    def _abrir_lacos(self, grade: Grade, rng: random.Random) -> None:
        altura, largura = len(grade), len(grade[0])
        paredes_internas = [
            (x, y) for y in range(1, altura - 1) for x in range(1, largura - 1)
            if grade[y][x] and (x % 2) != (y % 2)  # parede ENTRE duas celulas
        ]
        rng.shuffle(paredes_internas)
        for x, y in paredes_internas[: int(len(paredes_internas) * self._proporcao_lacos)]:
            grade[y][x] = False

    def _escolher_saida(self, grade: Grade, entrada: Coordenada,
                        rng: random.Random) -> tuple[Coordenada, int]:
        dist = self._distancias(grade, (entrada.coluna, entrada.linha))
        celulas = [(x, y) for (x, y) in dist if x % 2 == 1 and y % 2 == 1]
        maxima = max(dist[c] for c in celulas)
        distantes = [c for c in celulas if dist[c] >= maxima * 0.85]
        saida = rng.choice(distantes)
        return Coordenada(*saida), dist[saida]

    @staticmethod
    def _distancias(grade: Grade, origem: tuple[int, int]) -> dict[tuple[int, int], int]:
        """BFS: menor numero de tiles de `origem` ate cada tile livre."""
        dist = {origem: 0}
        fila = deque([origem])
        while fila:
            x, y = fila.popleft()
            for dx, dy in VIZINHOS:
                p = (x + dx, y + dy)
                if p not in dist and not grade[p[1]][p[0]]:
                    dist[p] = dist[(x, y)] + 1
                    fila.append(p)
        return dist
