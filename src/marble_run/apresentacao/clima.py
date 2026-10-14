"""
clima.py - Efeitos de atmosfera desenhados por cima da fase.

Polimorfismo: o Cenario so chama `clima.atualizar()` e `clima.desenhar()`.
Ele nao sabe (nem pergunta) se esta nevando - antes havia um
"if tema['neve']" no meio do desenho.

    CeuLimpo | Nevasca (gelo) | Brasas (fogo) | Ventania (vento) | Poeira (terra)
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


# ======================================================================
#  Fogo
# ======================================================================
class _Brasa:
    """Fagulha subindo e tremulando. `profundidade` vai de 0.3 (longe) a 1.0 (perto)."""

    __slots__ = ("_x", "_y", "_profundidade", "_fase")

    def __init__(self, x: float, y: float, profundidade: float, fase: float) -> None:
        self._x = x
        self._y = y
        self._profundidade = profundidade
        self._fase = fase

    def subir(self, tempo: float, dt: float) -> None:
        prof = self._profundidade
        self._x += 25 * math.sin(tempo * 1.7 + self._fase) * prof * dt
        self._y -= (25 + 75 * prof) * dt

    def desenhar(self, tela: pygame.Surface, camera: Deslocamento, largura: int, altura: int,
                 tempo: float, halo: pygame.Surface) -> None:
        prof = self._profundidade
        paralaxe = 1.0 + 0.6 * prof
        sx = int(self._x - camera[0] * paralaxe) % largura
        sy = int(self._y - camera[1] * paralaxe) % altura
        k = prof * (0.6 + 0.4 * math.sin(tempo * 9 + self._fase * 3))  # tremulando
        if prof > 0.75:  # as mais proximas brilham em volta
            r = halo.get_width() // 2
            tela.blit(halo, (sx - r, sy - r), special_flags=pygame.BLEND_RGB_ADD)
        cor = (int(150 + 105 * k), int(60 + 160 * k), int(20 + 60 * k * k))
        pygame.draw.circle(tela, cor, (sx, sy), 1 if prof < 0.6 else 2)


class Brasas(Clima):
    """Fagulhas subindo do chao de lava - brilham ate no escuro."""

    def __init__(self, quantidade: int = 120, aleatorio: random.Random | None = None) -> None:
        self._quantidade = quantidade
        self._aleatorio = aleatorio
        self._brasas: list[_Brasa] = []  # criadas no 1o desenho (precisa do tamanho da tela)
        self._tempo = 0.0
        self._halo = self._criar_halo(7)

    def atualizar(self, dt: float) -> None:
        self._tempo += dt
        for brasa in self._brasas:
            brasa.subir(self._tempo, dt)

    def desenhar(self, tela: pygame.Surface, camera: Deslocamento) -> None:
        largura, altura = tela.get_size()
        if not self._brasas:
            rng = self._aleatorio if self._aleatorio is not None else random.Random()
            self._brasas = [_Brasa(rng.uniform(0, largura), rng.uniform(0, altura),
                                   rng.uniform(0.3, 1.0), rng.uniform(0, math.tau))
                            for _ in range(self._quantidade)]
        for brasa in self._brasas:
            brasa.desenhar(tela, camera, largura, altura, self._tempo, self._halo)

    @staticmethod
    def _criar_halo(raio: int) -> pygame.Surface:
        s = pygame.Surface((raio * 2, raio * 2))
        for r in range(raio, 0, -1):
            k = (1 - r / raio) ** 2
            pygame.draw.circle(s, (int(170 * k), int(60 * k), int(10 * k)), (raio, raio), r)
        return s


# ======================================================================
#  Vento
# ======================================================================
class _Lufada:
    """Risco de vento que aparece e some, cortando a tela na horizontal."""

    __slots__ = ("_x", "_y", "_profundidade", "_fase", "_comprimento")

    def __init__(self, x: float, y: float, profundidade: float, fase: float, comprimento: int) -> None:
        self._x = x
        self._y = y
        self._profundidade = profundidade
        self._fase = fase
        self._comprimento = comprimento

    def soprar(self, forca: float, tempo: float, dt: float) -> None:
        self._x += forca * (0.5 + self._profundidade) * dt
        self._y += 12 * math.sin(tempo * 3 + self._fase) * dt

    def desenhar(self, tela: pygame.Surface, camera: Deslocamento, largura: int, altura: int,
                 tempo: float) -> None:
        if math.sin(tempo * 0.8 + self._fase) < 0.2:  # so aparece em parte do tempo
            return
        prof, comp = self._profundidade, self._comprimento
        paralaxe = 1.0 + 0.6 * prof
        sx = int(self._x - camera[0] * paralaxe) % (largura + comp * 2) - comp
        sy = int(self._y - camera[1] * paralaxe) % altura
        tom = int(70 + 120 * prof)
        onda = 3 * math.sin(tempo * 4 + self._fase)
        pontos = [(sx, sy), (sx - comp * 0.5, sy + onda), (sx - comp, sy)]
        pygame.draw.lines(tela, (tom, min(255, tom + 10), min(255, tom + 20)), False, pontos,
                          1 if prof < 0.7 else 2)


class _Folha:
    """Folha rodopiando levada pelo vento."""

    __slots__ = ("_x", "_y", "_profundidade", "_fase", "_angulo", "_giro", "_cor")

    def __init__(self, x: float, y: float, profundidade: float, fase: float, giro: float,
                 cor: tuple[int, int, int]) -> None:
        self._x = x
        self._y = y
        self._profundidade = profundidade
        self._fase = fase
        self._angulo = fase
        self._giro = giro
        self._cor = cor

    def soprar(self, forca: float, tempo: float, dt: float) -> None:
        prof = self._profundidade
        self._x += forca * 0.6 * prof * dt
        self._y += (20 + 40 * math.sin(tempo * 2 + self._fase)) * prof * dt
        self._angulo += self._giro * dt

    def desenhar(self, tela: pygame.Surface, camera: Deslocamento, largura: int, altura: int) -> None:
        prof = self._profundidade
        paralaxe = 1.0 + 0.6 * prof
        sx = int(self._x - camera[0] * paralaxe) % largura
        sy = int(self._y - camera[1] * paralaxe) % altura
        c, s = math.cos(self._angulo), math.sin(self._angulo)
        tam, larg = 2 + 3 * prof, (2 + 3 * prof) * 0.45
        pontos = [(sx + c * tam, sy + s * tam), (sx - s * larg, sy + c * larg),
                  (sx - c * tam, sy - s * tam), (sx + s * larg, sy - c * larg)]
        luz = 0.45 + 0.55 * prof
        pygame.draw.polygon(tela, tuple(int(v * luz) for v in self._cor), pontos)


class Ventania(Clima):
    """Lufadas e folhas soprando em rajadas da esquerda para a direita."""

    CORES_DAS_FOLHAS = ((120, 190, 80), (170, 200, 70), (220, 180, 60), (200, 120, 50))

    def __init__(self, lufadas: int = 45, folhas: int = 40, aleatorio: random.Random | None = None) -> None:
        self._qtd_lufadas = lufadas
        self._qtd_folhas = folhas
        self._aleatorio = aleatorio
        self._lufadas: list[_Lufada] = []  # criadas no 1o desenho (precisa do tamanho da tela)
        self._folhas: list[_Folha] = []
        self._tempo = 0.0
        self._forca = 0.0

    def atualizar(self, dt: float) -> None:
        self._tempo += dt
        rajada = 0.5 + 0.5 * math.sin(self._tempo * 0.7) * math.sin(self._tempo * 0.23 + 2.0)
        self._forca = 260 + 340 * rajada
        for lufada in self._lufadas:
            lufada.soprar(self._forca, self._tempo, dt)
        for folha in self._folhas:
            folha.soprar(self._forca, self._tempo, dt)

    def desenhar(self, tela: pygame.Surface, camera: Deslocamento) -> None:
        largura, altura = tela.get_size()
        if not self._lufadas:
            self._criar_particulas(largura, altura)
        for lufada in self._lufadas:
            lufada.desenhar(tela, camera, largura, altura, self._tempo)
        for folha in self._folhas:
            folha.desenhar(tela, camera, largura, altura)

    def _criar_particulas(self, largura: int, altura: int) -> None:
        rng = self._aleatorio if self._aleatorio is not None else random.Random()
        self._lufadas = [_Lufada(rng.uniform(0, largura), rng.uniform(0, altura), rng.uniform(0.3, 1.0),
                                 rng.uniform(0, math.tau), rng.randint(30, 90))
                         for _ in range(self._qtd_lufadas)]
        self._folhas = [_Folha(rng.uniform(0, largura), rng.uniform(0, altura), rng.uniform(0.3, 1.0),
                               rng.uniform(0, math.tau), rng.uniform(-6, 6), rng.choice(self.CORES_DAS_FOLHAS))
                        for _ in range(self._qtd_folhas)]


# ======================================================================
#  Terra
# ======================================================================
class _Grao:
    """Grao de poeira flutuando devagar e cintilando quando pega luz."""

    __slots__ = ("_x", "_y", "_profundidade", "_fase")

    def __init__(self, x: float, y: float, profundidade: float, fase: float) -> None:
        self._x = x
        self._y = y
        self._profundidade = profundidade
        self._fase = fase

    def flutuar(self, tempo: float, dt: float) -> None:
        prof = self._profundidade
        self._x += (10 + 14 * math.sin(tempo * 0.5 + self._fase)) * prof * dt
        self._y += (6 + 10 * math.sin(tempo * 0.8 + self._fase * 2)) * prof * dt

    def desenhar(self, tela: pygame.Surface, camera: Deslocamento, largura: int, altura: int,
                 tempo: float) -> None:
        prof = self._profundidade
        paralaxe = 1.0 + 0.6 * prof
        sx = int(self._x - camera[0] * paralaxe) % largura
        sy = int(self._y - camera[1] * paralaxe) % altura
        k = prof * (0.6 + 0.4 * math.sin(tempo * 2 + self._fase))
        cor = (int(110 + 100 * k), int(85 + 80 * k), int(55 + 50 * k))
        pygame.draw.circle(tela, cor, (sx, sy), 1 if prof < 0.75 else 2)


class Poeira(Clima):
    """Poeira de caverna pairando no ar."""

    def __init__(self, quantidade: int = 150, aleatorio: random.Random | None = None) -> None:
        self._quantidade = quantidade
        self._aleatorio = aleatorio
        self._graos: list[_Grao] = []  # criados no 1o desenho (precisa do tamanho da tela)
        self._tempo = 0.0

    def atualizar(self, dt: float) -> None:
        self._tempo += dt
        for grao in self._graos:
            grao.flutuar(self._tempo, dt)

    def desenhar(self, tela: pygame.Surface, camera: Deslocamento) -> None:
        largura, altura = tela.get_size()
        if not self._graos:
            rng = self._aleatorio if self._aleatorio is not None else random.Random()
            self._graos = [_Grao(rng.uniform(0, largura), rng.uniform(0, altura),
                                 rng.uniform(0.3, 1.0), rng.uniform(0, math.tau))
                           for _ in range(self._quantidade)]
        for grao in self._graos:
            grao.desenhar(tela, camera, largura, altura, self._tempo)
