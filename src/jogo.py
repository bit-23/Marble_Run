"""
jogo.py - Regras do jogo, geracao PROCEDURAL do labirinto e "reboot".

Fluxo (estilo roguelike, como Dead Cells):
    menu -> jogando -> (achou a saida) -> vitoria -> proximo labirinto (mais dificil)
                    -> (tempo acabou)  -> derrota -> ENTER = REBOOT: labirinto
                                                     totalmente novo, volta a fase 1
"""
import random
from collections import deque
from pathlib import Path

import pygame

from cenario import Cenario, TILE
from jogador import Jogador, VELOCIDADE

# ----------------------------------------------------------------------
# Ajustes de jogabilidade (mexa aqui para balancear!)
# ----------------------------------------------------------------------
TEMPO_FATOR_INICIAL = 2.8   # fase 1: tempo = (tempo minimo) x 2.8 ...
TEMPO_FATOR_MINIMO = 1.6    # ... cai a cada fase ate x 1.6
TEMPO_EXTRA = 5             # segundos de "folga" fixos
PROB_LACOS = 0.06           # % de paredes removidas para criar atalhos/loops
ARQ_RECORDE = Path(__file__).resolve().parent / "recorde.txt"

DIRS = ((1, 0), (-1, 0), (0, 1), (0, -1))


# ======================================================================
#  GERACAO PROCEDURAL
# ======================================================================
def gerar_labirinto(colunas, linhas, rng, laco=PROB_LACOS):
    """
    Gera um labirinto aleatorio.

    colunas/linhas = quantidade de CELULAS. A grade final tem (2n+1) tiles,
    porque entre duas celulas existe um tile que pode ser parede ou passagem.

    Algoritmo:
      1. "Recursive backtracker" (DFS): garante que TODAS as celulas estao
         ligadas por um unico caminho -> o labirinto sempre tem solucao.
      2. Remove algumas paredes ao acaso (lacos) para criar mais de um
         caminho, deixando de ser um labirinto "perfeito" e chato.
      3. Entrada em uma celula aleatoria; saida escolhida entre as celulas
         mais DISTANTES dela (BFS) -> o jogador sempre precisa explorar.

    Retorna (grade, entrada, saida, distancia_minima_em_tiles)
    """
    larg, alt = colunas * 2 + 1, linhas * 2 + 1
    grade = [[1] * larg for _ in range(alt)]

    inicio = (rng.randrange(colunas), rng.randrange(linhas))
    grade[inicio[1] * 2 + 1][inicio[0] * 2 + 1] = 0
    visitadas = {inicio}
    pilha = [inicio]
    while pilha:
        cx, cy = pilha[-1]
        vizinhas = [(cx + dx, cy + dy, dx, dy) for dx, dy in DIRS
                    if 0 <= cx + dx < colunas and 0 <= cy + dy < linhas
                    and (cx + dx, cy + dy) not in visitadas]
        if not vizinhas:
            pilha.pop()
            continue
        nx, ny, dx, dy = rng.choice(vizinhas)
        grade[cy * 2 + 1 + dy][cx * 2 + 1 + dx] = 0   # derruba a parede entre as duas
        grade[ny * 2 + 1][nx * 2 + 1] = 0
        visitadas.add((nx, ny))
        pilha.append((nx, ny))

    # 2. lacos
    paredes_internas = [
        (x, y) for y in range(1, alt - 1) for x in range(1, larg - 1)
        if grade[y][x] == 1 and (x % 2) != (y % 2)  # parede ENTRE duas celulas
    ]
    rng.shuffle(paredes_internas)
    for x, y in paredes_internas[: int(len(paredes_internas) * laco)]:
        grade[y][x] = 0

    # 3. entrada e saida
    entrada = (inicio[0] * 2 + 1, inicio[1] * 2 + 1)
    dist = _distancias(grade, entrada)
    celulas = [(x, y) for (x, y) in dist if x % 2 == 1 and y % 2 == 1]
    maxima = max(dist[c] for c in celulas)
    distantes = [c for c in celulas if dist[c] >= maxima * 0.85]
    saida = rng.choice(distantes)
    return grade, entrada, saida, dist[saida]


def _distancias(grade, origem):
    """BFS: menor numero de tiles de `origem` ate cada tile livre."""
    dist = {origem: 0}
    fila = deque([origem])
    while fila:
        x, y = fila.popleft()
        for dx, dy in DIRS:
            p = (x + dx, y + dy)
            if p not in dist and grade[p[1]][p[0]] == 0:
                dist[p] = dist[(x, y)] + 1
                fila.append(p)
    return dist


# ======================================================================
#  O JOGO
# ======================================================================
class Jogo:
    def __init__(self, tela, som, titulo="Marble Run"):
        self.tela = tela
        self.som = som
        self.titulo = titulo
        self.largura, self.altura = tela.get_size()

        self.fonte_gg = pygame.font.Font(None, 96)
        self.fonte_g = pygame.font.Font(None, 56)
        self.fonte_m = pygame.font.Font(None, 34)
        self.fonte_p = pygame.font.Font(None, 24)

        self.estado = "menu"      # menu | jogando | pausado | vitoria | derrota
        self.sair = False
        self.escuridao = True
        self.recorde = self._ler_recorde()
        self.nivel = 1
        self.pontos = 0
        self.semente = 0
        self.cenario = None
        self.jogador = None
        self.camera = (0, 0)
        self.tempo_restante = 0.0
        self.tempo_total = 1.0
        self.tempo_estado = 0.0   # cronometro do estado atual (usado na vitoria)
        self.tempo_passo = 0.0
        self.ultimo_segundo = 99
        self.bonus_ultimo = 0
        self._sprite_menu = Jogador.carregar_sprites()["parado"]
        self._luz = None
        self._veu = pygame.Surface((self.largura, self.altura), pygame.SRCALPHA)

    # ------------------------------------------------------------------
    # Reboot / niveis
    # ------------------------------------------------------------------
    def reiniciar(self):
        """REBOOT: nova corrida, labirinto inedito, volta para a fase 1."""
        self.nivel = 1
        self.pontos = 0
        self._construir_nivel()

    def proximo_nivel(self):
        self.nivel += 1
        self._construir_nivel()

    def _tamanho_nivel(self):
        colunas = min(10 + (self.nivel - 1), 30)
        linhas = min(7 + (self.nivel - 1) * 2 // 3, 20)
        return colunas, linhas

    def _construir_nivel(self):
        self.semente = random.SystemRandom().randrange(1_000_000)
        rng = random.Random(self.semente)  # mesma semente => mesmo labirinto
        colunas, linhas = self._tamanho_nivel()
        grade, entrada, saida, dist = gerar_labirinto(colunas, linhas, rng)

        self.cenario = Cenario(grade, entrada, saida)
        cx, cy = self.cenario.centro_tile(entrada)
        self.jogador = Jogador(cx, cy + 12)

        tempo_minimo = dist * TILE / VELOCIDADE
        fator = max(TEMPO_FATOR_MINIMO, TEMPO_FATOR_INICIAL - 0.1 * (self.nivel - 1))
        self.tempo_total = tempo_minimo * fator + TEMPO_EXTRA
        self.tempo_restante = self.tempo_total
        self.ultimo_segundo = 99
        self._luz = self._criar_luz(max(3.5, 7.0 - 0.4 * (self.nivel - 1)) * TILE)
        self._atualizar_camera()
        self.estado = "jogando"

    def _criar_luz(self, raio):
        raio = int(raio)
        luz = pygame.Surface((raio * 2, raio * 2), pygame.SRCALPHA)
        for r in range(raio, 0, -2):
            k = min(1.0, (1 - r / raio) * 1.6) ** 0.9
            pygame.draw.circle(luz, (0, 0, 0, int(235 * k)), (raio, raio), r)
        return luz

    def _atualizar_camera(self):
        cx = round(self.jogador.x) - self.largura // 2
        cy = round(self.jogador.y) - self.altura // 2
        # se o mapa for menor que a tela, centraliza; senao, nao passa da borda
        if self.cenario.largura <= self.largura:
            cx = -(self.largura - self.cenario.largura) // 2
        else:
            cx = max(0, min(cx, self.cenario.largura - self.largura))
        if self.cenario.altura <= self.altura:
            cy = -(self.altura - self.cenario.altura) // 2
        else:
            cy = max(0, min(cy, self.cenario.altura - self.altura))
        self.camera = (cx, cy)

    # ------------------------------------------------------------------
    # Recorde
    # ------------------------------------------------------------------
    def _ler_recorde(self):
        try:
            return int(ARQ_RECORDE.read_text().strip())
        except (OSError, ValueError):
            return 0

    def _salvar_recorde(self):
        if self.nivel > self.recorde:
            self.recorde = self.nivel
            try:
                ARQ_RECORDE.write_text(str(self.recorde))
            except OSError:
                pass

    # ------------------------------------------------------------------
    # Entrada
    # ------------------------------------------------------------------
    def processar_evento(self, ev):
        if ev.type != pygame.KEYDOWN:
            return
        confirmar = ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)

        if ev.key == pygame.K_m:
            self.som.alternar_mudo()
        elif ev.key == pygame.K_l:
            self.escuridao = not self.escuridao

        if self.estado == "menu":
            if confirmar:
                self.som.iniciar_musica()
                self.reiniciar()
            elif ev.key == pygame.K_ESCAPE:
                self.sair = True
        elif self.estado == "jogando":
            if ev.key in (pygame.K_ESCAPE, pygame.K_p):
                self.estado = "pausado"
        elif self.estado == "pausado":
            if ev.key in (pygame.K_ESCAPE, pygame.K_p) or confirmar:
                self.estado = "jogando"
            elif ev.key == pygame.K_q:
                self.estado = "menu"
        elif self.estado == "derrota":
            if confirmar:
                self.reiniciar()   # <<< REBOOT
            elif ev.key == pygame.K_ESCAPE:
                self.estado = "menu"

    # ------------------------------------------------------------------
    # Logica
    # ------------------------------------------------------------------
    def atualizar(self, dt):
        if self.estado == "jogando":
            self._atualizar_jogando(dt)
        elif self.estado == "vitoria":
            self.cenario.atualizar(dt)
            self.tempo_estado += dt
            if self.tempo_estado >= 1.8:
                self.proximo_nivel()

    def _atualizar_jogando(self, dt):
        self.cenario.atualizar(dt)
        self.jogador.atualizar(dt, self.cenario)
        self._atualizar_camera()

        # som de passos
        if self.jogador.andando:
            self.tempo_passo -= dt
            if self.tempo_passo <= 0:
                self.som.tocar("passo")
                self.tempo_passo = 0.26
        else:
            self.tempo_passo = 0.0

        # relogio
        self.tempo_restante -= dt
        segundo = int(self.tempo_restante)
        if self.tempo_restante <= 10 and segundo < self.ultimo_segundo and self.tempo_restante > 0:
            self.som.tocar("alerta")
        self.ultimo_segundo = segundo

        if self.jogador.rect().colliderect(self.cenario.rect_saida()):
            self.bonus_ultimo = int(self.tempo_restante) * 10
            self.pontos += 100 * self.nivel + self.bonus_ultimo
            self.estado = "vitoria"
            self.tempo_estado = 0.0
            self.som.tocar("vitoria")
        elif self.tempo_restante <= 0:
            self.tempo_restante = 0
            self._salvar_recorde()
            self.estado = "derrota"
            self.som.tocar("derrota")

    # ------------------------------------------------------------------
    # Desenho
    # ------------------------------------------------------------------
    def desenhar(self):
        if self.estado == "menu":
            self._desenhar_menu()
            return

        self.tela.fill((18, 16, 28))
        cx, cy = self.camera
        self.cenario.desenhar(self.tela, cx, cy)
        self.jogador.desenhar(self.tela, cx, cy)

        if self.escuridao and self.estado in ("jogando", "pausado"):
            self._veu.fill((0, 0, 0, 235))
            r = self._luz.get_width() // 2
            px, py = round(self.jogador.x) - cx, round(self.jogador.y) - cy - 20
            self._veu.blit(self._luz, (px - r, py - r), special_flags=pygame.BLEND_RGBA_SUB)
            self.tela.blit(self._veu, (0, 0))
            self.cenario.desenhar_brilho_saida(self.tela, cx, cy)

        self._desenhar_hud()

        if self.estado == "pausado":
            self._painel("PAUSADO", "ESC/ENTER continua   |   Q volta ao menu")
        elif self.estado == "vitoria":
            self._painel("SAIU DO LABIRINTO!", f"+{100 * self.nivel + self.bonus_ultimo} pontos  (bonus de tempo: {self.bonus_ultimo})")
        elif self.estado == "derrota":
            self._painel("TEMPO ESGOTADO!",
                         f"Voce chegou a fase {self.nivel}  |  Pontos: {self.pontos}  |  Recorde: fase {self.recorde}",
                         "ENTER = gerar um NOVO labirinto")

    def _texto(self, texto, fonte, cor, centro=None, topleft=None):
        img = fonte.render(texto, True, cor)
        pos = img.get_rect(center=centro) if centro else img.get_rect(topleft=topleft)
        sombra = fonte.render(texto, True, (0, 0, 0))
        self.tela.blit(sombra, pos.move(2, 2))
        self.tela.blit(img, pos)

    def _desenhar_hud(self):
        pygame.draw.rect(self.tela, (10, 8, 20), (0, 0, self.largura, 44))
        self._texto(f"FASE {self.nivel}", self.fonte_m, (255, 214, 90), topleft=(14, 10))
        self._texto(f"PONTOS {self.pontos}", self.fonte_m, (230, 230, 240), topleft=(150, 10))

        frac = max(0.0, self.tempo_restante / self.tempo_total)
        cor = (90, 200, 120) if frac > 0.5 else (240, 190, 60) if frac > 0.25 else (230, 70, 70)
        if frac < 0.25 and int(self.tempo_restante * 4) % 2:
            cor = (255, 130, 130)
        barra = pygame.Rect(self.largura - 420, 12, 300, 20)
        pygame.draw.rect(self.tela, (40, 36, 60), barra, border_radius=6)
        pygame.draw.rect(self.tela, cor, (barra.x, barra.y, int(barra.w * frac), barra.h), border_radius=6)
        pygame.draw.rect(self.tela, (200, 200, 220), barra, 2, border_radius=6)
        self._texto(f"{max(0, int(self.tempo_restante + 0.99))}s", self.fonte_m, cor, topleft=(barra.right + 12, 10))
        self._texto(f"seed {self.semente}", self.fonte_p, (140, 140, 170), topleft=(self.largura - 110, self.altura - 26))

    def _painel(self, titulo, linha1="", linha2=""):
        veu = pygame.Surface((self.largura, self.altura), pygame.SRCALPHA)
        veu.fill((0, 0, 0, 150))
        self.tela.blit(veu, (0, 0))
        cx, cy = self.largura // 2, self.altura // 2
        self._texto(titulo, self.fonte_gg, (255, 214, 90), centro=(cx, cy - 50))
        if linha1:
            self._texto(linha1, self.fonte_m, (235, 235, 245), centro=(cx, cy + 20))
        if linha2:
            self._texto(linha2, self.fonte_g, (120, 220, 150), centro=(cx, cy + 80))

    def _desenhar_menu(self):
        self.tela.fill((22, 18, 38))
        cx = self.largura // 2
        self._texto(self.titulo.upper(), self.fonte_gg, (255, 214, 90), centro=(cx, 110))
        self._texto("Escape do labirinto antes que o tempo acabe!", self.fonte_m, (220, 220, 235), centro=(cx, 175))
        img = pygame.transform.scale(self._sprite_menu, (self._sprite_menu.get_width() * 3, self._sprite_menu.get_height() * 3))
        self.tela.blit(img, img.get_rect(center=(cx, 340)))
        if int(pygame.time.get_ticks() / 500) % 2 == 0:
            self._texto("Pressione ENTER para jogar", self.fonte_g, (120, 220, 150), centro=(cx, 500))
        self._texto("WASD / Setas: mover   P: pausar   L: luz   M: som   ESC: sair",
                    self.fonte_p, (150, 150, 180), centro=(cx, 560))
        self._texto(f"Recorde: fase {self.recorde}", self.fonte_m, (255, 214, 90), centro=(cx, 600))