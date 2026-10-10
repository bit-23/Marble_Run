"""
entrada.py - Teclado -> intencoes do jogador.

Antes cada tela comparava teclas do pygame direto (K_RETURN, K_ESCAPE...)
dentro de uma cadeia de if/elif, e o Jogador lia o teclado sozinho. Agora:
* MapaDeTeclas traduz teclas em Acoes com significado (CONFIRMAR, PAUSAR...).
  Trocar os controles = mexer so aqui.
* ControleTeclado implementa o contrato Controle (setas ou WASD).
"""
from __future__ import annotations

from enum import Enum, auto
from typing import Mapping

import pygame

from ..dominio.geometria import Vetor2
from .contratos import Controle


class Acao(Enum):
    CONFIRMAR = auto()
    VOLTAR = auto()
    PAUSAR = auto()
    IR_PARA_MENU = auto()
    ALTERNAR_SOM = auto()
    ALTERNAR_LUZ = auto()


class MapaDeTeclas:
    PADRAO: Mapping[int, Acao] = {
        pygame.K_RETURN: Acao.CONFIRMAR,
        pygame.K_KP_ENTER: Acao.CONFIRMAR,
        pygame.K_SPACE: Acao.CONFIRMAR,
        pygame.K_ESCAPE: Acao.VOLTAR,
        pygame.K_p: Acao.PAUSAR,
        pygame.K_q: Acao.IR_PARA_MENU,
        pygame.K_m: Acao.ALTERNAR_SOM,
        pygame.K_l: Acao.ALTERNAR_LUZ,
    }

    def __init__(self, teclas: Mapping[int, Acao] | None = None) -> None:
        self._teclas = dict(teclas if teclas is not None else self.PADRAO)

    def traduzir(self, evento: pygame.event.Event) -> Acao | None:
        if evento.type != pygame.KEYDOWN:
            return None
        return self._teclas.get(evento.key)


class ControleTeclado(Controle):
    """Setas ou WASD."""

    def direcao_desejada(self) -> Vetor2:
        teclas = pygame.key.get_pressed()
        dx = int(teclas[pygame.K_RIGHT] or teclas[pygame.K_d]) - int(teclas[pygame.K_LEFT] or teclas[pygame.K_a])
        dy = int(teclas[pygame.K_DOWN] or teclas[pygame.K_s]) - int(teclas[pygame.K_UP] or teclas[pygame.K_w])
        return Vetor2(dx, dy)
