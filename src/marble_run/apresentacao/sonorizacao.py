"""
sonorizacao.py - Quando tocar cada som (o COMO tocar fica no ServicoAudio).

Antes a classe Jogo chamava `self.som.tocar("vitoria")` no meio das regras.
Agora a Partida so avisa o que aconteceu e estes objetos decidem o som.
"""
from __future__ import annotations

from ..dominio.contratos import OuvinteDaPartida
from ..dominio.regras import ResultadoDaFase
from .contratos import Efeito, ServicoAudio


class SonsDaPartida(OuvinteDaPartida):
    """Observer: traduz acontecimentos da partida em efeitos sonoros."""

    def __init__(self, audio: ServicoAudio) -> None:
        self._audio = audio

    def ao_alertar_tempo(self, segundos_restantes: float) -> None:
        self._audio.tocar(Efeito.ALERTA)

    def ao_concluir_fase(self, resultado: ResultadoDaFase) -> None:
        self._audio.tocar(Efeito.VITORIA)

    def ao_esgotar_tempo(self, fase_alcancada: int) -> None:
        self._audio.tocar(Efeito.DERROTA)


class RitmoDePassos:
    """Toca o som de passo em intervalos regulares enquanto o jogador anda."""

    INTERVALO = 0.26  # segundos entre dois passos

    def __init__(self, audio: ServicoAudio, intervalo: float = INTERVALO) -> None:
        self._audio = audio
        self._intervalo = intervalo
        self._espera = 0.0

    def atualizar(self, dt: float, andando: bool) -> None:
        if not andando:
            self._espera = 0.0
            return
        self._espera -= dt
        if self._espera <= 0:
            self._audio.tocar(Efeito.PASSO)
            self._espera = self._intervalo
