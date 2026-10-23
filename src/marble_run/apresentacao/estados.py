"""
estados.py - As telas do jogo como objetos (padrao State).

Antes:  self.estado = "menu" | "jogando" | "pausado" | "vitoria" | "derrota"
        + uma cadeia de if/elif em processar_evento, atualizar e desenhar.
Agora:  cada tela e uma classe com o MESMO contrato (Estado). O Jogo so
        repassa as chamadas para o estado atual - polimorfismo no lugar de
        if/elif. Uma tela nova (opcoes, creditos...) e uma classe nova, sem
        tocar nas existentes (Aberto/Fechado).

Aqui ficam as telas da PARTIDA. As telas de menu (principal, novo jogo,
configuracoes, som, controles e pausa) ficam em menus.py.

    Menu --COMECAR--> Jogando --ESC/P--> Pausa --CONTINUAR--> Jogando
                        |                  +--REINICIAR / MENU PRINCIPAL / SAIR
                        +--(abriu caixa "?")--> Roleta --(parou no buff)--> Jogando
                        +--(achou a saida)--> Vitoria --(1.8 s)--> Jogando (proxima fase)
                        +--(tempo/coracoes acabaram)--> Derrota --CONFIRMAR--> Jogando (REBOOT)
"""
from __future__ import annotations

from abc import ABC, abstractmethod

import pygame

from ..dominio.ambiente import TipoDeItem, TipoDeOcorrencia
from ..dominio.jogador import Direcao
from ..dominio.partida import Partida, SituacaoDaPartida
from .cena import Cena
from .entrada import Acao
from .interface import nome_do_mapa
from .servicos import ServicosDoJogo

SETAS = {Acao.CIMA: Direcao.CIMA, Acao.BAIXO: Direcao.BAIXO,
         Acao.ESQUERDA: Direcao.ESQUERDA, Acao.DIREITA: Direcao.DIREITA}


class ContextoDoJogo(ABC):
    """O que um Estado pode pedir ao jogo (contexto do State pattern).

    Os estados dependem desta abstracao, e nao da classe Jogo concreta (DIP).
    `ir_para_menu_principal` e `abrir_pausa` evitam que as telas da partida
    precisem conhecer as classes dos menus (e vice-versa).
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
    def nova_apresentacao(self, tema: str) -> Partida:
        """Partida do modo apresentacao (vitrine) de um mapa."""

    @abstractmethod
    def ir_para_menu_principal(self) -> None: ...

    @abstractmethod
    def abrir_pausa(self, jogando: EstadoJogando) -> None: ...

    @abstractmethod
    def abrir_roleta(self, jogando: EstadoJogando, premio: TipoDeItem) -> None: ...

    @abstractmethod
    def abrir_desejos(self, jogando: EstadoJogando) -> None:
        """Genio da lampada: escolher 1 de 3 desejos."""

    @abstractmethod
    def abrir_ranking(self, retorno: Estado) -> None: ...

    @abstractmethod
    def abrir_desenvolvedor(self, retorno: Estado) -> None:
        """Menu secreto: editar ranking e teste dos mapas."""

    @abstractmethod
    def encerrar(self) -> None: ...


class Estado(ABC):
    """Contrato de toda tela do jogo."""

    USA_TEXTO = False  # True = a tela recebe digitacao (liga o text input do SDL)

    def __init__(self, jogo: ContextoDoJogo) -> None:
        self._jogo = jogo

    @property
    def _servicos(self) -> ServicosDoJogo:
        return self._jogo.servicos

    @property
    def capturando_texto(self) -> bool:
        """True enquanto as teclas de letra devem virar TEXTO, e nao atalhos (W, E, M...)."""
        return False

    def executar(self, acao: Acao) -> None:
        """Reage a uma acao do jogador. Padrao: ignora."""

    def tratar_evento(self, evento: pygame.event.Event) -> None:
        """Recebe eventos especificos da tela antes do mapeamento de acoes."""

    def atualizar(self, dt: float) -> None:
        """Avanca a logica da tela. Padrao: nada muda."""

    @abstractmethod
    def desenhar(self, tela: pygame.Surface) -> None: ...


# ======================================================================
class EstadoJogando(Estado):
    def __init__(self, jogo: ContextoDoJogo, partida: Partida, cena: Cena) -> None:
        super().__init__(jogo)
        self._partida = partida
        self._cena = cena

    @property
    def partida(self) -> Partida:
        return self._partida

    @classmethod
    def nova_corrida(cls, jogo: ContextoDoJogo) -> EstadoJogando:
        """REBOOT: partida nova, labirinto inedito, volta para a fase 1."""
        partida = jogo.nova_partida()
        return cls(jogo, partida, jogo.servicos.cenas.criar(partida.fase))

    def reiniciar(self) -> EstadoJogando:
        """Comeca de novo no MESMO modo (o modo apresentacao sobrescreve)."""
        return EstadoJogando.nova_corrida(self._jogo)

    def com_nova_cena(self, cena: Cena) -> EstadoJogando:
        """Proxima fase da mesma partida, no mesmo tipo de tela."""
        return type(self)(self._jogo, self._partida, cena)

    def executar(self, acao: Acao) -> None:
        if acao in (Acao.VOLTAR, Acao.PAUSAR):
            self._jogo.abrir_pausa(self)
        elif acao in SETAS:  # so contam presas na teia
            self._partida.apertar(SETAS[acao])
        elif acao is Acao.APROXIMAR_ZOOM:
            self._servicos.preferencias.aproximar_zoom()
        elif acao is Acao.AFASTAR_ZOOM:
            self._servicos.preferencias.afastar_zoom()

    def atualizar(self, dt: float) -> None:
        s = self._servicos
        self._partida.atualizar(dt, s.controle.direcao_desejada())
        self._cena.reagir(self._partida.ocorrencias)
        self._cena.animar_ambiente(dt)
        self._cena.animar_jogador(dt)
        self._cena.enquadrar(dt, s.controle.olhar_desejado())
        s.passos.atualizar(dt, self._partida.fase.jogador.esta_andando)

        situacao = self._partida.situacao
        if situacao is SituacaoDaPartida.FASE_CONCLUIDA:
            self._jogo.mudar_estado(EstadoVitoria(self._jogo, self._partida, self._cena, self))
        elif situacao in (SituacaoDaPartida.TEMPO_ESGOTADO, SituacaoDaPartida.SEM_VIDA):
            self._jogo.mudar_estado(EstadoDerrota(self._jogo, self._partida, self._cena, self))
        else:
            caixas = [o for o in self._partida.ocorrencias if o.tipo is TipoDeOcorrencia.CAIXA_ABERTA]
            genio = [o for o in self._partida.ocorrencias
                     if o.tipo is TipoDeOcorrencia.BUFF_APLICADO and o.item is TipoDeItem.GENIO]
            if caixas:
                self._jogo.abrir_roleta(self, caixas[0].item)
            elif genio:
                self._jogo.abrir_desejos(self)

    def desenhar(self, tela: pygame.Surface) -> None:
        self._cena.desenhar(tela, com_escuridao=self._servicos.preferencias.escuridao)
        self._servicos.hud.desenhar(tela, self._partida)


# ======================================================================
class EstadoVitoria(Estado):
    """Comemora por alguns segundos (fase visivel, sem escuridao) e segue."""

    DURACAO = 1.8  # segundos comemorando antes da proxima fase

    def __init__(self, jogo: ContextoDoJogo, partida: Partida, cena: Cena, jogando: EstadoJogando) -> None:
        super().__init__(jogo)
        self._partida = partida
        self._cena = cena
        self._jogando = jogando
        self._tempo = 0.0

    def atualizar(self, dt: float) -> None:
        self._cena.animar_ambiente(dt)
        self._tempo += dt
        if self._tempo >= self.DURACAO:
            self._partida.avancar_para_proxima_fase()
            self._jogo.mudar_estado(self._jogando.com_nova_cena(self._servicos.cenas.criar(self._partida.fase)))

    def desenhar(self, tela: pygame.Surface) -> None:
        resultado = self._partida.ultimo_resultado
        fase = self._partida.fase
        if fase.tempo_ilimitado:
            proximo = ""
        elif fase.ultima_no_mapa:
            proximo = f"Mapa {nome_do_mapa(fase.tema)} concluido! Proximo: MAPA NOVO"
        else:
            proximo = f"Proximo: {nome_do_mapa(fase.tema)} {fase.etapa_no_mapa + 1}/{fase.fases_por_mapa}"
        self._cena.desenhar(tela, com_escuridao=False)
        self._servicos.hud.desenhar(tela, self._partida)
        cura = self._partida.dificuldade.cura_por_fase
        self._servicos.painel.desenhar(
            tela, "SAIU DO LABIRINTO!",
            f"+{resultado.pontos_ganhos} pontos  (bonus de tempo: {resultado.bonus})"
            + (f"  +{cura} coracao" if cura else "  (sem cura nesta dificuldade)"), proximo)


class EstadoDerrota(Estado):
    """Fim da partida (tempo ou coracoes acabaram): mostra o resultado e oferece o REBOOT."""

    def __init__(self, jogo: ContextoDoJogo, partida: Partida, cena: Cena, jogando: EstadoJogando) -> None:
        super().__init__(jogo)
        self._partida = partida
        self._cena = cena
        self._jogando = jogando

    def executar(self, acao: Acao) -> None:
        if acao is Acao.CONFIRMAR:
            self._jogo.mudar_estado(self._jogando.reiniciar())  # <<< REBOOT
        elif acao in (Acao.VOLTAR, Acao.IR_PARA_MENU):
            self._jogo.ir_para_menu_principal()

    def desenhar(self, tela: pygame.Surface) -> None:
        p = self._partida
        titulo = "SEM CORACOES!" if p.situacao is SituacaoDaPartida.SEM_VIDA else "TEMPO ESGOTADO!"
        self._cena.desenhar(tela, com_escuridao=False)
        self._servicos.hud.desenhar(tela, p)
        self._servicos.painel.desenhar(
            tela, titulo,
            f"Voce chegou a fase {p.nivel}  |  Pontos: {p.pontos}  |  "
            f"Recorde: fase {self._servicos.recorde.melhor_fase}",
            "A/ENTER: reiniciar   |   B/ESC: menu")
