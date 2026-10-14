"""
temas.py - A "pele" visual das fases (masmorra, gelo, fogo, vento, terra).

Antes cada tema era um dicionario de cores e o desenho tinha
"if tema['estilo'] == 'gelo'" no meio. Agora vale COMPOSICAO SOBRE HERANCA:
um Tema nao e uma subclasse - e a combinacao de uma Paleta com tres
estrategias (Strategy):
    EstiloDeParede  -> ParedeDeTijolos | ParedeDeGelo | ParedeVulcanica | ParedeDeNuvens | ParedeDeTerra
    DetalheDePiso   -> PisoLiso        | PisoTrincado | PisoDeBrasas    | PisoDeEspirais | PisoDePedrinhas
    Clima           -> CeuLimpo        | Nevasca      | Brasas          | Ventania       | Poeira  (clima.py)
Um tema novo (deserto, lava...) e so uma nova combinacao dessas pecas,
registrada no CatalogoDeTemas - nenhuma outra classe muda (Aberto/Fechado).
"""
from __future__ import annotations

import math
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, Iterable

import pygame

from .clima import Brasas, CeuLimpo, Clima, Nevasca, Poeira, Ventania

Cor = tuple[int, int, int]

ALTURA_FACE = 18  # faixa da parede que aparece "de frente" quando ha chao abaixo


@dataclass(frozen=True)
class Paleta:
    fundo: Cor
    pisos: tuple[Cor, Cor, Cor, Cor]  # 4 variacoes para o chao nao ficar monotono
    parede: Cor
    junta: Cor
    face: Cor
    face_linha: Cor
    entrada: Cor
    portal_aro: Cor
    portal_miolo: Cor
    brilho: Cor  # halo do portal de saida


@dataclass(frozen=True)
class Texturas:
    """Imagens prontas de um tema (feitas por codigo, nao precisam de assets)."""

    pisos: tuple[pygame.Surface, ...]
    parede: pygame.Surface
    parede_face: pygame.Surface
    brilho: pygame.Surface


# ======================================================================
#  Estrategias de parede
# ======================================================================
class EstiloDeParede(ABC):
    @abstractmethod
    def pintar_topo(self, tamanho: int, paleta: Paleta) -> pygame.Surface:
        """Bloco de parede visto de cima."""

    @abstractmethod
    def detalhar_face(self, face: pygame.Surface, tamanho: int, rng: random.Random) -> None:
        """Acabamento da faixa frontal (a face ja vem pintada com a cor base)."""


class ParedeDeTijolos(EstiloDeParede):
    def __init__(self, junta_face: Cor) -> None:
        self._junta_face = junta_face

    def pintar_topo(self, tamanho: int, paleta: Paleta) -> pygame.Surface:
        s = pygame.Surface((tamanho, tamanho))
        s.fill(paleta.parede)
        for i, y in enumerate(range(0, tamanho, 14)):
            pygame.draw.line(s, paleta.junta, (0, y), (tamanho, y), 2)
            for x in range((i % 2) * 14, tamanho, 28):
                pygame.draw.line(s, paleta.junta, (x, y), (x, y + 14), 2)
        return s

    def detalhar_face(self, face: pygame.Surface, tamanho: int, rng: random.Random) -> None:
        for x in range(0, tamanho, 14):
            pygame.draw.line(face, self._junta_face, (x, tamanho - ALTURA_FACE), (x, tamanho), 1)


class ParedeDeGelo(EstiloDeParede):
    """Blocos de gelo grandes (como um iglu) com reflexos e pingentes."""

    def __init__(self, reflexo: Cor, pingentes: Cor) -> None:
        self._reflexo = reflexo
        self._pingentes = pingentes

    def pintar_topo(self, tamanho: int, paleta: Paleta) -> pygame.Surface:
        s = pygame.Surface((tamanho, tamanho))
        s.fill(paleta.parede)
        lado = 28
        for i, y in enumerate(range(0, tamanho, lado)):
            for x in range((i % 2) * lado // 2 - lado, tamanho, lado):
                pygame.draw.line(s, self._reflexo, (x + 5, y + 12), (x + 12, y + 5), 2)
                pygame.draw.line(s, self._reflexo, (x + 6, y + 19), (x + 19, y + 6), 1)
                pygame.draw.line(s, paleta.junta, (x, y), (x, y + lado), 2)
            pygame.draw.line(s, paleta.junta, (0, y), (tamanho, y), 2)
        return s

    def detalhar_face(self, face: pygame.Surface, tamanho: int, rng: random.Random) -> None:
        """Pingentes de gelo pendurados na borda de cima da face."""
        topo = tamanho - ALTURA_FACE + 1
        x = rng.randint(1, 4)
        while x < tamanho - 6:
            largura = rng.randint(4, 7)
            comprimento = rng.randint(6, 15)
            pygame.draw.polygon(face, self._pingentes,
                                [(x, topo), (x + largura, topo), (x + largura // 2, topo + comprimento)])
            x += largura + rng.randint(2, 6)


class ParedeVulcanica(EstiloDeParede):
    """Lajes de basalto cortadas por veios de lava, com lava escorrendo na face."""

    def __init__(self, lava: Cor, nucleo: Cor) -> None:
        self._lava = lava
        self._nucleo = nucleo
        self._halo = tuple(v // 2 for v in lava)

    def pintar_topo(self, tamanho: int, paleta: Paleta) -> pygame.Surface:
        rng = random.Random(tamanho)  # topo e face precisam sair iguais
        s = pygame.Surface((tamanho, tamanho))
        s.fill(paleta.parede)
        lado = 28
        for i, y in enumerate(range(0, tamanho, lado)):
            pygame.draw.line(s, paleta.junta, (0, y), (tamanho, y), 2)
            for x in range((i % 2) * lado // 2, tamanho, lado):
                pygame.draw.line(s, paleta.junta, (x, y), (x + rng.randint(-3, 3), y + lado), 2)
        for _ in range(2):  # veios de lava saindo do meio do bloco
            x, y = tamanho // 2 + rng.randint(-6, 6), tamanho // 2 + rng.randint(-6, 6)
            dx, dy = rng.choice((-1, 1)) * 7, rng.choice((-1, 1)) * 7
            pontos = [(x, y)]
            for _ in range(3):
                x = min(tamanho - 4, max(3, x + dx + rng.randint(-5, 5)))
                y = min(tamanho - 4, max(3, y + dy + rng.randint(-5, 5)))
                pontos.append((x, y))
            pygame.draw.lines(s, self._halo, False, pontos, 5)
            pygame.draw.lines(s, self._lava, False, pontos, 3)
            pygame.draw.lines(s, self._nucleo, False, pontos, 1)
        return s

    def detalhar_face(self, face: pygame.Surface, tamanho: int, rng: random.Random) -> None:
        """Gotas de lava escorrendo da borda de cima da face."""
        topo = tamanho - ALTURA_FACE + 1
        x = rng.randint(2, 8)
        while x < tamanho - 4:
            comprimento = rng.randint(4, 13)
            pygame.draw.line(face, self._lava, (x, topo), (x, topo + comprimento), 3)
            pygame.draw.circle(face, self._lava, (x, topo + comprimento), 2)
            pygame.draw.line(face, self._nucleo, (x, topo), (x, topo + comprimento - 2), 1)
            x += rng.randint(8, 16)


class ParedeDeNuvens(EstiloDeParede):
    """Nuvens fofas (bolhas sobrepostas) com redemoinhos de vento na face."""

    def __init__(self, luz: Cor, redemoinho: Cor) -> None:
        self._luz = luz
        self._redemoinho = redemoinho

    def pintar_topo(self, tamanho: int, paleta: Paleta) -> pygame.Surface:
        rng = random.Random(tamanho)  # topo e face precisam sair iguais
        s = pygame.Surface((tamanho, tamanho))
        s.fill(paleta.parede)
        for _ in range(9):
            x, y = rng.randrange(tamanho), rng.randrange(tamanho)
            r = rng.randint(7, 13)
            pygame.draw.circle(s, paleta.junta, (x + 2, y + 3), r)  # sombra da bolha
            pygame.draw.circle(s, paleta.parede, (x, y), r)
            pygame.draw.circle(s, self._luz, (x - r // 3, y - r // 3), r // 2)
        return s

    def detalhar_face(self, face: pygame.Surface, tamanho: int, rng: random.Random) -> None:
        topo = tamanho - ALTURA_FACE
        for x in range(0, tamanho + 9, 9):  # a nuvem "transborda" sobre a face
            pygame.draw.circle(face, self._luz, (x, topo), 5)
        x = rng.randint(3, 8)
        while x < tamanho - 14:  # redemoinhos de vento
            y = topo + rng.randint(6, 9)
            pygame.draw.arc(face, self._redemoinho, (x, y, 10, 8), 0, 4.7, 1)
            pygame.draw.line(face, self._redemoinho, (x + 5, y + 8), (x + 14, y + 8), 1)
            x += rng.randint(16, 24)


class ParedeDeTerra(EstiloDeParede):
    """Barro batido com pedras encravadas, musgo na borda e raizes na face."""

    def __init__(self, pedra: Cor, musgo: Cor, raiz: Cor) -> None:
        self._pedra = pedra
        self._brilho_pedra = tuple(min(255, v + 40) for v in pedra)
        self._musgo = musgo
        self._raiz = raiz

    def pintar_topo(self, tamanho: int, paleta: Paleta) -> pygame.Surface:
        rng = random.Random(tamanho)  # topo e face precisam sair iguais
        s = pygame.Surface((tamanho, tamanho))
        s.fill(paleta.parede)
        for _ in range(40):  # granulado da terra
            s.set_at((rng.randrange(tamanho), rng.randrange(tamanho)), paleta.junta)
        for _ in range(5):
            w, h = rng.randint(8, 15), rng.randint(6, 11)
            pedra = pygame.Rect(rng.randrange(0, tamanho - w), rng.randrange(0, tamanho - h), w, h)
            pygame.draw.ellipse(s, paleta.junta, pedra.move(1, 2))
            pygame.draw.ellipse(s, self._pedra, pedra)
            pygame.draw.ellipse(s, self._brilho_pedra, (pedra.x + 2, pedra.y + 1, w // 2, h // 3))
        return s

    def detalhar_face(self, face: pygame.Surface, tamanho: int, rng: random.Random) -> None:
        topo = tamanho - ALTURA_FACE + 1
        for x in range(0, tamanho, 2):  # musgo pendendo da borda
            pygame.draw.line(face, self._musgo, (x, topo), (x, topo + rng.randint(1, 4)), 2)
        x = rng.randint(3, 9)
        while x < tamanho - 3:  # raizes tortas descendo
            px, py = x, topo + 3
            for _ in range(rng.randint(2, 4)):
                nx, ny = px + rng.randint(-2, 2), py + rng.randint(2, 4)
                pygame.draw.line(face, self._raiz, (px, py), (nx, ny), 1)
                px, py = nx, ny
            x += rng.randint(7, 14)


# ======================================================================
#  Estrategias de piso
# ======================================================================
class DetalheDePiso(ABC):
    @abstractmethod
    def aplicar(self, piso: pygame.Surface, variacao: int, tamanho: int, rng: random.Random) -> None: ...


class PisoLiso(DetalheDePiso):
    """Null Object: chao sem detalhe extra."""

    def aplicar(self, piso: pygame.Surface, variacao: int, tamanho: int, rng: random.Random) -> None:
        pass


class PisoTrincado(DetalheDePiso):
    """Trinca fina e quebrada (gelo rachado) em metade das variacoes, com brilhos."""

    def __init__(self, cor: Cor) -> None:
        self._cor = cor
        self._brilho = tuple(min(255, v + 90) for v in cor)

    def aplicar(self, piso: pygame.Surface, variacao: int, tamanho: int, rng: random.Random) -> None:
        if variacao % 2:
            return
        t = tamanho
        x, y = rng.randrange(10, t - 10), rng.randrange(10, t - 10)
        for _ in range(rng.randint(2, 4)):
            nx = min(t - 4, max(3, x + rng.randint(-14, 14)))
            ny = min(t - 4, max(3, y + rng.randint(-14, 14)))
            pygame.draw.line(piso, self._cor, (x, y), (nx, ny), 1)
            x, y = nx, ny
        for _ in range(3):
            piso.set_at((rng.randrange(2, t - 2), rng.randrange(2, t - 2)), self._brilho)


class PisoDeBrasas(DetalheDePiso):
    """Chao de cinzas com rachaduras incandescentes em metade das variacoes."""

    def __init__(self, cor: Cor) -> None:
        self._cor = cor
        self._fagulha = tuple(min(255, v + 70) for v in cor)
        self._halo = tuple(v // 3 + 20 for v in cor)

    def aplicar(self, piso: pygame.Surface, variacao: int, tamanho: int, rng: random.Random) -> None:
        t = tamanho
        if variacao % 2 == 0:
            x, y = rng.randrange(10, t - 10), rng.randrange(10, t - 10)
            for _ in range(rng.randint(2, 3)):
                nx = min(t - 4, max(3, x + rng.randint(-12, 12)))
                ny = min(t - 4, max(3, y + rng.randint(-12, 12)))
                pygame.draw.line(piso, self._halo, (x, y), (nx, ny), 3)
                pygame.draw.line(piso, self._cor, (x, y), (nx, ny), 1)
                x, y = nx, ny
        for _ in range(2):
            piso.set_at((rng.randrange(2, t - 2), rng.randrange(2, t - 2)), self._fagulha)


class PisoDeEspirais(DetalheDePiso):
    """Lajes de templo com uma espiral de vento gravada em metade das variacoes."""

    def __init__(self, cor: Cor) -> None:
        self._cor = cor

    def aplicar(self, piso: pygame.Surface, variacao: int, tamanho: int, rng: random.Random) -> None:
        if variacao % 2:
            return
        cx, cy = rng.randrange(18, tamanho - 18), rng.randrange(18, tamanho - 18)
        pontos = [(cx + (1 + i * 0.45) * math.cos(i * 0.35), cy + (1 + i * 0.45) * math.sin(i * 0.35))
                  for i in range(26)]
        pygame.draw.lines(piso, self._cor, False, pontos, 1)


class PisoDePedrinhas(DetalheDePiso):
    """Chao de terra com pedrinhas soltas e, de vez em quando, um tufo de capim."""

    def __init__(self, pedrinha: Cor, capim: Cor) -> None:
        self._pedrinha = pedrinha
        self._brilho = tuple(min(255, v + 35) for v in pedrinha)
        self._capim = capim

    def aplicar(self, piso: pygame.Surface, variacao: int, tamanho: int, rng: random.Random) -> None:
        t = tamanho
        for _ in range(rng.randint(2, 4)):
            x, y = rng.randrange(4, t - 8), rng.randrange(4, t - 8)
            w, h = rng.randint(3, 5), rng.randint(2, 4)
            pygame.draw.ellipse(piso, self._pedrinha, (x, y, w, h))
            piso.set_at((x + 1, y), self._brilho)
        if variacao == 1:
            x, y = rng.randrange(10, t - 10), rng.randrange(14, t - 6)
            for dx in (-3, 0, 3):
                pygame.draw.line(piso, self._capim, (x, y), (x + dx, y - rng.randint(4, 7)), 1)


# ======================================================================
#  Tema = composicao das pecas acima
# ======================================================================
class Tema:
    SEMENTE_TEXTURAS = 7  # semente fixa: o mesmo tema sempre tem a mesma cara

    def __init__(self, nome: str, paleta: Paleta, parede: EstiloDeParede,
                 piso: DetalheDePiso, clima: Callable[[], Clima] = CeuLimpo) -> None:
        self._nome = nome
        self._paleta = paleta
        self._parede = parede
        self._piso = piso
        self._fabrica_de_clima = clima
        self._texturas: dict[int, Texturas] = {}  # cache por tamanho de tile

    @property
    def nome(self) -> str:
        return self._nome

    @property
    def paleta(self) -> Paleta:
        return self._paleta

    def criar_clima(self) -> Clima:
        """Cada fase recebe um clima NOVO (flocos proprios, relogio proprio)."""
        return self._fabrica_de_clima()

    def texturas(self, tamanho_tile: int) -> Texturas:
        if tamanho_tile not in self._texturas:
            self._texturas[tamanho_tile] = self._criar_texturas(tamanho_tile)
        return self._texturas[tamanho_tile]

    # ------------------------------------------------------------------
    def _criar_texturas(self, t: int) -> Texturas:
        rng = random.Random(self.SEMENTE_TEXTURAS)
        pisos = tuple(self._criar_piso(base, i, t, rng) for i, base in enumerate(self._paleta.pisos))
        parede = self._parede.pintar_topo(t, self._paleta)
        parede_face = self._parede.pintar_topo(t, self._paleta)
        self._pintar_face(parede_face, t, rng)
        return Texturas(pisos, parede, parede_face, self._criar_brilho(t))

    def _criar_piso(self, base: Cor, variacao: int, t: int, rng: random.Random) -> pygame.Surface:
        s = pygame.Surface((t, t))
        s.fill(base)
        mancha = tuple(max(0, v - 10) for v in base)
        for _ in range(10):  # "pontinhos" para nao ficar monotono
            x, y = rng.randrange(t), rng.randrange(t)
            s.set_at((x, y), mancha)
            s.set_at((min(t - 1, x + 1), y), mancha)
        self._piso.aplicar(s, variacao, t, rng)
        pygame.draw.rect(s, tuple(max(0, v - 8) for v in base), (0, 0, t, t), 1)
        return s

    def _pintar_face(self, face: pygame.Surface, t: int, rng: random.Random) -> None:
        pygame.draw.rect(face, self._paleta.face, (0, t - ALTURA_FACE, t, ALTURA_FACE))
        pygame.draw.line(face, self._paleta.face_linha, (0, t - ALTURA_FACE), (t, t - ALTURA_FACE), 2)
        self._parede.detalhar_face(face, t, rng)

    def _criar_brilho(self, t: int) -> pygame.Surface:
        """Halo do portal de saida (gradiente radial)."""
        raio = int(t * 2.2)
        r_cor, g_cor, b_cor = self._paleta.brilho
        s = pygame.Surface((raio * 2, raio * 2))
        for r in range(raio, 0, -2):
            k = (1 - r / raio) ** 2
            pygame.draw.circle(s, (int(r_cor * k), int(g_cor * k), int(b_cor * k)), (raio, raio), r)
        return s


def criar_tema_masmorra() -> Tema:
    return Tema(
        "masmorra",
        Paleta(fundo=(18, 16, 28),
               pisos=((46, 42, 64), (50, 46, 70), (44, 40, 60), (48, 44, 66)),
               parede=(96, 88, 134), junta=(70, 63, 102),
               face=(56, 50, 84), face_linha=(130, 122, 168),
               entrada=(60, 140, 90),
               portal_aro=(255, 214, 90), portal_miolo=(255, 240, 170),
               brilho=(255, 200, 70)),
        parede=ParedeDeTijolos(junta_face=(40, 35, 64)),
        piso=PisoLiso(),
        clima=CeuLimpo,
    )


def criar_tema_gelo() -> Tema:
    return Tema(
        "gelo",
        Paleta(fundo=(12, 20, 32),
               pisos=((34, 56, 82), (38, 61, 88), (32, 52, 77), (36, 58, 85)),
               parede=(188, 216, 240), junta=(126, 166, 206),
               face=(70, 118, 168), face_linha=(228, 244, 255),
               entrada=(110, 200, 235),
               portal_aro=(120, 225, 255), portal_miolo=(205, 245, 255),
               brilho=(110, 200, 255)),
        parede=ParedeDeGelo(reflexo=(242, 250, 255), pingentes=(208, 234, 252)),
        piso=PisoTrincado(cor=(78, 114, 152)),
        clima=Nevasca,
    )


def criar_tema_fogo() -> Tema:
    return Tema(
        "fogo",
        Paleta(fundo=(20, 10, 8),
               pisos=((44, 28, 26), (48, 30, 27), (40, 25, 23), (46, 29, 26)),
               parede=(88, 62, 56), junta=(52, 34, 31),
               face=(58, 36, 32), face_linha=(255, 130, 50),
               entrada=(255, 150, 70),
               portal_aro=(255, 120, 40), portal_miolo=(255, 220, 140),
               brilho=(255, 110, 30)),
        parede=ParedeVulcanica(lava=(255, 96, 24), nucleo=(255, 214, 90)),
        piso=PisoDeBrasas(cor=(196, 70, 24)),
        clima=Brasas,
    )


def criar_tema_vento() -> Tema:
    return Tema(
        "vento",
        Paleta(fundo=(14, 22, 26),
               pisos=((54, 80, 76), (58, 85, 80), (51, 76, 72), (56, 83, 78)),
               parede=(214, 224, 236), junta=(160, 174, 198),
               face=(120, 138, 168), face_linha=(240, 246, 255),
               entrada=(150, 240, 200),
               portal_aro=(160, 255, 220), portal_miolo=(225, 255, 245),
               brilho=(100, 230, 190)),
        parede=ParedeDeNuvens(luz=(246, 249, 255), redemoinho=(200, 214, 236)),
        piso=PisoDeEspirais(cor=(80, 112, 106)),
        clima=Ventania,
    )


def criar_tema_terra() -> Tema:
    return Tema(
        "terra",
        Paleta(fundo=(16, 12, 8),
               pisos=((62, 48, 34), (66, 51, 36), (58, 45, 32), (64, 49, 35)),
               parede=(122, 88, 58), junta=(86, 60, 38),
               face=(78, 54, 34), face_linha=(110, 160, 70),
               entrada=(140, 200, 90),
               portal_aro=(150, 230, 90), portal_miolo=(220, 255, 170),
               brilho=(130, 220, 70)),
        parede=ParedeDeTerra(pedra=(140, 128, 112), musgo=(92, 140, 60), raiz=(60, 40, 24)),
        piso=PisoDePedrinhas(pedrinha=(96, 84, 70), capim=(90, 130, 56)),
        clima=Poeira,
    )


class CatalogoDeTemas:
    """Registro dos temas disponiveis; o sorteio entre eles e feito pelo dominio."""

    def __init__(self, temas: Iterable[Tema]) -> None:
        self._temas = {tema.nome: tema for tema in temas}

    @classmethod
    def padrao(cls) -> CatalogoDeTemas:
        return cls([criar_tema_masmorra(), criar_tema_gelo(), criar_tema_fogo(),
                    criar_tema_vento(), criar_tema_terra()])

    @property
    def nomes(self) -> tuple[str, ...]:
        return tuple(self._temas)

    def obter(self, nome: str) -> Tema:
        try:
            return self._temas[nome]
        except KeyError:
            raise ValueError(f"tema desconhecido: {nome!r}") from None
