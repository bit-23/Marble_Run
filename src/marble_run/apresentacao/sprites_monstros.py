"""
sprites_monstros.py - Pixel art dos 12 monstros (grades de caracteres -> superficies, com cache).

Cada monstro tem uma PALETA (letra -> cor) e QUADROS de animacao desenhados como
texto ("." = transparente). Na hora de desenhar o sprite ganha:
    * contorno escuro automatico (fica legivel em qualquer chao);
    * pixels grandes (ESCALA) sem suavizar;
    * variacoes: olhos fechados (piscar/dormir), clarao (aviso de ataque),
      pedra cinza (extintor) e escurecido (cansado);
    * espelho horizontal (olhando para a esquerda).
Os olhos ("o" e "O") brilham ate no escuro: `olhos()` diz onde eles ficam.
A "vida" (respirar, tremer, babar, saltitar...) fica no bestiario.py.
"""
from __future__ import annotations

import math
from enum import Enum

import pygame

from ..dominio.monstros import TipoDeMonstro

Cor = tuple[int, int, int]
Grade = tuple[str, ...]

ESCALA = 3
CONTORNO: Cor = (14, 8, 18)
OLHOS = "oO"  # letras dos olhos: piscam e brilham no escuro


class Modo(Enum):
    PISCANDO = "piscando"   # olhos fechados
    CLARAO = "clarao"       # quase branco (aviso de ataque)
    PEDRA = "pedra"         # cinza (magman petrificado, fornalha apagada)
    CANSADO = "cansado"     # mais escuro


def _grade(texto: str) -> Grade:
    linhas = [linha.strip() for linha in texto.strip().splitlines() if linha.strip()]
    largura = max(len(linha) for linha in linhas)
    return tuple(linha.ljust(largura, ".") for linha in linhas)


def _juntar(*partes: str) -> Grade:
    return _grade("\n".join(partes))


def _trocar(grade: Grade, de: str, para: str) -> Grade:
    tabela = str.maketrans(de + para, para + de)
    return tuple(linha.translate(tabela) for linha in grade)


# ======================================================================
# Arte
# ======================================================================
_ARANHA_1 = _grade("""
......bbbb......
....bbBBBBbb....
...bBBhBBBhBb...
...bBhrrrrBBb...
l..bBrbrrbrBb..l
.l.bBBrrrrBBb.l.
..l.bBrbbrBb.l..
lll..bbbbbb..lll
...l.bobbob.l...
..l.bOObbOOb.l..
.l..bbBBBBbb..l.
l...bmbBBbmb...l
.....m.vv.m.....
........v.......
""")
_ARANHA_2 = _grade("""
......bbbb......
....bbBBBBbb....
...bBBhBBBhBb...
.l.bBhrrrrBBb.l.
l..bBrbrrbrBb..l
l..bBBrrrrBBb..l
.l..bBrbbrBb..l.
..ll.bbbbbb.ll..
.ll..bobbob..ll.
l...bOObbOOb...l
....bbBBBBbb....
....bmbBBbmb....
.....m..v.m.....
.........v......
""")

_MINOTAURO_CORPO = """
.rr............rr.
hHh............hHh
.hHh..FFFFFF..hHh.
..hhhFFffffFFhhh..
.....FoOffOoF.....
.....FffffffF.....
......ssssss......
......snssns......
......mtmmtm......
.......sggs.......
...FFFFffffFFFF...
..FffFccccccFffF..
.FffFccrcccccFffF.
.FfF.FcccrccF.FfF.
.sss..FffffF..sss.
.....PPppppPP.....
.....PppppppP.....
"""
_MINOTAURO_1 = _juntar(_MINOTAURO_CORPO, """
.....FfF..FfF.....
.....FfF..FfF.....
....kkkk..kkkk....
""")
_MINOTAURO_2 = _juntar(_MINOTAURO_CORPO, """
....FfF....FfF....
...FfF......FfF...
..kkkk......kkkk..
""")

_BONECO_TOPO = """
....kkkkkk....
....kkkkkk....
...KKKKKKKK...
..kkkkkkkkkk..
...wwwwwwww...
...wOowwoOw...
...wwwnnwww...
...mtmtmtmt...
...wmmmmmmw...
"""
_BONECO_BASE = """
..wwcwwwwwww..
..wwwwwmwwcW..
.wcwwwwwwwwwW.
wwwwwwwwwwcwwW
wwwcwwwmwwwwwW
.WwwwwwwwwcwW.
..WWWWWWWWWW..
"""
_BONECO_1 = _juntar(_BONECO_TOPO, """
.....WwwW.....
a..wwwwwwww..a
.awwwwwmwwwwa.
""", _BONECO_BASE)
_BONECO_2 = _juntar(_BONECO_TOPO, """
a....WwwW....a
.a.wwwwwwww.a.
..awwwwmwwwa..
""", _BONECO_BASE)

_YETI_CORPO = """
.....WWWWWWWW.....
....WwwwwwwwwW....
...WwwwwwwwwwwW...
...WwwffffffwwW...
..WwwFoffffoFwwW..
..WwwfmmmmmmfwwW..
..WwwftmmmmtfwwW..
.WwwwwtmmmmtwwwwW.
WwwwwwFFFFFFwwwwwW
WwwWwwwwwwwwwwWwwW
WwwWwwwwwwwwwwWwwW
WwwWWwwwwwwwwWWwwW
rcc.WwwwwwwwwW.ccr
.r..WwwwwwwwwW..r.
"""
_YETI_1 = _juntar(_YETI_CORPO, """
....WwwW..WwwW....
....WwwW..WwwW....
...WwwwW..WwwwW...
""")
_YETI_2 = _juntar(_YETI_CORPO, """
...WwwW....WwwW...
..WwwW......WwwW..
..WwwwW.....WwwwW.
""")

_MAGMAN_1 = _grade("""
......y.........
.....yYy...y....
....rYYYyryYr...
...rRyYYYyyRRr..
..rRkoyYYyokRr..
..rRyyYYYYyyRr..
.rRRkmmmmmmkRr..
.rRRRmYmYmmRRRr.
.ryRRRyyyyRRRyr.
.ry.rRRyyRRkr.y.
..y.rRRYYRRRr...
..y.rRRyyRRRr...
....rkRRRRRRr...
...rRRRyRRRyr...
...ryRRyRRrr....
...y.rRyyRr.....
.....rRyyRr.y...
....rRRyyRRr.y..
.rrRRRRyyRRRRrr.
rRRyyyyYYyyyyRRr
.rrrrRRRRRRrrrr.
""")
_MAGMAN_2 = _grade("""
........y.......
...y...yYy......
...rYyrYYYyr....
..rRRyyYYYyRRr..
..rRkoyYYyokRr..
..rRyyYYYYyyRr..
.rRRkmmmmmmkRr..
.rRRRmYmYmmRRRr.
.ryRRRyyyyRRRyr.
.r..rRRyyRRkr.y.
.y..rRRYYRRRr.y.
..y.rRRyyRRRr...
....rkRRRRRRr...
...rRRRyRRRyr...
...ryRRyRRrr....
.....rRyyRr.y...
...y.rRyyRr.y...
....rRRyyRRr....
.rryRRRyyRRRRrr.
rRRyyyyYYyyyyRRr
.rrrrRRRRRRrrrr.
""")
_MAGMAN_3 = _grade("""
.......y........
......yYy..y....
....ryYYYyryYr..
...rRyYYYyyRRr..
..rRkoyYYyokRr..
..rRyyYYYYyyRr..
.rRRkmmmmmmkRr..
.rRRRmYmYmmRRRr.
.ryRRRyyyyRRRyr.
.ry.rRRyyRRkr...
....rRRYYRRRr.y.
..y.rRRyyRRRr.y.
..y.rkRRRRRRr...
...rRRRyRRRyr...
...ryRRyRRrr....
...y.rRyyRr.....
.....rRyyRr.....
...y.rRyyRRr....
.rrRRRRyyRRRyrr.
rRRyyyYYYYyyyRRr
.rrrRRRRRRRRrrr.
""")

_FORNALHA_1 = _grade("""
.h.............ccc
hhh............cSc
SSSSSSSSSSSSSSSSSS
SllSlllSlllSlllSlS
SssSsssSsssSsssSsS
SSSSSSSSSSSSSSSSSS
SsSoossssssssooSsS
SsSsoossssssoosSsS
SSSSSSSSSSSSSSSSSS
SssStmtmtmtmtSsssS
SssSmMmMmMmMmSsssS
SssStmtmtmtmtSsssS
SSSSmmmmmmmmmSSSSS
SsSssSsssSsssSsSsS
SSSSSSSSSSSSSSSSSS
""")
_FORNALHA_2 = _trocar(_FORNALHA_1, "m", "M")

_AGUIA_ASAS_EM_CIMA = _grade("""
B..................B
BB................BB
BbB..............BbB
.BbB....wwww....BbB.
.BbhB..wwwwww..BhbB.
..BbhBBwowwowBBhbB..
...BbbbbwyywbbbbB...
....BrrrrryyrrrrB...
.....BbbbbbbbbbbB...
.......bbbbbb.......
.......TTTTTT.......
........T..T........
........f..f........
""")
_AGUIA_ASAS_EM_BAIXO = _grade("""
....................
........wwww........
.......wwwwww.......
.......wowwow.......
....BBbbwyywbbBB....
..BBbrrrryyrrrrbBB..
.BbbhbbbbbbbbbbhbbB.
BbbB..bbbbbbbb..BbbB
Bb....bbbbbbbb....bB
B......TTTTTT......B
........T..T........
........f..f........
""")

_TOUPEIRA_TOPO = """
....PPPPPP....
...PppppppP...
..PppppppppP..
..PpoppppopP..
..PpnnnnnnpP..
..PpmtmmtmpP..
"""
_TOUPEIRA_1 = _juntar(_TOUPEIRA_TOPO, """
.cPpbbbbbbpPc.
ccPpbbbbbbpPcc
c.PpbbbbbbpP.c
..PppbbbbppP..
DddddddddddddD
.DDDDDDDDDDDD.
""")
_TOUPEIRA_2 = _juntar(_TOUPEIRA_TOPO, """
c.PpbbbbbbpP.c
ccPpbbbbbbpPcc
.cPpbbbbbbpPc.
..PppbbbbppP..
DddddddddddddD
.DDDDDDDDDDDD.
""")
_MONTINHO_1 = _grade("""
.....dd.....
...ddDDdd...
..dDDddDDd..
.dDdDDDDdDd.
dDDDDDDDDDDd
""")
_MONTINHO_2 = _grade("""
.....d.d....
...dDdDdd...
..dDDdDDDd..
.dDDDDdDDDd.
dDDDDDDDDDDd
""")

_GOLEM_CORPO = """
.....SSSSSSSS.....
....SllllllllS....
....SlsscsssSS....
....SsOosssoOS....
....SsccccccsS....
.....SSSSSSSS.....
.SSSSSSScSSSSSSSS.
SlllSsssscsssSlllS
SlssSsssccsssSsslS
SsssSssscssssSssSS
SsssSsssscsssSssSS
SSSSSsssscsssSSSSS
SllS.SssssssS.SllS
SSSS.SSSSSSSS.SSSS
"""
_GOLEM_1 = _juntar(_GOLEM_CORPO, """
.....SssS..SssS...
.....SssS..SssS...
....SSSSS..SSSSS..
""")
_GOLEM_2 = _juntar(_GOLEM_CORPO, """
....SssS....SssS..
....SssS.....SssS.
...SSSSS.....SSSSS
""")

_COBRA_CABECA = """
.......GGGGGG...
......GghgghgG..
......GgogggoG..
......GggmmggG..
......GgtmmtgG..
.......GgyyyG...
........GyyyG...
.........GyG....
"""
_COBRA_1 = _juntar(_COBRA_CABECA, """
.........x.x....
...GGGGGGgyG....
..GghgggggyG....
.GgyyyyyyyyG....
.GgGGGGGGGgG....
..GggggghgggGG..
...GGyyyyyyyggG.
.....GGGGGGGGG..
""")
_COBRA_2 = _juntar(_COBRA_CABECA, """
................
...GGGGGGgyG....
..GghgggggyGG...
.GgyyyyyyyyyG...
..GgGGGGGGGgG...
...GgggghgggGG..
..GGyyyyyyyggG..
....GGGGGGGGG...
""")

_MUMIA_CORPO = """
....WWWWWW....
...WwwrwwwW...
...WdddWdddW..
...WdodddodW..
...WjdjdjdjW..
....WwwwwwW...
..WWWwwrwWWWww
.WwwwWwwwWwrww
.WwrWwwwwwWWW.
..WWwwWwrwW...
...WwwwwWwW...
...WrwWwwwwW..
...WwwwWwwrW..
"""
_MUMIA_1 = _juntar(_MUMIA_CORPO, """
...WwW..WwwW..
...Www..Wwww..
..WWww..WwWW..
""")
_MUMIA_2 = _juntar(_MUMIA_CORPO, """
...WwW...WwW..
..Www.....WwW.
.WWww.....WWWw
""")


def _quadros_do_tornado() -> tuple[Grade, ...]:
    """Funil escuro girando, com dois olhos vermelhos no meio e raios piscando."""
    quadros = []
    altura, largura = 15, 20
    for q in range(4):
        linhas = []
        for y in range(altura):
            meia = round(1.5 + 7 * (1 - y / (altura - 1)) ** 1.2)
            centro = largura // 2 + round(math.sin(y * 0.55 + q * math.pi / 2) * 1.6)
            linha = ["."] * largura
            for x in range(centro - meia, centro + meia):
                if 0 <= x < largura:
                    linha[x] = "gGd"[((x - centro) + y * 2 + q * 2) // 2 % 3]
            if y == 4:  # olhos
                linha[centro - 2], linha[centro + 1] = "o", "o"
                linha[centro - 3], linha[centro + 2] = "d", "d"
            if y in (2, 7) and q in (1, 3):  # raio
                x = centro + (3 if y == 2 else -4)
                linha[x] = "z"
            if y in (3, 8) and 0 <= centro + meia + 1 < largura and q % 2 == 0:
                linha[centro + meia + 1] = "x"
            if y in (5, 11) and 0 <= centro - meia - 2 < largura and q % 2 == 1:
                linha[centro - meia - 2] = "x"
            linhas.append("".join(linha))
        quadros.append(tuple(linhas))
    return tuple(quadros)


PALETAS: dict[TipoDeMonstro, dict[str, Cor]] = {
    TipoDeMonstro.ARANHA: {"b": (22, 14, 28), "B": (50, 34, 60), "h": (92, 66, 106), "r": (175, 18, 30),
                           "o": (255, 60, 45), "O": (255, 25, 25), "l": (14, 10, 18), "m": (235, 228, 205),
                           "v": (130, 255, 90), "_": (22, 14, 28)},
    TipoDeMonstro.MINOTAURO: {"h": (222, 212, 186), "H": (148, 138, 112), "r": (150, 18, 18), "f": (108, 56, 30),
                              "F": (66, 32, 18), "s": (158, 108, 88), "n": (30, 12, 8), "o": (255, 50, 25),
                              "O": (255, 210, 90), "m": (40, 8, 8), "t": (240, 235, 215), "g": (200, 160, 50),
                              "c": (132, 78, 44), "p": (58, 38, 78), "P": (38, 24, 56), "k": (38, 26, 22),
                              "_": (66, 32, 18)},
    TipoDeMonstro.BONECO_DE_NEVE: {"k": (18, 14, 28), "K": (150, 18, 38), "w": (118, 128, 165),
                                   "W": (72, 80, 116), "o": (120, 240, 255), "O": (210, 255, 255),
                                   "n": (70, 28, 60), "m": (14, 10, 24), "t": (220, 240, 255), "a": (48, 34, 28),
                                   "c": (40, 44, 70), "_": (72, 80, 116)},
    TipoDeMonstro.YETI: {"w": (208, 212, 220), "W": (138, 148, 168), "f": (70, 80, 110), "F": (40, 46, 70),
                         "o": (255, 40, 35), "m": (60, 10, 16), "t": (250, 250, 240), "c": (36, 36, 46),
                         "r": (150, 18, 24), "_": (40, 46, 70)},
    TipoDeMonstro.MAGMAN: {"r": (78, 18, 6), "R": (226, 78, 14), "y": (255, 170, 45), "Y": (255, 238, 150),
                           "k": (48, 12, 4), "o": (255, 250, 210), "m": (34, 4, 0), "_": (48, 12, 4)},
    TipoDeMonstro.FORNALHA: {"s": (88, 80, 80), "S": (48, 42, 42), "l": (122, 112, 108), "c": (40, 34, 34),
                             "h": (30, 22, 22), "o": (255, 120, 30), "t": (228, 218, 196), "m": (210, 55, 15),
                             "M": (255, 190, 60), "_": (48, 42, 42)},
    TipoDeMonstro.AGUIA: {"B": (26, 18, 16), "b": (56, 38, 30), "h": (88, 60, 46), "w": (152, 62, 56),
                          "y": (222, 204, 154), "o": (255, 40, 30), "r": (210, 200, 185), "T": (38, 28, 24),
                          "f": (230, 220, 190), "_": (152, 62, 56)},
    TipoDeMonstro.TORNADO: {"g": (112, 118, 134), "G": (72, 76, 92), "d": (38, 40, 54), "x": (100, 80, 62),
                            "o": (255, 40, 40), "z": (255, 248, 150)},
    TipoDeMonstro.TOUPEIRA: {"P": (38, 24, 22), "p": (70, 48, 42), "b": (122, 86, 74), "n": (232, 98, 120),
                             "o": (240, 240, 222), "c": (205, 195, 172), "t": (250, 245, 220), "m": (30, 8, 8),
                             "d": (110, 78, 48), "D": (70, 48, 30), "_": (70, 48, 42)},
    TipoDeMonstro.GOLEM: {"S": (42, 40, 38), "s": (80, 76, 70), "l": (112, 106, 98), "c": (255, 118, 28),
                          "o": (255, 150, 40), "O": (255, 230, 140), "_": (42, 40, 38)},
    TipoDeMonstro.COBRA: {"g": (42, 74, 40), "G": (16, 32, 18), "h": (158, 28, 30), "y": (152, 142, 82),
                          "o": (255, 40, 30), "m": (60, 10, 14), "t": (240, 240, 228), "x": (225, 40, 60),
                          "_": (42, 74, 40)},
    TipoDeMonstro.MUMIA: {"w": (172, 156, 116), "W": (104, 92, 64), "d": (20, 14, 10), "o": (120, 255, 110),
                          "j": (226, 220, 196), "r": (82, 92, 42), "_": (20, 14, 10)},
}
# "_" = cor da palpebra (o olho fechado vira esta cor)

QUADROS: dict[TipoDeMonstro, tuple[Grade, ...]] = {
    TipoDeMonstro.ARANHA: (_ARANHA_1, _ARANHA_2),
    TipoDeMonstro.MINOTAURO: (_MINOTAURO_1, _MINOTAURO_2),
    TipoDeMonstro.BONECO_DE_NEVE: (_BONECO_1, _BONECO_2),
    TipoDeMonstro.YETI: (_YETI_1, _YETI_2),
    TipoDeMonstro.MAGMAN: (_MAGMAN_1, _MAGMAN_2, _MAGMAN_3),
    TipoDeMonstro.FORNALHA: (_FORNALHA_1, _FORNALHA_2),
    TipoDeMonstro.AGUIA: (_AGUIA_ASAS_EM_CIMA, _AGUIA_ASAS_EM_BAIXO),
    TipoDeMonstro.TORNADO: _quadros_do_tornado(),
    TipoDeMonstro.TOUPEIRA: (_TOUPEIRA_1, _TOUPEIRA_2),
    TipoDeMonstro.GOLEM: (_GOLEM_1, _GOLEM_2),
    TipoDeMonstro.COBRA: (_COBRA_1, _COBRA_2),
    TipoDeMonstro.MUMIA: (_MUMIA_1, _MUMIA_2),
}
QUADROS_DO_MONTINHO: tuple[Grade, ...] = (_MONTINHO_1, _MONTINHO_2)


def _variar(cor: Cor, modos: frozenset[Modo]) -> Cor:
    r, g, b = cor
    if Modo.PEDRA in modos:
        cinza = int(0.3 * r + 0.55 * g + 0.15 * b)
        r = g = b = int(60 + cinza * 0.55)
    if Modo.CANSADO in modos:
        r, g, b = int(r * 0.72), int(g * 0.72), int(b * 0.78)
    if Modo.CLARAO in modos:  # vermelho de raiva antes de atacar
        r, g, b = (int(c + (alvo - c) * 0.6) for c, alvo in zip((r, g, b), (255, 70, 50)))
    return r, g, b


class SpritesDosMonstros:
    """Monta (e guarda) a superficie de cada quadro/variacao de cada monstro."""

    def __init__(self, escala: int = ESCALA) -> None:
        self._escala = escala
        self._cache: dict[tuple, pygame.Surface] = {}
        self._olhos: dict[tuple, tuple[tuple[int, int], ...]] = {}

    @property
    def escala(self) -> int:
        return self._escala

    def quantidade_de_quadros(self, tipo: TipoDeMonstro) -> int:
        return len(QUADROS[tipo])

    def imagem(self, tipo: TipoDeMonstro, quadro: int, espelhar: bool = False,
               modos: frozenset[Modo] = frozenset()) -> pygame.Surface:
        chave = (tipo, quadro % len(QUADROS[tipo]), espelhar, modos)
        if chave not in self._cache:
            grade = self._normalizada(tipo, chave[1])
            img = self._renderizar(grade, PALETAS[tipo], modos)
            self._cache[chave] = pygame.transform.flip(img, True, False) if espelhar else img
        return self._cache[chave]

    def olhos(self, tipo: TipoDeMonstro, quadro: int, espelhar: bool) -> tuple[tuple[int, int], ...]:
        """Centro de cada pixel de olho, em pixels da imagem (ja com escala e espelho)."""
        chave = (tipo, quadro % len(QUADROS[tipo]), espelhar)
        if chave not in self._olhos:
            grade = self._normalizada(tipo, chave[1])
            largura = (len(grade[0]) + 2) * self._escala
            pontos = []
            for y, linha in enumerate(grade):
                for x, letra in enumerate(linha):
                    if letra in OLHOS:
                        px = (x + 1) * self._escala + self._escala // 2
                        pontos.append((largura - px if espelhar else px, (y + 1) * self._escala + self._escala // 2))
            self._olhos[chave] = tuple(pontos)
        return self._olhos[chave]

    def cor_dos_olhos(self, tipo: TipoDeMonstro) -> Cor:
        return PALETAS[tipo]["o"]

    def montinho(self, quadro: int) -> pygame.Surface:
        chave = ("montinho", quadro % 2)
        if chave not in self._cache:
            self._cache[chave] = self._renderizar(QUADROS_DO_MONTINHO[quadro % 2], PALETAS[TipoDeMonstro.TOUPEIRA],
                                                  frozenset())
        return self._cache[chave]

    def icone(self, tipo: TipoDeMonstro, tamanho: int) -> pygame.Surface:
        """Quadro parado, encaixado num quadrado (paleta do editor da arena)."""
        chave = ("icone", tipo, tamanho)
        if chave not in self._cache:
            img = self._renderizar(self._normalizada(tipo, 0), PALETAS[tipo], frozenset(), escala=1)
            k = min(tamanho / img.get_width(), tamanho / img.get_height())
            img = pygame.transform.scale(img, (max(1, round(img.get_width() * k)), max(1, round(img.get_height() * k))))
            quadrado = pygame.Surface((tamanho, tamanho), pygame.SRCALPHA)
            quadrado.blit(img, img.get_rect(center=(tamanho // 2, tamanho // 2)))
            self._cache[chave] = quadrado
        return self._cache[chave]

    # ------------------------------------------------------------------
    @staticmethod
    def _normalizada(tipo: TipoDeMonstro, quadro: int) -> Grade:
        """Todos os quadros do monstro com o mesmo tamanho (pes alinhados embaixo, centralizados)."""
        quadros = QUADROS[tipo]
        largura = max(len(g[0]) for g in quadros)
        altura = max(len(g) for g in quadros)
        grade = quadros[quadro]
        sobra = largura - len(grade[0])
        esquerda = sobra // 2
        linhas = ["." * esquerda + linha + "." * (sobra - esquerda) for linha in grade]
        return tuple(["." * largura] * (altura - len(linhas)) + linhas)

    def _renderizar(self, grade: Grade, paleta: dict[str, Cor], modos: frozenset[Modo],
                    escala: int | None = None) -> pygame.Surface:
        return renderizar_grade(grade, paleta, self._escala if escala is None else escala, modos)


def renderizar_grade(grade: Grade, paleta: dict[str, Cor], escala: int,
                     modos: frozenset[Modo] = frozenset()) -> pygame.Surface:
    """Grade de letras -> superficie com contorno escuro e pixels grandes (usado tambem pelo genio)."""
    largura, altura = len(grade[0]) + 2, len(grade) + 2  # 1 pixel de folga para o contorno
    base = pygame.Surface((largura, altura), pygame.SRCALPHA)
    palpebra = paleta.get("_", CONTORNO)
    cheios = set()
    for y, linha in enumerate(grade):
        for x, letra in enumerate(linha):
            if letra == ".":
                continue
            cor = palpebra if letra in OLHOS and Modo.PISCANDO in modos else paleta.get(letra, (255, 0, 255))
            base.set_at((x + 1, y + 1), (*_variar(cor, modos), 255))
            cheios.add((x + 1, y + 1))
    contorno = _variar(CONTORNO, modos - {Modo.CLARAO})
    for x, y in cheios:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            vizinho = (x + dx, y + dy)
            if vizinho not in cheios:
                base.set_at(vizinho, (*contorno, 255))
    return pygame.transform.scale(base, (largura * escala, altura * escala))
