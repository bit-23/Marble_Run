"""
contratos.py - Interfaces que a apresentacao usa, sem saber quem as implementa.

* ServicoAudio: a apresentacao pede "toque a vitoria"; quem toca de verdade
  (pygame.mixer ou ninguem, se nao houver placa de som) e decidido no main.py.
* RepositorioDePreferencias: onde as configuracoes ficam salvas (arquivo JSON).
* Controle: de onde vem a intencao de movimento (teclado e gamepad) -
  Aberto/Fechado.
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
    ITEM = "item"
    RELOGIO = "relogio"
    FLAUTA = "flauta"
    MOLA = "mola"
    CONGELAR = "congelar"
    QUEIMAR = "queimar"
    TEIA = "teia"
    TEMPESTADE = "tempestade"
    TERREMOTO = "terremoto"
    RAJADA = "rajada"
    APAGAO = "apagao"
    ERUPCAO = "erupcao"
    MENU = "menu"            # mover a selecao nos menus
    CONFIRMAR = "confirmar"  # escolher uma opcao
    DESLIZAR = "deslizar"    # pisou na placa de gelo
    TIQUE = "tique"          # roleta passando de uma fatia para outra
    PREMIO = "premio"        # roleta parou
    SEGREDO = "segredo"      # codigo secreto do menu
    ERRO = "erro"            # seta errada na teia
    MONSTRO = "monstro"      # monstro acertou o jogador
    MAGIA = "magia"          # genio, tunel, tapete
    GUINCHO = "guincho"      # aguia
    SIBILO = "sibilo"        # cobra
    BROCA = "broca"
    EXTINTOR = "extintor"


class ServicoAudio(ABC):
    @abstractmethod
    def tocar(self, efeito: Efeito) -> None: ...

    @abstractmethod
    def iniciar_musica(self) -> None: ...

    @abstractmethod
    def alternar_mudo(self) -> None: ...

    @abstractmethod
    def definir_volumes(self, musica: float, efeitos: float) -> None:
        """Volumes de 0.0 a 1.0."""

    @abstractmethod
    def definir_mudo(self, mudo: bool) -> None: ...


class RepositorioDePreferencias(ABC):
    """Onde as configuracoes do jogador ficam guardadas entre uma sessao e outra."""

    @abstractmethod
    def carregar(self) -> dict[str, object]:
        """Devolve o que foi salvo ({} se nada)."""

    @abstractmethod
    def salvar(self, dados: dict[str, object]) -> None: ...


class Controle(ABC):
    @abstractmethod
    def direcao_desejada(self) -> Vetor2:
        """Para onde o jogador quer andar agora (Vetor2 nulo = parado)."""

    def olhar_desejado(self) -> Vetor2:
        """Para onde o jogador quer deslocar a camera (cada eixo de -1 a 1). Padrao: nada."""
        return Vetor2()

    def tratar_evento(self, evento: object) -> None:
        """Recebe eventos de conexao de controle, se a implementacao precisar."""
