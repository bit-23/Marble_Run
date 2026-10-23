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

import math
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
    GIROS_POR_SEGUNDO = 14  # deslizando no gelo: gira olhando para todos os lados
    ALTURA_DO_PULO = 46     # pixels do ponto mais alto do arco da mola
    DURACAO_DO_IMPACTO = 0.16
    ORDEM_DO_GIRO = (Direcao.BAIXO, Direcao.ESQUERDA, Direcao.CIMA, Direcao.DIREITA)

    def __init__(self, sprites: SpritesDoJogador) -> None:
        self._sprites = sprites
        self._tempo = 0.0
        self._tempo_ambiente = 0.0
        self._giro = 0.0
        self._girando = False
        self._impacto = 0.0
        self._bateu_anteriormente = False
        self._sombra = pygame.Surface((30, 10), pygame.SRCALPHA)
        pygame.draw.ellipse(self._sombra, (0, 0, 0, 90), self._sombra.get_rect())

    def atualizar(self, dt: float, andando: bool, girando: bool = False,
                  bateu: bool = False) -> None:
        dt = max(0.0, dt)
        self._tempo_ambiente += dt
        self._tempo = self._tempo + dt * self.QUADROS_POR_SEGUNDO if andando else 0.0
        self._girando = girando
        self._giro = self._giro + dt * self.GIROS_POR_SEGUNDO if girando else 0.0
        self._impacto = max(0.0, self._impacto - dt)
        if bateu and not self._bateu_anterior:
            self._impacto = self.DURACAO_DO_IMPACTO
        self._bateu_anterior = bateu

    def imagem(self, jogador: Jogador) -> pygame.Surface:
        if self._girando:
            return self._sprites.quadro(self.ORDEM_DO_GIRO[int(self._giro) % 4], 0)
        if not jogador.esta_andando and jogador.direcao is Direcao.BAIXO:
            return self._sprites.parado
        return self._sprites.quadro(jogador.direcao, int(self._tempo))

    def desenhar(self, tela: pygame.Surface, jogador: Jogador, camera: Deslocamento) -> None:
        img = self.imagem(jogador)
        altura = round(jogador.altura_do_salto * self.ALTURA_DO_PULO)
        chao = (round(jogador.x) - camera[0], round(jogador.y) - camera[1] + 2)

        escala_x = escala_y = 1.0
        levantar = 0.0
        if jogador.altura_do_salto > 0:
            # O cachorro se estica no ar e fica um pouco mais estreito no topo do salto.
            arco = jogador.altura_do_salto
            escala_x -= 0.035 * arco
            escala_y += 0.065 * arco
        elif jogador.esta_andando and not self._girando:
            # Um pequeno impulso acompanha a passada sem competir com os quadros existentes.
            passo = abs(math.sin(self._tempo * math.pi / 2))
            escala_x += 0.018 * passo
            escala_y -= 0.035 * passo
            levantar = passo * 1.5
        elif not self._girando:
            # Respiração lenta no repouso, também aplicada às poses viradas de lado.
            respiracao = (1 + math.sin(self._tempo_ambiente * 2.0)) / 2
            escala_x -= 0.006 * respiracao
            escala_y += 0.018 * respiracao
            levantar = respiracao * 0.7

        if self._impacto:
            impacto = self._impacto / self.DURACAO_DO_IMPACTO
            escala_x += 0.045 * impacto
            escala_y -= 0.07 * impacto

        if escala_x != 1.0 or escala_y != 1.0:
            tamanho = (max(1, round(img.get_width() * escala_x)),
                       max(1, round(img.get_height() * escala_y)))
            img = pygame.transform.scale(img, tamanho)

        sombra = self._sombra
        if altura:  # no ar: sombra menor la embaixo
            k = 1 - 0.5 * jogador.altura_do_salto
            sombra = pygame.transform.scale(self._sombra, (round(30 * k), round(10 * k)))
        tela.blit(sombra, sombra.get_rect(midbottom=(chao[0], chao[1] + 2)))
        tela.blit(img, img.get_rect(midbottom=(chao[0], chao[1] - altura - round(levantar))))
