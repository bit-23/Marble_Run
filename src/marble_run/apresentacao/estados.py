"""
estados.py - As telas do jogo como objetos (padrao State).

Antes:  self.estado = "menu" | "jogando" | "pausado" | "vitoria" | "derrota"
        + uma cadeia de if/elif em processar_evento, atualizar e desenhar.
Agora:  cada tela e uma classe com o MESMO contrato (Estado). O Jogo so
        repassa as chamadas para o estado atual - polimorfismo no lugar de
        if/elif. Uma tela nova (opcoes, creditos...) e uma classe nova, sem
        tocar nas existentes (Aberto/Fechado).

    Menu --CONFIRMAR--> Jogando --VOLTAR/PAUSAR--> Pausado --IR_PARA_MENU--> Menu
                          |  ^                        |
                          |  +------ CONFIRMAR -------+
                          +--(achou a saida)--> Vitoria --(1.8 s)--> Jogando (proxima fase)
                          +--(tempo acabou)---> Derrota --CONFIRMAR--> Jogando (REBOOT)
"""
from __future__ import annotations

from abc import ABC, abstractmethod

import pygame

from ..dominio.partida import Partida, SituacaoDaPartida
from .cena import Cena
from .entrada import Acao
from .interface import DOURADO, VERDE_CLARO, Fonte
from .servicos import ServicosDoJogo


class ContextoDoJogo(ABC):
    """O que um Estado pode pedir ao jogo (contexto do State pattern).

    Os estados dependem desta abstracao, e nao da classe Jogo concreta (DIP).
    """

    @property
    @abstractmethod
    def servicos(self) -> ServicosDoJogo: ...

    @property
    @abstractmethod
    def nome_jogador(self) -> str: ...

    @abstractmethod
    def definir_nome_jogador(self, nome: str) -> None: ...

    @abstractmethod
    def mudar_estado(self, estado: Estado) -> None: ...

    @abstractmethod
    def nova_partida(self) -> Partida: ...

    @abstractmethod
    def encerrar(self) -> None: ...


class Estado(ABC):
    """Contrato de toda tela do jogo."""

    def __init__(self, jogo: ContextoDoJogo) -> None:
        self._jogo = jogo

    @property
    def _servicos(self) -> ServicosDoJogo:
        return self._jogo.servicos

    def executar(self, acao: Acao) -> None:
        """Reage a uma acao do jogador. Padrao: ignora."""

    def tratar_evento(self, evento: pygame.event.Event) -> None:
        """Recebe eventos especificos da tela antes do mapeamento de acoes."""

    def atualizar(self, dt: float) -> None:
        """Avanca a logica da tela. Padrao: nada muda."""

    @abstractmethod
    def desenhar(self, tela: pygame.Surface) -> None: ...


# ======================================================================
class EstadoMenu(Estado):
    PISCA_A_CADA = 0.5  # segundos

    def __init__(self, jogo: ContextoDoJogo) -> None:
        super().__init__(jogo)
        parado = self._servicos.sprites.parado
        self._mascote = pygame.transform.scale(parado, (parado.get_width() * 3, parado.get_height() * 3))
        self._tempo = 0.0
        self._nome_jogador = jogo.nome_jogador
        self._melhor_pontuacao = self._carregar_melhor_pontuacao()
        pygame.key.start_text_input()

    def tratar_evento(self, evento: pygame.event.Event) -> None:
        if evento.type == pygame.TEXTINPUT:
            texto = "".join(caractere for caractere in evento.text if caractere.isprintable())
            self._nome_jogador = (self._nome_jogador + texto)[:16]
            self._jogo.definir_nome_jogador(self._nome_jogador)
            self._melhor_pontuacao = self._carregar_melhor_pontuacao()
        elif evento.type == pygame.KEYDOWN and evento.key == pygame.K_BACKSPACE:
            self._nome_jogador = self._nome_jogador[:-1]
            self._jogo.definir_nome_jogador(self._nome_jogador)
            self._melhor_pontuacao = self._carregar_melhor_pontuacao()

    def _carregar_melhor_pontuacao(self) -> int:
        nome = self._nome_jogador.strip() or "Jogador"
        return self._servicos.pontuacoes.carregar_melhor(nome)[0]

    def executar(self, acao: Acao) -> None:
        if acao is Acao.CONFIRMAR:
            self._jogo.definir_nome_jogador(self._nome_jogador.strip() or "Jogador")
            self._jogo.mudar_estado(EstadoJogando.nova_corrida(self._jogo))
        elif acao is Acao.VOLTAR:
            self._jogo.encerrar()

    def atualizar(self, dt: float) -> None:
        self._tempo += dt

    def desenhar(self, tela: pygame.Surface) -> None:
        s = self._servicos
        escrever = s.tipografia.escrever
        cx = tela.get_width() // 2
        tela.fill((22, 18, 38))
        escrever(tela, s.titulo.upper(), Fonte.GIGANTE, DOURADO, centro=(cx, 110))
        escrever(tela, "Escape do labirinto antes que o tempo acabe!", Fonte.MEDIA, (220, 220, 235),
                 centro=(cx, 175))
        tela.blit(self._mascote, self._mascote.get_rect(center=(cx, 340)))
        escrever(tela, f"Jogador: {self._nome_jogador or 'digite seu nome'}", Fonte.MEDIA,
                 (220, 220, 235), centro=(cx, 455))
        if int(self._tempo / self.PISCA_A_CADA) % 2 == 0:
            escrever(tela, "Digite seu nome e pressione ENTER ou botao de baixo", Fonte.MEDIA,
                     VERDE_CLARO, centro=(cx, 505))
        escrever(tela, "Backspace: apagar   |   Mover: WASD, setas, analogico ou direcional",
                 Fonte.PEQUENA, (150, 150, 180), centro=(cx, 550))
        escrever(tela, "Botao de baixo: confirmar   |   da direita: voltar   |   Start: pausar",
                 Fonte.PEQUENA, (150, 150, 180), centro=(cx, 578))
        escrever(tela, f"Recorde fase: {s.recorde.melhor_fase}   |   Pontos salvos: {self._melhor_pontuacao}",
                 Fonte.PEQUENA, DOURADO, centro=(cx, 614))


# ======================================================================
class EstadoJogando(Estado):
    def __init__(self, jogo: ContextoDoJogo, partida: Partida, cena: Cena) -> None:
        super().__init__(jogo)
        self._partida = partida
        self._cena = cena

    @classmethod
    def nova_corrida(cls, jogo: ContextoDoJogo) -> EstadoJogando:
        """REBOOT: partida nova, labirinto inedito, volta para a fase 1."""
        partida = jogo.nova_partida()
        return cls(jogo, partida, jogo.servicos.cenas.criar(partida.fase))

    def executar(self, acao: Acao) -> None:
        if acao in (Acao.VOLTAR, Acao.PAUSAR):
            self._jogo.mudar_estado(EstadoPausado(self._jogo, self))

    def atualizar(self, dt: float) -> None:
        s = self._servicos
        self._cena.animar_ambiente(dt)
        self._partida.atualizar(dt, s.controle.direcao_desejada())
        self._cena.animar_jogador(dt)
        self._cena.enquadrar()
        s.passos.atualizar(dt, self._partida.fase.jogador.esta_andando)

        if self._partida.situacao is SituacaoDaPartida.FASE_CONCLUIDA:
            self._jogo.mudar_estado(EstadoVitoria(self._jogo, self._partida, self._cena))
        elif self._partida.situacao is SituacaoDaPartida.TEMPO_ESGOTADO:
            self._jogo.mudar_estado(EstadoDerrota(self._jogo, self._partida, self._cena))

    def desenhar(self, tela: pygame.Surface) -> None:
        self._cena.desenhar(tela, com_escuridao=self._servicos.preferencias.escuridao)
        self._servicos.hud.desenhar(tela, self._partida)


# ======================================================================
class EstadoPausado(Estado):
    """Congela a partida: guarda o estado Jogando e volta para ELE mesmo."""

    def __init__(self, jogo: ContextoDoJogo, jogando: EstadoJogando) -> None:
        super().__init__(jogo)
        self._jogando = jogando

    def executar(self, acao: Acao) -> None:
        if acao in (Acao.VOLTAR, Acao.PAUSAR, Acao.CONFIRMAR):
            self._jogo.mudar_estado(self._jogando)
        elif acao is Acao.IR_PARA_MENU:
            self._jogo.mudar_estado(EstadoMenu(self._jogo))

    def desenhar(self, tela: pygame.Surface) -> None:
        self._jogando.desenhar(tela)
        self._servicos.painel.desenhar(
            tela, "PAUSADO", "ESC/ENTER ou botoes de baixo/direita continua",
            "Q/Select volta ao menu")


# ======================================================================
class EstadoVitoria(Estado):
    """Comemora por alguns segundos (fase visivel, sem escuridao) e segue."""

    DURACAO = 1.8  # segundos comemorando antes da proxima fase

    def __init__(self, jogo: ContextoDoJogo, partida: Partida, cena: Cena) -> None:
        super().__init__(jogo)
        self._partida = partida
        self._cena = cena
        self._tempo = 0.0

    def atualizar(self, dt: float) -> None:
        self._cena.animar_ambiente(dt)
        self._tempo += dt
        if self._tempo >= self.DURACAO:
            self._partida.avancar_para_proxima_fase()
            cena = self._servicos.cenas.criar(self._partida.fase)
            self._jogo.mudar_estado(EstadoJogando(self._jogo, self._partida, cena))

    def desenhar(self, tela: pygame.Surface) -> None:
        resultado = self._partida.ultimo_resultado
        self._cena.desenhar(tela, com_escuridao=False)
        self._servicos.hud.desenhar(tela, self._partida)
        self._servicos.painel.desenhar(
            tela, "SAIU DO LABIRINTO!",
            f"+{resultado.pontos_ganhos} pontos  (bonus de tempo: {resultado.bonus})")


class EstadoDerrota(Estado):
    """Fim da partida: mostra o resultado e oferece o REBOOT."""

    def __init__(self, jogo: ContextoDoJogo, partida: Partida, cena: Cena) -> None:
        super().__init__(jogo)
        self._partida = partida
        self._cena = cena

    def executar(self, acao: Acao) -> None:
        if acao is Acao.CONFIRMAR:
            self._jogo.mudar_estado(EstadoJogando.nova_corrida(self._jogo))  # <<< REBOOT
        elif acao is Acao.VOLTAR:
            self._jogo.mudar_estado(EstadoMenu(self._jogo))

    def desenhar(self, tela: pygame.Surface) -> None:
        p = self._partida
        self._cena.desenhar(tela, com_escuridao=False)
        self._servicos.hud.desenhar(tela, p)
        self._servicos.painel.desenhar(
            tela, "TEMPO ESGOTADO!",
            f"Voce chegou a fase {p.nivel}  |  Pontos: {p.pontos}  |  "
            f"Recorde: fase {self._servicos.recorde.melhor_fase}",
            "A/ENTER: reiniciar   |   B: menu")
