"""
cena.py - Tudo o que se ve de UMA fase.

    Cena = Cenario (labirinto + tema + clima)
         + AnimacaoDoJogador
         + Camera
         + Escuridao

Composicao: a Cena nao herda de ninguem; ela junta objetos pequenos, cada
um com uma responsabilidade. Antes tudo isso vivia dentro de Jogo e Cenario.
Os estados Jogando, Pausado, Vitoria e Derrota compartilham a mesma Cena.
"""
from __future__ import annotations

import math

import pygame

from ..dominio.labirinto import Labirinto
from ..dominio.partida import Fase
from .personagem import AnimacaoDoJogador, SpritesDoJogador
from .temas import CatalogoDeTemas, Tema

Deslocamento = tuple[int, int]  # canto superior esquerdo da camera, em pixels do mapa
BRANCO = (255, 255, 255)


class Camera:
    """Decide qual pedaco do mapa aparece na tela (segue o jogador)."""

    def __init__(self, largura_tela: int, altura_tela: int) -> None:
        self._largura_tela = largura_tela
        self._altura_tela = altura_tela
        self._x = 0
        self._y = 0

    @property
    def deslocamento(self) -> Deslocamento:
        return self._x, self._y

    def enquadrar(self, alvo_x: float, alvo_y: float, largura_mapa: int, altura_mapa: int) -> None:
        self._x = self._eixo(alvo_x, self._largura_tela, largura_mapa)
        self._y = self._eixo(alvo_y, self._altura_tela, altura_mapa)

    @staticmethod
    def _eixo(alvo: float, tela: int, mapa: int) -> int:
        if mapa <= tela:  # mapa menor que a tela: centraliza
            return -(tela - mapa) // 2
        return max(0, min(round(alvo) - tela // 2, mapa - tela))  # senao, nao passa da borda


class Escuridao:
    """Veu escuro com um 'buraco' de luz em volta do jogador."""

    OPACIDADE = 235

    def __init__(self, tamanho_tela: tuple[int, int], raio: float) -> None:
        self._veu = pygame.Surface(tamanho_tela, pygame.SRCALPHA)
        self._luz = self._criar_luz(int(raio))

    def desenhar(self, tela: pygame.Surface, centro: tuple[int, int]) -> None:
        self._veu.fill((0, 0, 0, self.OPACIDADE))
        r = self._luz.get_width() // 2
        self._veu.blit(self._luz, (centro[0] - r, centro[1] - r), special_flags=pygame.BLEND_RGBA_SUB)
        tela.blit(self._veu, (0, 0))

    @classmethod
    def _criar_luz(cls, raio: int) -> pygame.Surface:
        luz = pygame.Surface((raio * 2, raio * 2), pygame.SRCALPHA)
        for r in range(raio, 0, -2):
            k = min(1.0, (1 - r / raio) * 1.6) ** 0.9
            pygame.draw.circle(luz, (0, 0, 0, int(cls.OPACIDADE * k)), (raio, raio), r)
        return luz


class Cenario:
    """Desenha um Labirinto com a pele de um Tema.

    Guarda so estado VISUAL (relogio das animacoes e o clima). As regras
    (paredes, colisao, saida) continuam no Labirinto do dominio.
    """

    def __init__(self, labirinto: Labirinto, tema: Tema) -> None:
        self._labirinto = labirinto
        self._paleta = tema.paleta
        self._texturas = tema.texturas(labirinto.tamanho_tile)
        self._clima = tema.criar_clima()
        self._tempo = 0.0

    @property
    def cor_de_fundo(self) -> tuple[int, int, int]:
        return self._paleta.fundo

    def atualizar(self, dt: float) -> None:
        self._tempo += dt
        self._clima.atualizar(dt)

    def desenhar(self, tela: pygame.Surface, camera: Deslocamento) -> None:
        lab, t = self._labirinto, self._labirinto.tamanho_tile
        cam_x, cam_y = camera
        c0 = max(0, cam_x // t)
        c1 = min(lab.colunas, (cam_x + tela.get_width()) // t + 2)
        l0 = max(0, cam_y // t)
        l1 = min(lab.linhas, (cam_y + tela.get_height()) // t + 2)

        for linha in range(l0, l1):
            for coluna in range(c0, c1):
                pos = (coluna * t - cam_x, linha * t - cam_y)
                if lab.eh_parede(coluna, linha):
                    com_face = not lab.eh_parede(coluna, linha + 1)  # chao logo abaixo
                    tela.blit(self._texturas.parede_face if com_face else self._texturas.parede, pos)
                else:
                    tela.blit(self._texturas.pisos[(coluna * 7 + linha * 13) % 4], pos)

        self._desenhar_entrada(tela, camera)
        self._desenhar_portal(tela, camera)

    def desenhar_brilho_da_saida(self, tela: pygame.Surface, camera: Deslocamento) -> None:
        """Halo do portal desenhado POR CIMA da escuridao: serve de farol."""
        cx, cy = self._labirinto.centro_do_tile(self._labirinto.saida)
        pulso = 0.75 + 0.25 * math.sin(self._tempo * 3)
        img = self._texturas.brilho
        if pulso < 0.99:
            img = img.copy()
            img.fill((int(255 * pulso),) * 3, special_flags=pygame.BLEND_RGB_MULT)
        r = self._texturas.brilho.get_width() // 2
        tela.blit(img, (cx - camera[0] - r, cy - camera[1] - r), special_flags=pygame.BLEND_RGB_ADD)

    def desenhar_clima(self, tela: pygame.Surface, camera: Deslocamento) -> None:
        self._clima.desenhar(tela, camera)

    def _desenhar_entrada(self, tela: pygame.Surface, camera: Deslocamento) -> None:
        cx, cy = self._labirinto.centro_do_tile(self._labirinto.entrada)
        t = self._labirinto.tamanho_tile
        pygame.draw.circle(tela, self._paleta.entrada, (cx - camera[0], cy - camera[1]), t // 2 - 8, 2)

    def _desenhar_portal(self, tela: pygame.Surface, camera: Deslocamento) -> None:
        cx, cy = self._labirinto.centro_do_tile(self._labirinto.saida)
        cx, cy = cx - camera[0], cy - camera[1]
        pulso = 0.5 + 0.5 * math.sin(self._tempo * 4)
        r = int(self._labirinto.tamanho_tile * (0.30 + 0.06 * pulso))
        pygame.draw.circle(tela, self._paleta.portal_aro, (cx, cy), r + 6, 3)
        pygame.draw.circle(tela, self._paleta.portal_miolo, (cx, cy), r)
        pygame.draw.circle(tela, BRANCO, (cx, cy), max(2, r // 2))


class Cena:
    ALTURA_DA_LUZ = 20  # a luz fica na altura do rosto, nao dos pes

    def __init__(self, fase: Fase, cenario: Cenario, animacao: AnimacaoDoJogador,
                 camera: Camera, escuridao: Escuridao) -> None:
        self._fase = fase
        self._cenario = cenario
        self._animacao = animacao
        self._camera = camera
        self._escuridao = escuridao
        self.enquadrar()

    def animar_ambiente(self, dt: float) -> None:
        """Portal pulsando, neve caindo... (continua ate na tela de vitoria)."""
        self._cenario.atualizar(dt)

    def animar_jogador(self, dt: float) -> None:
        self._animacao.atualizar(dt, self._fase.jogador.esta_andando)

    def enquadrar(self) -> None:
        jogador, labirinto = self._fase.jogador, self._fase.labirinto
        self._camera.enquadrar(jogador.x, jogador.y, labirinto.largura, labirinto.altura)

    def desenhar(self, tela: pygame.Surface, com_escuridao: bool) -> None:
        camera = self._camera.deslocamento
        jogador = self._fase.jogador
        tela.fill(self._cenario.cor_de_fundo)
        self._cenario.desenhar(tela, camera)
        self._animacao.desenhar(tela, jogador, camera)
        if com_escuridao:
            centro = (round(jogador.x) - camera[0], round(jogador.y) - camera[1] - self.ALTURA_DA_LUZ)
            self._escuridao.desenhar(tela, centro)
            self._cenario.desenhar_brilho_da_saida(tela, camera)
        self._cenario.desenhar_clima(tela, camera)


class FabricaDeCenas:
    """Factory: monta a Cena de uma Fase com o tema sorteado pelo dominio."""

    def __init__(self, temas: CatalogoDeTemas, sprites: SpritesDoJogador, tamanho_tela: tuple[int, int]) -> None:
        self._temas = temas
        self._sprites = sprites
        self._tamanho_tela = tamanho_tela

    def criar(self, fase: Fase) -> Cena:
        labirinto = fase.labirinto
        return Cena(
            fase,
            Cenario(labirinto, self._temas.obter(fase.tema)),
            AnimacaoDoJogador(self._sprites),
            Camera(*self._tamanho_tela),
            Escuridao(self._tamanho_tela, fase.raio_visao * labirinto.tamanho_tile),
        )
