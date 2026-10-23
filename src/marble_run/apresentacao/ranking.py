"""
ranking.py - O ranking (top 10 por dificuldade) e o editor do ranking (desenvolvedor).

    EstadoRanking          -> abas FACIL / NORMAL / DIFICIL / INSANO + top 10
    EstadoEditorDoRanking  -> mesma lista, mas cada jogador e um botao: editar ou apagar;
                              e da para limpar a aba inteira (com confirmacao)
    EstadoEdicaoDoJogador  -> nome, pontos e fase de um jogador

As telas so falam com os contratos do dominio: RepositorioDePontuacao
(ler/salvar) e EdicaoDoRanking (apagar/atualizar/limpar).
"""
from __future__ import annotations

from typing import Callable

import pygame

from ..dominio.contratos import EntradaDoRanking
from ..dominio.regras import NivelDeDificuldade
from .contratos import Efeito
from .entrada import Acao
from .estados import ContextoDoJogo, Estado
from .menus import (CINZA, CREME, DIFICULDADES, DOURADO, FUNDO_PAINEL, HACHURA, LILAS, Botao, CampoDeTexto,
                    EstadoConfirmacao, Opcao, TelaDeMenu)
from .pixelart import TAMANHO_CAMADA, CamadaPixel, FontePixel, caixa_rabiscada, semente_fervendo

Cor = tuple[int, int, int]
NIVEIS = tuple(NivelDeDificuldade)
MEDALHAS: tuple[Cor, ...] = ((255, 214, 90), (200, 210, 225), (215, 140, 80))  # ouro, prata, bronze
TAMANHO_DO_RANKING = 10


class AbasDeDificuldade:
    """As 4 abas do topo (esquerda/direita troca; clique do mouse tambem)."""

    LARGURA, ALTURA, ESPACO = 92, 16, 6

    def __init__(self, inicial: NivelDeDificuldade) -> None:
        self._indice = NIVEIS.index(inicial)
        self._areas: list[pygame.Rect] = []

    @property
    def atual(self) -> NivelDeDificuldade:
        return NIVEIS[self._indice]

    def mudar(self, passos: int) -> None:
        self._indice = (self._indice + passos) % len(NIVEIS)

    def clicar(self, pos_tela: tuple[int, int]) -> bool:
        pos = CamadaPixel.da_tela(pos_tela)
        for indice, area in enumerate(self._areas):
            if area.collidepoint(pos):
                self._indice = indice
                return True
        return False

    def desenhar(self, c: pygame.Surface, fonte: FontePixel, tempo: float, y: int) -> None:
        total = len(NIVEIS) * (self.LARGURA + self.ESPACO) - self.ESPACO
        x = (TAMANHO_CAMADA[0] - total) // 2
        self._areas = []
        for i, nivel in enumerate(NIVEIS):
            nome, cor, _ = DIFICULDADES[nivel]
            area = pygame.Rect(x + i * (self.LARGURA + self.ESPACO), y, self.LARGURA, self.ALTURA)
            ativa = i == self._indice
            fundo = (*[v // 3 for v in cor], 235) if ativa else (30, 24, 48, 220)
            caixa_rabiscada(c, area, DOURADO if ativa else (80, 70, 110), fundo,
                            semente_fervendo(40 + i, tempo) if ativa else 40 + i, sombra=ativa)
            fonte.escrever(c, nome, 1, cor if ativa else CINZA, centro=area.center)
            self._areas.append(area)


# ======================================================================
class EstadoRanking(TelaDeMenu):
    TITULO = "RANKING"
    LARGURA_PAINEL = 140
    RODAPE = "ESQUERDA/DIREITA: TROCAR DIFICULDADE   ESC: VOLTAR"

    def __init__(self, jogo: ContextoDoJogo, retorno: Estado) -> None:
        self._retorno = retorno
        super().__init__(jogo)
        self._abas = AbasDeDificuldade(self._servicos.preferencias.dificuldade)
        self._entradas: list[EntradaDoRanking] = []
        self._recarregar()

    def _criar_opcoes(self) -> list[Opcao]:
        return [Botao("VOLTAR", self._voltar)]

    def _voltar(self) -> None:
        self._jogo.mudar_estado(self._retorno)

    def _recarregar(self) -> None:
        self._entradas = self._servicos.pontuacoes.ranking(self._abas.atual, TAMANHO_DO_RANKING)

    def _topo_painel(self) -> int:
        return 262

    def executar(self, acao: Acao) -> None:
        if acao in (Acao.ESQUERDA, Acao.DIREITA):
            self._abas.mudar(-1 if acao is Acao.ESQUERDA else 1)
            self._recarregar()
            self._som_de_menu()
        else:
            super().executar(acao)

    def tratar_evento(self, evento: pygame.event.Event) -> None:
        if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1 and self._abas.clicar(evento.pos):
            self._recarregar()
            self._som_de_menu()
            return
        super().tratar_evento(evento)

    def _som_de_menu(self) -> None:
        self._servicos.audio.tocar(Efeito.MENU)

    def _desenhar_extras(self, c: pygame.Surface) -> None:
        self._abas.desenhar(c, self._fonte, self._tempo, 66)
        quadro = pygame.Rect(40, 88, TAMANHO_CAMADA[0] - 80, 166)
        caixa_rabiscada(c, quadro, LILAS, FUNDO_PAINEL, semente_fervendo(9, self._tempo), hachura=HACHURA)
        colunas = (quadro.left + 14, quadro.left + 52, quadro.right - 96, quadro.right - 16)
        self._fonte.escrever(c, "POS", 1, LILAS, canto=(colunas[0], quadro.top + 8))
        self._fonte.escrever(c, "JOGADOR", 1, LILAS, canto=(colunas[1], quadro.top + 8))
        self._fonte.escrever(c, "PONTOS", 1, LILAS, direita=(colunas[2], quadro.top + 8))
        self._fonte.escrever(c, "FASE", 1, LILAS, direita=(colunas[3], quadro.top + 8))
        if not self._entradas:
            self._fonte.escrever(c, "NINGUEM AINDA... SEJA O PRIMEIRO!", 1, CREME, centro=quadro.center)
            return
        eu = self._servicos.preferencias.nome_jogador.strip().casefold()
        for i, entrada in enumerate(self._entradas):
            y = quadro.top + 24 + i * 14
            meu = entrada.jogador.strip().casefold() == eu and eu != ""
            if meu:
                c.fill((110, 80, 30, 200), (quadro.left + 6, y - 3, quadro.width - 12, 13))
            cor = MEDALHAS[i] if i < len(MEDALHAS) else (DOURADO if meu else CREME)
            if i < len(MEDALHAS):  # medalhinha
                c.fill(cor, (colunas[0] - 8, y, 5, 5))
                c.fill((20, 12, 30), (colunas[0] - 7, y + 1, 3, 3))
            self._fonte.escrever(c, f"{i + 1}.", 1, cor, canto=(colunas[0], y))
            self._fonte.escrever(c, entrada.jogador + ("  < VOCE" if meu else ""), 1, cor, canto=(colunas[1], y))
            self._fonte.escrever(c, str(entrada.pontos), 1, cor, direita=(colunas[2], y))
            self._fonte.escrever(c, str(entrada.fase), 1, cor, direita=(colunas[3], y))


# ======================================================================
class LinhaDoRanking(Opcao):
    """Um jogador do editor: nome a esquerda, pontos e fase a direita."""

    def __init__(self, posicao: int, entrada: EntradaDoRanking, editar: Callable[[], None]) -> None:
        super().__init__(f"{posicao}. {entrada.jogador}", "ENTER: EDITAR/APAGAR   ESQUERDA/DIREITA: TROCAR ABA")
        self._entrada = entrada
        self._editar = editar

    def valor(self) -> str:
        return f"{self._entrada.pontos} PTS  F{self._entrada.fase}"

    def ativar(self) -> None:
        self._editar()


class EstadoEditorDoRanking(TelaDeMenu):
    TITULO = "EDITAR RANKING"
    ESCALA_TITULO = 3
    TOPO_TITULO = 8
    ALTURA_LINHA = 18
    LARGURA_PAINEL = 410
    RODAPE = ""

    def __init__(self, jogo: ContextoDoJogo, retorno: Estado) -> None:
        self._retorno = retorno
        self._abas = AbasDeDificuldade(NivelDeDificuldade.NORMAL)
        self._entradas: list[EntradaDoRanking] = []
        super().__init__(jogo)
        self._recarregar()

    def _criar_opcoes(self) -> list[Opcao]:
        linhas: list[Opcao] = [LinhaDoRanking(i + 1, e, lambda e=e: self._editar(e))
                               for i, e in enumerate(self._entradas)]
        return linhas + [
            Botao("LIMPAR ESTA ABA", self._confirmar_limpeza, "APAGA TODO MUNDO DESTA DIFICULDADE"),
            Botao("VOLTAR", self._voltar),
        ]

    def recarregar_e_mostrar(self) -> None:
        """Volta para esta tela com a lista atualizada (depois de editar/apagar)."""
        self._recarregar()
        self._jogo.mudar_estado(self)

    def _recarregar(self) -> None:
        self._entradas = self._servicos.pontuacoes.ranking(self._abas.atual, TAMANHO_DO_RANKING)
        self._opcoes = self._criar_opcoes()
        self._indice = min(self._indice, len(self._opcoes) - 1)

    def _editar(self, entrada: EntradaDoRanking) -> None:
        self._jogo.mudar_estado(EstadoEdicaoDoJogador(self._jogo, entrada, self._abas.atual, self))

    def _confirmar_limpeza(self) -> None:
        nivel = self._abas.atual

        def limpar() -> None:
            self._servicos.editor_do_ranking.limpar(nivel)
            self.recarregar_e_mostrar()

        self._jogo.mudar_estado(EstadoConfirmacao(
            self._jogo, f"APAGAR TODO O RANKING {DIFICULDADES[nivel][0]}?", "SIM, LIMPAR TUDO", limpar, self))

    def _voltar(self) -> None:
        self._jogo.mudar_estado(self._retorno)

    def _topo_painel(self) -> int:
        return 62

    def executar(self, acao: Acao) -> None:
        if acao in (Acao.ESQUERDA, Acao.DIREITA):
            self._abas.mudar(-1 if acao is Acao.ESQUERDA else 1)
            self._indice = 0
            self._recarregar()
        else:
            super().executar(acao)

    def tratar_evento(self, evento: pygame.event.Event) -> None:
        if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1 and self._abas.clicar(evento.pos):
            self._indice = 0
            self._recarregar()
            return
        super().tratar_evento(evento)

    def _desenhar_extras(self, c: pygame.Surface) -> None:
        self._abas.desenhar(c, self._fonte, self._tempo, 40)
        if not self._entradas:
            self._fonte.escrever(c, "(NINGUEM NESTA DIFICULDADE)", 1, CINZA,
                                 centro=(TAMANHO_CAMADA[0] // 2, self._topo_painel() - 4))


class EstadoEdicaoDoJogador(TelaDeMenu):
    USA_TEXTO = True
    TITULO = "EDITAR JOGADOR"
    LARGURA_PAINEL = 340

    def __init__(self, jogo: ContextoDoJogo, entrada: EntradaDoRanking, nivel: NivelDeDificuldade,
                 editor: EstadoEditorDoRanking) -> None:
        self._entrada = entrada
        self._nivel = nivel
        self._editor = editor
        self._nome = entrada.jogador
        self._pontos = str(entrada.pontos)
        self._fase = str(entrada.fase)
        self._erro = ""
        super().__init__(jogo)

    def _criar_opcoes(self) -> list[Opcao]:
        def definir(atributo: str) -> Callable[[str], None]:
            def _definir(valor: str) -> None:
                setattr(self, atributo, valor)
                self._erro = ""
            return _definir

        return [
            CampoDeTexto("NOME", lambda: self._nome, definir("_nome"), ajuda="RENOMEAR O JOGADOR"),
            CampoDeTexto("PONTOS", lambda: self._pontos, definir("_pontos"), limite=7, vazio="0",
                         so_numeros=True, ajuda="SO NUMEROS"),
            CampoDeTexto("FASE", lambda: self._fase, definir("_fase"), limite=3, vazio="0",
                         so_numeros=True, ajuda="FASE ALCANCADA"),
            Botao("SALVAR", self._salvar),
            Botao("APAGAR JOGADOR", self._confirmar_apagar, "TIRA ESTE JOGADOR DO RANKING"),
            Botao("VOLTAR", self._editor.recarregar_e_mostrar, "SAI SEM SALVAR"),
        ]

    def _salvar(self) -> None:
        nome = self._nome.strip()
        if not nome:
            self._erro = "O NOME NAO PODE FICAR VAZIO"
            return
        salvou = self._servicos.editor_do_ranking.atualizar(
            self._entrada.jogador, self._nivel, nome, int(self._pontos or 0), int(self._fase or 0))
        if not salvou:
            self._erro = "JA EXISTE OUTRO JOGADOR COM ESSE NOME"
            return
        self._editor.recarregar_e_mostrar()

    def _confirmar_apagar(self) -> None:
        def apagar() -> None:
            self._servicos.editor_do_ranking.apagar(self._entrada.jogador, self._nivel)
            self._editor.recarregar_e_mostrar()

        self._jogo.mudar_estado(EstadoConfirmacao(
            self._jogo, f"APAGAR {self._entrada.jogador} DO RANKING {DIFICULDADES[self._nivel][0]}?",
            "SIM, APAGAR", apagar, self))

    def _voltar(self) -> None:
        self._editor.recarregar_e_mostrar()

    def _subtitulo(self) -> str:
        return f"{self._entrada.jogador}  -  RANKING {DIFICULDADES[self._nivel][0]}"

    def _desenhar_extras(self, c: pygame.Surface) -> None:
        if self._erro:
            self._fonte.escrever(c, self._erro, 1, (255, 110, 110), centro=(TAMANHO_CAMADA[0] // 2, 250))
