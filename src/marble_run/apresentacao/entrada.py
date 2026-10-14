"""
entrada.py - Teclado e controle -> intencoes do jogador.

Antes cada tela comparava teclas do pygame direto (K_RETURN, K_ESCAPE...)
dentro de uma cadeia de if/elif, e o Jogador lia o teclado sozinho. Agora:
* MapaDeTeclas traduz teclas em Acoes com significado (CONFIRMAR, PAUSAR...).
  Trocar os controles = mexer so aqui.
* ControleHibrido implementa o contrato Controle (teclado, direcional ou analógico).
"""
from __future__ import annotations

from enum import Enum, auto
from typing import Mapping

import pygame
from pygame._sdl2 import controller as controle_sdl

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
    BOTOES_DO_CONTROLE: Mapping[int, Acao] = {
        pygame.CONTROLLER_BUTTON_A: Acao.CONFIRMAR,
        pygame.CONTROLLER_BUTTON_B: Acao.VOLTAR,
        pygame.CONTROLLER_BUTTON_START: Acao.PAUSAR,
        pygame.CONTROLLER_BUTTON_BACK: Acao.IR_PARA_MENU,
        pygame.CONTROLLER_BUTTON_X: Acao.ALTERNAR_LUZ,
        pygame.CONTROLLER_BUTTON_Y: Acao.ALTERNAR_SOM,
    }

    def __init__(self, teclas: Mapping[int, Acao] | None = None) -> None:
        self._teclas = dict(teclas if teclas is not None else self.PADRAO)

    def traduzir(self, evento: pygame.event.Event) -> Acao | None:
        if evento.type == pygame.KEYDOWN:
            return self._teclas.get(evento.key)
        if evento.type == pygame.CONTROLLERBUTTONDOWN:
            return self.BOTOES_DO_CONTROLE.get(evento.button)
        return None


class ControleTeclado(Controle):
    """Setas ou WASD."""

    def direcao_desejada(self) -> Vetor2:
        teclas = pygame.key.get_pressed()
        dx = int(teclas[pygame.K_RIGHT] or teclas[pygame.K_d]) - int(teclas[pygame.K_LEFT] or teclas[pygame.K_a])
        dy = int(teclas[pygame.K_DOWN] or teclas[pygame.K_s]) - int(teclas[pygame.K_UP] or teclas[pygame.K_w])
        return Vetor2(dx, dy)


class ControleHibrido(Controle):
    """Teclado e gamepad Xbox/PlayStation com mapeamento padronizado pelo SDL."""

    ZONA_MORTA = 0.22

    def __init__(self, teclado: ControleTeclado | None = None) -> None:
        self._teclado = teclado or ControleTeclado()
        self._controle: controle_sdl.Controller | None = None
        controle_sdl.init()
        pygame.event.set_allowed((
            pygame.CONTROLLERBUTTONDOWN,
            pygame.CONTROLLERBUTTONUP,
            pygame.CONTROLLERDEVICEADDED,
            pygame.CONTROLLERDEVICEREMOVED,
            pygame.CONTROLLERDEVICEREMAPPED,
            pygame.JOYDEVICEADDED,
            pygame.JOYDEVICEREMOVED,
        ))
        self._sincronizar_controle()

    def tratar_evento(self, evento: object) -> None:
        tipos_conexao = (
            pygame.CONTROLLERDEVICEADDED,
            pygame.CONTROLLERDEVICEREMOVED,
        )
        if getattr(evento, "type", None) in tipos_conexao:
            self._sincronizar_controle()

    def direcao_desejada(self) -> Vetor2:
        direcao_teclado = self._teclado.direcao_desejada()
        if not direcao_teclado.eh_nulo:
            return direcao_teclado

        self._sincronizar_controle()
        if self._controle is None:
            return Vetor2()

        try:
            x = self._direcao_eixo(self._controle.get_axis(pygame.CONTROLLER_AXIS_LEFTX))
            y = self._direcao_eixo(self._controle.get_axis(pygame.CONTROLLER_AXIS_LEFTY))
            dpad_x = (int(self._controle.get_button(pygame.CONTROLLER_BUTTON_DPAD_RIGHT))
                      - int(self._controle.get_button(pygame.CONTROLLER_BUTTON_DPAD_LEFT)))
            dpad_y = (int(self._controle.get_button(pygame.CONTROLLER_BUTTON_DPAD_DOWN))
                      - int(self._controle.get_button(pygame.CONTROLLER_BUTTON_DPAD_UP)))
            return Vetor2(dpad_x or x, dpad_y or y)
        except pygame.error:
            self._descartar_controle()
            return Vetor2()

    def _sincronizar_controle(self) -> None:
        if self._controle is not None and self._controle.attached():
            return
        self._descartar_controle()
        for indice in range(controle_sdl.get_count()):
            if controle_sdl.is_controller(indice):
                try:
                    self._controle = controle_sdl.Controller(indice)
                    return
                except pygame.error:
                    continue

    def _descartar_controle(self) -> None:
        if self._controle is not None:
            self._controle.quit()
            self._controle = None

    @classmethod
    def _direcao_eixo(cls, valor: int) -> int:
        if abs(valor) < int(32767 * cls.ZONA_MORTA):
            return 0
        return 1 if valor > 0 else -1
