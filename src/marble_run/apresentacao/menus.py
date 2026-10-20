"""
menus.py - As telas de menu, no estilo pixel art "desenhado a mao".

    EstadoMenu ----------> JOGAR ---------> EstadoNovoJogo (nome + dificuldade)
        |                  CONFIGURACOES -> EstadoConfiguracoes -> EstadoControles
        |                  SOM -----------> EstadoSom
        |                  SAIR
    EstadoPausado (ESC na partida): CONTINUAR | REINICIAR | CONFIGURACOES | SOM
                                    | MENU PRINCIPAL | SAIR DO JOGO

Todas sao TelaDeMenu: uma lista de Opcoes (Botao, Alternador, Seletor,
Barra, CampoDeTexto) + navegacao por teclado, controle e mouse. Uma tela
nova so declara as suas opcoes (Template Method). O "fundo" e um Strategy:
o labirinto animado no menu principal ou a partida congelada na pausa -
assim Configuracoes e Som funcionam igual nos dois lugares.
"""
from __future__ import annotations

import math
import random
from abc import abstractmethod
from typing import Callable, Protocol

import pygame

from ..dominio.jogador import Direcao
from ..dominio.regras import NivelDeDificuldade
from .contratos import Efeito
from .entrada import Acao
from .estados import ContextoDoJogo, Estado, EstadoJogando
from .personagem import SpritesDoJogador
from .pixelart import (TAMANHO_CAMADA, CamadaPixel, ExplosaoDePixels, caixa_rabiscada, linha_rabiscada, pixelizar,
                       semente_fervendo)

Cor = tuple[int, int, int]

DOURADO: Cor = (255, 214, 90)
CREME: Cor = (245, 236, 210)
LILAS: Cor = (170, 150, 220)
CINZA: Cor = (120, 112, 150)
FUNDO_PAINEL = (34, 26, 56, 235)
FUNDO_SELECIONADO = (110, 80, 30, 200)
HACHURA: Cor = (52, 42, 84)

DIFICULDADES: dict[NivelDeDificuldade, tuple[str, Cor, str]] = {
    NivelDeDificuldade.FACIL: ("FACIL", (130, 230, 150), "+40% DE TEMPO, MAIS LUZ E MENOS PERIGOS"),
    NivelDeDificuldade.NORMAL: ("NORMAL", DOURADO, "O LABIRINTO DO JEITO QUE FOI PENSADO"),
    NivelDeDificuldade.DIFICIL: ("DIFICIL", (255, 150, 70), "-25% DE TEMPO, MENOS LUZ E MAIS PERIGOS"),
    NivelDeDificuldade.INSANO: ("INSANO", (255, 80, 90), "METADE DO TEMPO, SEM LUZ EXTRA, SEM LANTERNA"),
}

Texto = str | Callable[[], str]


def _ler(texto: Texto) -> str:
    return texto() if callable(texto) else texto


# ======================================================================
#  Opcoes
# ======================================================================
class Opcao:
    """Uma linha do menu. Cada tipo sabe reagir a CONFIRMAR e a esquerda/direita."""

    def __init__(self, rotulo: str, ajuda: Texto = "") -> None:
        self.rotulo = rotulo
        self._ajuda = ajuda

    @property
    def ajuda(self) -> str:
        return _ler(self._ajuda)

    @property
    def ajustavel(self) -> bool:
        """Mostra setinhas < > e aceita esquerda/direita."""
        return False

    def valor(self) -> str | None:
        return None

    def cor_do_valor(self) -> Cor | None:
        return None

    def ativar(self) -> None:
        pass

    def ajustar(self, passos: int) -> bool:
        return False


class Botao(Opcao):
    def __init__(self, rotulo: str, acao: Callable[[], None], ajuda: Texto = "") -> None:
        super().__init__(rotulo, ajuda)
        self._acao = acao

    def ativar(self) -> None:
        self._acao()


class Alternador(Opcao):
    """SIM / NAO."""

    def __init__(self, rotulo: str, obter: Callable[[], bool], alternar: Callable[[], None],
                 ajuda: Texto = "") -> None:
        super().__init__(rotulo, ajuda)
        self._obter = obter
        self._alternar = alternar

    @property
    def ajustavel(self) -> bool:
        return True

    def valor(self) -> str:
        return "SIM" if self._obter() else "NAO"

    def cor_do_valor(self) -> Cor:
        return (130, 230, 150) if self._obter() else (230, 120, 120)

    def ativar(self) -> None:
        self._alternar()

    def ajustar(self, passos: int) -> bool:
        self._alternar()
        return True


class Seletor(Opcao):
    """Escolhe entre varios valores com esquerda/direita."""

    def __init__(self, rotulo: str, obter: Callable[[], str], mudar: Callable[[int], None],
                 ajuda: Texto = "", cor: Callable[[], Cor] | None = None) -> None:
        super().__init__(rotulo, ajuda)
        self._obter = obter
        self._mudar = mudar
        self._cor = cor

    @property
    def ajustavel(self) -> bool:
        return True

    def valor(self) -> str:
        return self._obter()

    def cor_do_valor(self) -> Cor | None:
        return self._cor() if self._cor else None

    def ativar(self) -> None:
        self.ajustar(1)

    def ajustar(self, passos: int) -> bool:
        antes = self._obter()
        self._mudar(passos)
        return self._obter() != antes


class Barra(Opcao):
    """Volume de 0 a 100% em blocos."""

    BLOCOS = 10

    def __init__(self, rotulo: str, obter: Callable[[], float], mudar: Callable[[int], None],
                 ajuda: Texto = "") -> None:
        super().__init__(rotulo, ajuda)
        self._obter = obter
        self._mudar = mudar

    @property
    def ajustavel(self) -> bool:
        return True

    @property
    def fracao(self) -> float:
        return self._obter()

    def valor(self) -> str:
        return f"{round(self._obter() * 100)}%"

    def ajustar(self, passos: int) -> bool:
        antes = self._obter()
        self._mudar(passos)
        return self._obter() != antes


class CampoDeTexto(Opcao):
    def __init__(self, rotulo: str, obter: Callable[[], str], definir: Callable[[str], None],
                 limite: int = 16, vazio: str = "DIGITE AQUI", ao_confirmar: Callable[[], None] | None = None,
                 ajuda: Texto = "", so_numeros: bool = False) -> None:
        super().__init__(rotulo, ajuda)
        self._obter = obter
        self._definir = definir
        self._limite = limite
        self.vazio = vazio
        self._ao_confirmar = ao_confirmar
        self._so_numeros = so_numeros

    @property
    def texto(self) -> str:
        return self._obter()

    def digitar(self, texto: str) -> None:
        texto = "".join(c for c in texto if (c.isdigit() if self._so_numeros else c.isprintable()))
        self._definir((self._obter() + texto)[: self._limite])

    def apagar(self) -> None:
        self._definir(self._obter()[:-1])

    def ativar(self) -> None:
        if self._ao_confirmar:
            self._ao_confirmar()


# ======================================================================
#  Fundos (Strategy)
# ======================================================================
class Fundo(Protocol):
    def atualizar(self, dt: float) -> None: ...

    def desenhar(self, tela: pygame.Surface) -> None: ...


class FundoDaPartida:
    """A partida congelada, escurecida, atras do menu de pausa."""

    def __init__(self, jogando: EstadoJogando) -> None:
        self._jogando = jogando
        self._veu: pygame.Surface | None = None

    def atualizar(self, dt: float) -> None:
        pass

    def desenhar(self, tela: pygame.Surface) -> None:
        self._jogando.desenhar(tela)
        if self._veu is None or self._veu.get_size() != tela.get_size():
            self._veu = pygame.Surface(tela.get_size(), pygame.SRCALPHA)
            self._veu.fill((10, 6, 20, 170))
        tela.blit(self._veu, (0, 0))


# ======================================================================
#  Tela de menu generica (Template Method)
# ======================================================================
class TelaDeMenu(Estado):
    TITULO = ""
    ESCALA_TITULO = 4
    TOPO_TITULO = 22
    LARGURA_PAINEL = 300
    ALTURA_LINHA = 22
    RODAPE = "SETAS: ESCOLHER   ENTER: CONFIRMAR   ESC: VOLTAR   MOUSE TAMBEM!"
    LIMIAR_ANALOGICO = int(32767 * 0.6)

    def __init__(self, jogo: ContextoDoJogo, fundo: Fundo | None = None) -> None:
        super().__init__(jogo)
        self._fundo = fundo if fundo is not None else self._servicos.fundo_menu
        self._fonte = self._servicos.fonte_pixel
        self._camada = CamadaPixel()
        self._opcoes = self._criar_opcoes()
        self._indice = 0
        self._tempo = 0.0
        self._areas: list[tuple[pygame.Rect, pygame.Rect | None, pygame.Rect | None]] = []
        self._zonas_analogico: dict[int, int] = {}

    # ------------------------------------------------------------------
    # Ganchos das telas concretas
    # ------------------------------------------------------------------
    @abstractmethod
    def _criar_opcoes(self) -> list[Opcao]: ...

    def _voltar(self) -> None:
        """ESC / botao B."""

    def _subtitulo(self) -> str:
        return ""

    def _centro_x(self) -> int:
        return TAMANHO_CAMADA[0] // 2

    def _topo_painel(self) -> int:
        return 84

    def _desenhar_extras(self, c: pygame.Surface) -> None:
        """Mascote, tabelas, recordes... (o que cada tela tiver de especial)."""

    def _rotulo_visivel(self, indice: int) -> bool:
        return True

    def _cor_do_rotulo(self, indice: int, selecionada: bool) -> Cor:
        return DOURADO if selecionada else CREME

    def _deslocamento(self) -> tuple[int, int]:
        """Tremor da tela inteira (em pixels da tela)."""
        return 0, 0

    # ------------------------------------------------------------------
    # Estado
    # ------------------------------------------------------------------
    @property
    def _opcao_atual(self) -> Opcao:
        return self._opcoes[self._indice]

    @property
    def capturando_texto(self) -> bool:
        return isinstance(self._opcao_atual, CampoDeTexto)

    def executar(self, acao: Acao) -> None:
        if acao is Acao.CIMA:
            self._mover(-1)
        elif acao is Acao.BAIXO:
            self._mover(1)
        elif acao in (Acao.ESQUERDA, Acao.DIREITA):
            if self._opcao_atual.ajustar(-1 if acao is Acao.ESQUERDA else 1):
                self._som(Efeito.MENU)
        elif acao is Acao.CONFIRMAR:
            self._som(Efeito.CONFIRMAR)
            self._opcao_atual.ativar()
        elif acao is Acao.VOLTAR:
            self._som(Efeito.MENU)
            self._voltar()

    def tratar_evento(self, evento: pygame.event.Event) -> None:
        campo = self._opcao_atual if isinstance(self._opcao_atual, CampoDeTexto) else None
        if evento.type == pygame.TEXTINPUT and campo is not None:
            campo.digitar(evento.text)
        elif evento.type == pygame.KEYDOWN and evento.key == pygame.K_BACKSPACE and campo is not None:
            campo.apagar()
        elif evento.type == pygame.MOUSEMOTION:
            indice = self._linha_em(evento.pos)
            if indice is not None and indice != self._indice:
                self._indice = indice
                self._som(Efeito.MENU)
        elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            self._clicar(evento.pos)
        elif evento.type == pygame.MOUSEWHEEL and evento.y:
            if self._opcao_atual.ajustar(1 if evento.y > 0 else -1):
                self._som(Efeito.MENU)
        elif evento.type == pygame.CONTROLLERAXISMOTION:
            self._analogico(evento.axis, evento.value)

    def atualizar(self, dt: float) -> None:
        self._tempo += dt
        self._fundo.atualizar(dt)

    def desenhar(self, tela: pygame.Surface) -> None:
        self._fundo.desenhar(tela)
        self._camada.limpar()
        c = self._camada.superficie
        self._desenhar_titulo(c)
        self._desenhar_painel(c)
        self._desenhar_extras(c)
        self._fonte.escrever(c, self.RODAPE, 1, CINZA, centro=(TAMANHO_CAMADA[0] // 2, TAMANHO_CAMADA[1] - 10))
        self._camada.apresentar(tela, self._deslocamento())

    # ------------------------------------------------------------------
    # Navegacao
    # ------------------------------------------------------------------
    def _mover(self, passo: int) -> None:
        self._indice = (self._indice + passo) % len(self._opcoes)
        self._som(Efeito.MENU)

    def _som(self, efeito: Efeito) -> None:
        self._servicos.audio.tocar(efeito)

    def _linha_em(self, pos_tela: tuple[int, int]) -> int | None:
        pos = CamadaPixel.da_tela(pos_tela)
        for indice, (linha, _, _) in enumerate(self._areas):
            if linha.collidepoint(pos):
                return indice
        return None

    def _clicar(self, pos_tela: tuple[int, int]) -> None:
        indice = self._linha_em(pos_tela)
        if indice is None:
            return
        self._indice = indice
        _, esquerda, direita = self._areas[indice]
        pos = CamadaPixel.da_tela(pos_tela)
        if esquerda is not None and esquerda.inflate(8, 8).collidepoint(pos):
            self.executar(Acao.ESQUERDA)
        elif direita is not None and direita.inflate(8, 8).collidepoint(pos):
            self.executar(Acao.DIREITA)
        elif not isinstance(self._opcao_atual, (Barra, CampoDeTexto)):
            self.executar(Acao.CONFIRMAR)

    def _analogico(self, eixo: int, valor: int) -> None:
        acoes = {pygame.CONTROLLER_AXIS_LEFTY: (Acao.CIMA, Acao.BAIXO),
                 pygame.CONTROLLER_AXIS_LEFTX: (Acao.ESQUERDA, Acao.DIREITA)}
        if eixo not in acoes:
            return
        zona = 0 if abs(valor) < self.LIMIAR_ANALOGICO else (1 if valor > 0 else -1)
        anterior = self._zonas_analogico.get(eixo, 0)
        self._zonas_analogico[eixo] = zona
        if zona and zona != anterior:
            self.executar(acoes[eixo][0] if zona < 0 else acoes[eixo][1])

    # ------------------------------------------------------------------
    # Desenho
    # ------------------------------------------------------------------
    def _desenhar_titulo(self, c: pygame.Surface) -> None:
        texto = self._fonte.normalizar(self.TITULO)
        e = self.ESCALA_TITULO
        largura, altura = self._fonte.medir(texto, e)
        x = (TAMANHO_CAMADA[0] - largura) // 2
        for i, letra in enumerate(texto):  # cada letra pula um pouquinho: titulo "vivo"
            dy = round(math.sin(self._tempo * 3 + i * 0.55) * 2)
            px = x + i * 6 * e
            relevo = max(1, e // 2)
            c.blit(self._fonte.render(letra, e, (120, 60, 20), None), (px + relevo, self.TOPO_TITULO + dy + relevo))
            c.blit(self._fonte.render(letra, e, DOURADO, None), (px, self.TOPO_TITULO + dy))
        sublinhado = self.TOPO_TITULO + altura + e + 3
        linha_rabiscada(c, (x - 4, sublinhado), (x + largura + 4, sublinhado), DOURADO,
                        random.Random(semente_fervendo(99, self._tempo)), passo=9)
        subtitulo = self._subtitulo()
        if subtitulo:
            self._fonte.escrever(c, subtitulo, 1, LILAS, centro=(TAMANHO_CAMADA[0] // 2, sublinhado + 10))

    def _desenhar_painel(self, c: pygame.Surface) -> None:
        largura = self.LARGURA_PAINEL
        altura = len(self._opcoes) * self.ALTURA_LINHA + 14
        x = self._centro_x() - largura // 2
        y = self._topo_painel()
        painel = pygame.Rect(x, y, largura, altura)
        caixa_rabiscada(c, painel, LILAS, FUNDO_PAINEL, semente_fervendo(1, self._tempo), hachura=HACHURA)
        self._areas = []
        for i, opcao in enumerate(self._opcoes):
            linha = pygame.Rect(x + 7, y + 7 + i * self.ALTURA_LINHA, largura - 14, self.ALTURA_LINHA - 2)
            self._areas.append(self._desenhar_opcao(c, opcao, linha, i == self._indice, i))
        ajuda = self._opcao_atual.ajuda
        if ajuda:
            self._fonte.escrever(c, ajuda, 1, LILAS, centro=(self._centro_x(), painel.bottom + 12))

    def _desenhar_opcao(self, c: pygame.Surface, opcao: Opcao, linha: pygame.Rect, selecionada: bool,
                        indice: int) -> tuple[pygame.Rect, pygame.Rect | None, pygame.Rect | None]:
        if selecionada:
            caixa_rabiscada(c, linha, DOURADO, FUNDO_SELECIONADO, semente_fervendo(10 + indice, self._tempo),
                            sombra=False)
            balanco = round(math.sin(self._tempo * 9) * 1.5)
            self._fonte.escrever(c, ">", 2, DOURADO, canto=(linha.left + 3 + balanco, linha.centery - 7))
        if not self._rotulo_visivel(indice):
            return linha, None, None
        cor = self._cor_do_rotulo(indice, selecionada)
        self._fonte.escrever(c, opcao.rotulo, 2, cor, canto=(linha.left + 19, linha.centery - 7))

        direita = linha.right - 6
        seta_esq = seta_dir = None
        cor_setas = DOURADO if selecionada else CINZA
        if opcao.ajustavel:
            seta_dir = self._fonte.escrever(c, ">", 2, cor_setas, direita=(direita, linha.centery - 7))
            direita = seta_dir.left - 5
        if isinstance(opcao, Barra):
            self._fonte.escrever(c, opcao.valor(), 1, cor, direita=(direita, linha.centery - 3))
            direita -= 28
            for b in range(Barra.BLOCOS):
                bloco = pygame.Rect(direita - (Barra.BLOCOS - b) * 6, linha.centery - 4, 5, 8)
                cheio = b < round(opcao.fracao * Barra.BLOCOS)
                c.fill(DOURADO if cheio else (60, 50, 90), bloco)
                if cheio:
                    c.fill((255, 245, 190), (bloco.x, bloco.y, 5, 2))
            direita -= Barra.BLOCOS * 6 + 4
        elif isinstance(opcao, CampoDeTexto):
            texto = opcao.texto
            cursor = "_" if selecionada and int(self._tempo * 2.5) % 2 == 0 else " "
            if texto:
                self._fonte.escrever(c, texto + cursor, 2, CREME, direita=(direita, linha.centery - 7))
            else:
                self._fonte.escrever(c, opcao.vazio + cursor, 2, CINZA, direita=(direita, linha.centery - 7))
        elif opcao.valor() is not None:
            ret = self._fonte.escrever(c, opcao.valor(), 2, opcao.cor_do_valor() or cor,
                                       direita=(direita, linha.centery - 7))
            direita = ret.left - 5
        if opcao.ajustavel:
            seta_esq = self._fonte.escrever(c, "<", 2, cor_setas, direita=(direita, linha.centery - 7))
        return linha, seta_esq, seta_dir


# ======================================================================
#  Mascote (cachorro de cartola andando de um lado para o outro)
# ======================================================================
class MascoteAndando:
    ALTURA = 56
    VELOCIDADE = 28.0
    QUADROS_POR_SEGUNDO = 9

    def __init__(self, sprites: SpritesDoJogador, x_min: int, x_max: int, base: int) -> None:
        self._quadros = {
            direcao: [pixelizar(sprites.quadro(direcao, i), self.ALTURA) for i in range(SpritesDoJogador.QUADROS_POR_DIRECAO)]
            for direcao in (Direcao.DIREITA, Direcao.ESQUERDA)
        }
        self._x_min, self._x_max, self._base = x_min, x_max, base
        self._x = float(x_min)
        self._direcao = Direcao.DIREITA
        self._tempo = 0.0

    def atualizar(self, dt: float) -> None:
        self._tempo += dt
        passo = self.VELOCIDADE * dt * (1 if self._direcao is Direcao.DIREITA else -1)
        self._x += passo
        if self._x >= self._x_max:
            self._x, self._direcao = self._x_max, Direcao.ESQUERDA
        elif self._x <= self._x_min:
            self._x, self._direcao = self._x_min, Direcao.DIREITA

    def desenhar(self, c: pygame.Surface) -> None:
        quadros = self._quadros[self._direcao]
        img = quadros[int(self._tempo * self.QUADROS_POR_SEGUNDO) % len(quadros)]
        c.fill((10, 6, 18, 140), (round(self._x) - 12, self._base - 1, 24, 3))  # sombra
        c.blit(img, img.get_rect(midbottom=(round(self._x), self._base)))


# ======================================================================
#  Telas
# ======================================================================
class EstadoMenu(TelaDeMenu):
    TITULO = "MARBLE RUN"
    ESCALA_TITULO = 5
    TOPO_TITULO = 26
    LARGURA_PAINEL = 200
    CODIGO_SECRETO = (Acao.CIMA, Acao.BAIXO, Acao.DIREITA, Acao.ESQUERDA)
    ROTULO_SECRETO = "DESENVOLVEDOR"
    ATRASO_DO_SURGIMENTO = 0.3   # a opcao aparece logo depois do clarao
    DESTAQUE_DO_SEGREDO = 3.0    # segundos piscando "NOVO!" e mensagem
    TREMOR_DO_SEGREDO = 0.5

    def __init__(self, jogo: ContextoDoJogo) -> None:
        super().__init__(jogo)
        self._mascote = MascoteAndando(self._servicos.sprites, 60, 150, 250)
        self._sequencia: list[Acao] = []
        self._explosao: ExplosaoDePixels | None = None

    def _criar_opcoes(self) -> list[Opcao]:
        jogo = self._jogo
        opcoes = [
            Botao("JOGAR", lambda: jogo.mudar_estado(EstadoNovoJogo(jogo)), "ESCOLHA SEU NOME E A DIFICULDADE"),
            Botao("RANKING", lambda: jogo.abrir_ranking(self), "OS 10 MELHORES DE CADA DIFICULDADE"),
            Botao("CONFIGURACOES", lambda: jogo.mudar_estado(EstadoConfiguracoes(jogo, self)),
                  "CAMERA, TELA CHEIA, TREMOR E CONTROLES"),
            Botao("SOM", lambda: jogo.mudar_estado(EstadoSom(jogo, self)), "VOLUME DA MUSICA E DOS EFEITOS"),
        ]
        if self._servicos.preferencias.apresentacao_liberada:
            opcoes.append(Botao(self.ROTULO_SECRETO, lambda: jogo.abrir_desenvolvedor(self),
                                "EDITAR O RANKING E TESTAR OS MAPAS"))
        opcoes.append(Botao("SAIR", jogo.encerrar, "ATE A PROXIMA!"))
        return opcoes

    def executar(self, acao: Acao) -> None:
        if acao in self.CODIGO_SECRETO:
            self._sequencia = (self._sequencia + [acao])[-len(self.CODIGO_SECRETO):]
            if tuple(self._sequencia) == self.CODIGO_SECRETO and not self._servicos.preferencias.apresentacao_liberada:
                self._revelar_segredo()
                return
        super().executar(acao)

    def _revelar_segredo(self) -> None:
        self._servicos.preferencias.liberar_apresentacao()
        self._opcoes = self._criar_opcoes()
        self._indice = next(i for i, o in enumerate(self._opcoes) if o.rotulo == self.ROTULO_SECRETO)
        linha_y = self._topo_painel() + 7 + self._indice * self.ALTURA_LINHA + self.ALTURA_LINHA // 2
        self._explosao = ExplosaoDePixels(self._centro_x(), linha_y)
        self._servicos.audio.tocar(Efeito.SEGREDO)

    def _voltar(self) -> None:
        self._indice = len(self._opcoes) - 1  # ESC leva ate "SAIR" (sem fechar sem querer)

    def _subtitulo(self) -> str:
        if self._explosao is not None and self._explosao.tempo < self.DESTAQUE_DO_SEGREDO:
            return "*** CODIGO SECRETO DESBLOQUEADO! ***" if int(self._tempo * 6) % 2 == 0 else ""
        return "ESCAPE DO LABIRINTO ANTES QUE O TEMPO ACABE!"

    def _centro_x(self) -> int:
        return 300

    def _topo_painel(self) -> int:
        return 108

    def _eh_a_opcao_secreta(self, indice: int) -> bool:
        return self._opcoes[indice].rotulo == self.ROTULO_SECRETO

    def _rotulo_visivel(self, indice: int) -> bool:
        surgindo = self._explosao is not None and self._explosao.tempo < self.ATRASO_DO_SURGIMENTO
        return not (surgindo and self._eh_a_opcao_secreta(indice))

    def _cor_do_rotulo(self, indice: int, selecionada: bool) -> Cor:
        destaque = self._explosao is not None and self._explosao.tempo < self.DESTAQUE_DO_SEGREDO
        if destaque and self._eh_a_opcao_secreta(indice):  # arco-iris enquanto e novidade
            cor = pygame.Color(0)
            cor.hsva = ((self._tempo * 360) % 360, 55, 100, 100)
            return cor.r, cor.g, cor.b
        return super()._cor_do_rotulo(indice, selecionada)

    def _deslocamento(self) -> tuple[int, int]:
        if self._explosao is None or self._explosao.tempo > self.TREMOR_DO_SEGREDO:
            return 0, 0
        forca = round(8 * (1 - self._explosao.tempo / self.TREMOR_DO_SEGREDO))
        return random.randint(-forca, forca), random.randint(-forca, forca)

    def atualizar(self, dt: float) -> None:
        super().atualizar(dt)
        self._mascote.atualizar(dt)
        if self._explosao is not None:
            self._explosao.atualizar(dt)

    def _desenhar_extras(self, c: pygame.Surface) -> None:
        self._mascote.desenhar(c)
        s = self._servicos
        nome = s.preferencias.nome_jogador.strip()
        if nome:
            self._fonte.escrever(c, f"OLA, {nome}!", 1, CREME, centro=(105, 266))
        self._fonte.escrever(c, f"RECORDE: FASE {s.recorde.melhor_fase}", 1, DOURADO, centro=(105, 278))
        if self._explosao is None:
            return
        if self._explosao.tempo < self.DESTAQUE_DO_SEGREDO and int(self._tempo * 4) % 2 == 0:
            indice = next(i for i in range(len(self._opcoes)) if self._eh_a_opcao_secreta(i))
            linha, _, _ = self._areas[indice]
            self._fonte.escrever(c, "NOVO!", 1, (255, 90, 120), canto=(linha.right + 12, linha.centery - 3))
        self._explosao.desenhar(c)


class EstadoNovoJogo(TelaDeMenu):
    """Antes de comecar: nome do jogador e dificuldade."""

    USA_TEXTO = True
    TITULO = "NOVO JOGO"
    LARGURA_PAINEL = 360

    def __init__(self, jogo: ContextoDoJogo) -> None:
        super().__init__(jogo)
        self._indice = 2 if jogo.nome_jogador.strip() else 0  # ja tem nome? cursor no COMECAR

    def _criar_opcoes(self) -> list[Opcao]:
        prefs = self._servicos.preferencias

        def dificuldade() -> tuple[str, Cor, str]:
            return DIFICULDADES[prefs.dificuldade]

        return [
            CampoDeTexto("NOME", lambda: self._jogo.nome_jogador, self._jogo.definir_nome_jogador,
                         ao_confirmar=lambda: self.executar(Acao.BAIXO),
                         ajuda="DIGITE SEU NOME E APERTE ENTER"),
            Seletor("DIFICULDADE", lambda: dificuldade()[0], prefs.mudar_dificuldade,
                    ajuda=lambda: dificuldade()[2], cor=lambda: dificuldade()[1]),
            Botao("COMECAR!", self._comecar, "BOA SORTE NO LABIRINTO!"),
            Botao("VOLTAR", self._voltar),
        ]

    def _comecar(self) -> None:
        if not self._jogo.nome_jogador.strip():
            self._jogo.definir_nome_jogador("Jogador")
        self._jogo.mudar_estado(EstadoJogando.nova_corrida(self._jogo))

    def _voltar(self) -> None:
        self._jogo.ir_para_menu_principal()

    def _subtitulo(self) -> str:
        return "QUEM VAI ENCARAR O LABIRINTO?"

    def _desenhar_extras(self, c: pygame.Surface) -> None:
        s = self._servicos
        nome = self._jogo.nome_jogador.strip() or "Jogador"
        pontos = s.pontuacoes.carregar_melhor(nome, s.preferencias.dificuldade)[0]
        self._fonte.escrever(c, f"RECORDE: FASE {s.recorde.melhor_fase}     SEUS PONTOS NESTA DIFICULDADE: {pontos}",
                             1, DOURADO, centro=(TAMANHO_CAMADA[0] // 2, 210))
        # "caveirinhas" de dificuldade: quantos niveis acima do facil
        niveis = list(NivelDeDificuldade)
        atual = niveis.index(s.preferencias.dificuldade)
        cor = DIFICULDADES[s.preferencias.dificuldade][1]
        for i in range(len(niveis)):
            x = TAMANHO_CAMADA[0] // 2 - 30 + i * 16
            c.fill(cor if i <= atual else (60, 50, 90), (x, 226, 10, 10))
            c.fill((20, 12, 30), (x + 2, 229, 2, 2))
            c.fill((20, 12, 30), (x + 6, 229, 2, 2))


class EstadoConfiguracoes(TelaDeMenu):
    TITULO = "CONFIGURACOES"
    LARGURA_PAINEL = 340

    def __init__(self, jogo: ContextoDoJogo, retorno: Estado, fundo: Fundo | None = None) -> None:
        self._retorno = retorno
        super().__init__(jogo, fundo)

    def _criar_opcoes(self) -> list[Opcao]:
        prefs = self._servicos.preferencias

        def mudar_zoom(passos: int) -> None:
            if passos > 0:
                prefs.aproximar_zoom()
            else:
                prefs.afastar_zoom()

        return [
            Seletor("ZOOM DA CAMERA", lambda: f"{prefs.zoom:g}X", mudar_zoom,
                    "APROXIMA OU AFASTA A CAMERA (NO JOGO: + E -)"),
            Alternador("TELA CHEIA", lambda: prefs.tela_cheia, prefs.alternar_tela_cheia,
                       "OCUPA O MONITOR INTEIRO"),
            Alternador("TREMOR DE TELA", lambda: prefs.tremor, prefs.alternar_tremor,
                       "TREME A TELA EM TERREMOTOS, FOGO E PULOS"),
            Alternador("MOSTRAR FPS", lambda: prefs.mostrar_fps, prefs.alternar_fps,
                       "QUADROS POR SEGUNDO NO CANTO DA TELA"),
            Botao("CONTROLES", lambda: self._jogo.mudar_estado(EstadoControles(self._jogo, self, self._fundo)),
                  "VEJA TODAS AS TECLAS E BOTOES"),
            Botao("VOLTAR", self._voltar),
        ]

    def _voltar(self) -> None:
        self._jogo.mudar_estado(self._retorno)


class EstadoSom(TelaDeMenu):
    TITULO = "SOM"
    LARGURA_PAINEL = 320

    def __init__(self, jogo: ContextoDoJogo, retorno: Estado, fundo: Fundo | None = None) -> None:
        self._retorno = retorno
        super().__init__(jogo, fundo)

    def _criar_opcoes(self) -> list[Opcao]:
        prefs = self._servicos.preferencias
        return [
            Barra("MUSICA", lambda: prefs.volume_musica, prefs.ajustar_volume_musica, "ESQUERDA/DIREITA PARA AJUSTAR"),
            Barra("EFEITOS", lambda: prefs.volume_efeitos, prefs.ajustar_volume_efeitos,
                  "PASSOS, ITENS, ALERTAS..."),
            Alternador("MUDO", lambda: prefs.mudo, prefs.alternar_mudo, "SILENCIA TUDO (NO JOGO: TECLA M)"),
            Botao("VOLTAR", self._voltar),
        ]

    def _voltar(self) -> None:
        self._jogo.mudar_estado(self._retorno)


class EstadoControles(TelaDeMenu):
    TITULO = "CONTROLES"
    LARGURA_PAINEL = 160
    TABELA = (
        ("MOVER", "WASD / SETAS", "ANALOGICO ESQ."),
        ("PULAR NA MOLA", "ANDE CONTRA ELA", "ANDE CONTRA ELA"),
        ("SAIR DA TEIA", "SETAS / WASD", "DIRECIONAL"),
        ("OLHAR EM VOLTA", "T F G H", "ANALOGICO DIR."),
        ("ZOOM", "+ / -", "LB / RB"),
        ("PAUSAR", "ESC / P", "START"),
        ("LIGAR A LUZ", "L", "X"),
        ("SOM", "M", "Y"),
    )

    def __init__(self, jogo: ContextoDoJogo, retorno: Estado, fundo: Fundo | None = None) -> None:
        self._retorno = retorno
        super().__init__(jogo, fundo)

    def _criar_opcoes(self) -> list[Opcao]:
        return [Botao("VOLTAR", self._voltar)]

    def _voltar(self) -> None:
        self._jogo.mudar_estado(self._retorno)

    def _topo_painel(self) -> int:
        return 262

    def _desenhar_extras(self, c: pygame.Surface) -> None:
        quadro = pygame.Rect(36, 76, TAMANHO_CAMADA[0] - 72, 178)
        caixa_rabiscada(c, quadro, LILAS, FUNDO_PAINEL, semente_fervendo(5, self._tempo), hachura=HACHURA)
        colunas = (quadro.left + 14, quadro.left + 150, quadro.left + 280)
        for coluna, titulo in zip(colunas, ("ACAO", "TECLADO", "CONTROLE")):
            self._fonte.escrever(c, titulo, 1, LILAS, canto=(coluna, quadro.top + 12))
        for i, linha in enumerate(self.TABELA):
            y = quadro.top + 32 + i * 17
            for coluna, texto, cor in zip(colunas, linha, (DOURADO, CREME, CREME)):
                self._fonte.escrever(c, texto, 1, cor, canto=(coluna, y))


class EstadoPausado(TelaDeMenu):
    """ESC durante a partida: a partida fica congelada e escurecida atras do menu."""

    TITULO = "PAUSADO"
    LARGURA_PAINEL = 230

    def __init__(self, jogo: ContextoDoJogo, jogando: EstadoJogando) -> None:
        self._jogando = jogando
        super().__init__(jogo, FundoDaPartida(jogando))

    def _criar_opcoes(self) -> list[Opcao]:
        jogo = self._jogo
        return [
            Botao("CONTINUAR", self._voltar, "VOLTA PARA O LABIRINTO"),
            Botao("REINICIAR", lambda: jogo.mudar_estado(self._jogando.reiniciar()),
                  "COMECA DE NOVO DA FASE 1 (MESMA DIFICULDADE)"),
            Botao("CONFIGURACOES", lambda: jogo.mudar_estado(EstadoConfiguracoes(jogo, self, self._fundo))),
            Botao("SOM", lambda: jogo.mudar_estado(EstadoSom(jogo, self, self._fundo))),
            Botao("MENU PRINCIPAL", jogo.ir_para_menu_principal, "A PARTIDA ATUAL SERA PERDIDA"),
            Botao("SAIR DO JOGO", jogo.encerrar, "FECHA O MARBLE RUN"),
        ]

    def executar(self, acao: Acao) -> None:
        if acao is Acao.PAUSAR:
            self._voltar()
        elif acao is Acao.IR_PARA_MENU:
            self._jogo.ir_para_menu_principal()
        else:
            super().executar(acao)

    def _voltar(self) -> None:
        self._jogo.mudar_estado(self._jogando)

    def _subtitulo(self) -> str:
        partida = self._jogando.partida
        nome = "TESTE DE MAPA" if partida.vitrine else DIFICULDADES[partida.dificuldade.nivel][0]
        return f"FASE {partida.nivel}  -  {nome}  -  {partida.pontos} PONTOS"

class EstadoConfirmacao(TelaDeMenu):
    """Pergunta "tem certeza?" antes de algo que nao tem volta. Comeca no NAO, por seguranca."""

    TITULO = "TEM CERTEZA?"
    LARGURA_PAINEL = 260

    def __init__(self, jogo: ContextoDoJogo, pergunta: str, rotulo_sim: str, ao_confirmar: Callable[[], None],
                 retorno: Estado, fundo: Fundo | None = None) -> None:
        self._pergunta = pergunta
        self._rotulo_sim = rotulo_sim
        self._ao_confirmar = ao_confirmar
        self._retorno = retorno
        super().__init__(jogo, fundo)
        self._indice = 1

    def _criar_opcoes(self) -> list[Opcao]:
        return [Botao(self._rotulo_sim, self._ao_confirmar, "NAO DA PARA DESFAZER"),
                Botao("NAO, VOLTAR", self._voltar)]

    def _voltar(self) -> None:
        self._jogo.mudar_estado(self._retorno)

    def _subtitulo(self) -> str:
        return self._pergunta

    def _topo_painel(self) -> int:
        return 120
