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


def _coracao(s: pygame.Surface) -> None:
    contorno, vermelho, brilho = (120, 20, 35), (230, 50, 70), (255, 190, 200)
    pontos = [(16, 29), (4, 17), (2, 11), (4, 6), (9, 3), (13, 4), (16, 8), (19, 4), (23, 3), (28, 6), (30, 11),
              (28, 17)]
    pygame.draw.polygon(s, vermelho, pontos)
    pygame.draw.polygon(s, contorno, pontos, 2)
    pygame.draw.circle(s, brilho, (9, 9), 3)
    pygame.draw.line(s, (255, 255, 255), (22, 13), (22, 21), 3)  # "+"
    pygame.draw.line(s, (255, 255, 255), (18, 17), (26, 17), 3)


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
    TipoDeItem.BLUSA: ("BLUSA", "NAO CONGELA NEM DESLIZA NO GELO (10S)"),
    TipoDeItem.FLAUTA: ("FLAUTA", "ACALMA A TEMPESTADE E OS MONSTROS DORMEM (8S)"),
    TipoDeItem.RELOGIO: ("RELOGIO", "+10 SEGUNDOS NO RELOGIO"),
    TipoDeItem.LANTERNA: ("LANTERNA", "+60% DE VISAO E A ARANHA FOGE (12S)"),
    TipoDeItem.ESTRELA: ("ESTRELA", "IMUNE A DEBUFFS E MONSTROS (6S)"),
    TipoDeItem.BUSSOLA: ("BUSSOLA", "SETA APONTANDO A SAIDA (15S)"),
    TipoDeItem.CAFE: ("CAFE", "+30% DE VELOCIDADE E SEM LENTIDAO (8S)"),
    TipoDeItem.CORACAO: ("CORACAO", "+1 CORACAO (COM A VIDA CHEIA, SOME)"),
    TipoDeItem.EXTINTOR: ("EXTINTOR", "APAGA FOGO E LAVA EM VOLTA. MAGMAN VIRA PEDRA"),
    TipoDeItem.BOTA: ("BOTA", "BOTA DE OBSIDIANA: IMUNE A FOGO E LAVA (8S)"),
    TipoDeItem.GUARDA_CHUVA: ("GUARDA-CHUVA", "IMUNE A VENTO, TORNADO E AGUIA (10S)"),
    TipoDeItem.PIPA: ("PIPA", "O VENTO E O TORNADO LEVAM PARA O PORTAL (12S)"),
    TipoDeItem.TAPETE: ("TAPETE", "FLUTUA (8S) E VOA POR CIMA DE 1 PAREDE"),
    TipoDeItem.GENIO: ("GENIO", "ESCOLHA 1 DE 3 DESEJOS"),
    TipoDeItem.BROCA: ("BROCA", "QUEBRA ATE 2 PAREDES DE VERDADE (15S)"),
    TipoDeItem.CAPACETE: ("CAPACETE", "SEM TERREMOTO, +LUZ, IMUNE A TOUPEIRA E GOLEM"),
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


def _extintor(s: pygame.Surface) -> None:
    pygame.draw.rect(s, (130, 20, 20), (9, 8, 13, 22), border_radius=4)
    pygame.draw.rect(s, (220, 40, 40), (10, 9, 11, 20), border_radius=4)
    pygame.draw.rect(s, (245, 240, 230), (11, 15, 9, 6))
    pygame.draw.rect(s, (60, 60, 70), (12, 4, 7, 5), border_radius=1)
    pygame.draw.lines(s, (40, 40, 45), False, [(18, 5), (25, 4), (29, 9)], 2)  # mangueira
    for i in range(3):  # jato de espuma
        pygame.draw.circle(s, (235, 245, 255), (28 + i, 12 + i * 3), 2)


def _bota(s: pygame.Surface) -> None:
    contorno = [(9, 4), (19, 4), (19, 20), (29, 23), (29, 29), (6, 29), (6, 20), (9, 18)]
    pygame.draw.polygon(s, (45, 25, 60), contorno)
    pygame.draw.polygon(s, (190, 90, 255), contorno, 2)
    pygame.draw.line(s, (255, 150, 60), (8, 25), (28, 25), 2)  # brilho de lava na sola
    pygame.draw.line(s, (120, 70, 160), (11, 8), (16, 8), 2)


def _guarda_chuva(s: pygame.Surface) -> None:
    gomos = [(2, 16), (9, 13), (16, 16), (23, 13), (30, 16)]
    pygame.draw.polygon(s, (220, 60, 80), [(16, 3)] + gomos)
    for gx, gy in gomos[1:-1]:
        pygame.draw.line(s, (150, 30, 50), (16, 3), (gx, gy), 1)
    pygame.draw.line(s, (90, 70, 60), (16, 15), (16, 27), 2)
    pygame.draw.arc(s, (90, 70, 60), (10, 24, 7, 7), math.pi, math.tau, 2)


def _pipa(s: pygame.Surface) -> None:
    pygame.draw.polygon(s, (80, 170, 240), [(14, 2), (25, 12), (14, 24), (3, 12)])
    pygame.draw.polygon(s, (40, 90, 160), [(14, 2), (25, 12), (14, 24), (3, 12)], 2)
    pygame.draw.line(s, (250, 230, 90), (14, 2), (14, 24), 1)
    pygame.draw.line(s, (250, 230, 90), (3, 12), (25, 12), 1)
    pygame.draw.lines(s, (250, 90, 90), False, [(14, 24), (18, 27), (15, 30), (21, 31)], 2)


def _tapete(s: pygame.Surface) -> None:
    pontos = [(3 + i * 2, 10 + round(math.sin(i * 0.6) * 2)) for i in range(14)]
    base = [(x + 1, y + 13) for x, y in reversed(pontos)]
    pygame.draw.polygon(s, (120, 40, 140), pontos + base)
    pygame.draw.lines(s, (240, 200, 80), False, pontos, 2)
    pygame.draw.lines(s, (240, 200, 80), False, base, 2)
    pygame.draw.circle(s, (240, 200, 80), (16, 17), 3)
    for x, y in base[::3]:
        pygame.draw.line(s, (240, 200, 80), (x, y), (x, y + 3), 1)


def _genio(s: pygame.Surface) -> None:
    for i in range(3):  # fumaca magica
        pygame.draw.circle(s, (150, 120, 230), (12 + i * 4, 10 - i * 3), 4 - i)
    pygame.draw.ellipse(s, (150, 100, 20), (4, 18, 24, 11))
    pygame.draw.ellipse(s, (240, 190, 60), (5, 18, 22, 9))
    pygame.draw.polygon(s, (240, 190, 60), [(26, 21), (31, 17), (30, 21), (27, 24)])  # bico
    pygame.draw.arc(s, (200, 150, 40), (1, 19, 8, 8), math.pi / 2, math.pi * 1.5, 2)    # alca
    pygame.draw.ellipse(s, (255, 230, 140), (11, 15, 9, 4))


def _broca(s: pygame.Surface) -> None:
    pygame.draw.rect(s, (230, 170, 40), (2, 12, 12, 9), border_radius=2)        # corpo
    pygame.draw.rect(s, (120, 80, 20), (5, 20, 5, 9), border_radius=1)          # cabo
    pygame.draw.polygon(s, (170, 175, 190), [(14, 10), (31, 16), (14, 23)])     # ponta
    for x in (17, 21, 25):
        pygame.draw.line(s, (90, 95, 110), (x, 12 + (x - 14) // 3), (x + 2, 21 - (x - 14) // 3), 1)


def _capacete(s: pygame.Surface) -> None:
    pygame.draw.ellipse(s, (230, 190, 40), (4, 8, 24, 22))
    pygame.draw.rect(s, (0, 0, 0, 0), (0, 21, 32, 11))
    pygame.draw.rect(s, (200, 160, 30), (2, 19, 28, 5), border_radius=2)
    pygame.draw.circle(s, (120, 120, 130), (16, 13), 5)
    pygame.draw.circle(s, (255, 250, 200), (16, 13), 3)
    pygame.draw.polygon(s, (255, 250, 200, 140), [(16, 13), (30, 4), (31, 13)])


_DESENHOS: dict[TipoDeItem, Callable[[pygame.Surface], None]] = {
    TipoDeItem.BLUSA: _blusa,
    TipoDeItem.FLAUTA: _flauta,
    TipoDeItem.RELOGIO: _relogio,
    TipoDeItem.LANTERNA: _lanterna,
    TipoDeItem.ESTRELA: _estrela,
    TipoDeItem.BUSSOLA: _bussola,
    TipoDeItem.CAFE: _cafe,
    TipoDeItem.CORACAO: _coracao,
    TipoDeItem.EXTINTOR: _extintor,
    TipoDeItem.BOTA: _bota,
    TipoDeItem.GUARDA_CHUVA: _guarda_chuva,
    TipoDeItem.PIPA: _pipa,
    TipoDeItem.TAPETE: _tapete,
    TipoDeItem.GENIO: _genio,
    TipoDeItem.BROCA: _broca,
    TipoDeItem.CAPACETE: _capacete,
}
