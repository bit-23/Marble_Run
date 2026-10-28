"""
roleta.py - A roleta da caixa surpresa "?".

O DOMINIO ja sorteou e aplicou o premio quando a caixa abriu; aqui e so o
espetaculo: o jogo pausa, a roda gira desacelerando (com "tique" a cada
fatia) e para EXATAMENTE na fatia do premio, com uma chuva de pixels.
"""
from __future__ import annotations

import math
import random

import pygame

from ..dominio.ambiente import TipoDeItem
from .contratos import Efeito
from .entrada import Acao
from .estados import ContextoDoJogo, Estado, EstadoJogando
from .icones import DESCRICOES_DOS_ITENS, icone
from .menus import CINZA, CREME, DOURADO, FundoDaPartida
from .pixelart import TAMANHO_CAMADA, CamadaPixel
from .sonorizacao import SonsDaPartida

Cor = tuple[int, int, int]

CORES_DAS_FATIAS: tuple[Cor, ...] = (
    (235, 90, 90), (250, 180, 60), (90, 180, 240), (120, 210, 120), (190, 120, 230), (245, 225, 110),
)


class _Faisca:
    __slots__ = ("x", "y", "vx", "vy", "vida", "cor")

    def __init__(self, x: float, y: float, rng: random.Random) -> None:
        ang = rng.uniform(0, math.tau)
        rapidez = rng.uniform(40, 170)
        self.x, self.y = x, y
        self.vx, self.vy = math.cos(ang) * rapidez, math.sin(ang) * rapidez - 60
        self.vida = rng.uniform(0.6, 1.3)
        self.cor = rng.choice(CORES_DAS_FATIAS + ((255, 255, 255),))

    def atualizar(self, dt: float) -> None:
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += 220 * dt  # gravidade
        self.vida -= dt


class EstadoRoleta(Estado):
    DURACAO_DO_GIRO = 2.6
    TEMPO_MOSTRANDO = 1.8   # depois de parar, volta sozinho para o jogo
    VOLTAS = 4
    MINIMO_DE_FATIAS = 8
    RAIO = 98
    CENTRO = (TAMANHO_CAMADA[0] // 2, 166)

    def __init__(self, jogo: ContextoDoJogo, jogando: EstadoJogando, premio: TipoDeItem,
                 sorteio: random.Random | None = None) -> None:
        super().__init__(jogo)
        self._jogando = jogando
        self._premio = premio
        self._rng = sorteio if sorteio is not None else random.Random()
        self._fundo = FundoDaPartida(jogando)
        self._camada = CamadaPixel()
        self._fonte = self._servicos.fonte_pixel
        self._fatias = self._montar_fatias(jogando.partida.fase.ambiente.premios, premio)
        self._angulo_por_fatia = math.tau / len(self._fatias)
        alvo = self._rng.choice([i for i, tipo in enumerate(self._fatias) if tipo is premio])
        self._inicio = self._rng.uniform(0, math.tau)
        folga = self._rng.uniform(-0.35, 0.35) * self._angulo_por_fatia  # nao para sempre no meio
        final = -math.pi / 2 - (alvo + 0.5) * self._angulo_por_fatia + folga
        self._giro_total = (final - self._inicio) % math.tau + self.VOLTAS * math.tau
        self._indice_vencedor = alvo
        self._tempo = 0.0
        self._fatia_no_ponteiro = self._fatia_sob_o_ponteiro(self._inicio)
        self._chute_do_ponteiro = 0.0
        self._parou = False
        self._faiscas: list[_Faisca] = []

    # ------------------------------------------------------------------
    def executar(self, acao: Acao) -> None:
        if acao is not Acao.CONFIRMAR:
            return
        if self._parou:
            self._voltar_ao_jogo()
        else:
            self._tempo = self.DURACAO_DO_GIRO  # pula a animacao

    def atualizar(self, dt: float) -> None:
        self._tempo += dt
        self._chute_do_ponteiro = max(0.0, self._chute_do_ponteiro - dt * 6)
        fatia = self._fatia_sob_o_ponteiro(self._angulo())
        if fatia != self._fatia_no_ponteiro and not self._parou:
            self._fatia_no_ponteiro = fatia
            self._chute_do_ponteiro = 1.0
            self._servicos.audio.tocar(Efeito.TIQUE)
        if not self._parou and self._tempo >= self.DURACAO_DO_GIRO:
            self._parou = True
            self._servicos.audio.tocar(SonsDaPartida.som_do_premio(self._premio))
            cx, cy = self.CENTRO
            self._faiscas = [_Faisca(cx, cy - self.RAIO, self._rng) for _ in range(60)]
        for faisca in self._faiscas:
            faisca.atualizar(dt)
        self._faiscas = [f for f in self._faiscas if f.vida > 0]
        if self._parou and self._tempo >= self.DURACAO_DO_GIRO + self.TEMPO_MOSTRANDO:
            self._voltar_ao_jogo()

    def desenhar(self, tela: pygame.Surface) -> None:
        self._fundo.desenhar(tela)
        self._camada.limpar()
        c = self._camada.superficie
        self._fonte.escrever(c, "CAIXA SURPRESA!", 3, DOURADO, centro=(TAMANHO_CAMADA[0] // 2, 26))
        self._desenhar_roda(c, self._angulo())
        self._desenhar_ponteiro(c)
        for faisca in self._faiscas:
            c.fill(faisca.cor, (round(faisca.x), round(faisca.y), 2, 2))
        cx = TAMANHO_CAMADA[0] // 2
        if self._parou:
            nome, descricao = DESCRICOES_DOS_ITENS[self._premio]
            self._fonte.escrever(c, f"{nome}!", 3, DOURADO, centro=(cx, 284))
            self._fonte.escrever(c, descricao, 1, CREME, centro=(cx, 302))
        dica = "ENTER: CONTINUAR" if self._parou else "ENTER: PARAR JA"
        self._fonte.escrever(c, dica, 1, CINZA, centro=(cx, 314))
        self._camada.apresentar(tela)

    # ------------------------------------------------------------------
    def _voltar_ao_jogo(self) -> None:
        if self._premio is TipoDeItem.GENIO:  # o genio saiu da lampada: hora de escolher o desejo
            self._jogo.abrir_desejos(self._jogando)
        else:
            self._jogo.mudar_estado(self._jogando)

    def _montar_fatias(self, premios: tuple[TipoDeItem, ...], premio: TipoDeItem) -> list[TipoDeItem]:
        fatias = list(premios) or [premio]
        if premio not in fatias:
            fatias.append(premio)
        while len(fatias) < self.MINIMO_DE_FATIAS:  # roda com poucas fatias fica sem graca
            fatias += list(premios) or [premio]
        return fatias[: max(self.MINIMO_DE_FATIAS, len(premios))]

    def _angulo(self) -> float:
        k = min(1.0, self._tempo / self.DURACAO_DO_GIRO)
        desacelerando = 1 - (1 - k) ** 3
        return self._inicio + self._giro_total * desacelerando

    def _fatia_sob_o_ponteiro(self, angulo: float) -> int:
        return int(((-math.pi / 2 - angulo) % math.tau) // self._angulo_por_fatia) % len(self._fatias)

    def _desenhar_roda(self, c: pygame.Surface, angulo: float) -> None:
        cx, cy = self.CENTRO
        r = self.RAIO
        passo = self._angulo_por_fatia
        pygame.draw.circle(c, (20, 12, 30), (cx + 3, cy + 4), r + 6)  # sombra
        pygame.draw.circle(c, (60, 40, 20), (cx, cy), r + 6)          # aro
        piscando = self._parou and int(self._tempo * 8) % 2 == 0
        for i, tipo in enumerate(self._fatias):
            a0 = angulo + i * passo
            pontos = [(cx, cy)] + [(cx + r * math.cos(a0 + passo * k / 8), cy + r * math.sin(a0 + passo * k / 8))
                                   for k in range(9)]
            cor = CORES_DAS_FATIAS[i % len(CORES_DAS_FATIAS)]
            if piscando and i == self._indice_vencedor:
                cor = (255, 255, 255)
            pygame.draw.polygon(c, cor, pontos)
            pygame.draw.line(c, (40, 24, 20), (cx, cy), pontos[1], 2)
            meio = a0 + passo / 2
            img = icone(tipo, 24)
            c.blit(img, img.get_rect(center=(cx + r * 0.66 * math.cos(meio), cy + r * 0.66 * math.sin(meio))))
        for i in range(16):  # lampadinhas do aro
            a = i * math.tau / 16
            acesa = (i + int(self._tempo * 10)) % 2 == 0
            c.fill((255, 240, 150) if acesa else (120, 80, 30),
                   (round(cx + (r + 3) * math.cos(a)) - 1, round(cy + (r + 3) * math.sin(a)) - 1, 3, 3))
        pygame.draw.circle(c, (120, 60, 10), (cx, cy), 15)
        pygame.draw.circle(c, DOURADO, (cx, cy), 13)
        self._fonte.escrever(c, "?", 2, (255, 255, 255), centro=(cx + 1, cy + 1))

    def _desenhar_ponteiro(self, c: pygame.Surface) -> None:
        cx, cy = self.CENTRO
        topo = cy - self.RAIO - 14
        desvio = round(self._chute_do_ponteiro * 4)  # leva um "chute" a cada fatia
        pontos = [(cx - 9 + desvio, topo), (cx + 9 + desvio, topo), (cx, topo + 20)]
        pygame.draw.polygon(c, (60, 30, 10), [(x + 2, y + 2) for x, y in pontos])
        pygame.draw.polygon(c, DOURADO, pontos)
        pygame.draw.polygon(c, (255, 250, 210), pontos, 1)
