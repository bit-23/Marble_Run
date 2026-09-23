"""
cenario.py - O labirinto na tela.

A classe Cenario recebe uma "grade" (lista de listas com 1 = parede e
0 = chao) gerada em jogo.py e cuida de:
  * desenhar o labirinto (so os tiles visiveis na camera);
  * responder colisoes (o jogador usa `colide(rect)`);
  * desenhar o portal de saida e o ponto de entrada.
"""
import math
import random

import pygame

TILE = 56  # tamanho de cada quadrado do labirinto, em pixels


class Cenario:
    def __init__(self, grade, entrada, saida, tile=TILE):
        self.grade = grade
        self.linhas = len(grade)
        self.colunas = len(grade[0])
        self.entrada = entrada  # (coluna, linha) em tiles
        self.saida = saida      # (coluna, linha) em tiles
        self.tile = tile
        self.largura = self.colunas * tile
        self.altura = self.linhas * tile
        self.tempo = 0.0
        self._criar_superficies()

    # ------------------------------------------------------------------
    # Construcao das imagens (feitas por codigo, nao precisa de assets)
    # ------------------------------------------------------------------
    def _criar_superficies(self):
        t = self.tile
        rng = random.Random(7)

        # Pisos: 4 variacoes com "pontinhos" para nao ficar monotono
        self.pisos = []
        for base in ((46, 42, 64), (50, 46, 70), (44, 40, 60), (48, 44, 66)):
            s = pygame.Surface((t, t))
            s.fill(base)
            for _ in range(10):
                x, y = rng.randrange(t), rng.randrange(t)
                c = tuple(max(0, v - 10) for v in base)
                s.set_at((x, y), c)
                s.set_at((min(t - 1, x + 1), y), c)
            pygame.draw.rect(s, tuple(max(0, v - 8) for v in base), (0, 0, t, t), 1)
            self.pisos.append(s)

        # Parede (vista de cima) e parede com "face" (quando ha chao abaixo)
        self.parede = self._tijolos((96, 88, 134), (70, 63, 102))
        self.parede_face = self._tijolos((96, 88, 134), (70, 63, 102))
        face = pygame.Rect(0, t - 18, t, 18)
        pygame.draw.rect(self.parede_face, (56, 50, 84), face)
        pygame.draw.line(self.parede_face, (130, 122, 168), (0, t - 18), (t, t - 18), 2)
        for x in range(0, t, 14):
            pygame.draw.line(self.parede_face, (40, 35, 64), (x, t - 18), (x, t), 1)

        # Brilho do portal de saida (gradiente radial)
        raio = int(t * 2.2)
        self.brilho = pygame.Surface((raio * 2, raio * 2))
        for r in range(raio, 0, -2):
            k = (1 - r / raio) ** 2
            cor = (int(255 * k), int(200 * k), int(70 * k))
            pygame.draw.circle(self.brilho, cor, (raio, raio), r)

    def _tijolos(self, cor, junta):
        t = self.tile
        s = pygame.Surface((t, t))
        s.fill(cor)
        for i, y in enumerate(range(0, t, 14)):
            pygame.draw.line(s, junta, (0, y), (t, y), 2)
            for x in range((i % 2) * 14, t, 28):
                pygame.draw.line(s, junta, (x, y), (x, y + 14), 2)
        return s

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------
    def eh_parede(self, col, lin):
        if col < 0 or lin < 0 or col >= self.colunas or lin >= self.linhas:
            return True
        return self.grade[lin][col] == 1

    def colide(self, rect):
        """True se o retangulo (em pixels do mapa) encosta em alguma parede."""
        t = self.tile
        for lin in range(rect.top // t, (rect.bottom - 1) // t + 1):
            for col in range(rect.left // t, (rect.right - 1) // t + 1):
                if self.eh_parede(col, lin):
                    return True
        return False

    def centro_tile(self, tile):
        col, lin = tile
        return col * self.tile + self.tile // 2, lin * self.tile + self.tile // 2

    def rect_saida(self):
        """Area do portal (um pouco menor que o tile, para nao ser 'injusto')."""
        cx, cy = self.centro_tile(self.saida)
        r = pygame.Rect(0, 0, self.tile - 16, self.tile - 16)
        r.center = (cx, cy)
        return r

    # ------------------------------------------------------------------
    # Atualizacao / desenho
    # ------------------------------------------------------------------
    def atualizar(self, dt):
        self.tempo += dt

    def desenhar(self, tela, cam_x, cam_y):
        t = self.tile
        c0 = max(0, cam_x // t)
        c1 = min(self.colunas, (cam_x + tela.get_width()) // t + 2)
        l0 = max(0, cam_y // t)
        l1 = min(self.linhas, (cam_y + tela.get_height()) // t + 2)

        for lin in range(l0, l1):
            for col in range(c0, c1):
                x, y = col * t - cam_x, lin * t - cam_y
                if self.grade[lin][col] == 1:
                    abaixo_livre = not self.eh_parede(col, lin + 1)
                    tela.blit(self.parede_face if abaixo_livre else self.parede, (x, y))
                else:
                    tela.blit(self.pisos[(col * 7 + lin * 13) % 4], (x, y))

        self._desenhar_entrada(tela, cam_x, cam_y)
        self._desenhar_portal(tela, cam_x, cam_y)

    def _desenhar_entrada(self, tela, cam_x, cam_y):
        cx, cy = self.centro_tile(self.entrada)
        pygame.draw.circle(tela, (60, 140, 90), (cx - cam_x, cy - cam_y), self.tile // 2 - 8, 2)

    def _desenhar_portal(self, tela, cam_x, cam_y):
        cx, cy = self.centro_tile(self.saida)
        cx, cy = cx - cam_x, cy - cam_y
        pulso = 0.5 + 0.5 * math.sin(self.tempo * 4)
        r = int(self.tile * (0.30 + 0.06 * pulso))
        pygame.draw.circle(tela, (255, 214, 90), (cx, cy), r + 6, 3)
        pygame.draw.circle(tela, (255, 240, 170), (cx, cy), r)
        pygame.draw.circle(tela, (255, 255, 255), (cx, cy), max(2, r // 2))

    def desenhar_brilho_saida(self, tela, cam_x, cam_y):
        """Halo dourado desenhado POR CIMA da escuridao: serve de farol."""
        cx, cy = self.centro_tile(self.saida)
        pulso = 0.75 + 0.25 * math.sin(self.tempo * 3)
        img = self.brilho
        if pulso < 0.99:
            img = self.brilho.copy()
            img.fill((int(255 * pulso),) * 3, special_flags=pygame.BLEND_RGB_MULT)
        r = self.brilho.get_width() // 2
        tela.blit(img, (cx - cam_x - r, cy - cam_y - r), special_flags=pygame.BLEND_RGB_ADD)