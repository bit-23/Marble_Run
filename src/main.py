<<<<<<< HEAD
=======
"""
main.py - Inicializador do jogo.

Como rodar (dentro da pasta src):
    python main.py
"""
import sys

>>>>>>> e6da2966a95a738576107d65d58c81b13366afd2
import pygame
import pygame.mixer

<<<<<<< HEAD
#inicializando o pygame
print("Iniciando o jogo...\n{}".format(print(pygame.version.ver)))

#nome do jogo
pygame.display.set_caption("Marble Run")

tela = pygame.display.set_mode((800, 600))

tela=True
while tela:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            tela = False
pygame.init()
=======
# Configurar o audio ANTES do pygame.init() evita atraso nos sons
pygame.mixer.pre_init(22050, -16, 1, 512)
pygame.init()

from jogo import Jogo          # noqa: E402  (importado depois do init de proposito)
from song import GerenciadorSom  # noqa: E402

LARGURA, ALTURA = 960, 640
FPS = 60
TITULO = "Marble Run"


def main():
    tela = pygame.display.set_mode((LARGURA, ALTURA))
    pygame.display.set_caption(TITULO)
    
    # -------------------------------------------------------------------------
    # CORREÇÃO PARA LINUX (FEDORA / WAYLAND):
    # Força o sistema operacional a validar o contexto gráfico da janela.
    # Sem isso, carregar imagens logo em seguida gera 'Parameter surface is invalid'.
    pygame.event.pump()
    pygame.display.flip()
    # -------------------------------------------------------------------------

    relogio = pygame.time.Clock()

    som = GerenciadorSom()
    jogo = Jogo(tela, som, TITULO)

    while not jogo.sair:
        dt = min(relogio.tick(FPS) / 1000.0, 0.05)  # limita dt p/ nao "atravessar" paredes em lag

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                jogo.sair = True
            else:
                jogo.processar_evento(evento)

        jogo.atualizar(dt)
        jogo.desenhar()
        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
>>>>>>> e6da2966a95a738576107d65d58c81b13366afd2
