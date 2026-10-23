"""
caminhos.py - Buscas no labirinto (BFS), usadas por monstros, itens e pelo sorteio dos mapas.

    distancias(lab, origem)       -> passos andando ate cada tile de chao
    caminho(lab, origem, destino) -> lista de tiles do menor caminho (origem ... destino)
    proximo_passo(...)            -> so o primeiro passo desse caminho
    linha_de_visao(...)           -> direcao (dx, dy) se der para ver em linha reta, sem parede no meio
    tiles_em_linha(...)           -> tiles de chao em linha reta ate bater numa parede
"""
from __future__ import annotations

from collections import deque

from .labirinto import Coordenada, Labirinto

DIRECOES_DA_GRADE: tuple[tuple[int, int], ...] = ((1, 0), (-1, 0), (0, 1), (0, -1))


def vizinhos_livres(labirinto: Labirinto, tile: Coordenada) -> list[Coordenada]:
    return [Coordenada(tile.coluna + dx, tile.linha + dy) for dx, dy in DIRECOES_DA_GRADE
            if not labirinto.eh_parede(tile.coluna + dx, tile.linha + dy)]


def distancias(labirinto: Labirinto, origem: Coordenada) -> dict[Coordenada, int]:
    resultado = {origem: 0}
    fila = deque([origem])
    while fila:
        atual = fila.popleft()
        for vizinho in vizinhos_livres(labirinto, atual):
            if vizinho not in resultado:
                resultado[vizinho] = resultado[atual] + 1
                fila.append(vizinho)
    return resultado


def caminho(labirinto: Labirinto, origem: Coordenada, destino: Coordenada) -> list[Coordenada]:
    """Menor caminho andando (inclui origem e destino). Lista vazia se nao houver."""
    if labirinto.eh_parede(*origem) or labirinto.eh_parede(*destino):
        return []
    anterior: dict[Coordenada, Coordenada | None] = {origem: None}
    fila = deque([origem])
    while fila:
        atual = fila.popleft()
        if atual == destino:
            break
        for vizinho in vizinhos_livres(labirinto, atual):
            if vizinho not in anterior:
                anterior[vizinho] = atual
                fila.append(vizinho)
    if destino not in anterior:
        return []
    trajeto = [destino]
    while trajeto[-1] != origem:
        trajeto.append(anterior[trajeto[-1]])
    trajeto.reverse()
    return trajeto


def proximo_passo(labirinto: Labirinto, origem: Coordenada, destino: Coordenada) -> Coordenada | None:
    trajeto = caminho(labirinto, origem, destino)
    return trajeto[1] if len(trajeto) > 1 else None


def linha_de_visao(labirinto: Labirinto, de: Coordenada, ate: Coordenada, alcance: int) -> tuple[int, int] | None:
    """(dx, dy) se `ate` estiver na mesma linha/coluna, a ate `alcance` tiles e sem parede no meio."""
    if de == ate:
        return None
    if de.coluna == ate.coluna:
        passo = (0, 1 if ate.linha > de.linha else -1)
        distancia = abs(ate.linha - de.linha)
    elif de.linha == ate.linha:
        passo = (1 if ate.coluna > de.coluna else -1, 0)
        distancia = abs(ate.coluna - de.coluna)
    else:
        return None
    if distancia > alcance:
        return None
    for i in range(1, distancia):
        if labirinto.eh_parede(de.coluna + passo[0] * i, de.linha + passo[1] * i):
            return None
    return passo


def tiles_em_linha(labirinto: Labirinto, de: Coordenada, passo: tuple[int, int], alcance: int) -> list[Coordenada]:
    """Tiles de chao a partir do vizinho de `de`, em linha reta, ate a parede (ou o alcance)."""
    tiles = []
    for i in range(1, alcance + 1):
        tile = Coordenada(de.coluna + passo[0] * i, de.linha + passo[1] * i)
        if labirinto.eh_parede(*tile):
            break
        tiles.append(tile)
    return tiles


def manhattan(a: Coordenada, b: Coordenada) -> int:
    return abs(a.coluna - b.coluna) + abs(a.linha - b.linha)
