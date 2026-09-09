import pygame

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
