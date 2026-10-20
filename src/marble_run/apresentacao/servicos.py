"""
servicos.py - Objetos compartilhados pelas telas do jogo.

ServicosDoJogo e um "Parameter Object": em vez de cada Estado receber dez
parametros (ou buscar variaveis globais), recebe um pacote imutavel com
os colaboradores ja montados pelo main.py (injecao de dependencias).

Preferencias guarda TODAS as configuracoes do jogador (tela, camera, som,
dificuldade, nome). Cada mudanca e aplicada no audio na hora e salva pelo
RepositorioDePreferencias (o jogo lembra tudo ao abrir de novo).
"""
from __future__ import annotations

from dataclasses import dataclass

from ..dominio.contratos import EdicaoDoRanking, RepositorioDePontuacao
from ..dominio.regras import NivelDeDificuldade, Recorde
from .cena import FabricaDeCenas
from .contratos import Controle, RepositorioDePreferencias, ServicoAudio
from .interface import Hud, Painel, Tipografia
from .personagem import SpritesDoJogador
from .pixelart import FontePixel, FundoDoMenu
from .sonorizacao import RitmoDePassos


class Preferencias:
    """Opcoes que o jogador escolhe nos menus (valem para todas as fases)."""

    NIVEIS_DE_ZOOM = (0.75, 1.0, 1.25, 1.5)
    PASSO_DE_VOLUME = 0.1
    TAMANHO_MAXIMO_DO_NOME = 16
    NIVEIS_DE_DIFICULDADE = tuple(NivelDeDificuldade)

    def __init__(self, repositorio: RepositorioDePreferencias | None = None,
                 audio: ServicoAudio | None = None) -> None:
        self._repositorio = repositorio
        self._audio = audio
        self._escuridao = True
        self._nivel_zoom = 1
        self._tela_cheia = False
        self._tremor = True
        self._mostrar_fps = False
        self._volume_musica = 1.0
        self._volume_efeitos = 1.0
        self._mudo = False
        self._dificuldade = NivelDeDificuldade.NORMAL
        self._nome_jogador = ""
        self._apresentacao_liberada = False  # codigo secreto: vale so ate fechar o jogo
        if repositorio is not None:
            self._restaurar(repositorio.carregar())
        self._aplicar_som()

    @property
    def apresentacao_liberada(self) -> bool:
        return self._apresentacao_liberada

    def liberar_apresentacao(self) -> None:
        self._apresentacao_liberada = True

    # ------------------------------------------------------------------
    # Tela e camera
    # ------------------------------------------------------------------
    @property
    def escuridao(self) -> bool:
        return self._escuridao

    def alternar_escuridao(self) -> None:
        self._escuridao = not self._escuridao
        self._mudou()

    @property
    def zoom(self) -> float:
        return self.NIVEIS_DE_ZOOM[self._nivel_zoom]

    def aproximar_zoom(self) -> None:
        self._nivel_zoom = min(len(self.NIVEIS_DE_ZOOM) - 1, self._nivel_zoom + 1)
        self._mudou()

    def afastar_zoom(self) -> None:
        self._nivel_zoom = max(0, self._nivel_zoom - 1)
        self._mudou()

    @property
    def tela_cheia(self) -> bool:
        return self._tela_cheia

    def alternar_tela_cheia(self) -> None:
        self._tela_cheia = not self._tela_cheia
        self._mudou()

    @property
    def tremor(self) -> bool:
        """Tremor de tela (terremoto, fogo...). Pode ser desligado por acessibilidade."""
        return self._tremor

    def alternar_tremor(self) -> None:
        self._tremor = not self._tremor
        self._mudou()

    @property
    def mostrar_fps(self) -> bool:
        return self._mostrar_fps

    def alternar_fps(self) -> None:
        self._mostrar_fps = not self._mostrar_fps
        self._mudou()

    # ------------------------------------------------------------------
    # Som
    # ------------------------------------------------------------------
    @property
    def volume_musica(self) -> float:
        return self._volume_musica

    @property
    def volume_efeitos(self) -> float:
        return self._volume_efeitos

    @property
    def mudo(self) -> bool:
        return self._mudo

    def ajustar_volume_musica(self, passos: int) -> None:
        self._volume_musica = self._volume(self._volume_musica + passos * self.PASSO_DE_VOLUME)
        self._mudou()

    def ajustar_volume_efeitos(self, passos: int) -> None:
        self._volume_efeitos = self._volume(self._volume_efeitos + passos * self.PASSO_DE_VOLUME)
        self._mudou()

    def alternar_mudo(self) -> None:
        self._mudo = not self._mudo
        self._mudou()

    # ------------------------------------------------------------------
    # Partida
    # ------------------------------------------------------------------
    @property
    def dificuldade(self) -> NivelDeDificuldade:
        return self._dificuldade

    def mudar_dificuldade(self, passos: int) -> None:
        niveis = self.NIVEIS_DE_DIFICULDADE
        indice = max(0, min(len(niveis) - 1, niveis.index(self._dificuldade) + passos))
        self._dificuldade = niveis[indice]
        self._mudou()

    @property
    def nome_jogador(self) -> str:
        return self._nome_jogador

    def definir_nome_jogador(self, nome: str) -> None:
        self._nome_jogador = nome[: self.TAMANHO_MAXIMO_DO_NOME]
        self._mudou()

    # ------------------------------------------------------------------
    def _mudou(self) -> None:
        self._aplicar_som()
        if self._repositorio is not None:
            self._repositorio.salvar(self._para_dicionario())

    def _aplicar_som(self) -> None:
        if self._audio is not None:
            self._audio.definir_volumes(self._volume_musica, self._volume_efeitos)
            self._audio.definir_mudo(self._mudo)

    def _para_dicionario(self) -> dict[str, object]:
        return {
            "escuridao": self._escuridao,
            "zoom": self.zoom,
            "tela_cheia": self._tela_cheia,
            "tremor": self._tremor,
            "mostrar_fps": self._mostrar_fps,
            "volume_musica": round(self._volume_musica, 2),
            "volume_efeitos": round(self._volume_efeitos, 2),
            "mudo": self._mudo,
            "dificuldade": self._dificuldade.value,
            "nome_jogador": self._nome_jogador,
        }

    def _restaurar(self, dados: dict[str, object]) -> None:
        """Le o que foi salvo, ignorando valores estranhos (arquivo editado a mao...)."""
        def booleano(chave: str, padrao: bool) -> bool:
            valor = dados.get(chave, padrao)
            return valor if isinstance(valor, bool) else padrao

        def numero(chave: str, padrao: float) -> float:
            valor = dados.get(chave, padrao)
            return float(valor) if isinstance(valor, (int, float)) and not isinstance(valor, bool) else padrao

        self._escuridao = booleano("escuridao", self._escuridao)
        self._tela_cheia = booleano("tela_cheia", self._tela_cheia)
        self._tremor = booleano("tremor", self._tremor)
        self._mostrar_fps = booleano("mostrar_fps", self._mostrar_fps)
        self._mudo = booleano("mudo", self._mudo)
        zoom = numero("zoom", self.zoom)
        if zoom in self.NIVEIS_DE_ZOOM:
            self._nivel_zoom = self.NIVEIS_DE_ZOOM.index(zoom)
        self._volume_musica = self._volume(numero("volume_musica", self._volume_musica))
        self._volume_efeitos = self._volume(numero("volume_efeitos", self._volume_efeitos))
        try:
            self._dificuldade = NivelDeDificuldade(dados.get("dificuldade", self._dificuldade.value))
        except ValueError:
            pass
        nome = dados.get("nome_jogador", "")
        if isinstance(nome, str):
            self._nome_jogador = nome[: self.TAMANHO_MAXIMO_DO_NOME]

    @staticmethod
    def _volume(valor: float) -> float:
        return round(max(0.0, min(1.0, valor)), 2)


@dataclass(frozen=True)
class ServicosDoJogo:
    titulo: str
    tipografia: Tipografia
    hud: Hud
    painel: Painel
    cenas: FabricaDeCenas
    sprites: SpritesDoJogador
    controle: Controle
    passos: RitmoDePassos
    recorde: Recorde
    pontuacoes: RepositorioDePontuacao
    editor_do_ranking: EdicaoDoRanking
    preferencias: Preferencias
    audio: ServicoAudio
    fonte_pixel: FontePixel
    fundo_menu: FundoDoMenu
