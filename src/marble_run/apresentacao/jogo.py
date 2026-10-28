"""
jogo.py - O Jogo (contexto da maquina de estados) e a Aplicacao (game loop).

Antes, Jogo era uma "classe Deus" com mais de 20 atributos publicos: gerava
labirintos, contava tempo e pontos, salvava recorde, tocava sons, lia o
teclado e desenhava todas as telas. Agora ele so:
  * guarda qual tela (Estado) esta ativa e repassa eventos/logica/desenho;
  * trata as teclas globais (som e luz);
  * cria partidas (na dificuldade escolhida) ja com seus ouvintes inscritos.
"""
from __future__ import annotations

from typing import Callable, Iterable

import pygame

from ..dominio.ambiente import TipoDeItem
from ..dominio.contratos import OuvinteDaPartida
from ..dominio.partida import FabricaDeFases, Partida
from ..dominio.regras import NivelDeDificuldade, PontuacaoDoJogador
from .contratos import ServicoAudio
from .desenvolvedor import EstadoDesenvolvedor
from .entrada import Acao, MapaDeTeclas
from .estados import ContextoDoJogo, Estado, EstadoJogando
from .genio import EstadoDesejos
from .menus import EstadoMenu, EstadoPausado
from .ranking import EstadoRanking
from .roleta import EstadoRoleta
from .servicos import ServicosDoJogo

CriarFases = Callable[[NivelDeDificuldade], FabricaDeFases]
CriarApresentacao = Callable[[str], FabricaDeFases]


class Jogo(ContextoDoJogo):
    def __init__(self, servicos: ServicosDoJogo, fases: CriarFases,
                 ouvintes: Iterable[OuvinteDaPartida], audio: ServicoAudio,
                 teclas: MapaDeTeclas, apresentacoes: CriarApresentacao) -> None:
        self._servicos = servicos
        self._fases = fases
        self._apresentacoes = apresentacoes
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
        if estado.USA_TEXTO and not self._estado.USA_TEXTO:
            pygame.key.start_text_input()
        elif self._estado.USA_TEXTO and not estado.USA_TEXTO:
            pygame.key.stop_text_input()
        self._estado = estado

    @property
    def nome_jogador(self) -> str:
        return self._servicos.preferencias.nome_jogador

    def definir_nome_jogador(self, nome: str) -> None:
        self._servicos.preferencias.definir_nome_jogador(nome)

    def nova_partida(self) -> Partida:
        dificuldade = self._servicos.preferencias.dificuldade
        partida = Partida(self._fases(dificuldade))
        for ouvinte in self._ouvintes:
            partida.inscrever(ouvinte)
        partida.inscrever(PontuacaoDoJogador(
            self.nome_jogador.strip() or "Jogador", dificuldade, self._servicos.pontuacoes))
        return partida

    def nova_apresentacao(self, tema: str) -> Partida:
        partida = Partida(self._apresentacoes(tema))  # nao salva pontuacao: e so demonstracao
        for ouvinte in self._ouvintes:
            partida.inscrever(ouvinte)
        return partida

    def ir_para_menu_principal(self) -> None:
        self.mudar_estado(EstadoMenu(self))

    def abrir_pausa(self, jogando: EstadoJogando) -> None:
        self.mudar_estado(EstadoPausado(self, jogando))

    def abrir_roleta(self, jogando: EstadoJogando, premio: TipoDeItem) -> None:
        self.mudar_estado(EstadoRoleta(self, jogando, premio))

    def abrir_desejos(self, jogando: EstadoJogando) -> None:
        self.mudar_estado(EstadoDesejos(self, jogando))

    def abrir_ranking(self, retorno: Estado) -> None:
        self.mudar_estado(EstadoRanking(self, retorno))

    def abrir_desenvolvedor(self, retorno: Estado) -> None:
        self.mudar_estado(EstadoDesenvolvedor(self, retorno))

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
        self._servicos.controle.tratar_evento(evento)
        self._estado.tratar_evento(evento)
        if (evento.type == pygame.KEYDOWN and self._estado.capturando_texto
                and evento.unicode and evento.unicode.isprintable()):
            return  # digitando o nome: a letra vira texto, nao atalho (W, E, M...)
        acao = self._teclas.traduzir(evento)
        if acao is Acao.ALTERNAR_SOM:
            self._servicos.preferencias.alternar_mudo()
        elif acao is Acao.ALTERNAR_LUZ:
            self._servicos.preferencias.alternar_escuridao()
        elif acao is not None:
            self._estado.executar(acao)

    def atualizar(self, dt: float) -> None:
        self._estado.atualizar(dt)

    def desenhar(self, tela: pygame.Surface, fps: float = 0.0) -> None:
        self._estado.desenhar(tela)
        if self._servicos.preferencias.mostrar_fps:
            self._servicos.fonte_pixel.escrever(tela, f"FPS {fps:.0f}", 2, (130, 230, 150),
                                                canto=(8, tela.get_height() - 22))


class Aplicacao:
    """Game loop: le eventos -> atualiza -> desenha, num FPS fixo."""

    def __init__(self, jogo: Jogo, tela: pygame.Surface, fps: int = 60, passo_maximo: float = 0.05) -> None:
        self._jogo = jogo
        self._tela = tela
        self._fps = fps
        self._passo_maximo = passo_maximo  # evita "teleporte" se o jogo engasgar
        self._em_tela_cheia = False

    def executar(self) -> None:
        relogio = pygame.time.Clock()
        self._jogo.iniciar()
        while not self._jogo.encerrado:
            dt = min(relogio.tick(self._fps) / 1000.0, self._passo_maximo)
            self._sincronizar_tela_cheia()
            for evento in pygame.event.get():
                self._jogo.tratar_evento(evento)
            self._jogo.atualizar(dt)
            self._jogo.desenhar(self._tela, relogio.get_fps())
            pygame.display.flip()

    def _sincronizar_tela_cheia(self) -> None:
        """A opcao TELA CHEIA so muda uma preferencia; quem mexe na janela e o loop."""
        desejada = self._jogo.servicos.preferencias.tela_cheia
        if desejada == self._em_tela_cheia:
            return
        self._em_tela_cheia = desejada
        try:
            pygame.display.toggle_fullscreen()
        except pygame.error as erro:
            print(f"[tela] nao foi possivel alternar tela cheia: {erro}")
        self._tela = pygame.display.get_surface()
