import pygame
from jogo import Jogo

def main():
    # Inicializa os componentes principais do Pygame-CE (Áudio, Fontes, Vídeo)
    pygame.init()
    
    # Cria a instância do jogo e inicia o loop principal
    meu_jogo = Jogo()
    meu_jogo.rodar()

if __name__ == "__main__":
    main()
