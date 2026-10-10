"""
contratos.py - Interfaces (abstracoes) de que o dominio precisa.

Inversao de Dependencia (DIP): o dominio diz O QUE precisa; quem implementa
(arquivo, alto-falante, tela...) fica em outras camadas e depende destes
contratos - nunca o contrario.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from .geometria import Caixa
    from .regras import ResultadoDaFase


class MapaDeColisao(Protocol):
    """Qualquer coisa que saiba dizer se uma caixa bate em algo solido.

    Protocol = interface estrutural: o Labirinto cumpre o contrato so por
    ter o metodo `colide`, sem herdar nada. Segregacao de Interface (ISP):
    o Jogador enxerga apenas o pedacinho do labirinto de que precisa.
    """

    def colide(self, caixa: Caixa) -> bool: ...


class OuvinteDaPartida(ABC):
    """Observer: quem quer reagir ao que acontece na partida (som, recorde...).

    Os metodos tem implementacao vazia de proposito: cada ouvinte sobrescreve
    so o que lhe interessa. Assim a Partida nao conhece quem esta ouvindo e
    novas reacoes entram sem mexer nela (Aberto/Fechado).
    """

    def ao_alertar_tempo(self, segundos_restantes: float) -> None:
        """Entrou em um novo segundo da contagem regressiva final."""

    def ao_concluir_fase(self, resultado: ResultadoDaFase) -> None:
        """O jogador chegou na saida."""

    def ao_esgotar_tempo(self, fase_alcancada: int) -> None:
        """O tempo acabou: fim da partida."""


class RepositorioDeRecorde(ABC):
    """Onde o recorde fica guardado (arquivo, banco, nuvem... o dominio nao liga)."""

    @abstractmethod
    def carregar(self) -> int:
        """Devolve a melhor fase salva (0 se ainda nao houver)."""

    @abstractmethod
    def salvar(self, fase: int) -> None:
        """Guarda a nova melhor fase."""
