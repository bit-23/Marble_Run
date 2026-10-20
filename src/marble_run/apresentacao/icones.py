"""
icones.py - Desenho dos buffs, da caixa surpresa e da mola (feito por codigo, sem arquivos).

O mesmo icone aparece na roleta, no HUD e no modo apresentacao, por isso
fica aqui, com cache: cada (item, tamanho) e desenhado uma unica vez.
"""
from __future__ import annotations

import math
from typing import Callable

import pygame

from ..dominio.ambiente import TipoDeItem

BASE = 32  # tudo e desenhado em 32x32 e depois redimensionado

_cache: dict[tuple[TipoDeItem, int], pygame.Surface] = {}


def icone(tipo: TipoDeItem, tamanho: int = BASE) -> pygame.Surface:
    chave = (tipo, tamanho)
    if chave not in _cache:
        s = pygame.Surface((BASE, BASE), pygame.SRCALPHA)
        _DESENHOS[tipo](s)
        _cache[chave] = s if tamanho == BASE else pygame.transform.smoothscale(s, (tamanho, tamanho))
    return _cache[chave]


def _blusa(s: pygame.Surface) -> None:
    vermelho, escuro, listra = (210, 50, 60), (130, 25, 35), (245, 240, 230)
    corpo = [(9, 7), (23, 7), (30, 14), (26, 18), (24, 15), (24, 29), (8, 29), (8, 15), (6, 18), (2, 14)]
    pygame.draw.polygon(s, vermelho, corpo)
    pygame.draw.polygon(s, escuro, corpo, 2)
    for y in (18, 23):
        pygame.draw.line(s, listra, (9, y), (23, y), 2)
    pygame.draw.arc(s, listra, (12, 4, 8, 7), math.pi, 2 * math.pi, 2)  # gola


def _banana(s: pygame.Surface) -> None:
    pygame.draw.arc(s, (120, 90, 20), (3, -6, 30, 32), math.pi * 1.05, math.pi * 1.85, 9)
    pygame.draw.arc(s, (250, 215, 60), (3, -6, 30, 32), math.pi * 1.05, math.pi * 1.85, 7)
    pygame.draw.arc(s, (255, 245, 160), (6, -4, 25, 27), math.pi * 1.2, math.pi * 1.6, 2)
    pygame.draw.circle(s, (90, 60, 20), (5, 14), 2)
    pygame.draw.circle(s, (90, 60, 20), (29, 12), 2)


def _mola(s: pygame.Surface) -> None:
    metal, sombra = (200, 205, 215), (110, 115, 130)
    pygame.draw.rect(s, (220, 60, 60), (6, 3, 20, 5), border_radius=2)
    pygame.draw.rect(s, sombra, (6, 26, 20, 4), border_radius=2)
    pontos = [(8 if i % 2 else 24, 8 + i * 3) for i in range(7)]
    pygame.draw.lines(s, sombra, False, [(x + 1, y + 1) for x, y in pontos], 3)
    pygame.draw.lines(s, metal, False, pontos, 3)


def icone_da_caixa(tamanho: int = BASE) -> pygame.Surface:
    """Caixa surpresa "?" (estilo bloco de videogame)."""
    chave = ("caixa", tamanho)
    if chave not in _cache_extra:
        s = pygame.Surface((BASE, BASE), pygame.SRCALPHA)
        pygame.draw.rect(s, (120, 60, 10), (1, 1, 30, 30), border_radius=4)
        pygame.draw.rect(s, (245, 180, 40), (3, 3, 26, 26), border_radius=3)
        pygame.draw.rect(s, (255, 225, 120), (3, 3, 26, 4), border_radius=2)
        for x, y in ((5, 5), (25, 5), (5, 25), (25, 25)):  # rebites
            pygame.draw.rect(s, (150, 80, 20), (x, y, 2, 2))
        pontos = [(12, 11), (13, 8), (19, 8), (21, 11), (21, 14), (17, 17), (17, 20)]
        pygame.draw.lines(s, (120, 60, 10), False, [(x + 1, y + 1) for x, y in pontos], 4)
        pygame.draw.lines(s, (255, 255, 255), False, pontos, 3)
        pygame.draw.rect(s, (120, 60, 10), (16, 23, 4, 4))
        pygame.draw.rect(s, (255, 255, 255), (15, 22, 3, 3))
        _cache_extra[chave] = s if tamanho == BASE else pygame.transform.scale(s, (tamanho, tamanho))
    return _cache_extra[chave]


def icone_da_mola(tamanho: int = BASE) -> pygame.Surface:
    chave = ("mola", tamanho)
    if chave not in _cache_extra:
        s = pygame.Surface((BASE, BASE), pygame.SRCALPHA)
        _mola(s)
        _cache_extra[chave] = s if tamanho == BASE else pygame.transform.smoothscale(s, (tamanho, tamanho))
    return _cache_extra[chave]


_cache_extra: dict[tuple[str, int], pygame.Surface] = {}

# Nome e descricao curta de cada buff (roleta, HUD e modo apresentacao)
DESCRICOES_DOS_ITENS: dict[TipoDeItem, tuple[str, str]] = {
    TipoDeItem.BLUSA: ("BLUSA", "NAO CONGELA NA AGUA NEM DESLIZA NO GELO (10S)"),
    TipoDeItem.BANANA: ("BANANA", "+50% DE VELOCIDADE (5S)"),
    TipoDeItem.FLAUTA: ("FLAUTA", "APAGA O FOGO E ACALMA A TEMPESTADE (8S)"),
    TipoDeItem.RELOGIO: ("RELOGIO", "+10 SEGUNDOS NO RELOGIO"),
    TipoDeItem.LANTERNA: ("LANTERNA", "+60% DE VISAO (12S)"),
    TipoDeItem.ESTRELA: ("ESTRELA", "IMUNE A TODOS OS DEBUFFS (6S)"),
    TipoDeItem.BUSSOLA: ("BUSSOLA", "SETA APONTANDO A SAIDA (15S)"),
    TipoDeItem.CAFE: ("CAFE", "+30% DE VELOCIDADE E SEM LENTIDAO (8S)"),
}


def _flauta(s: pygame.Surface) -> None:
    pygame.draw.line(s, (90, 55, 25), (5, 28), (28, 5), 7)
    pygame.draw.line(s, (180, 120, 60), (5, 27), (27, 5), 4)
    for i in range(4):
        x, y = 11 + i * 4, 22 - i * 4
        pygame.draw.circle(s, (50, 30, 15), (x, y), 1)
    pygame.draw.line(s, (230, 200, 90), (4, 29), (7, 26), 3)


def _relogio(s: pygame.Surface) -> None:
    pygame.draw.circle(s, (200, 60, 60), (9, 6), 4)
    pygame.draw.circle(s, (200, 60, 60), (23, 6), 4)
    pygame.draw.circle(s, (60, 40, 40), (16, 18), 13)
    pygame.draw.circle(s, (250, 248, 235), (16, 18), 10)
    pygame.draw.line(s, (40, 40, 40), (16, 18), (16, 11), 2)
    pygame.draw.line(s, (40, 40, 40), (16, 18), (21, 20), 2)
    pygame.draw.circle(s, (200, 60, 60), (16, 18), 2)


def _lanterna(s: pygame.Surface) -> None:
    pygame.draw.polygon(s, (255, 240, 150), [(20, 8), (31, 2), (31, 30), (20, 24)])
    pygame.draw.rect(s, (90, 95, 110), (3, 11, 15, 10), border_radius=3)
    pygame.draw.rect(s, (150, 155, 170), (16, 8, 6, 16), border_radius=2)
    pygame.draw.rect(s, (220, 60, 60), (8, 9, 4, 3))


def _estrela(s: pygame.Surface) -> None:
    pontos = []
    for i in range(10):
        raio = 15 if i % 2 == 0 else 6.5
        ang = -math.pi / 2 + i * math.pi / 5
        pontos.append((16 + raio * math.cos(ang), 17 + raio * math.sin(ang)))
    pygame.draw.polygon(s, (255, 215, 40), pontos)
    pygame.draw.polygon(s, (200, 130, 10), pontos, 2)
    pygame.draw.circle(s, (255, 250, 200), (13, 13), 2)


def _bussola(s: pygame.Surface) -> None:
    pygame.draw.circle(s, (180, 130, 40), (16, 16), 14)
    pygame.draw.circle(s, (245, 240, 225), (16, 16), 11)
    pygame.draw.polygon(s, (220, 50, 50), [(16, 5), (19, 16), (13, 16)])
    pygame.draw.polygon(s, (60, 60, 80), [(16, 27), (19, 16), (13, 16)])
    pygame.draw.circle(s, (180, 130, 40), (16, 16), 2)


def _cafe(s: pygame.Surface) -> None:
    for x in (11, 17):  # fumacinha
        pygame.draw.arc(s, (220, 220, 230), (x, 1, 5, 8), -math.pi / 2, math.pi / 2, 1)
    pygame.draw.circle(s, (240, 240, 245), (25, 19), 5, 2)
    pygame.draw.rect(s, (240, 240, 245), (6, 11, 18, 18), border_radius=4)
    pygame.draw.rect(s, (110, 65, 35), (8, 12, 14, 4))
    pygame.draw.rect(s, (170, 170, 185), (6, 11, 18, 18), 1, border_radius=4)


_DESENHOS: dict[TipoDeItem, Callable[[pygame.Surface], None]] = {
    TipoDeItem.BLUSA: _blusa,
    TipoDeItem.BANANA: _banana,
    TipoDeItem.FLAUTA: _flauta,
    TipoDeItem.RELOGIO: _relogio,
    TipoDeItem.LANTERNA: _lanterna,
    TipoDeItem.ESTRELA: _estrela,
    TipoDeItem.BUSSOLA: _bussola,
    TipoDeItem.CAFE: _cafe,
}
