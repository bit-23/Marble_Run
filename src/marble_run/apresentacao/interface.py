"""
interface.py - Componentes de interface reutilizaveis: texto, HUD e painel.

Antes eram metodos privados de Jogo (_texto, _desenhar_hud, _painel).
Separados, cada tela usa o que precisa e as cores ganham nomes.
"""
from __future__ import annotations

from enum import Enum

import pygame

from ..dominio.partida import Partida

Cor = tuple[int, int, int]

DOURADO = (255, 214, 90)
BRANCO_SUAVE = (230, 230, 240)
CINZA_AZULADO = (140, 140, 170)
VERDE_CLARO = (120, 220, 150)


class Fonte(Enum):
    GIGANTE = 96
    GRANDE = 56
    MEDIA = 34
    PEQUENA = 24


class Tipografia:
    """Fontes do jogo + texto com sombra (todas as telas escrevem por aqui)."""

    COR_SOMBRA = (0, 0, 0)

    def __init__(self) -> None:
        self._fontes = {fonte: pygame.font.Font(None, fonte.value) for fonte in Fonte}

    def escrever(self, tela: pygame.Surface, texto: str, fonte: Fonte, cor: Cor, *,
                 centro: tuple[int, int] | None = None, canto: tuple[int, int] | None = None) -> None:
        """Escreve centralizado em `centro` ou a partir do canto superior esquerdo `canto`."""
        f = self._fontes[fonte]
        img = f.render(texto, True, cor)
        pos = img.get_rect(center=centro) if centro else img.get_rect(topleft=canto)
        tela.blit(f.render(texto, True, self.COR_SOMBRA), pos.move(2, 2))
        tela.blit(img, pos)


class Hud:
    """Barra superior: fase, pontos e relogio (+ semente no rodape)."""

    ALTURA = 44
    COR_FUNDO = (10, 8, 20)
    COR_TRILHO = (40, 36, 60)
    COR_MOLDURA = (200, 200, 220)

    def __init__(self, tipografia: Tipografia, tamanho_tela: tuple[int, int]) -> None:
        self._tipografia = tipografia
        self._largura, self._altura = tamanho_tela

    def desenhar(self, tela: pygame.Surface, partida: Partida) -> None:
        escrever = self._tipografia.escrever
        fase = partida.fase
        pygame.draw.rect(tela, self.COR_FUNDO, (0, 0, self._largura, self.ALTURA))
        escrever(tela, f"FASE {partida.nivel}", Fonte.MEDIA, DOURADO, canto=(14, 10))
        escrever(tela, f"PONTOS {partida.pontos}", Fonte.MEDIA, BRANCO_SUAVE, canto=(150, 10))

        fracao, restante = fase.fracao_de_tempo, fase.tempo_restante
        cor = self._cor_do_relogio(fracao, restante)
        barra = pygame.Rect(self._largura - 420, 12, 300, 20)
        pygame.draw.rect(tela, self.COR_TRILHO, barra, border_radius=6)
        pygame.draw.rect(tela, cor, (barra.x, barra.y, int(barra.w * fracao), barra.h), border_radius=6)
        pygame.draw.rect(tela, self.COR_MOLDURA, barra, 2, border_radius=6)
        escrever(tela, f"{max(0, int(restante + 0.99))}s", Fonte.MEDIA, cor, canto=(barra.right + 12, 10))
        escrever(tela, f"seed {fase.semente}", Fonte.PEQUENA, CINZA_AZULADO,
                 canto=(self._largura - 110, self._altura - 26))

    @staticmethod
    def _cor_do_relogio(fracao: float, restante: float) -> Cor:
        if fracao < 0.25 and int(restante * 4) % 2:  # pisca quando o tempo esta no fim
            return (255, 130, 130)
        if fracao > 0.5:
            return (90, 200, 120)
        return (240, 190, 60) if fracao > 0.25 else (230, 70, 70)


class Painel:
    """Mensagem grande no meio da tela, sobre um veu escuro (pausa, vitoria...)."""

    OPACIDADE_VEU = 150

    def __init__(self, tipografia: Tipografia, tamanho_tela: tuple[int, int]) -> None:
        self._tipografia = tipografia
        self._centro = (tamanho_tela[0] // 2, tamanho_tela[1] // 2)
        self._veu = pygame.Surface(tamanho_tela, pygame.SRCALPHA)
        self._veu.fill((0, 0, 0, self.OPACIDADE_VEU))

    def desenhar(self, tela: pygame.Surface, titulo: str, linha1: str = "", linha2: str = "") -> None:
        tela.blit(self._veu, (0, 0))
        cx, cy = self._centro
        escrever = self._tipografia.escrever
        escrever(tela, titulo, Fonte.GIGANTE, DOURADO, centro=(cx, cy - 50))
        if linha1:
            escrever(tela, linha1, Fonte.MEDIA, (235, 235, 245), centro=(cx, cy + 20))
        if linha2:
            escrever(tela, linha2, Fonte.GRANDE, VERDE_CLARO, centro=(cx, cy + 80))
