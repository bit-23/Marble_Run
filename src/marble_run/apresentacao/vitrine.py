"""
vitrine.py - TESTE DOS MAPAS (menu secreto DESENVOLVEDOR).

Feito para apresentar o jogo: escolhe um mapa e joga num labirinto pequeno,
SEM limite de tempo e sem fim de jogo, com todos os perigos, molas e caixas
daquele mapa colados na entrada. Um painel lateral explica cada coisa e as
teclas abaixo mostram qualquer efeito na hora:

    1..8  aplica um buff (blusa, banana, flauta, relogio, lanterna, estrela, bussola, cafe)
    9     abre a roleta (como se pegasse uma caixa "?")
    F     forca o fenomeno do mapa (tempestade, apagao, terremoto, rajada)
    R     gera outro labirinto do mesmo mapa
    TAB   esconde/mostra o painel
"""
from __future__ import annotations

import pygame

from ..dominio.ambiente import TipoDeItem
from ..dominio.partida import Partida
from .cena import Cena
from .estados import ContextoDoJogo, Estado, EstadoJogando
from .icones import DESCRICOES_DOS_ITENS, icone
from .interface import nome_do_mapa
from .menus import CINZA, CREME, DOURADO, FUNDO_PAINEL, HACHURA, LILAS, Botao, Opcao, Seletor, TelaDeMenu
from .pixelart import TAMANHO_CAMADA, CamadaPixel, caixa_rabiscada, semente_fervendo

_MOLA =  ("MOLA NA PAREDE", "ANDE CONTRA ELA PARA PULAR A PAREDE")
_CAIXA = ("CAIXA ?", "ABRE A ROLETA DE BUFFS")
EXPLICACOES: dict[str, tuple[tuple[str, str], ...]] = {
    "gelo": (("POCA D'AGUA", "CONGELA 2S (A BLUSA PROTEGE)"),
             ("PLACA DE GELO", "DESLIZA GIRANDO ATE BATER EM ALGO"),
             _MOLA, ("CAIXA ?", "ROLETA COM BLUSA E BANANA")),
    "fogo": (("FOGO", "ACENDE E APAGA. QUEIMOU: -1 CORACAO E CORRE SEM CONTROLE"),
             ("ERUPCAO", "O CHAO RACHA PERTO DE VOCE E VIRA JATO DE LAVA. SAIA DE CIMA!"),
             _MOLA, ("CAIXA ?", "ROLETA COM FLAUTA (APAGA FOGO E LAVA)")),
    "deserto": (("AREIA MOVEDICA", "-60% DE VELOCIDADE"),
                ("TEMPESTADE", "DE TEMPOS EM TEMPOS: AREIA NA CARA E -45% VELOCIDADE"),
                ("SOL FORTE", "ENXERGA 25% MAIS LONGE"),
                _MOLA, ("CAIXA ?", "ROLETA COM FLAUTA (ACALMA A TEMPESTADE)")),
    "masmorra": (("TEIA DE ARANHA", "PRENDE ATE ACERTAR 4 SETAS EM ORDEM (ERROU, RECOMECA)"),
                 ("APAGAO", "A LUZ CAI PARA 30% POR 3S"), _MOLA, _CAIXA),
    "terra": (("TERREMOTO", "TELA TREME E OS CONTROLES INVERTEM"), _MOLA, _CAIXA),
    "vento": (("RAJADA", "O VENTO EMPURRA O JOGADOR"), _MOLA, _CAIXA),
}

ATALHOS_DE_BUFF: dict[int, TipoDeItem] = {
    pygame.K_1: TipoDeItem.BLUSA, pygame.K_2: TipoDeItem.BANANA, pygame.K_3: TipoDeItem.FLAUTA,
    pygame.K_4: TipoDeItem.RELOGIO, pygame.K_5: TipoDeItem.LANTERNA, pygame.K_6: TipoDeItem.ESTRELA,
    pygame.K_7: TipoDeItem.BUSSOLA, pygame.K_8: TipoDeItem.CAFE,
}


def quebrar_linhas(texto: str, largura: int) -> list[str]:
    """Quebra o texto em linhas de no maximo `largura` letras (sem cortar palavras)."""
    linhas, atual = [], ""
    for palavra in texto.split():
        if atual and len(atual) + 1 + len(palavra) > largura:
            linhas.append(atual)
            atual = palavra
        else:
            atual = f"{atual} {palavra}".strip()
    if atual:
        linhas.append(atual)
    return linhas


class EstadoEscolhaDaApresentacao(TelaDeMenu):
    TITULO = "TESTE DOS MAPAS"
    LARGURA_PAINEL = 320

    def __init__(self, jogo: ContextoDoJogo, retorno: Estado) -> None:
        self._retorno = retorno
        self._temas = jogo.servicos.cenas.nomes_dos_temas
        self._tema = 0
        super().__init__(jogo)

    @property
    def _nome_do_tema(self) -> str:
        return self._temas[self._tema]

    def _criar_opcoes(self) -> list[Opcao]:
        def mudar(passos: int) -> None:
            self._tema = (self._tema + passos) % len(self._temas)

        return [
            Seletor("MAPA", lambda: nome_do_mapa(self._nome_do_tema), mudar,
                    "ESQUERDA/DIREITA PARA TROCAR O MAPA"),
            Botao("COMECAR", self._comecar, "SEM TEMPO, SEM GAME OVER E TUDO PERTO DO INICIO"),
            Botao("VOLTAR", self._voltar),
        ]

    def _comecar(self) -> None:
        self._jogo.mudar_estado(EstadoApresentacao.nova(self._jogo, self._nome_do_tema))

    def _voltar(self) -> None:
        self._jogo.mudar_estado(self._retorno)

    def _subtitulo(self) -> str:
        return "ESCOLHA UM MAPA PARA MOSTRAR SEUS BUFFS E DEBUFFS"

    def _desenhar_extras(self, c: pygame.Surface) -> None:
        quadro = pygame.Rect(60, 190, TAMANHO_CAMADA[0] - 120, 104)
        caixa_rabiscada(c, quadro, LILAS, FUNDO_PAINEL, semente_fervendo(7, self._tempo), hachura=HACHURA)
        y = quadro.top + 8
        for nome, descricao in EXPLICACOES.get(self._nome_do_tema, ()):
            self._fonte.escrever(c, nome, 1, DOURADO, canto=(quadro.left + 10, y))
            for linha in quebrar_linhas(descricao, 36):
                self._fonte.escrever(c, linha, 1, CREME, canto=(quadro.left + 112, y))
                y += 10
            y += 3


class EstadoApresentacao(EstadoJogando):
    """A partida do modo apresentacao: igual ao jogo, com atalhos e painel explicativo."""

    LARGURA_DO_PAINEL = 178
    LETRAS_POR_LINHA = 27
    FOCO_COM_PAINEL = 0.31  # jogador no meio da area livre, a esquerda do painel

    def __init__(self, jogo: ContextoDoJogo, partida: Partida, cena: Cena) -> None:
        super().__init__(jogo, partida, cena)
        self._camada = CamadaPixel()
        self._mostrar_painel = True
        self._tempo = 0.0
        self._focar_camera()
        self._cena.enquadrar(instantaneo=True)

    def _focar_camera(self) -> None:
        if self._mostrar_painel:
            self._cena.focar(self.FOCO_COM_PAINEL, prender_nas_bordas=False)
        else:
            self._cena.focar(0.5)

    @classmethod
    def nova(cls, jogo: ContextoDoJogo, tema: str) -> EstadoApresentacao:
        partida = jogo.nova_apresentacao(tema)
        return cls(jogo, partida, jogo.servicos.cenas.criar(partida.fase))

    def reiniciar(self) -> EstadoJogando:
        return EstadoApresentacao.nova(self._jogo, self._partida.fase.tema)

    def tratar_evento(self, evento: pygame.event.Event) -> None:
        if evento.type != pygame.KEYDOWN:
            return
        fase = self._partida.fase
        if evento.key in ATALHOS_DE_BUFF:
            fase.aplicar_premio(ATALHOS_DE_BUFF[evento.key])
        elif evento.key == pygame.K_9:
            fase.abrir_caixa_magica()
        elif evento.key == pygame.K_f:
            fase.ambiente.forcar_fenomeno()
        elif evento.key == pygame.K_r:
            self._jogo.mudar_estado(self.reiniciar())
        elif evento.key == pygame.K_TAB:
            self._mostrar_painel = not self._mostrar_painel
            self._focar_camera()

    def atualizar(self, dt: float) -> None:
        self._tempo += dt
        super().atualizar(dt)

    def desenhar(self, tela: pygame.Surface) -> None:
        super().desenhar(tela)
        self._camada.limpar()
        c = self._camada.superficie
        fonte = self._servicos.fonte_pixel
        if not self._mostrar_painel:
            fonte.escrever(c, "TAB: MOSTRAR PAINEL", 1, CINZA, canto=(6, TAMANHO_CAMADA[1] - 12))
            self._camada.apresentar(tela)
            return
        quadro = pygame.Rect(TAMANHO_CAMADA[0] - self.LARGURA_DO_PAINEL - 4, 48, self.LARGURA_DO_PAINEL, 268)
        caixa_rabiscada(c, quadro, LILAS, (24, 18, 40, 215), semente_fervendo(3, self._tempo), hachura=HACHURA)
        x, y = quadro.left + 8, quadro.top + 8
        tema = self._partida.fase.tema
        fonte.escrever(c, f"MAPA: {nome_do_mapa(tema)}", 1, DOURADO, canto=(x, y))
        y += 14
        for nome, descricao in EXPLICACOES.get(tema, ()):
            fonte.escrever(c, nome, 1, (255, 170, 120), canto=(x, y))
            y += 9
            for linha in quebrar_linhas(descricao, self.LETRAS_POR_LINHA):
                fonte.escrever(c, linha, 1, CREME, canto=(x + 4, y))
                y += 9
            y += 3
        y += 2
        fonte.escrever(c, "ATALHOS", 1, DOURADO, canto=(x, y))
        y += 11
        for i, tipo in enumerate(ATALHOS_DE_BUFF.values()):
            coluna, linha = i % 2, i // 2
            px, py = x + coluna * 84, y + linha * 13
            fonte.escrever(c, str(i + 1), 1, LILAS, canto=(px, py + 2))
            c.blit(icone(tipo, 11), (px + 8, py))
            fonte.escrever(c, DESCRICOES_DOS_ITENS[tipo][0], 1, CREME, canto=(px + 22, py + 2))
        y += 4 * 13 + 3
        for tecla, texto in (("9", "ROLETA"), ("F", "FENOMENO JA"), ("R", "NOVO MAPA"), ("TAB", "ESCONDER")):
            fonte.escrever(c, tecla, 1, LILAS, canto=(x, y))
            fonte.escrever(c, texto, 1, CREME, canto=(x + 22, y))
            y += 9
        self._camada.apresentar(tela)
