"""
personagem.py - Como o personagem (cachorro de cartola) aparece na tela.

Os sprites ficam em  assets/images/jogador/ :
    baixo_0..7.png  cima_0..7.png  direita_0..7.png  esquerda_0..7.png  parado.png

Antes os sprites eram um cache em atributo de CLASSE do Jogador (estado
global escondido) e o Jogador se desenhava sozinho. Agora:
* SpritesDoJogador carrega as imagens UMA vez e e injetado onde precisar;
* AnimacaoDoJogador escolhe o quadro e desenha, lendo o Jogador do dominio
  apenas pelas suas propriedades publicas.
"""
from __future__ import annotations

from pathlib import Path

import pygame

from ..dominio.jogador import Direcao, Jogador

Deslocamento = tuple[int, int]  # canto superior esquerdo da camera, em pixels do mapa


class SpritesDoJogador:
    QUADROS_POR_DIRECAO = 8
    # Altura (em pixels na tela) de cada animacao. Os desenhos de lado sao maiores
    # que os de frente/costas, entao ajustamos para o cachorro parecer do mesmo tamanho.
    ALTURAS = {Direcao.BAIXO: 58, Direcao.CIMA: 58, Direcao.DIREITA: 70, Direcao.ESQUERDA: 70}

    def __init__(self, pasta: Path) -> None:
        self._pasta = pasta
        self._quadros = {
            direcao: tuple(self._carregar(f"{direcao.value}_{i}.png", altura)
                           for i in range(self.QUADROS_POR_DIRECAO))
            for direcao, altura in self.ALTURAS.items()
        }
        self._parado = self._carregar("parado.png", self.ALTURAS[Direcao.BAIXO])

    @property
    def parado(self) -> pygame.Surface:
        return self._parado

    def quadro(self, direcao: Direcao, indice: int) -> pygame.Surface:
        return self._quadros[direcao][indice % self.QUADROS_POR_DIRECAO]

    def _carregar(self, nome: str, altura: int) -> pygame.Surface:
        caminho = self._pasta / nome
        if not caminho.exists():
            return self._substituto(altura)  # sem o arquivo, o jogo roda com uma bolinha
        try:
            bruta = pygame.image.load(str(caminho))
            # copia limpa em memoria: evita superficies invalidas no Linux/Windows
            img = pygame.Surface(bruta.get_size(), pygame.SRCALPHA)
            img.blit(bruta, (0, 0))
            try:
                img = img.convert_alpha()
            except pygame.error:
                pass
            largura = max(1, round(img.get_width() * altura / img.get_height()))
            return pygame.transform.scale(img, (largura, altura))
        except pygame.error:
            print(f"\n[ERRO DO PYGAME] Falha critica ao processar a imagem: {nome}")
            print(f"Caminho completo tentado: {caminho}")
            raise

    @staticmethod
    def _substituto(altura: int) -> pygame.Surface:
        s = pygame.Surface((32, altura), pygame.SRCALPHA)
        pygame.draw.circle(s, (0, 180, 255), (16, altura // 2), 14)
        return s


class AnimacaoDoJogador:
    QUADROS_POR_SEGUNDO = 12

    def __init__(self, sprites: SpritesDoJogador) -> None:
        self._sprites = sprites
        self._tempo = 0.0
        self._sombra = pygame.Surface((30, 10), pygame.SRCALPHA)
        pygame.draw.ellipse(self._sombra, (0, 0, 0, 90), self._sombra.get_rect())

    def atualizar(self, dt: float, andando: bool) -> None:
        self._tempo = self._tempo + dt * self.QUADROS_POR_SEGUNDO if andando else 0.0

    def imagem(self, jogador: Jogador) -> pygame.Surface:
        if not jogador.esta_andando and jogador.direcao is Direcao.BAIXO:
            return self._sprites.parado
        return self._sprites.quadro(jogador.direcao, int(self._tempo))

    def desenhar(self, tela: pygame.Surface, jogador: Jogador, camera: Deslocamento) -> None:
        img = self.imagem(jogador)
        pos = img.get_rect(midbottom=(round(jogador.x) - camera[0], round(jogador.y) - camera[1] + 2))
        tela.blit(self._sombra, self._sombra.get_rect(midbottom=(pos.centerx, pos.bottom + 2)))
        tela.blit(img, pos)
