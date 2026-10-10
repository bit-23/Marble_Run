"""
jogo.py - O Jogo (contexto da maquina de estados) e a Aplicacao (game loop).

Antes, Jogo era uma "classe Deus" com mais de 20 atributos publicos: gerava
labirintos, contava tempo e pontos, salvava recorde, tocava sons, lia o
teclado e desenhava todas as telas. Agora ele so:
  * guarda qual tela (Estado) esta ativa e repassa eventos/logica/desenho;
  * trata as teclas globais (som e luz);
  * cria partidas ja com seus ouvintes inscritos.
"""
from __future__ import annotations

from typing import Iterable

import pygame

from ..dominio.contratos import OuvinteDaPartida
from ..dominio.partida import FabricaDeFases, Partida
from .contratos import ServicoAudio
from .entrada import Acao, MapaDeTeclas
from .estados import ContextoDoJogo, Estado, EstadoMenu
from .servicos import ServicosDoJogo


class Jogo(ContextoDoJogo):
    def __init__(self, servicos: ServicosDoJogo, fases: FabricaDeFases,
                 ouvintes: Iterable[OuvinteDaPartida], audio: ServicoAudio,
                 teclas: MapaDeTeclas) -> None:
        self._servicos = servicos
        self._fases = fases
        self._ouvintes = tuple(ouvintes)
        self._audio = audio
        self._teclas = teclas
        self._encerrado = False
        self._estado: Estado = EstadoMenu(self)

    # ------------------------------------------------------------------
    # ContextoDoJogo (o que os estados podem pedir)
    # ------------------------------------------------------------------
    @property
    def servicos(self) -> ServicosDoJogo:
        return self._servicos

    def mudar_estado(self, estado: Estado) -> None:
        self._estado = estado

    def nova_partida(self) -> Partida:
        partida = Partida(self._fases)
        for ouvinte in self._ouvintes:
            partida.inscrever(ouvinte)
        return partida

    def encerrar(self) -> None:
        self._encerrado = True

    # ------------------------------------------------------------------
    # Ciclo de vida (usado pela Aplicacao)
    # ------------------------------------------------------------------
    @property
    def encerrado(self) -> bool:
        return self._encerrado

    @property
    def estado(self) -> Estado:
        return self._estado

    def iniciar(self) -> None:
        self._audio.iniciar_musica()

    def tratar_evento(self, evento: pygame.event.Event) -> None:
        if evento.type == pygame.QUIT:
            self.encerrar()
            return
        acao = self._teclas.traduzir(evento)
        if acao is Acao.ALTERNAR_SOM:
            self._audio.alternar_mudo()
        elif acao is Acao.ALTERNAR_LUZ:
            self._servicos.preferencias.alternar_escuridao()
        elif acao is not None:
            self._estado.executar(acao)

    def atualizar(self, dt: float) -> None:
        self._estado.atualizar(dt)

    def desenhar(self, tela: pygame.Surface) -> None:
        self._estado.desenhar(tela)


class Aplicacao:
    """Game loop: le eventos -> atualiza -> desenha, num FPS fixo."""

    def __init__(self, jogo: Jogo, tela: pygame.Surface, fps: int = 60, passo_maximo: float = 0.05) -> None:
        self._jogo = jogo
        self._tela = tela
        self._fps = fps
        self._passo_maximo = passo_maximo  # evita "teleporte" se o jogo engasgar

    def executar(self) -> None:
        relogio = pygame.time.Clock()
        self._jogo.iniciar()
        while not self._jogo.encerrado:
            dt = min(relogio.tick(self._fps) / 1000.0, self._passo_maximo)
            for evento in pygame.event.get():
                self._jogo.tratar_evento(evento)
            self._jogo.atualizar(dt)
            self._jogo.desenhar(self._tela)
            pygame.display.flip()
