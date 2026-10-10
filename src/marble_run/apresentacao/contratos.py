"""
contratos.py - Interfaces que a apresentacao usa, sem saber quem as implementa.

* ServicoAudio: a apresentacao pede "toque a vitoria"; quem toca de verdade
  (pygame.mixer ou ninguem, se nao houver placa de som) e decidido no main.py.
* Controle: de onde vem a intencao de movimento (teclado hoje; joystick,
  IA ou um roteiro de testes amanha) - Aberto/Fechado.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum

from ..dominio.geometria import Vetor2


class Efeito(Enum):
    """Efeitos sonoros do jogo (o valor e o nome do arquivo em assets/sound/)."""

    PASSO = "passo"
    VITORIA = "vitoria"
    DERROTA = "derrota"
    ALERTA = "alerta"


class ServicoAudio(ABC):
    @abstractmethod
    def tocar(self, efeito: Efeito) -> None: ...

    @abstractmethod
    def iniciar_musica(self) -> None: ...

    @abstractmethod
    def alternar_mudo(self) -> None: ...


class Controle(ABC):
    @abstractmethod
    def direcao_desejada(self) -> Vetor2:
        """Para onde o jogador quer andar agora (Vetor2 nulo = parado)."""
