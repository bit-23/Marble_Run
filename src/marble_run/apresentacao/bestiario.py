"""
bestiario.py - Como os monstros aparecem na tela: pixel art animada e assustadora.

So LE os monstros do dominio (posicao, estado, progresso do aviso, tiles do ataque).
Os sprites vem de sprites_monstros.py; aqui eles ganham VIDA:
    * andam saltitando e respiram pesado parados; tremem de repente (tique nervoso);
    * aura escura pulsando em volta, baba/veneno/lava pingando;
    * antes de atacar: incham, tremem cada vez mais e ficam vermelhos de raiva;
    * no ataque esticam; tontos balancam; dormindo fecham os olhos (Zzz);
    * os OLHOS brilham no escuro, mais fortes quando o jogador chega perto.
Camadas, chamadas pela Cena:
    desenhar_avisos   -> no chao: tiles que o ataque vai pegar, sombra da aguia, bolhas, montinho da toupeira
    desenhar_corpos   -> os monstros (atras ou na frente do jogador, conforme a altura na tela)
    desenhar_no_alto  -> aguia voando, teias voando, raio congelante, labareda, laco
    desenhar_luzes    -> olhos brilhando e ataques que brilham ate no escuro
"""
from __future__ import annotations

import math
import random

import pygame

from ..dominio.ambiente import Ambiente
from ..dominio.labirinto import Labirinto
from ..dominio.monstros import EstadoDoMonstro, Monstro, TipoDeMonstro
from .elementos import criar_halo
from .sprites_monstros import Modo, SpritesDosMonstros

Deslocamento = tuple[int, int]
Cor = tuple[int, int, int]

COR_DO_AVISO: dict[TipoDeMonstro, Cor] = {
    TipoDeMonstro.ARANHA: (230, 230, 240),
    TipoDeMonstro.MINOTAURO: (255, 90, 60),
    TipoDeMonstro.BONECO_DE_NEVE: (120, 220, 255),
    TipoDeMonstro.YETI: (170, 230, 255),
    TipoDeMonstro.MAGMAN: (255, 140, 40),
    TipoDeMonstro.FORNALHA: (255, 110, 30),
    TipoDeMonstro.AGUIA: (255, 80, 80),
    TipoDeMonstro.TORNADO: (220, 230, 240),
    TipoDeMonstro.TOUPEIRA: (190, 140, 80),
    TipoDeMonstro.GOLEM: (255, 170, 60),
    TipoDeMonstro.COBRA: (140, 230, 90),
    TipoDeMonstro.MUMIA: (230, 210, 150),
}
VOADORES = (TipoDeMonstro.AGUIA,)
SEMPRE_ANIMADOS = {TipoDeMonstro.TORNADO: 10.0, TipoDeMonstro.FORNALHA: 7.0, TipoDeMonstro.MAGMAN: 4.0}
NUNCA_ESPELHA = (TipoDeMonstro.TORNADO, TipoDeMonstro.FORNALHA)
# (cor, de onde pinga: fracao da altura do sprite) - baba, veneno e lava escorrendo
PINGOS: dict[TipoDeMonstro, tuple[Cor, float]] = {
    TipoDeMonstro.ARANHA: ((130, 255, 90), 0.88),
    TipoDeMonstro.YETI: ((220, 230, 240), 0.42),
    TipoDeMonstro.MAGMAN: ((255, 150, 30), 0.6),
    TipoDeMonstro.COBRA: ((130, 255, 90), 0.3),
    TipoDeMonstro.MINOTAURO: ((150, 18, 18), 0.4),
    TipoDeMonstro.MUMIA: ((90, 110, 50), 0.3),
}
PERTO_DO_JOGADOR = 3.5  # tiles: os monstros "rosnam" (tremem e os olhos acendem)


class _Animacao:
    """Estado so VISUAL de um monstro (para onde olha, se esta andando, tiques, pingos)."""

    def __init__(self, m: Monstro, rng: random.Random) -> None:
        self.tipo = m.tipo
        self.x, self.y = m.x, m.y
        self.esquerda = False
        self.andando = False
        self.fase = rng.uniform(0, 10)
        self.tique = rng.uniform(1.5, 5.0)
        self.tremendo = 0.0
        self.proximo_pingo = rng.uniform(0.3, 1.5)
        self.pingos: list[list[float]] = []  # [x, y, velocidade, vida] em pixels do mapa
        self.colocacao: tuple[pygame.Rect, int, bool, float, float] | None = None
        self.perto = False


class DesenhoDosMonstros:
    def __init__(self, ambiente: Ambiente, labirinto: Labirinto, sprites: SpritesDosMonstros | None = None) -> None:
        self._ambiente = ambiente
        self._tile = labirinto.tamanho_tile
        self._tempo = 0.0
        self._sprites = sprites if sprites is not None else SpritesDosMonstros()
        self._rng = random.Random(7)
        self._anim: dict[int, _Animacao] = {}
        self._halo_dos_olhos = criar_halo(16, (255, 255, 255))
        self._halo_do_ataque = criar_halo(int(labirinto.tamanho_tile * 0.9), (255, 255, 255))
        self._sombra = pygame.Surface((40, 14), pygame.SRCALPHA)
        pygame.draw.ellipse(self._sombra, (0, 0, 0, 110), self._sombra.get_rect())
        self._aura = self._criar_aura(64)
        self._camada_tile = pygame.Surface((self._tile, self._tile), pygame.SRCALPHA)

    @staticmethod
    def _criar_aura(raio: int) -> pygame.Surface:
        """Sombra roxa-escura em volta do monstro (deixa tudo mais ameacador)."""
        s = pygame.Surface((raio * 2, raio * 2), pygame.SRCALPHA)
        for r in range(raio, 0, -2):
            k = 1 - r / raio
            pygame.draw.circle(s, (18, 0, 22, int(150 * k * k)), (raio, raio), r)
        return s

    def atualizar(self, dt: float) -> None:
        self._tempo += dt
        jogador = self._ambiente.jogador
        vivos = set()
        for m in self._ambiente.monstros:
            vivos.add(id(m))
            a = self._anim.get(id(m))
            if a is None:
                a = self._anim[id(m)] = _Animacao(m, self._rng)
            dx, dy = m.x - a.x, m.y - a.y
            a.andando = math.hypot(dx, dy) > 0.2
            if abs(dx) > 0.2:
                a.esquerda = dx < 0
            elif not a.andando and abs(m.direcao.x) > 0.3:
                a.esquerda = m.direcao.x < 0
            a.x, a.y = m.x, m.y
            a.perto = jogador is not None and math.hypot(jogador.x - m.x, jogador.y - m.y) < PERTO_DO_JOGADOR * self._tile
            a.tique -= dt
            a.tremendo = max(0.0, a.tremendo - dt)
            if a.tique <= 0:  # tique nervoso: um tremor de repente
                a.tremendo = 0.22
                a.tique = self._rng.uniform(1.2, 3.0) if a.perto else self._rng.uniform(2.5, 6.0)
            self._atualizar_pingos(m, a, dt)
        for chave in [c for c in self._anim if c not in vivos]:
            del self._anim[chave]

    def _atualizar_pingos(self, m: Monstro, a: _Animacao, dt: float) -> None:
        for p in a.pingos:
            p[2] += 260 * dt
            p[1] += p[2] * dt
            p[3] -= dt
        a.pingos = [p for p in a.pingos if p[3] > 0]
        if m.tipo not in PINGOS or a.colocacao is None or m.estado in (EstadoDoMonstro.DORMINDO,
                                                                        EstadoDoMonstro.APAGADO):
            return
        a.proximo_pingo -= dt * (2.5 if a.perto or m.estado is EstadoDoMonstro.AVISANDO else 1.0)
        if a.proximo_pingo <= 0 and m.visivel:
            a.proximo_pingo = self._rng.uniform(0.4, 1.4)
            ret = a.colocacao[0]  # em pixels do mapa
            _, fracao = PINGOS[m.tipo]
            frente = (0.38 if a.esquerda else 0.62) if m.tipo is TipoDeMonstro.COBRA else 0.5
            x = ret.x + ret.w * frente + self._rng.uniform(-6, 6)
            y = ret.y + ret.h * fracao
            a.pingos.append([x, y, 0.0, self._rng.uniform(0.35, 0.6)])
    # ------------------------------------------------------------------
    # Camadas
    # ------------------------------------------------------------------
    def desenhar_avisos(self, tela: pygame.Surface, camera: Deslocamento) -> None:
        for m in self._ambiente.monstros:
            if m.estado in (EstadoDoMonstro.AVISANDO, EstadoDoMonstro.ATACANDO, EstadoDoMonstro.ESCONDIDO):
                self._marcar_tiles(tela, camera, m)
            if m.tipo is TipoDeMonstro.AGUIA:
                self._sombra_da_aguia(tela, camera, m)
            elif m.tipo is TipoDeMonstro.TOUPEIRA and m.estado is not EstadoDoMonstro.ATACANDO:
                self._montinho(tela, camera, m)

    def desenhar_corpos(self, tela: pygame.Surface, camera: Deslocamento, *, atras_de: float | None = None,
                        na_frente_de: float | None = None) -> None:
        """Monstros com os pes acima de `atras_de` (ou abaixo de `na_frente_de`), do fundo para a frente."""
        visivel = tela.get_rect().inflate(self._tile * 3, self._tile * 3)
        for m in sorted(self._ambiente.monstros, key=lambda m: m.y):
            if m.tipo in VOADORES or m.tipo is TipoDeMonstro.TOUPEIRA and m.estado is not EstadoDoMonstro.ATACANDO:
                continue
            pes = m.y + 12
            if atras_de is not None and pes > atras_de or na_frente_de is not None and pes <= na_frente_de:
                continue
            x, y = round(m.x) - camera[0], round(m.y) - camera[1]
            if visivel.collidepoint(x, y):
                self._desenhar_monstro(tela, m, x, y, camera)

    def desenhar_no_alto(self, tela: pygame.Surface, camera: Deslocamento) -> None:
        jogador = self._ambiente.jogador
        for m in self._ambiente.monstros:
            x, y = round(m.x) - camera[0], round(m.y) - camera[1]
            if m.tipo is TipoDeMonstro.AGUIA:
                self._desenhar_monstro(tela, m, x, y, camera, altura=round(60 * m.altura_de_voo))
            for p in m.projeteis:
                self._bola_de_teia(tela, round(p.x) - camera[0], round(p.y) - camera[1])
            if m.estado is EstadoDoMonstro.ATACANDO:
                if m.tipo is TipoDeMonstro.BONECO_DE_NEVE:
                    self._raio_congelante(tela, camera, m)
                elif m.tipo is TipoDeMonstro.FORNALHA:
                    self._labareda(tela, camera, m)
                elif m.tipo is TipoDeMonstro.MUMIA and jogador is not None:
                    self._laco(tela, x, y, round(jogador.x) - camera[0], round(jogador.y) - camera[1] - 24, 1.0)
                elif m.tipo is TipoDeMonstro.GOLEM:
                    self._onda_de_choque(tela, x, y, m.progresso)
            elif m.estado is EstadoDoMonstro.AVISANDO and m.tipo is TipoDeMonstro.MUMIA and m.tiles_do_ataque:
                fim = m.tiles_do_ataque[-1]
                t = self._tile
                self._laco(tela, x, y, fim.coluna * t + t // 2 - camera[0], fim.linha * t + t // 2 - camera[1],
                           m.progresso)

    def desenhar_luzes(self, tela: pygame.Surface, camera: Deslocamento) -> None:
        """Os olhos aparecem ate no breu (e acendem quando o jogador chega perto ou o ataque vem)."""
        r = self._halo_dos_olhos.get_width() // 2
        escala = self._sprites.escala
        for m in self._ambiente.monstros:
            a = self._anim.get(id(m))
            if a is None or a.colocacao is None:
                continue
            if m.estado in (EstadoDoMonstro.DORMINDO, EstadoDoMonstro.APAGADO, EstadoDoMonstro.ESCONDIDO):
                continue
            if m.tipo is TipoDeMonstro.TOUPEIRA and m.estado is not EstadoDoMonstro.ATACANDO:
                continue
            ret, quadro, espelhar, kx, ky = a.colocacao
            olhos = self._sprites.olhos(m.tipo, quadro, espelhar)
            if not olhos:
                continue
            furioso = a.perto or m.estado in (EstadoDoMonstro.AVISANDO, EstadoDoMonstro.ATACANDO)
            forca = (0.75 if furioso else 0.4) + 0.25 * math.sin(self._tempo * (9 if furioso else 3) + a.fase)
            cor = self._sprites.cor_dos_olhos(m.tipo)
            pontos = [(ret.x - camera[0] + px * kx, ret.y - camera[1] + py * ky) for px, py in olhos]
            cx = sum(p[0] for p in pontos) / len(pontos)
            cy = sum(p[1] for p in pontos) / len(pontos)
            halo = self._halo_dos_olhos.copy()
            halo.fill(tuple(int(c * forca * 0.6) for c in cor), special_flags=pygame.BLEND_RGB_MULT)
            tela.blit(halo, (round(cx) - r, round(cy) - r), special_flags=pygame.BLEND_RGB_ADD)
            brilho = tuple(min(255, int(c * (0.7 + 0.3 * forca) + 60 * forca)) for c in cor)
            lado = max(2, round(escala * kx))
            for px, py in pontos:
                tela.fill(brilho, (round(px - lado / 2), round(py - lado / 2), lado, lado))
            if m.estado is EstadoDoMonstro.ATACANDO and m.tipo in (TipoDeMonstro.BONECO_DE_NEVE,
                                                                    TipoDeMonstro.FORNALHA):
                self._brilho_nos_tiles(tela, camera, m)

    # ------------------------------------------------------------------
    # Efeitos comuns
    # ------------------------------------------------------------------
    def _marcar_tiles(self, tela: pygame.Surface, camera: Deslocamento, m: Monstro) -> None:
        """Aviso no chao: os tiles que o ataque vai pegar piscam cada vez mais rapido."""
        if not m.tiles_do_ataque or m.tipo is TipoDeMonstro.MUMIA:
            return
        cor = COR_DO_AVISO[m.tipo]
        k = m.progresso if m.estado is EstadoDoMonstro.AVISANDO else 1.0
        piscar = 0.5 + 0.5 * math.sin(self._tempo * (8 + 22 * k))
        alfa = int(40 + 90 * k * piscar)
        t = self._tile
        camada = self._camada_tile
        for tile in m.tiles_do_ataque:
            x, y = tile.coluna * t - camera[0], tile.linha * t - camera[1]
            camada.fill((0, 0, 0, 0))
            if m.tipo in (TipoDeMonstro.MAGMAN, TipoDeMonstro.TOUPEIRA):
                self._bolhas_ou_rachaduras(tela, m, x + t // 2, y + t // 2, k)
                continue
            pygame.draw.rect(camada, (*cor, alfa), (4, 4, t - 8, t - 8), border_radius=8)
            pygame.draw.rect(camada, (*cor, min(255, alfa + 80)), (4, 4, t - 8, t - 8), 2, border_radius=8)
            if m.tipo is TipoDeMonstro.GOLEM:  # rachaduras
                for i in range(3):
                    a = i * 2.1 + tile.coluna
                    pygame.draw.line(camada, (60, 40, 30, 220), (t // 2, t // 2),
                                     (t // 2 + math.cos(a) * 20 * k, t // 2 + math.sin(a) * 20 * k), 2)
            tela.blit(camada, (x, y))

    def _bolhas_ou_rachaduras(self, tela: pygame.Surface, m: Monstro, cx: int, cy: int, k: float) -> None:
        if m.tipo is TipoDeMonstro.MAGMAN:
            pygame.draw.ellipse(tela, (120, 30, 5), (cx - 18, cy - 7, 36, 16))
            for i in range(5):
                fase = (self._tempo * 2.5 + i * 0.37) % 1.0
                bx = cx + math.cos(i * 1.7) * 11
                by = cy + math.sin(i * 1.7) * 4 - fase * 6
                pygame.draw.circle(tela, (255, 150, 40), (round(bx), round(by)), max(1, round(2 + 3 * fase * k)), 1)
        else:  # toupeira: a terra comeca a tremer embaixo do jogador
            tremor = round(math.sin(self._tempo * 50) * 2 * k)
            pygame.draw.ellipse(tela, (90, 60, 35), (cx - 20 + tremor, cy - 6, 40, 18))
            for i in range(6):
                a = i * 1.05
                pygame.draw.line(tela, (60, 40, 20), (cx, cy + 3),
                                 (cx + math.cos(a) * (10 + 12 * k), cy + 3 + math.sin(a) * (5 + 6 * k)), 2)

    def _marcas_de_estado(self, tela: pygame.Surface, m: Monstro, x: int, topo: int) -> None:
        if m.estado is EstadoDoMonstro.AVISANDO and int(self._tempo * 10) % 2 == 0:
            pygame.draw.rect(tela, (20, 6, 10), (x - 6, topo - 22, 13, 21), border_radius=3)
            pygame.draw.rect(tela, (255, 50, 40), (x - 4, topo - 20, 9, 11), border_radius=2)
            pygame.draw.rect(tela, (255, 50, 40), (x - 4, topo - 6, 9, 4))
        elif m.estado is EstadoDoMonstro.DORMINDO:
            for i in range(3):
                k = (self._tempo * 0.6 + i / 3) % 1.0
                zx, zy, lado = x + 8 + round(k * 14), topo - round(k * 22), 4 + i
                pygame.draw.lines(tela, (220, 230, 255), False,
                                  [(zx, zy), (zx + lado, zy), (zx, zy + lado), (zx + lado, zy + lado)], 2)
        elif m.estado is EstadoDoMonstro.ATORDOADO:
            for i in range(3):
                a = self._tempo * 5 + i * math.tau / 3
                sx, sy = x + math.cos(a) * 14, topo + 4 + math.sin(a) * 4
                pygame.draw.circle(tela, (255, 230, 90), (round(sx), round(sy)), 3)

    def _brilho_nos_tiles(self, tela: pygame.Surface, camera: Deslocamento, m: Monstro) -> None:
        r = self._halo_do_ataque.get_width() // 2
        halo = self._halo_do_ataque.copy()
        halo.fill(tuple(c // 2 for c in COR_DO_AVISO[m.tipo]), special_flags=pygame.BLEND_RGB_MULT)
        t = self._tile
        for tile in m.tiles_do_ataque:
            cx, cy = tile.coluna * t + t // 2 - camera[0], tile.linha * t + t // 2 - camera[1]
            tela.blit(halo, (cx - r, cy - r), special_flags=pygame.BLEND_RGB_ADD)

    def _sombra_da_aguia(self, tela: pygame.Surface, camera: Deslocamento, m: Monstro) -> None:
        if m.estado is EstadoDoMonstro.AVISANDO and m.alvo is not None:  # alvo do mergulho
            ax, ay = round(m.alvo[0]) - camera[0], round(m.alvo[1]) - camera[1]
            raio = round(10 + 18 * m.progresso)
            pygame.draw.ellipse(tela, (0, 0, 0), (ax - raio, ay - raio // 2, raio * 2, raio))
            if int(self._tempo * 12) % 2:
                pygame.draw.ellipse(tela, (255, 80, 80), (ax - 28, ay - 14, 56, 28), 2)
        escala = 1.0 - 0.5 * m.altura_de_voo
        largura = round(40 * escala)
        x, y = round(m.x) - camera[0], round(m.y) - camera[1]
        sombra = pygame.transform.scale(self._sombra, (largura, max(4, round(14 * escala))))
        tela.blit(sombra, sombra.get_rect(center=(x, y + 10)))

    def _montinho(self, tela: pygame.Surface, camera: Deslocamento, m: Monstro) -> None:
        """Toupeira cavando: so um montinho de terra andando (some dentro das paredes)."""
        lab = self._ambiente.labirinto
        if lab.eh_parede(*m.tile):
            return
        x, y = round(m.x) - camera[0], round(m.y) - camera[1] + 18
        img = self._sprites.montinho(int(self._tempo * 6))
        tela.blit(img, img.get_rect(midbottom=(x, y)))
        for i in range(4):  # torroes pulando
            k = (self._tempo * 3 + i / 4) % 1.0
            tela.fill((70, 48, 30), (round(x - 12 + i * 8), round(y - 14 - math.sin(k * math.pi) * 10), 3, 3))

    def _bola_de_teia(self, tela: pygame.Surface, x: int, y: int) -> None:
        pygame.draw.circle(tela, (235, 235, 245), (x, y - 20), 6)
        for i in range(4):
            a = i * math.pi / 4 + self._tempo * 10
            pygame.draw.line(tela, (200, 200, 215), (x - math.cos(a) * 9, y - 20 - math.sin(a) * 9),
                             (x + math.cos(a) * 9, y - 20 + math.sin(a) * 9), 1)

    def _raio_congelante(self, tela: pygame.Surface, camera: Deslocamento, m: Monstro) -> None:
        if not m.tiles_do_ataque:
            return
        t = self._tile
        x0, y0 = round(m.x) - camera[0], round(m.y) - camera[1] - 18
        fim = m.tiles_do_ataque[-1]
        x1, y1 = fim.coluna * t + t // 2 - camera[0], fim.linha * t + t // 2 - camera[1] - 18
        for cor, largura in (((60, 160, 255), 14), ((150, 220, 255), 8), ((240, 250, 255), 3)):
            pygame.draw.line(tela, cor, (x0, y0), (x1, y1), largura)
        for i in range(8):  # cristais de gelo
            k = (i / 8 + self._tempo * 2) % 1.0
            cx, cy = x0 + (x1 - x0) * k, y0 + (y1 - y0) * k + math.sin(i * 3 + self._tempo * 20) * 6
            pygame.draw.line(tela, (255, 255, 255), (cx - 3, cy - 3), (cx + 3, cy + 3), 1)
            pygame.draw.line(tela, (255, 255, 255), (cx - 3, cy + 3), (cx + 3, cy - 3), 1)

    def _labareda(self, tela: pygame.Surface, camera: Deslocamento, m: Monstro) -> None:
        t = self._tile
        forca = min(1.0, m.progresso * 4, (1 - m.progresso) * 4)
        for i, tile in enumerate(m.tiles_do_ataque):
            cx, cy = tile.coluna * t + t // 2 - camera[0], tile.linha * t + t // 2 + 10 - camera[1]
            for cor, k in (((220, 60, 20), 1.0), ((255, 150, 40), 0.7), ((255, 240, 170), 0.4)):
                altura = 44 * forca * k * (0.85 + 0.15 * math.sin(self._tempo * 20 + i))
                meia = 18 * k
                balanco = 3 * math.sin(self._tempo * 13 + i)
                pygame.draw.polygon(tela, cor, [(cx - meia, cy), (cx - meia * 0.5, cy - altura * 0.7),
                                                (cx + balanco, cy - altura), (cx + meia * 0.5, cy - altura * 0.7),
                                                (cx + meia, cy)])

    def _laco(self, tela: pygame.Surface, x0: int, y0: int, x1: int, y1: int, alcance: float) -> None:
        """Faixa da mumia: uma linha ondulada esticando ate o alvo."""
        pontos = []
        for i in range(13):
            k = i / 12 * alcance
            onda = math.sin(k * 14 + self._tempo * 12) * 4 * (1 - k)
            pontos.append((x0 + (x1 - x0) * k + onda, y0 - 14 + (y1 - y0 + 14) * k + onda))
        pygame.draw.lines(tela, (120, 100, 60), False, pontos, 6)
        pygame.draw.lines(tela, (235, 220, 170), False, pontos, 3)

    def _onda_de_choque(self, tela: pygame.Surface, x: int, y: int, progresso: float) -> None:
        raio = round(20 + progresso * self._tile * 2.4)
        cor = (255, round(200 - 120 * progresso), 80)
        pygame.draw.ellipse(tela, cor, (x - raio, y + 12 - raio // 2, raio * 2, raio), 4)
        pygame.draw.ellipse(tela, (120, 90, 60), (x - raio + 8, y + 16 - raio // 2, raio * 2 - 16, raio - 8), 2)

    # ------------------------------------------------------------------
    # O sprite com vida
    # ------------------------------------------------------------------
    def _desenhar_monstro(self, tela: pygame.Surface, m: Monstro, x: int, y: int, camera: Deslocamento,
                          altura: int = 0) -> None:
        a = self._anim.get(id(m))
        if a is None:
            return
        estado, tipo = m.estado, m.tipo
        t = self._tempo + a.fase
        if estado is EstadoDoMonstro.ESCONDIDO:
            a.colocacao = None
            return

        quadro = self._quadro(m, a, t)
        modos = set()
        if estado is EstadoDoMonstro.DORMINDO or t % 3.7 < 0.13:
            modos.add(Modo.PISCANDO)
        if estado is EstadoDoMonstro.AVISANDO and int(self._tempo * 12) % 2:
            modos.add(Modo.CLARAO)
        if estado is EstadoDoMonstro.APAGADO:
            modos.add(Modo.PEDRA)
        if estado is EstadoDoMonstro.ATORDOADO:
            modos.add(Modo.CANSADO)
        espelhar = a.esquerda and tipo not in NUNCA_ESPELHA
        base = self._sprites.imagem(tipo, quadro, espelhar, frozenset(modos))
        w, h = base.get_size()

        kx = ky = 1.0
        dx = dy = 0.0
        angulo = 0.0
        if tipo is TipoDeMonstro.MAGMAN and estado in (EstadoDoMonstro.ANDANDO, EstadoDoMonstro.ATACANDO):
            gosma = math.sin(t * 5)  # nao saltita: escorre, esticando e achatando
            kx, ky = 1 + 0.07 * gosma, 1 - 0.07 * gosma
        elif estado is EstadoDoMonstro.ANDANDO and a.andando and tipo not in VOADORES:
            dy = -abs(math.sin(t * 8)) * 4  # passos pesados, saltitando
            kx = 1 + 0.04 * math.sin(t * 16)
            ky = 1 - 0.04 * math.sin(t * 16)
        else:  # respiracao pesada
            folego = math.sin(t * (3.2 if a.perto else 2.0))
            ky = 1 + 0.05 * folego
            kx = 1 - 0.03 * folego
        if estado is EstadoDoMonstro.AVISANDO:  # incha e treme cada vez mais
            p = m.progresso
            kx, ky = 1 + 0.16 * p, 1 - 0.12 * p
            dx += math.sin(self._tempo * 60) * (1.5 + 3 * p)
        elif estado is EstadoDoMonstro.ATACANDO and tipo is not TipoDeMonstro.FORNALHA:
            kx, ky = 0.86, 1.18
        elif estado is EstadoDoMonstro.DORMINDO:
            ky = 1 + 0.06 * math.sin(t * 1.3)
        elif estado is EstadoDoMonstro.ATORDOADO:
            angulo = math.sin(t * 7) * 12
        if a.tremendo > 0 or (a.perto and estado is EstadoDoMonstro.ANDANDO):
            forca = 3 if a.tremendo > 0 else 1
            dx += self._rng.uniform(-forca, forca)
            dy += self._rng.uniform(-forca, forca) * 0.5

        img = base
        if kx != 1 or ky != 1:
            img = pygame.transform.scale(base, (max(1, round(w * kx)), max(1, round(h * ky))))
        if angulo:
            img = pygame.transform.rotate(img, angulo)
        ret = img.get_rect(midbottom=(round(x + dx), round(y + 20 + dy - altura)))
        a.colocacao = (ret.move(camera[0], camera[1]), quadro, espelhar, img.get_width() / w, img.get_height() / h)
        if not m.visivel:  # mumia na tempestade: so os olhos (camada de luzes)
            return

        if tipo not in VOADORES and tipo is not TipoDeMonstro.FORNALHA:
            sombra = pygame.transform.scale(self._sombra, (max(8, round(w * 0.75)), 14))
            tela.blit(sombra, sombra.get_rect(center=(round(x), y + 20)))
        if estado not in (EstadoDoMonstro.APAGADO, EstadoDoMonstro.DORMINDO):
            pulso = 1.0 + 0.12 * math.sin(t * 2.4) + (0.25 if a.perto else 0.0)
            lado = round(max(w, h) * 1.45 * pulso)
            aura = pygame.transform.scale(self._aura, (lado, lado))
            tela.blit(aura, aura.get_rect(center=ret.center))

        corte = self._corte(m)
        if corte < 1.0:  # afundando na lava / saindo da terra
            visivel = max(1, round(img.get_height() * corte))
            tela.blit(img, (ret.x, ret.bottom - visivel), pygame.Rect(0, 0, img.get_width(), visivel))
        else:
            tela.blit(img, ret)
        self._desenhar_pingos(tela, a, camera)
        self._marcas_de_estado(tela, m, round(x), ret.top)

    def _quadro(self, m: Monstro, a: _Animacao, t: float) -> int:
        tipo = m.tipo
        if tipo in SEMPRE_ANIMADOS:
            return int(t * SEMPRE_ANIMADOS[tipo])
        if tipo is TipoDeMonstro.AGUIA:
            if m.estado is EstadoDoMonstro.ATACANDO:
                return 1
            return int(t * (10 if m.estado is EstadoDoMonstro.ANDANDO else 5))
        if m.estado is EstadoDoMonstro.ANDANDO and a.andando:
            return int(t * 7)
        if m.estado is EstadoDoMonstro.ATACANDO:
            return int(t * 12)
        return 0

    @staticmethod
    def _corte(m: Monstro) -> float:
        """Quanto do sprite aparece (1 = inteiro)."""
        if m.tipo is TipoDeMonstro.MAGMAN and m.estado is EstadoDoMonstro.AVISANDO:
            return max(0.0, 1 - m.progresso)
        if m.tipo is TipoDeMonstro.TOUPEIRA and m.estado is EstadoDoMonstro.ATACANDO:
            return min(1.0, m.progresso * 3)
        return 1.0

    def _desenhar_pingos(self, tela: pygame.Surface, a: _Animacao, camera: Deslocamento) -> None:
        if not a.pingos:
            return
        cor = PINGOS[a.tipo][0]
        for px, py, _, vida in a.pingos:
            comprimento = 3 if vida > 0.2 else 2
            tela.fill(cor, (round(px - camera[0]) - 1, round(py - camera[1]), 3, comprimento * 2))


