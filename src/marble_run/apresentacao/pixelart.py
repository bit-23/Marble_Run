"""
pixelart.py - O visual "pixelado e desenhado a mao" dos menus.

    FontePixel    -> fonte bitmap 5x7 desenhada por codigo (nao precisa de .ttf)
    CamadaPixel   -> tela de baixa resolucao (480x320) ampliada 2x sem suavizar
    caixa_rabiscada / linha_rabiscada -> contornos tortinhos, como rabisco de lapis;
                     trocando a semente a cada poucos quadros o traco "ferve"
                     (efeito classico de animacao desenhada a mao)
    pixelizar     -> deixa qualquer sprite com cara de pixel art
    ExplosaoDePixels -> clarao + onda de choque + pixels voando (codigo secreto)
    FundoDoMenu   -> labirinto pixelado passando devagar atras dos menus
"""
from __future__ import annotations

import math
import random
import unicodedata

import pygame

from ..dominio.geradores import GeradorBacktracker

Cor = tuple[int, int, int]
CorA = tuple[int, int, int, int]

ESCALA = 2                  # 1 pixel da camada = 2x2 pixels na tela
TAMANHO_CAMADA = (480, 320)  # 960x640 / 2

# Cada glifo: 7 linhas de 5 colunas ("#" = pixel aceso)
_GLIFOS_FONTE = """
A .###. #...# #...# ##### #...# #...# #...#
B ####. #...# #...# ####. #...# #...# ####.
C .###. #...# #.... #.... #.... #...# .###.
D ####. #...# #...# #...# #...# #...# ####.
E ##### #.... #.... ####. #.... #.... #####
F ##### #.... #.... ####. #.... #.... #....
G .###. #...# #.... #.### #...# #...# .####
H #...# #...# #...# ##### #...# #...# #...#
I .###. ..#.. ..#.. ..#.. ..#.. ..#.. .###.
J ..### ...#. ...#. ...#. #..#. #..#. .##..
K #...# #..#. #.#.. ##... #.#.. #..#. #...#
L #.... #.... #.... #.... #.... #.... #####
M #...# ##.## #.#.# #.#.# #...# #...# #...#
N #...# #...# ##..# #.#.# #..## #...# #...#
O .###. #...# #...# #...# #...# #...# .###.
P ####. #...# #...# ####. #.... #.... #....
Q .###. #...# #...# #...# #.#.# #..#. .##.#
R ####. #...# #...# ####. #.#.. #..#. #...#
S .#### #.... #.... .###. ....# ....# ####.
T ##### ..#.. ..#.. ..#.. ..#.. ..#.. ..#..
U #...# #...# #...# #...# #...# #...# .###.
V #...# #...# #...# #...# #...# .#.#. ..#..
W #...# #...# #...# #.#.# #.#.# #.#.# .#.#.
X #...# #...# .#.#. ..#.. .#.#. #...# #...#
Y #...# #...# .#.#. ..#.. ..#.. ..#.. ..#..
Z ##### ....# ...#. ..#.. .#... #.... #####
0 .###. #...# #..## #.#.# ##..# #...# .###.
1 ..#.. .##.. ..#.. ..#.. ..#.. ..#.. .###.
2 .###. #...# ....# ...#. ..#.. .#... #####
3 ####. ....# ....# .###. ....# ....# ####.
4 ...#. ..##. .#.#. #..#. ##### ...#. ...#.
5 ##### #.... ####. ....# ....# #...# .###.
6 .###. #.... #.... ####. #...# #...# .###.
7 ##### ....# ...#. ..#.. .#... .#... .#...
8 .###. #...# #...# .###. #...# #...# .###.
9 .###. #...# #...# .#### ....# ....# .###.
. ..... ..... ..... ..... ..... .##.. .##..
, ..... ..... ..... ..... .##.. ..#.. .#...
: ..... .##.. .##.. ..... .##.. .##.. .....
! ..#.. ..#.. ..#.. ..#.. ..#.. ..... ..#..
? .###. #...# ....# ...#. ..#.. ..... ..#..
- ..... ..... ..... ##### ..... ..... .....
+ ..... ..#.. ..#.. ##### ..#.. ..#.. .....
/ ....# ....# ...#. ..#.. .#... #.... #....
% ##..# ##..# ...#. ..#.. .#... #..## #..##
( ...#. ..#.. .#... .#... .#... ..#.. ...#.
) .#... ..#.. ...#. ...#. ...#. ..#.. .#...
[ .###. .#... .#... .#... .#... .#... .###.
] .###. ...#. ...#. ...#. ...#. ...#. .###.
< ...#. ..#.. .#... #.... .#... ..#.. ...#.
> .#... ..#.. ...#. ....# ...#. ..#.. .#...
' ..#.. ..#.. .#... ..... ..... ..... .....
" .#.#. .#.#. ..... ..... ..... ..... .....
| ..#.. ..#.. ..#.. ..#.. ..#.. ..#.. ..#..
_ ..... ..... ..... ..... ..... ..... #####
= ..... ..... ##### ..... ##### ..... .....
* ..... #.#.# .###. ##### .###. #.#.# .....
"""


def _ler_glifos() -> dict[str, tuple[str, ...]]:
    glifos = {" ": ("....." ,) * 7}
    for linha in _GLIFOS_FONTE.strip().splitlines():
        caractere, *linhas = linha.split(" ")
        glifos[caractere] = tuple(linhas)
    return glifos


class FontePixel:
    """Fonte bitmap 5x7. `escala` = tamanho de cada pixel da letra."""

    LARGURA, ALTURA, ESPACO = 5, 7, 1
    SOMBRA: Cor = (20, 12, 30)
    LIMITE_DO_CACHE = 400

    def __init__(self) -> None:
        self._glifos = _ler_glifos()
        self._cache: dict[tuple[str, int, tuple, tuple | None], pygame.Surface] = {}

    def normalizar(self, texto: str) -> str:
        """Maiusculas sem acento; o que a fonte nao tem vira '?'."""
        sem_acento = unicodedata.normalize("NFD", texto)
        sem_acento = "".join(c for c in sem_acento if unicodedata.category(c) != "Mn").upper()
        return "".join(c if c in self._glifos else "?" for c in sem_acento)

    def medir(self, texto: str, escala: int = 1) -> tuple[int, int]:
        n = len(texto)
        largura = (n * (self.LARGURA + self.ESPACO) - self.ESPACO) * escala if n else 0
        return largura, self.ALTURA * escala

    def render(self, texto: str, escala: int = 1, cor: Cor = (255, 255, 255),
               sombra: Cor | None = SOMBRA) -> pygame.Surface:
        texto = self.normalizar(texto)
        chave = (texto, escala, tuple(cor), tuple(sombra) if sombra else None)
        if chave not in self._cache:
            if len(self._cache) > self.LIMITE_DO_CACHE:
                self._cache.clear()
            self._cache[chave] = self._desenhar(texto, escala, cor, sombra)
        return self._cache[chave]

    def escrever(self, superficie: pygame.Surface, texto: str, escala: int, cor: Cor, *,
                 centro: tuple[int, int] | None = None, canto: tuple[int, int] | None = None,
                 direita: tuple[int, int] | None = None, sombra: Cor | None = SOMBRA) -> pygame.Rect:
        """Escreve centralizado, a partir do canto superior esquerdo ou alinhado a direita."""
        img = self.render(texto, escala, cor, sombra)
        if centro is not None:
            ret = img.get_rect(center=centro)
        elif direita is not None:
            ret = img.get_rect(topright=direita)
        else:
            ret = img.get_rect(topleft=canto or (0, 0))
        superficie.blit(img, ret)
        return ret

    def _desenhar(self, texto: str, escala: int, cor: Cor, sombra: Cor | None) -> pygame.Surface:
        largura, altura = self.medir(texto, escala)
        extra = escala if sombra else 0
        s = pygame.Surface((max(1, largura + extra), altura + extra), pygame.SRCALPHA)
        camadas = ((sombra, extra), (cor, 0)) if sombra else ((cor, 0),)
        for tinta, desvio in camadas:
            for i, caractere in enumerate(texto):
                x0 = i * (self.LARGURA + self.ESPACO) * escala + desvio
                for y, linha in enumerate(self._glifos[caractere]):
                    for x, pixel in enumerate(linha):
                        if pixel == "#":
                            s.fill(tinta, (x0 + x * escala, y * escala + desvio, escala, escala))
        return s


class CamadaPixel:
    """Desenha em baixa resolucao e amplia 2x sem suavizar = pixels grandes e nitidos."""

    def __init__(self, tamanho: tuple[int, int] = TAMANHO_CAMADA) -> None:
        self.superficie = pygame.Surface(tamanho, pygame.SRCALPHA)

    def limpar(self) -> None:
        self.superficie.fill((0, 0, 0, 0))

    def apresentar(self, tela: pygame.Surface, deslocamento: tuple[int, int] = (0, 0)) -> None:
        tela.blit(pygame.transform.scale(self.superficie, tela.get_size()), deslocamento)

    @staticmethod
    def da_tela(pos: tuple[int, int]) -> tuple[int, int]:
        """Converte uma posicao do mouse (tela) para a camada."""
        return pos[0] // ESCALA, pos[1] // ESCALA


# ======================================================================
#  Traco "desenhado a mao"
# ======================================================================
def _tremer(rng: random.Random) -> int:
    return rng.choice((-1, 0, 0, 0, 1))


def linha_rabiscada(sup: pygame.Surface, inicio: tuple[float, float], fim: tuple[float, float],
                    cor: Cor | CorA, rng: random.Random, passo: int = 7, largura: int = 1) -> None:
    """Linha levemente torta: quebrada em pedacos com pontas tremidas."""
    (x0, y0), (x1, y1) = inicio, fim
    tamanho = max(1, int(math.hypot(x1 - x0, y1 - y0) // passo))
    pontos = []
    for i in range(tamanho + 1):
        k = i / tamanho
        tremor = 0 if i in (0, tamanho) else _tremer(rng)
        if abs(x1 - x0) >= abs(y1 - y0):
            pontos.append((round(x0 + (x1 - x0) * k), round(y0 + (y1 - y0) * k) + tremor))
        else:
            pontos.append((round(x0 + (x1 - x0) * k) + tremor, round(y0 + (y1 - y0) * k)))
    pygame.draw.lines(sup, cor, False, pontos, largura)


def caixa_rabiscada(sup: pygame.Surface, ret: pygame.Rect, borda: Cor, fundo: CorA | None = None,
                    semente: int = 0, sombra: bool = True, hachura: Cor | None = None) -> None:
    """Retangulo com cara de desenhado: sombra, contorno duplo tremido e cantos que 'passam'."""
    rng = random.Random(semente)
    if sombra:
        sup.fill((10, 6, 18, 150), ret.move(3, 3))
    if fundo is not None:
        sup.fill(fundo, ret)
    if hachura is not None:  # riscos de lapis no rodape, como pintura a mao
        for x in range(ret.left + 3, ret.right - 6, 5):
            pygame.draw.line(sup, hachura, (x, ret.bottom - 2), (x + 4, ret.bottom - 6))
    esq, dir_, topo, base = ret.left, ret.right - 1, ret.top, ret.bottom - 1
    escura = tuple(max(0, c - 70) for c in borda[:3])
    for cor, desvio in ((escura, 1), (borda, 0)):  # dois tracos = esboco de lapis
        linha_rabiscada(sup, (esq - 2, topo + desvio), (dir_ + 2, topo + desvio), cor, rng)
        linha_rabiscada(sup, (esq - 1, base - desvio), (dir_ + 1, base - desvio), cor, rng)
        linha_rabiscada(sup, (esq + desvio, topo - 2), (esq + desvio, base + 2), cor, rng)
        linha_rabiscada(sup, (dir_ - desvio, topo - 1), (dir_ - desvio, base + 1), cor, rng)


def semente_fervendo(base: int, tempo: float, quadros_por_segundo: float = 6) -> int:
    """Muda a semente algumas vezes por segundo: o contorno 'ferve' como desenho animado."""
    return base * 31 + int(tempo * quadros_por_segundo) % 3


def pixelizar(imagem: pygame.Surface, altura: int, fator: int = 2) -> pygame.Surface:
    """Reduz para `altura / fator` e amplia de volta sem suavizar (cara de pixel art)."""
    largura = max(1, round(imagem.get_width() * altura / imagem.get_height()))
    pequena = pygame.transform.smoothscale(imagem, (max(1, largura // fator), max(1, altura // fator)))
    return pygame.transform.scale(pequena, (pequena.get_width() * fator, pequena.get_height() * fator))


class ExplosaoDePixels:
    """Explosao estilo 8-bit: clarao, onda de choque e pixels voando com gravidade."""

    CORES: tuple[Cor, ...] = ((255, 214, 90), (255, 255, 255), (255, 140, 60), (170, 150, 220),
                              (120, 220, 255), (255, 90, 120))
    DURACAO_DA_ONDA = 0.45
    RAIO_DA_ONDA = 70

    class _Pixel:
        __slots__ = ("x", "y", "vx", "vy", "vida", "vida_total", "tamanho", "cor")

    def __init__(self, x: float, y: float, quantidade: int = 110, sorteio: random.Random | None = None) -> None:
        rng = sorteio if sorteio is not None else random.Random()
        self._x, self._y = x, y
        self._tempo = 0.0
        self._pixels = []
        for _ in range(quantidade):
            p = self._Pixel()
            ang = rng.uniform(0, math.tau)
            rapidez = rng.uniform(50, 260)
            p.x, p.y = x + rng.uniform(-20, 20), y + rng.uniform(-4, 4)
            p.vx, p.vy = math.cos(ang) * rapidez, math.sin(ang) * rapidez * 0.7 - 50
            p.vida = p.vida_total = rng.uniform(0.6, 1.5)
            p.tamanho = rng.choice((1, 2, 2, 3))
            p.cor = rng.choice(self.CORES)
            self._pixels.append(p)

    @property
    def tempo(self) -> float:
        return self._tempo

    @property
    def terminou(self) -> bool:
        return not self._pixels and self._tempo > self.DURACAO_DA_ONDA

    def atualizar(self, dt: float) -> None:
        self._tempo += dt
        for p in self._pixels:
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.vx *= 0.985
            p.vy += 200 * dt  # gravidade
            p.vida -= dt
        self._pixels = [p for p in self._pixels if p.vida > 0]

    def desenhar(self, sup: pygame.Surface) -> None:
        if self._tempo < 0.12:  # clarao
            raio = int(10 + 120 * self._tempo)
            pygame.draw.circle(sup, (255, 255, 240), (round(self._x), round(self._y)), raio)
        if self._tempo < self.DURACAO_DA_ONDA:  # onda de choque
            k = self._tempo / self.DURACAO_DA_ONDA
            pygame.draw.circle(sup, (255, 230, 160), (round(self._x), round(self._y)),
                               int(8 + self.RAIO_DA_ONDA * k), max(1, int(4 * (1 - k))))
        for p in self._pixels:
            if p.vida < p.vida_total * 0.3 and int(p.vida * 20) % 2:  # pisca antes de sumir
                continue
            sup.fill(p.cor, (round(p.x), round(p.y), p.tamanho, p.tamanho))


# ======================================================================
#  Fundo animado dos menus
# ======================================================================
class FundoDoMenu:
    """Labirinto pixelado deslizando na diagonal, com brilhinhos piscando.

    E um objeto compartilhado entre as telas de menu: trocar de tela nao
    "reinicia" o fundo.
    """

    TILE = 8
    VELOCIDADE = (9.0, 5.0)  # pixels da camada por segundo
    PAREDE: Cor = (58, 50, 92)
    PAREDE_LUZ: Cor = (96, 86, 140)
    CHAO: Cor = (26, 22, 42)
    CHAO_PONTO: Cor = (36, 31, 58)

    def __init__(self, sorteio: random.Random | None = None) -> None:
        self._rng = sorteio if sorteio is not None else random.Random(2024)
        self._mapa = self._desenhar_labirinto()
        self._camada = pygame.Surface(TAMANHO_CAMADA)
        self._vinheta = self._criar_vinheta()
        self._brilhos = [(self._rng.randrange(TAMANHO_CAMADA[0]), self._rng.randrange(TAMANHO_CAMADA[1]),
                          self._rng.uniform(0, math.tau)) for _ in range(40)]
        self._tempo = 0.0

    def atualizar(self, dt: float) -> None:
        self._tempo += dt

    def desenhar(self, tela: pygame.Surface) -> None:
        c = self._camada
        mw, mh = self._mapa.get_size()
        ox = int(self._tempo * self.VELOCIDADE[0]) % mw
        oy = int(self._tempo * self.VELOCIDADE[1]) % mh
        for dx in (0, mw):
            for dy in (0, mh):
                c.blit(self._mapa, (dx - ox, dy - oy))
        for x, y, fase in self._brilhos:
            k = math.sin(self._tempo * 2.5 + fase)
            if k > 0.6:
                cor = (255, 230, 150) if k > 0.9 else (170, 150, 220)
                c.fill(cor, (x, y, 1, 1))
                if k > 0.9:
                    c.fill((140, 120, 80), (x - 1, y, 3, 1))
                    c.fill((140, 120, 80), (x, y - 1, 1, 3))
        c.blit(self._vinheta, (0, 0))
        tela.blit(pygame.transform.scale(c, tela.get_size()), (0, 0))

    def _desenhar_labirinto(self) -> pygame.Surface:
        lab = GeradorBacktracker(proporcao_lacos=0.12).gerar(31, 21, self._rng)
        t = self.TILE
        s = pygame.Surface((lab.colunas * t, lab.linhas * t))
        s.fill(self.CHAO)
        for linha in range(lab.linhas):
            for coluna in range(lab.colunas):
                x, y = coluna * t, linha * t
                if lab.eh_parede(coluna, linha):
                    s.fill(self.PAREDE, (x, y, t, t))
                    if not lab.eh_parede(coluna, linha - 1):
                        s.fill(self.PAREDE_LUZ, (x, y, t, 1))
                    if not lab.eh_parede(coluna, linha + 1):
                        s.fill((40, 34, 66), (x, y + t - 2, t, 2))  # faixa de sombra
                elif (coluna * 7 + linha * 3) % 5 == 0:
                    s.fill(self.CHAO_PONTO, (x + 3, y + 4, 1, 1))
        return s

    @staticmethod
    def _criar_vinheta() -> pygame.Surface:
        """Escurece o meio (onde ficam os menus) e as bordas."""
        s = pygame.Surface(TAMANHO_CAMADA, pygame.SRCALPHA)
        s.fill((8, 6, 16, 120))
        largura, altura = TAMANHO_CAMADA
        for i in range(24):
            pygame.draw.rect(s, (8, 6, 16, 235 - i * 5), (i, i, largura - 2 * i, altura - 2 * i), 1)
        return s
