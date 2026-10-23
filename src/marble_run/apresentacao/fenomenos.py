"""
fenomenos.py - Efeitos de tela dos fenomenos periodicos do Ambiente.

    Tempestade de areia -> veu cor de areia + graos riscando a tela + graos
                           grandes "batendo na cara" (deserto)
    Tempestade de gelo  -> veu branco-azulado + flocos de neve voando (gelo)
    Rajada de vento     -> riscos de vento na direcao da rajada (vento)
    Terremoto           -> so devolve a forca do tremor para a Camera (terra)
    Erupcao             -> tremor leve (os jatos de lava sao desenhados em elementos.py)
    Apagao              -> nada aqui: a Cena diminui a luz (masmorra)
"""
from __future__ import annotations

import random

import pygame

from ..dominio.ambiente import Ambiente, Fenomeno
from ..dominio.geometria import Vetor2

Cor = tuple[int, int, int]


class _Grao:
    __slots__ = ("x", "y", "rapidez", "tamanho")

    def __init__(self, x: float, y: float, rapidez: float, tamanho: float) -> None:
        self.x = x
        self.y = y
        self.rapidez = rapidez
        self.tamanho = tamanho


class CorrenteDeAr:
    """Particulas atravessando a tela numa direcao, com veu opcional."""

    def __init__(self, cor_risco: Cor, cor_veu: Cor | None = None, opacidade_veu: int = 0,
                 riscos: int = 220, graos_na_cara: int = 0, velocidade: float = 900.0,
                 sorteio: random.Random | None = None) -> None:
        self._cor_risco = cor_risco
        self._cor_veu = cor_veu
        self._opacidade_veu = opacidade_veu
        self._qtd_riscos = riscos
        self._qtd_graos = graos_na_cara
        self._velocidade = velocidade
        self._sorteio = sorteio if sorteio is not None else random.Random()
        self._riscos: list[_Grao] = []  # criados no 1o desenho (precisa do tamanho da tela)
        self._graos: list[_Grao] = []
        self._camada: pygame.Surface | None = None

    def atualizar(self, dt: float, direcao: Vetor2, intensidade: float) -> None:
        if intensidade <= 0 or direcao.eh_nulo:
            return
        norma = direcao.norma
        dx, dy = direcao.x / norma, direcao.y / norma
        rapidez = self._velocidade * (0.5 + 0.5 * intensidade) * dt
        for p in self._riscos:
            p.x += dx * rapidez * p.rapidez
            p.y += dy * rapidez * p.rapidez
        for p in self._graos:
            p.x += dx * rapidez * p.rapidez * 1.8
            p.y += dy * rapidez * p.rapidez * 1.8

    def desenhar(self, tela: pygame.Surface, direcao: Vetor2, intensidade: float) -> None:
        if intensidade <= 0.01 or direcao.eh_nulo:
            return
        largura, altura = tela.get_size()
        if self._camada is None or self._camada.get_size() != (largura, altura):
            self._camada = pygame.Surface((largura, altura), pygame.SRCALPHA)
            self._criar_particulas(largura, altura)
        camada = self._camada
        if self._cor_veu is not None:
            camada.fill((*self._cor_veu, int(self._opacidade_veu * intensidade)))
        else:
            camada.fill((0, 0, 0, 0))

        norma = direcao.norma
        dx, dy = direcao.x / norma, direcao.y / norma
        alfa = int(210 * intensidade)
        for p in self._riscos[: int(len(self._riscos) * intensidade)]:
            x, y = p.x % largura, p.y % altura
            comprimento = p.tamanho * (0.6 + 0.6 * intensidade)
            pygame.draw.line(camada, (*self._cor_risco, alfa), (x, y), (x - dx * comprimento, y - dy * comprimento),
                             1 if p.rapidez < 1.1 else 2)
        for p in self._graos[: int(len(self._graos) * intensidade)]:
            x, y = p.x % (largura + 40) - 20, p.y % (altura + 40) - 20
            pygame.draw.circle(camada, (*self._cor_risco, int(150 * intensidade)), (x, y), p.tamanho)
            pygame.draw.circle(camada, (255, 245, 220, int(110 * intensidade)), (x - 1, y - 1), max(1, p.tamanho // 3))
        tela.blit(camada, (0, 0))

    def _criar_particulas(self, largura: int, altura: int) -> None:
        rng = self._sorteio
        self._riscos = [_Grao(rng.uniform(0, largura), rng.uniform(0, altura), rng.uniform(0.6, 1.5),
                              rng.uniform(8, 34)) for _ in range(self._qtd_riscos)]
        self._graos = [_Grao(rng.uniform(0, largura), rng.uniform(0, altura), rng.uniform(0.8, 1.4),
                             rng.randint(3, 8)) for _ in range(self._qtd_graos)]


class EfeitosDoFenomeno:
    """Escolhe o efeito de tela certo para o fenomeno da fase (ou nenhum)."""

    DIRECAO_DA_TEMPESTADE = Vetor2(1, 0.3)
    DICA_NO_AVISO = 0.2  # um pouco de areia/tremor antes do fenomeno, como aviso

    def __init__(self, ambiente: Ambiente) -> None:
        self._ambiente = ambiente
        self._corrente: CorrenteDeAr | None = None
        if ambiente.fenomeno is Fenomeno.TEMPESTADE_DE_AREIA:
            self._corrente = CorrenteDeAr((236, 200, 140), (196, 156, 96), 165, riscos=260, graos_na_cara=34)
        elif ambiente.fenomeno is Fenomeno.TEMPESTADE_DE_GELO:
            self._corrente = CorrenteDeAr((245, 250, 255), (200, 225, 245), 140, riscos=200, graos_na_cara=60,
                                          velocidade=650)
        elif ambiente.fenomeno is Fenomeno.RAJADA:
            self._corrente = CorrenteDeAr((235, 242, 255), (220, 230, 245), 25, riscos=160, velocidade=1100)

    def intensidade(self) -> float:
        ciclo = self._ambiente.ciclo
        if ciclo is None:
            return 0.0
        if ciclo.ativo:
            forca = ciclo.intensidade
        elif ciclo.em_aviso and self._ambiente.fenomeno is not Fenomeno.RAJADA:
            forca = self.DICA_NO_AVISO * ciclo.progresso_do_aviso
        else:
            forca = 0.0
        return forca * (0.35 if self._ambiente.fenomeno_neutralizado else 1.0)

    def tremor(self) -> float:
        """Forca do tremor continuo de tela (terremoto forte; erupcao de leve)."""
        if self._ambiente.fenomeno is Fenomeno.TERREMOTO:
            return self.intensidade()
        if self._ambiente.fenomeno is Fenomeno.ERUPCAO:
            return 0.35 * self.intensidade()
        return 0.0

    def _direcao(self) -> Vetor2:
        if self._ambiente.fenomeno is Fenomeno.RAJADA:
            return self._ambiente.direcao_da_rajada
        return self.DIRECAO_DA_TEMPESTADE

    def atualizar(self, dt: float) -> None:
        if self._corrente is not None:
            self._corrente.atualizar(dt, self._direcao(), self.intensidade())

    def desenhar(self, tela: pygame.Surface) -> None:
        if self._corrente is not None:
            self._corrente.desenhar(tela, self._direcao(), self.intensidade())
