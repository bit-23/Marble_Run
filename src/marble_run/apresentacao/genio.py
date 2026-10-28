"""
genio.py - A tela do Genio da Lampada: o jogo pausa e o jogador escolhe 1 de 3 desejos.

    +20 SEGUNDOS      -> tempo extra no relogio
    MELHOR CAMINHO    -> setas no chao do jogador ate o portal (3.5s)
    TELEPORTE         -> pula alguns tiles para mais perto do portal

Abre depois da roleta (caixa "?") ou direto no teste dos mapas. Teclado,
controle e mouse funcionam (setas/ENTER ou clique).
"""
from __future__ import annotations

import math

import pygame

from ..dominio.ambiente import Ambiente, Desejo, TipoDeItem
from .contratos import Efeito
from .entrada import Acao
from .estados import ContextoDoJogo, Estado, EstadoJogando
from .icones import icone
from .menus import CINZA, CREME, DOURADO, FundoDaPartida, LILAS
from .pixelart import TAMANHO_CAMADA, CamadaPixel
from .sprites_monstros import Modo, renderizar_grade

_GENIO_CORPO = """
.........j..........
........tjt.........
......ttTtTtt.......
.....tTtttttTt......
.....TtTtTtTtT......
......bbbbbbb.......
.....bkobbbokb......
....gbbbbhbbbbg.....
....G.bmwwwmb.G.....
.......kkkkk........
........kkk.........
...bbbvvvvvvvbbb....
..bBbbvVvhvVvbbBb...
..bggbbbbbbbbbggb...
...bbbbbbbbbbbbb....
....vvsssssssvv.....
.....ssgsssgss......
"""
_CAUDAS = ("""
.....fffffffff......
......fFfffFff......
.......ffcfFf.......
........fFfc........
.........fff........
..........ff........
..........cf........
""", """
.....fffffffff......
.....fFffffFff......
......ffcffFf.......
.......fFffc........
........ffff........
.........fff........
.........cf.........
""", """
.....fffffffff......
......ffFfffFf......
.......fffcfFf......
.........fFff.......
.........ffc........
........fff.........
........fc..........
""")
QUADROS_DO_GENIO = tuple(
    tuple(linha.strip().ljust(20, ".") for linha in (_GENIO_CORPO + cauda).strip().splitlines() if linha.strip())
    for cauda in _CAUDAS)
PALETA_DO_GENIO = {
    "t": (150, 60, 205), "T": (100, 35, 150), "j": (255, 60, 90), "g": (255, 205, 60), "G": (190, 130, 30),
    "b": (90, 150, 245), "B": (55, 100, 200), "h": (150, 195, 255), "o": (255, 240, 120), "k": (24, 22, 60),
    "m": (40, 20, 60), "w": (255, 255, 255), "v": (125, 42, 145), "V": (82, 26, 100), "s": (225, 50, 64),
    "f": (140, 120, 240), "F": (100, 80, 210), "c": (195, 182, 255), "_": (55, 100, 200),
}

OPCOES: tuple[tuple[Desejo, str, str], ...] = (
    (Desejo.TEMPO, f"+{Ambiente.BONUS_DO_GENIO:.0f} SEGUNDOS", "MAIS TEMPO NO RELOGIO"),
    (Desejo.CAMINHO, "MELHOR CAMINHO", f"SETAS NO CHAO ATE O PORTAL ({3.5:.1f}S)"),
    (Desejo.TELEPORTE, "TELEPORTE", f"PULA {Ambiente.PASSOS_DO_TELEPORTE} PASSOS PARA PERTO DO PORTAL"),
)


class EstadoDesejos(Estado):
    TOPO = 124
    ALTURA_DA_OPCAO = 44
    LARGURA = 300

    def __init__(self, jogo: ContextoDoJogo, jogando: EstadoJogando) -> None:
        super().__init__(jogo)
        self._jogando = jogando
        self._fundo = FundoDaPartida(jogando)
        self._camada = CamadaPixel()
        self._fonte = self._servicos.fonte_pixel
        self._selecionado = 0
        self._tempo = 0.0
        self._sprites_do_genio: dict[tuple[int, bool], pygame.Surface] = {}

    def executar(self, acao: Acao) -> None:
        if acao is Acao.CIMA:
            self._mover(-1)
        elif acao is Acao.BAIXO:
            self._mover(1)
        elif acao is Acao.CONFIRMAR:
            self._escolher()

    def tratar_evento(self, evento: pygame.event.Event) -> None:
        if evento.type not in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
            return
        indice = self._opcao_em(CamadaPixel.da_tela(evento.pos))
        if indice is None:
            return
        self._selecionado = indice
        if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            self._escolher()

    def atualizar(self, dt: float) -> None:
        self._tempo += dt

    def desenhar(self, tela: pygame.Surface) -> None:
        self._fundo.desenhar(tela)
        self._camada.limpar()
        c = self._camada.superficie
        cx = TAMANHO_CAMADA[0] // 2
        self._desenhar_genio(c, cx, 92)
        self._fonte.escrever(c, "O GENIO CONCEDE 1 DESEJO!", 2, DOURADO, centro=(cx, 112))
        for i, (_, titulo, descricao) in enumerate(OPCOES):
            caixa = self._caixa(i)
            ativa = i == self._selecionado
            pygame.draw.rect(c, (20, 12, 30), caixa.move(2, 2), border_radius=6)
            pygame.draw.rect(c, (70, 40, 110) if ativa else (36, 26, 56), caixa, border_radius=6)
            pygame.draw.rect(c, DOURADO if ativa else LILAS, caixa, 2, border_radius=6)
            pulo = round(abs(math.sin(self._tempo * 6)) * 2) if ativa else 0
            self._fonte.escrever(c, titulo, 2, DOURADO if ativa else CREME, canto=(caixa.x + 14, caixa.y + 8 - pulo))
            self._fonte.escrever(c, descricao, 1, CREME, canto=(caixa.x + 14, caixa.y + 29))
        self._fonte.escrever(c, "SETAS: ESCOLHER   ENTER: PEDIR", 1, CINZA, centro=(cx, TAMANHO_CAMADA[1] - 12))
        self._camada.apresentar(tela)

    # ------------------------------------------------------------------
    def _mover(self, passos: int) -> None:
        self._selecionado = (self._selecionado + passos) % len(OPCOES)
        self._servicos.audio.tocar(Efeito.MENU)

    def _escolher(self) -> None:
        desejo = OPCOES[self._selecionado][0]
        self._jogando.partida.fase.realizar_desejo(desejo)
        self._jogo.mudar_estado(self._jogando)

    def _caixa(self, indice: int) -> pygame.Rect:
        return pygame.Rect((TAMANHO_CAMADA[0] - self.LARGURA) // 2, self.TOPO + indice * (self.ALTURA_DA_OPCAO + 6),
                           self.LARGURA, self.ALTURA_DA_OPCAO)

    def _opcao_em(self, pos: tuple[int, int]) -> int | None:
        for i in range(len(OPCOES)):
            if self._caixa(i).collidepoint(pos):
                return i
        return None

    def _desenhar_genio(self, c: pygame.Surface, cx: int, cy: int) -> None:
        """Genio em pixel art saindo da lampada: flutua, a cauda de fumaca se enrola, pisca e brilha."""
        quadro = int(self._tempo * 6) % len(QUADROS_DO_GENIO)
        piscando = self._tempo % 3.2 < 0.14
        chave = (quadro, piscando)
        if chave not in self._sprites_do_genio:
            modos = frozenset({Modo.PISCANDO}) if piscando else frozenset()
            self._sprites_do_genio[chave] = renderizar_grade(QUADROS_DO_GENIO[quadro], PALETA_DO_GENIO, 3, modos)
        img = self._sprites_do_genio[chave]
        flutua = round(math.sin(self._tempo * 2.5) * 3)
        brilho = pygame.Surface((120, 96), pygame.SRCALPHA)  # aura magica
        for r in range(46, 0, -3):
            alfa = int(70 * (1 - r / 46) ** 1.5 * (0.8 + 0.2 * math.sin(self._tempo * 4)))
            pygame.draw.ellipse(brilho, (150, 120, 255, alfa), (60 - r * 1.25, 48 - r, r * 2.5, r * 2))
        c.blit(brilho, brilho.get_rect(center=(cx, cy - 34 + flutua)))
        lampada = icone(TipoDeItem.GENIO, 26)
        c.blit(lampada, lampada.get_rect(center=(cx + 5, cy + 6)))
        c.blit(img, img.get_rect(midbottom=(cx + 1, cy + 2 + flutua)))
        for i in range(6):  # brilhinhos girando
            a = self._tempo * 2 + i * math.tau / 6
            raio = 40 + 5 * math.sin(self._tempo * 5 + i)
            px, py = round(cx + math.cos(a) * raio), round(cy - 36 + math.sin(a) * raio * 0.55 + flutua)
            c.fill((255, 240, 160), (px, py, 2, 2))
            if (int(self._tempo * 8) + i) % 3 == 0:
                c.fill((255, 255, 255), (px - 1, py, 4, 1))
                c.fill((255, 255, 255), (px, py - 1, 1, 4))
