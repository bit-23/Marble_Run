"""
contratos.py - Interfaces (abstracoes) de que o dominio precisa.

Inversao de Dependencia (DIP): o dominio diz O QUE precisa; quem implementa
(arquivo, alto-falante, tela...) fica em outras camadas e depende destes
contratos - nunca o contrario.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from .ambiente import Ocorrencia
    from .geometria import Caixa
    from .regras import NivelDeDificuldade, ResultadoDaFase


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

    def ao_perder_todas_as_vidas(self, fase_alcancada: int) -> None:
        """Acabaram os coracoes: fim da partida."""

    def ao_ocorrer(self, ocorrencia: Ocorrencia) -> None:
        """Abriu uma caixa, congelou, queimou, pulou na mola, comecou uma tempestade..."""


class RepositorioDeRecorde(ABC):
    """Onde o recorde fica guardado (arquivo, banco, nuvem... o dominio nao liga)."""

    @abstractmethod
    def carregar(self) -> int:
        """Devolve a melhor fase salva (0 se ainda nao houver)."""

    @abstractmethod
    def salvar(self, fase: int) -> None:
        """Guarda a nova melhor fase."""


class RepositorioDePontuacao(ABC):
    """Melhor pontuacao de cada jogador, separada por dificuldade (o ranking)."""

    @abstractmethod
    def carregar_melhor(self, jogador: str, dificuldade: NivelDeDificuldade) -> tuple[int, int]:
        """Devolve (pontos, fase) ou (0, 0) se ainda nao houver pontuacao."""

    @abstractmethod
    def salvar_melhor(self, jogador: str, dificuldade: NivelDeDificuldade, pontos: int, fase: int) -> None:
        """Guarda a pontuacao quando superar o recorde do jogador naquela dificuldade."""

    @abstractmethod
    def ranking(self, dificuldade: NivelDeDificuldade, limite: int = 10) -> list[EntradaDoRanking]:
        """Os melhores da dificuldade, do maior para o menor."""


class EdicaoDoRanking(ABC):
    """Operacoes de manutencao do ranking (so a tela de DESENVOLVEDOR usa - ISP)."""

    @abstractmethod
    def apagar(self, jogador: str, dificuldade: NivelDeDificuldade) -> None: ...

    @abstractmethod
    def atualizar(self, jogador: str, dificuldade: NivelDeDificuldade, novo_nome: str,
                  pontos: int, fase: int) -> bool:
        """Renomeia/edita. False se `novo_nome` ja for de OUTRO jogador nessa dificuldade."""

    @abstractmethod
    def limpar(self, dificuldade: NivelDeDificuldade) -> None:
        """Apaga o ranking inteiro de uma dificuldade."""


@dataclass(frozen=True)
class EntradaDoRanking:
    jogador: str
    pontos: int
    fase: int
