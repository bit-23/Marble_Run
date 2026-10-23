"""
elementos.py - Como caixas, molas, perigos e efeitos do Ambiente aparecem na tela.

So LE o Ambiente do dominio (posicoes, ciclos do fogo, condicoes ativas);
nenhuma regra e decidida aqui. Tres camadas, chamadas pela Cena:
    desenhar_chao          -> placas de gelo, pocas, teias, areia, fogo, molas e caixas "?"
    desenhar_sobre_jogador -> bloco de gelo, teia grudada, fogo no corpo, aura da estrela...
    desenhar_luzes         -> brilho das chamas e seta da bussola (sobre a escuridao)
"""
from __future__ import annotations

import math

import pygame

from ..dominio.ambiente import Ambiente, Condicao, MolaDeParede, Perigo, TipoDeItem, TipoDePerigo
from ..dominio.jogador import Direcao, Jogador
from ..dominio.labirinto import Labirinto
from .icones import icone, icone_da_caixa

Deslocamento = tuple[int, int]
Cor = tuple[int, int, int]

TAMANHO_DA_CAIXA = 30
AVISO_DO_FOGO = 0.5     # segundos de "faisca" antes de a chama acender
MOLA_COMPRIMIDA = 0.25  # segundos que a mola fica encolhida depois de lancar
GIRO_DA_MOLA = {Direcao.CIMA: 0, Direcao.ESQUERDA: 90, Direcao.BAIXO: 180, Direcao.DIREITA: -90}
ORDEM_DOS_PERIGOS = {TipoDePerigo.GELO: 0, TipoDePerigo.BURACO: 0}  # por baixo de todo o resto


def criar_halo(raio: int, cor: Cor) -> pygame.Surface:
    """Gradiente radial para somar (BLEND_RGB_ADD) por cima da escuridao."""
    s = pygame.Surface((raio * 2, raio * 2))
    for r in range(raio, 0, -2):
        k = (1 - r / raio) ** 2
        pygame.draw.circle(s, tuple(int(c * k) for c in cor), (raio, raio), r)
    return s


class DesenhoDoAmbiente:
    def __init__(self, ambiente: Ambiente, labirinto: Labirinto) -> None:
        self._ambiente = ambiente
        self._labirinto = labirinto
        self._tempo = 0.0
        t = labirinto.tamanho_tile
        self._tile = t
        self._agua = self._criar_poca(t)
        self._teia = self._criar_teia(t)
        self._areia = self._criar_areia(t)
        self._cinzas = self._criar_cinzas(t)
        self._placa_de_gelo = self._criar_placa_de_gelo(t)
        self._bloco_de_gelo = self._criar_bloco_de_gelo()
        self._molas = {comprimida: {d: pygame.transform.rotate(self._criar_mola(t, comprimida), giro)
                                    for d, giro in GIRO_DA_MOLA.items()}
                       for comprimida in (False, True)}
        self._halo_do_fogo = criar_halo(int(t * 1.3), (255, 110, 30))
        self._sombra = pygame.Surface((24, 8), pygame.SRCALPHA)
        pygame.draw.ellipse(self._sombra, (0, 0, 0, 90), self._sombra.get_rect())
        self._erros_vistos = 0
        self._direcao_do_jogador = Direcao.BAIXO
        self._tremor_da_teia = 0.0

    def atualizar(self, dt: float) -> None:
        self._tempo += dt
        desafio = self._ambiente.desafio_da_teia
        erros = desafio.erros if desafio is not None else 0
        if erros > self._erros_vistos:  # errou uma seta: baloes tremem
            self._tremor_da_teia = 0.3
        self._erros_vistos = erros
        self._tremor_da_teia = max(0.0, self._tremor_da_teia - dt)

    def _desenhar_setas_da_teia(self, tela: pygame.Surface, x: int, y: int) -> None:
        """Baloes com a sequencia: verdes = acertadas, a proxima pula e brilha (veneno: barra de tempo)."""
        desafio = self._ambiente.desafio_da_teia
        tamanho, espaco = 26, 6
        largura = len(desafio.sequencia) * (tamanho + espaco) - espaco
        if self._ambiente.envenenado:
            fracao = self._ambiente.veneno_restante / Ambiente.TEMPO_DO_VENENO
            barra = pygame.Rect(x - largura // 2, y + tamanho + 6, largura, 6)
            pygame.draw.rect(tela, (20, 12, 30), barra.inflate(4, 4), border_radius=3)
            pygame.draw.rect(tela, (120, 230, 80), (barra.x, barra.y, round(barra.w * fracao), barra.h),
                             border_radius=3)
        tremor = round(math.sin(self._tempo * 60) * 4) if self._tremor_da_teia > 0 else 0
        inicio = x - largura // 2 + tremor
        for i, direcao in enumerate(desafio.sequencia):
            feita, atual = i < desafio.acertos, i == desafio.acertos
            pulo = round(abs(math.sin(self._tempo * 7)) * 4) if atual else 0
            caixa = pygame.Rect(inicio + i * (tamanho + espaco), y - pulo, tamanho, tamanho)
            fundo = (60, 170, 90) if feita else (255, 214, 90) if atual else (50, 44, 70)
            if self._tremor_da_teia > 0:
                fundo = (210, 60, 60)
            pygame.draw.rect(tela, (20, 12, 30), caixa.move(2, 2), border_radius=5)
            pygame.draw.rect(tela, fundo, caixa, border_radius=5)
            pygame.draw.rect(tela, (245, 240, 230), caixa, 2, border_radius=5)
            self._desenhar_seta(tela, caixa.center, direcao, (20, 12, 30) if atual or feita else (200, 200, 220))

    @staticmethod
    def _desenhar_seta(tela: pygame.Surface, centro: tuple[int, int], direcao: Direcao, cor: Cor) -> None:
        cx, cy = centro
        pontos = [(cx, cy - 8), (cx + 8, cy + 2), (cx + 3, cy + 2), (cx + 3, cy + 8),
                  (cx - 3, cy + 8), (cx - 3, cy + 2), (cx - 8, cy + 2)]  # seta para cima, depois gira
        giro = {Direcao.CIMA: 0, Direcao.DIREITA: 90, Direcao.BAIXO: 180, Direcao.ESQUERDA: 270}[direcao]
        c, s = math.cos(math.radians(giro)), math.sin(math.radians(giro))
        girados = [(cx + (px - cx) * c - (py - cy) * s, cy + (px - cx) * s + (py - cy) * c) for px, py in pontos]
        pygame.draw.polygon(tela, cor, girados)

    # ------------------------------------------------------------------
    # Camada do chao
    # ------------------------------------------------------------------
    def desenhar_chao(self, tela: pygame.Surface, camera: Deslocamento) -> None:
        visivel = tela.get_rect().inflate(self._tile * 2, self._tile * 2)
        for perigo in sorted(self._ambiente.perigos, key=lambda p: ORDEM_DOS_PERIGOS.get(p.tipo, 1)):
            x, y = perigo.centro[0] - camera[0], perigo.centro[1] - camera[1]
            if perigo.ativo and visivel.collidepoint(x, y):
                self._desenhar_perigo(tela, perigo, x, y)
        tempo = self._ambiente.tempo
        for rastro in sorted(self._ambiente.rastros, key=lambda p: ORDEM_DOS_PERIGOS.get(p.tipo, 1)):
            x, y = rastro.centro[0] - camera[0], rastro.centro[1] - camera[1]
            sumindo = rastro.expira_em is not None and rastro.expira_em - tempo < 1.0
            if visivel.collidepoint(x, y) and not (sumindo and int(self._tempo * 10) % 2):
                self._desenhar_perigo(tela, rastro, x, y)

        for mola in self._ambiente.molas:
            self._desenhar_mola(tela, mola, camera, visivel)
        self._desenhar_erupcao(tela, camera)
        self._desenhar_parede_quebrando(tela, camera)

        for indice, surpresa in enumerate(self._ambiente.caixas):
            x, y = surpresa.centro[0] - camera[0], surpresa.centro[1] - camera[1]
            if surpresa.aberta or not visivel.collidepoint(x, y):
                continue
            pulo = 3 * math.sin(self._tempo * 3 + indice)
            tela.blit(self._sombra, self._sombra.get_rect(center=(x, y + 13)))
            if surpresa.conteudo is not None:  # item largado no chao (arena): o proprio icone flutuando
                brilho = 0.5 + 0.5 * math.sin(self._tempo * 4 + indice)
                pygame.draw.circle(tela, (255, 240, 170), (x, round(y - 4 + pulo)), round(13 + 3 * brilho), 1)
                img = icone(surpresa.conteudo, 26)
                tela.blit(img, img.get_rect(center=(x, round(y - 4 + pulo))))
                continue
            img = icone_da_caixa(TAMANHO_DA_CAIXA)
            tela.blit(img, img.get_rect(center=(x, round(y - 4 + pulo))))
            if int(self._tempo * 4 + indice) % 4 == 0:  # brilhinho piscando
                bx, by = x + 11, round(y - 16 + pulo)
                pygame.draw.line(tela, (255, 255, 230), (bx - 3, by), (bx + 3, by))
                pygame.draw.line(tela, (255, 255, 230), (bx, by - 3), (bx, by + 3))

    def _desenhar_mola(self, tela: pygame.Surface, mola: MolaDeParede, camera: Deslocamento,
                       visivel: pygame.Rect) -> None:
        t = self._tile
        x, y = mola.tile.coluna * t - camera[0], mola.tile.linha * t - camera[1]
        if not visivel.collidepoint(x, y):
            return
        comprimida = self._ambiente.tempo - mola.ultimo_uso < MOLA_COMPRIMIDA
        img = self._molas[comprimida][mola.direcao]
        presa_na = {Direcao.CIMA: {"midtop": (x + t // 2, y)},
                    Direcao.BAIXO: {"midbottom": (x + t // 2, y + t)},
                    Direcao.ESQUERDA: {"midleft": (x, y + t // 2)},
                    Direcao.DIREITA: {"midright": (x + t, y + t // 2)}}[mola.direcao]
        tela.blit(img, img.get_rect(**presa_na))

    def _desenhar_erupcao(self, tela: pygame.Surface, camera: Deslocamento) -> None:
        """Aviso: rachaduras brilhando cada vez mais. Ativa: coluna de lava borbulhando."""
        amb, ciclo = self._ambiente, self._ambiente.ciclo
        if not amb.jatos_de_lava or ciclo is None:
            return
        t = self._tile
        for i, tile in enumerate(amb.jatos_de_lava):
            cx, cy = tile.coluna * t + t // 2 - camera[0], tile.linha * t + t // 2 - camera[1]
            if ciclo.em_aviso:
                k = ciclo.progresso_do_aviso
                piscando = k > 0.6 and int(self._tempo * 14) % 2
                cor = (255, 230, 120) if piscando else (int(120 + 135 * k), int(40 + 60 * k), 10)
                pygame.draw.ellipse(tela, (60, 14, 4), (cx - 22, cy - 9, 44, 20))  # chao afundando
                for ang in range(5):  # rachaduras saindo do centro
                    a = ang * 1.26 + i
                    fim = (cx + math.cos(a) * (12 + 14 * k), cy + math.sin(a) * (8 + 10 * k))
                    meio = (cx + math.cos(a + 0.4) * (6 + 7 * k), cy + math.sin(a + 0.4) * (5 + 5 * k))
                    pygame.draw.lines(tela, cor, False, [(cx, cy), meio, fim], 2)
                pygame.draw.circle(tela, cor, (cx, cy), int(4 + 5 * k))
            elif ciclo.ativo:
                self._jato_de_lava(tela, cx, cy, ciclo.intensidade, i)

    def _jato_de_lava(self, tela: pygame.Surface, cx: int, cy: int, forca: float, fase: int) -> None:
        pygame.draw.ellipse(tela, (90, 20, 5), (cx - 20, cy - 8, 40, 18))
        pygame.draw.ellipse(tela, (255, 110, 20), (cx - 16, cy - 6, 32, 13))
        altura = 70 * forca * (0.9 + 0.1 * math.sin(self._tempo * 25 + fase))
        for cor, largura in (((200, 50, 10), 20), ((255, 140, 30), 13), ((255, 235, 150), 6)):
            meia = largura * (0.6 + 0.4 * forca) / 2
            balanco = 2 * math.sin(self._tempo * 18 + fase)
            pygame.draw.polygon(tela, cor, [(cx - meia, cy + 2), (cx - meia * 0.7 + balanco, cy - altura * 0.7),
                                            (cx + balanco, cy - altura), (cx + meia * 0.7 + balanco, cy - altura * 0.7),
                                            (cx + meia, cy + 2)])
        for gota in range(4):  # respingos
            k = (self._tempo * 2.2 + gota / 4 + fase * 0.13) % 1.0
            gx = cx + (gota - 1.5) * 9 * k
            gy = cy - altura * 0.8 - 30 * math.sin(math.pi * k) + 40 * k * k
            pygame.draw.circle(tela, (255, 160, 40), (round(gx), round(gy)), 2)

    def _desenhar_perigo(self, tela: pygame.Surface, perigo: Perigo, x: int, y: int) -> None:
        if perigo.tipo is TipoDePerigo.GELO:
            tela.blit(self._placa_de_gelo, self._placa_de_gelo.get_rect(center=(x, y)))
            k = (self._tempo * 0.8 + (x * 7 + y * 3) * 0.001) % 1.0  # reflexo passando
            if k < 0.35:
                desvio = int(-24 + 48 * k / 0.35)
                pygame.draw.line(tela, (255, 255, 255), (x + desvio - 6, y + 10), (x + desvio + 6, y - 10), 2)
            return
        if perigo.tipo is TipoDePerigo.AGUA:
            tela.blit(self._agua, self._agua.get_rect(center=(x, y)))
            for i in range(2):  # ondinhas
                k = (self._tempo * 0.6 + i * 0.5 + x * 0.01) % 1.0
                largura, altura = int(8 + 28 * k), int(4 + 14 * k)
                cor = (150, 210, 255) if k < 0.7 else (90, 150, 220)
                pygame.draw.ellipse(tela, cor, (x - largura // 2, y - altura // 2, largura, altura), 1)
        elif perigo.tipo is TipoDePerigo.TEIA:
            tela.blit(self._teia, self._teia.get_rect(center=(x, y)))
        elif perigo.tipo is TipoDePerigo.AREIA_MOVEDICA:
            tela.blit(self._areia, self._areia.get_rect(center=(x, y)))
            giro = self._tempo * 1.4
            pontos = [(x + (2 + i * 0.75) * math.cos(giro + i * 0.45),
                       y + (2 + i * 0.75) * math.sin(giro + i * 0.45) * 0.6) for i in range(24)]
            pygame.draw.lines(tela, (140, 105, 55), False, pontos, 2)
        elif perigo.tipo is TipoDePerigo.FOGO:
            tela.blit(self._cinzas, self._cinzas.get_rect(center=(x, y + 6)))
            self._desenhar_fogo(tela, perigo, x, y)
        elif perigo.tipo is TipoDePerigo.LAVA:
            pygame.draw.ellipse(tela, (110, 25, 5), (x - 20, y - 9, 40, 22))
            pygame.draw.ellipse(tela, (240, 90, 20), (x - 17, y - 7, 34, 17))
            pygame.draw.ellipse(tela, (255, 190, 70), (x - 9, y - 4, 16, 8))
            k = (self._tempo * 2 + x * 0.01) % 1.0  # bolha estourando
            pygame.draw.circle(tela, (255, 200, 90), (x + 6, y - round(3 * k)), round(1 + 3 * k), 1)
        elif perigo.tipo is TipoDePerigo.BURACO:
            pygame.draw.ellipse(tela, (90, 60, 35), (x - 19, y - 9, 38, 22))
            pygame.draw.ellipse(tela, (15, 10, 8), (x - 14, y - 6, 28, 15))
            for i in range(5):  # terra em volta
                a = i * 1.26
                pygame.draw.circle(tela, (110, 80, 50), (round(x + math.cos(a) * 19), round(y + 2 + math.sin(a) * 9)), 3)

    def _desenhar_fogo(self, tela: pygame.Surface, perigo: Perigo, x: int, y: int) -> None:
        if self._ambiente.fogo_apagado:  # flauta: so fumacinha
            for i in range(3):
                k = (self._tempo * 0.7 + i / 3) % 1.0
                pygame.draw.circle(tela, (90, 90, 95), (x + int(5 * math.sin(k * 6 + i)), y - int(26 * k)),
                                   int(2 + 4 * k), 1)
            return
        escala = self._escala_da_chama(perigo)
        if escala > 0:
            self._chama(tela, x, y + 12, escala, perigo.centro[0] * 0.37 + perigo.centro[1] * 0.11)
        elif perigo.momento_do_ciclo(self._ambiente.tempo) > Perigo.CICLO_DO_FOGO - AVISO_DO_FOGO:
            if int(self._tempo * 20) % 2:  # faiscas avisando que vai acender
                for dx in (-6, 0, 6):
                    pygame.draw.circle(tela, (255, 180, 60), (x + dx, y + 8 - abs(dx) // 3), 2)

    def _escala_da_chama(self, perigo: Perigo) -> float:
        if not perigo.fogo_aceso(self._ambiente.tempo):
            return 0.0
        momento = perigo.momento_do_ciclo(self._ambiente.tempo)
        return min(1.0, momento / 0.15, (Perigo.FOGO_ACESO - momento) / 0.15)

    def _chama(self, tela: pygame.Surface, x: int, base: int, escala: float, fase: float) -> None:
        tremula = 0.85 + 0.15 * math.sin(self._tempo * 18 + fase)
        balanco = 3 * math.sin(self._tempo * 11 + fase)
        camadas = (((220, 60, 20), 1.0), ((255, 150, 40), 0.7), ((255, 240, 170), 0.4))
        for cor, k in camadas:
            altura = 40 * escala * tremula * k
            meia = 13 * escala * k
            pygame.draw.polygon(tela, cor, [
                (x - meia, base), (x - meia * 0.95, base - altura * 0.35),
                (x - meia * 0.45, base - altura * 0.72), (x + balanco * k, base - altura),
                (x + meia * 0.5, base - altura * 0.66), (x + meia * 0.95, base - altura * 0.3),
                (x + meia, base)])

    # ------------------------------------------------------------------
    # Camada sobre o jogador
    # ------------------------------------------------------------------
    def desenhar_sob_jogador(self, tela: pygame.Surface, camera: Deslocamento, jogador: Jogador) -> None:
        """Tapete magico embaixo dos pes e buraco de quem caiu."""
        amb = self._ambiente
        x, y = round(jogador.x) - camera[0], round(jogador.y) - camera[1]
        if amb.condicao_ativa(Condicao.CAIDO):
            pygame.draw.ellipse(tela, (15, 10, 8), (x - 20, y - 8, 40, 16))
            pygame.draw.ellipse(tela, (110, 80, 50), (x - 22, y - 9, 44, 18), 3)
        if amb.condicao_ativa(Condicao.TAPETE):
            flutua = round(math.sin(self._tempo * 4) * 2) - 4
            pontos = [(x - 26 + i * 4, y + flutua + round(math.sin(self._tempo * 8 + i * 0.7) * 2)) for i in range(14)]
            base = [(px, py + 12) for px, py in reversed(pontos)]
            pygame.draw.polygon(tela, (120, 40, 140), pontos + base)
            pygame.draw.lines(tela, (240, 200, 80), False, pontos, 2)
            pygame.draw.lines(tela, (240, 200, 80), False, base, 2)
            for px, py in pontos[::3]:  # franjas
                pygame.draw.line(tela, (240, 200, 80), (px, py + 12), (px, py + 16), 1)

    def desenhar_sobre_jogador(self, tela: pygame.Surface, camera: Deslocamento, jogador: Jogador) -> None:
        amb = self._ambiente
        self._direcao_do_jogador = jogador.direcao
        x, y = round(jogador.x) - camera[0], round(jogador.y) - camera[1]
        if amb.condicao_ativa(Condicao.CONGELADO):
            tela.blit(self._bloco_de_gelo, self._bloco_de_gelo.get_rect(midbottom=(x, y + 6)))
        if amb.desafio_da_teia is not None:
            if amb.envenenado:
                for i in range(4):  # bolhas de veneno
                    k = (self._tempo * 1.2 + i / 4) % 1.0
                    pygame.draw.circle(tela, (120, 230, 80), (x - 12 + i * 8, y - 30 - round(30 * k)), 2 + round(2 * k), 1)
            else:
                for dx1, dy1, dx2, dy2 in ((-20, -56, 18, -8), (20, -50, -16, 0), (-22, -30, 22, -28), (0, -62, 2, 4)):
                    pygame.draw.line(tela, (230, 230, 240), (x + dx1, y + dy1), (x + dx2, y + dy2), 1)
            self._desenhar_setas_da_teia(tela, x, y - 92)
        if amb.condicao_ativa(Condicao.QUEIMANDO):  # pegando fogo: chamas no corpo todo
            for dx, escala, fase in ((-9, 0.75, 0.0), (9, 0.75, 2.0), (0, 1.15, 4.0)):
                self._chama(tela, x + dx, y - 4, escala, fase)
        elif amb.condicao_ativa(Condicao.PROTEGIDO):  # acabou de se queimar: fumacinha
            for i in range(3):
                k = (self._tempo * 1.5 + i / 3) % 1.0
                pygame.draw.circle(tela, (110, 110, 115), (x - 8 + i * 8, y - 50 - int(22 * k)), int(3 + 4 * k))
        if amb.condicao_ativa(Condicao.ESTRELA):
            for i in range(6):
                ang = self._tempo * 4 + i * math.tau / 6
                cx, cy = x + 26 * math.cos(ang), y - 28 + 30 * math.sin(ang)
                cor = pygame.Color(0)
                cor.hsva = ((self._tempo * 240 + i * 60) % 360, 70, 100, 100)
                pygame.draw.line(tela, cor, (cx - 4, cy), (cx + 4, cy), 2)
                pygame.draw.line(tela, cor, (cx, cy - 4), (cx, cy + 4), 2)
        if amb.condicao_ativa(Condicao.CALMARIA):  # notas da flauta
            for i in range(3):
                k = (self._tempo * 0.7 + i / 3) % 1.0
                nx = x + 22 * math.sin(k * 5 + i * 2)
                ny = y - 66 - 40 * k
                pygame.draw.circle(tela, (160, 240, 200), (round(nx), round(ny)), 3)
                pygame.draw.line(tela, (160, 240, 200), (nx + 3, ny), (nx + 3, ny - 10), 2)
        self._desenhar_itens_no_jogador(tela, x, y)
        self._desenhar_espuma(tela, camera)

    def _desenhar_itens_no_jogador(self, tela: pygame.Surface, x: int, y: int) -> None:
        amb = self._ambiente
        if amb.condicao_ativa(Condicao.BROCA):
            self._desenhar_broca_na_mao(tela, x, y)
        if amb.condicao_ativa(Condicao.BOTA):  # brilho de obsidiana nos pes
            for dx in (-7, 7):
                pygame.draw.ellipse(tela, (40, 20, 50), (x + dx - 6, y - 4, 12, 7))
                pygame.draw.ellipse(tela, (200, 90, 255), (x + dx - 6, y - 4, 12, 7), 1)
        if amb.condicao_ativa(Condicao.CAPACETE):  # capacete de mineiro com lampada
            pygame.draw.ellipse(tela, (230, 190, 40), (x - 13, y - 66, 26, 16))
            pygame.draw.rect(tela, (200, 160, 30), (x - 15, y - 56, 30, 4), border_radius=2)
            pygame.draw.circle(tela, (255, 250, 200), (x, y - 61), 4)
        if amb.condicao_ativa(Condicao.GUARDA_CHUVA):
            topo = y - 82
            pygame.draw.line(tela, (80, 60, 50), (x + 10, topo + 4), (x + 10, y - 40), 2)
            pygame.draw.arc(tela, (80, 60, 50), (x + 4, y - 44, 8, 8), math.pi, math.tau, 2)
            gomos = [(x + 10 - 26 + i * 13, topo + 10) for i in range(5)]
            pygame.draw.polygon(tela, (220, 60, 80), [(x + 10, topo - 6)] + gomos)
            for gx, gy in gomos[1:-1]:
                pygame.draw.line(tela, (150, 30, 50), (x + 10, topo - 6), (gx, gy), 1)
        if amb.condicao_ativa(Condicao.PIPA):
            px, py = x + 34 + round(math.sin(self._tempo * 2) * 6), y - 96 + round(math.cos(self._tempo * 3) * 4)
            pygame.draw.line(tela, (230, 230, 230), (x + 8, y - 30), (px, py + 10), 1)
            pygame.draw.polygon(tela, (80, 170, 240), [(px, py - 10), (px + 8, py), (px, py + 10), (px - 8, py)])
            pygame.draw.line(tela, (250, 230, 90), (px, py - 10), (px, py + 10), 1)
            pygame.draw.lines(tela, (250, 90, 90), False, [(px, py + 10), (px - 4, py + 16), (px + 3, py + 22)], 1)
        if amb.condicao_ativa(Condicao.TONTO):  # passarinhos/estrelas girando na cabeca
            for i in range(3):
                a = self._tempo * 6 + i * math.tau / 3
                sx, sy = x + math.cos(a) * 16, y - 66 + math.sin(a) * 5
                pygame.draw.circle(tela, (255, 230, 90), (round(sx), round(sy)), 3)
        cargas = amb.cargas_de_parede
        if cargas and not amb.condicao_ativa(Condicao.BROCA):  # tapete: quantas paredes ainda da para voar
            for i in range(cargas):
                img = icone(TipoDeItem.TAPETE, 14)
                tela.blit(img, (x - 7 * cargas + i * 15, y - 104))

    # Onde a mao segura a broca e para onde ela aponta (graus), conforme o jogador esta virado
    MAO_DA_BROCA = {Direcao.DIREITA: ((13, -22), 0), Direcao.ESQUERDA: ((-13, -22), 180),
                    Direcao.BAIXO: ((11, -16), 90), Direcao.CIMA: ((11, -30), -90)}

    def _desenhar_broca_na_mao(self, tela: pygame.Surface, x: int, y: int) -> None:
        """Broca de verdade na mao: corpo amarelo, ponta de aco com espiral girando (rapido ao perfurar)."""
        amb = self._ambiente
        perfurando = amb.perfuracao is not None
        (mx, my), graus = self.MAO_DA_BROCA[self._direcao_do_jogador]
        cx, cy = x + mx, y + my
        if perfurando:
            cx += round(math.sin(self._tempo * 70) * 2)
            cy += round(math.cos(self._tempo * 55) * 1.5)
        a = math.radians(graus)
        c, s = math.cos(a), math.sin(a)

        def p(px: float, py: float) -> tuple[float, float]:
            return cx + px * c - py * s, cy + px * s + py * c

        escuro, amarelo, claro = (60, 40, 10), (235, 180, 40), (255, 225, 120)
        aco, aco_escuro = (190, 195, 210), (95, 100, 118)
        pygame.draw.polygon(tela, escuro, [p(-3, 4), p(3, 4), p(2, 13), p(-4, 13)])  # cabo
        pygame.draw.polygon(tela, (40, 30, 30), [p(-2, 5), p(2, 5), p(1, 12), p(-3, 12)])
        corpo = [p(-9, -6), p(7, -6), p(7, 6), p(-9, 6)]
        pygame.draw.polygon(tela, amarelo, corpo)
        pygame.draw.polygon(tela, escuro, corpo, 2)
        pygame.draw.line(tela, claro, p(-7, -4), p(5, -4), 2)
        pygame.draw.polygon(tela, aco_escuro, [p(7, -4), p(10, -4), p(10, 4), p(7, 4)])  # mandril
        ponta = [p(10, -5), p(27, 0), p(10, 5)]
        pygame.draw.polygon(tela, aco, ponta)
        giro = (self._tempo * (28 if perfurando else 6)) % 1.0
        for i in range(4):  # espiral andando = girando
            k = (i + giro) / 4
            px = 10 + 17 * k
            meia = 5 * (1 - k)
            pygame.draw.line(tela, aco_escuro, p(px, -meia), p(px + 3, meia), 2)
        pygame.draw.polygon(tela, (40, 40, 52), ponta, 1)
        if perfurando:  # faiscas na ponta
            pontaX, pontaY = p(28, 0)
            for i in range(5):
                ang = self._tempo * 40 + i * 1.3
                comprimento = 4 + (i * 7 + int(self._tempo * 30)) % 6
                pygame.draw.line(tela, (255, 230, 120), (pontaX, pontaY),
                                 (pontaX + math.cos(ang) * comprimento, pontaY + math.sin(ang) * comprimento), 1)

    def _desenhar_parede_quebrando(self, tela: pygame.Surface, camera: Deslocamento) -> None:
        """Rachaduras crescendo na parede que a broca esta furando + entulho caindo."""
        perfuracao = self._ambiente.perfuracao
        if perfuracao is None:
            return
        tile, progresso = perfuracao
        t = self._tile
        x0, y0 = tile.coluna * t - camera[0], tile.linha * t - camera[1]
        cx, cy = x0 + t // 2, y0 + t // 2
        sombra = pygame.Surface((t, t), pygame.SRCALPHA)
        sombra.fill((0, 0, 0, int(110 * progresso)))
        tela.blit(sombra, (x0, y0))
        for i in range(7):
            ang = i * 0.9 + 0.4
            comprimento = (t * 0.55) * min(1.0, progresso * 1.4) * (0.6 + 0.4 * ((i * 37) % 10) / 10)
            meio = (cx + math.cos(ang + 0.3) * comprimento * 0.5, cy + math.sin(ang + 0.3) * comprimento * 0.5)
            fim = (cx + math.cos(ang) * comprimento, cy + math.sin(ang) * comprimento)
            pygame.draw.lines(tela, (25, 18, 14), False, [(cx, cy), meio, fim], 3)
            pygame.draw.lines(tela, (255, 190, 90), False, [(cx, cy), meio, fim], 1)
        for i in range(8):  # pedrinhas caindo
            k = (self._tempo * 2.2 + i / 8) % 1.0
            px = cx + ((i * 23) % t) - t // 2
            py = cy - 6 + k * t * 0.7
            tela.fill((120, 105, 95), (round(px), round(py), 3, 3))

    def _desenhar_espuma(self, tela: pygame.Surface, camera: Deslocamento) -> None:
        extintor = self._ambiente.extintor
        if extintor is None:
            return
        ex, ey, momento = extintor
        k = (self._ambiente.tempo - momento) / 0.8
        if not 0 <= k < 1:
            return
        raio = self._tile * 3 * min(1.0, k * 2)
        for i in range(16):
            a = i * math.tau / 16 + i
            r = raio * (0.5 + 0.5 * ((i * 7) % 5) / 4)
            cx, cy = ex - camera[0] + math.cos(a) * r, ey - camera[1] - 10 + math.sin(a) * r * 0.6
            pygame.draw.circle(tela, (235, 245, 255), (round(cx), round(cy)), round(10 * (1 - k)) + 2)

    # ------------------------------------------------------------------
    # Camada sobre a escuridao
    # ------------------------------------------------------------------
    def desenhar_luzes(self, tela: pygame.Surface, camera: Deslocamento, jogador: Jogador) -> None:
        amb = self._ambiente
        if not amb.fogo_apagado:
            r = self._halo_do_fogo.get_width() // 2
            for perigo in amb.perigos:
                escala = self._escala_da_chama(perigo) if perigo.tipo is TipoDePerigo.FOGO else 0.0
                if escala > 0.05:
                    halo = self._halo_do_fogo
                    if escala < 0.99:
                        halo = halo.copy()
                        halo.fill((int(255 * escala),) * 3, special_flags=pygame.BLEND_RGB_MULT)
                    tela.blit(halo, (perigo.centro[0] - camera[0] - r, perigo.centro[1] - camera[1] - r),
                              special_flags=pygame.BLEND_RGB_ADD)
        ciclo = amb.ciclo
        if amb.jatos_de_lava and ciclo is not None and (ciclo.ativo or ciclo.em_aviso):
            forca = ciclo.intensidade if ciclo.ativo else 0.35 * ciclo.progresso_do_aviso
            r = self._halo_do_fogo.get_width() // 2
            halo = self._halo_do_fogo.copy()
            halo.fill((int(255 * min(1.0, forca)),) * 3, special_flags=pygame.BLEND_RGB_MULT)
            t = self._tile
            for tile in amb.jatos_de_lava:  # lava (e o aviso) brilham ate no escuro
                cx, cy = tile.coluna * t + t // 2 - camera[0], tile.linha * t + t // 2 - camera[1]
                tela.blit(halo, (cx - r, cy - r), special_flags=pygame.BLEND_RGB_ADD)
        if amb.condicao_ativa(Condicao.BUSSOLA):
            self._desenhar_bussola(tela, camera, jogador)
        self._desenhar_rastros_brilhando(tela, camera)
        self._desenhar_melhor_caminho(tela, camera)

    def _desenhar_rastros_brilhando(self, tela: pygame.Surface, camera: Deslocamento) -> None:
        lavas = [p for p in self._ambiente.rastros if p.tipo is TipoDePerigo.LAVA]
        if not lavas:
            return
        r = self._halo_do_fogo.get_width() // 2
        halo = self._halo_do_fogo.copy()
        halo.fill((150, 150, 150), special_flags=pygame.BLEND_RGB_MULT)
        for lava in lavas:
            tela.blit(halo, (lava.centro[0] - camera[0] - r, lava.centro[1] - camera[1] - r),
                      special_flags=pygame.BLEND_RGB_ADD)

    def _desenhar_melhor_caminho(self, tela: pygame.Surface, camera: Deslocamento) -> None:
        """Desejo do genio: setas douradas no chao, do jogador ate o portal (aparecem ate no escuro)."""
        trajeto = self._ambiente.melhor_caminho
        t = self._tile
        for i, (a, b) in enumerate(zip(trajeto, trajeto[1:])):
            dx, dy = b.coluna - a.coluna, b.linha - a.linha
            direcao = {(0, -1): Direcao.CIMA, (0, 1): Direcao.BAIXO, (-1, 0): Direcao.ESQUERDA,
                       (1, 0): Direcao.DIREITA}[(dx, dy)]
            cx, cy = a.coluna * t + t // 2 - camera[0], a.linha * t + t // 2 - camera[1]
            onda = 0.5 + 0.5 * math.sin(self._tempo * 8 - i * 0.6)
            pygame.draw.circle(tela, (90, 60, 10), (cx, cy), 12)
            self._desenhar_seta(tela, (cx, cy), direcao, (255, round(200 + 55 * onda), round(60 + 120 * onda)))

    def _desenhar_bussola(self, tela: pygame.Surface, camera: Deslocamento, jogador: Jogador) -> None:
        sx, sy = jogador.x - camera[0], jogador.y - camera[1] - 24
        alvo_x, alvo_y = self._labirinto.centro_do_tile(self._labirinto.saida)
        ang = math.atan2(alvo_y - camera[1] - sy, alvo_x - camera[0] - sx)
        distancia = 50 + 3 * math.sin(self._tempo * 6)
        c, s = math.cos(ang), math.sin(ang)
        ponta = (sx + c * (distancia + 14), sy + s * (distancia + 14))
        esquerda = (sx + c * distancia - s * 8, sy + s * distancia + c * 8)
        direita = (sx + c * distancia + s * 8, sy + s * distancia - c * 8)
        pygame.draw.polygon(tela, (255, 214, 90), (ponta, esquerda, direita))
        pygame.draw.polygon(tela, (90, 60, 10), (ponta, esquerda, direita), 2)

    # ------------------------------------------------------------------
    # Texturas
    # ------------------------------------------------------------------
    @staticmethod
    def _criar_poca(t: int) -> pygame.Surface:
        s = pygame.Surface((t, t), pygame.SRCALPHA)
        pygame.draw.ellipse(s, (30, 80, 160, 230), (4, 10, t - 8, t - 20))
        pygame.draw.ellipse(s, (60, 130, 210, 255), (8, 13, t - 16, t - 26))
        pygame.draw.ellipse(s, (170, 225, 255, 255), (4, 10, t - 8, t - 20), 2)
        pygame.draw.line(s, (220, 240, 255), (16, 20), (24, 18), 2)
        return s

    @staticmethod
    def _criar_teia(t: int) -> pygame.Surface:
        s = pygame.Surface((t, t), pygame.SRCALPHA)
        cor = (225, 225, 235, 200)
        meio = t // 2
        raios = [(meio + 24 * math.cos(i * math.tau / 8), meio + 24 * math.sin(i * math.tau / 8)) for i in range(8)]
        for ponta in raios:
            pygame.draw.line(s, cor, (meio, meio), ponta, 1)
        for k in (0.35, 0.65, 1.0):
            pygame.draw.polygon(s, cor, [(meio + (px - meio) * k, meio + (py - meio) * k) for px, py in raios], 1)
        pygame.draw.circle(s, (20, 20, 20, 255), (meio + 9, meio - 7), 4)  # aranha
        for dx in (-5, 5):
            pygame.draw.line(s, (20, 20, 20, 255), (meio + 9, meio - 7), (meio + 9 + dx, meio - 12), 1)
            pygame.draw.line(s, (20, 20, 20, 255), (meio + 9, meio - 7), (meio + 9 + dx, meio - 2), 1)
        return s

    @staticmethod
    def _criar_areia(t: int) -> pygame.Surface:
        s = pygame.Surface((t, t), pygame.SRCALPHA)
        pygame.draw.ellipse(s, (150, 115, 65, 255), (2, 8, t - 4, t - 16))
        pygame.draw.ellipse(s, (205, 170, 105, 255), (6, 11, t - 12, t - 22))
        pygame.draw.ellipse(s, (175, 140, 85, 255), (14, 17, t - 28, t - 34))
        return s

    @staticmethod
    def _criar_cinzas(t: int) -> pygame.Surface:
        s = pygame.Surface((t - 14, (t - 14) // 2), pygame.SRCALPHA)
        pygame.draw.ellipse(s, (35, 22, 18, 230), s.get_rect())
        pygame.draw.ellipse(s, (150, 60, 20, 180), s.get_rect(), 1)
        return s

    @staticmethod
    def _criar_bloco_de_gelo() -> pygame.Surface:
        s = pygame.Surface((46, 70), pygame.SRCALPHA)
        pygame.draw.rect(s, (170, 220, 255, 120), s.get_rect(), border_radius=6)
        pygame.draw.rect(s, (235, 248, 255, 230), s.get_rect(), 2, border_radius=6)
        pygame.draw.line(s, (255, 255, 255, 200), (8, 10), (18, 4), 3)
        pygame.draw.line(s, (255, 255, 255, 140), (8, 20), (30, 6), 2)
        return s

    @staticmethod
    def _criar_placa_de_gelo(t: int) -> pygame.Surface:
        """Chao de gelo liso e brilhante (cobre o tile inteiro, estilo Pokemon)."""
        s = pygame.Surface((t, t), pygame.SRCALPHA)
        s.fill((170, 225, 255, 205))
        for i in range(0, t, 8):  # azulejos de gelo
            pygame.draw.line(s, (140, 200, 240, 220), (i, 0), (i, t), 1)
            pygame.draw.line(s, (140, 200, 240, 220), (0, i), (t, i), 1)
        pygame.draw.line(s, (245, 252, 255, 230), (6, t - 14), (16, t - 24), 2)
        pygame.draw.line(s, (245, 252, 255, 230), (t - 20, 12), (t - 10, 4), 2)
        pygame.draw.rect(s, (225, 245, 255, 255), s.get_rect(), 2)
        return s

    @staticmethod
    def _criar_mola(t: int, comprimida: bool) -> pygame.Surface:
        """Mola vista de cima, PRESA EM CIMA (na parede) e com a almofada vermelha embaixo.

        Depois e girada para a parede certa (esquerda, direita, baixo).
        """
        largura, profundidade = 30, 18
        s = pygame.Surface((largura, profundidade), pygame.SRCALPHA)
        pygame.draw.rect(s, (90, 95, 110), (2, 0, largura - 4, 3))  # chapa presa na parede
        fim = 9 if comprimida else 13
        pontos = [(6 if i % 2 else largura - 6, 3 + i * (fim - 3) / 5) for i in range(6)]
        pygame.draw.lines(s, (110, 115, 130), False, [(x + 1, y + 1) for x, y in pontos], 3)
        pygame.draw.lines(s, (215, 220, 230), False, pontos, 2)
        pygame.draw.rect(s, (150, 30, 30), (3, fim, largura - 6, 5), border_radius=2)
        pygame.draw.rect(s, (235, 70, 60), (3, fim, largura - 6, 3), border_radius=2)
        return s
