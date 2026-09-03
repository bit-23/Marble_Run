# inisializando a janela do jogo

import pygame

pygame.init()

tela=pygame.display.set_mode((800,600))

AZUL=(0,225,0)
VERDE=(0,225,225)
BRANCO=(225,225,225)

rodando=True

while rodando:
    for evento in pygame.event.get():
        if evento.type==pygame.QUIT:
            rodando=False
    tela.fill(AZUL)
    pygame.draw.rect(tela,VERDE,(200,200,200,200))
    pygame.draw.circle(tela,BRANCO,(400,300),120)
    pygame.draw.line(tela,BRANCO,(100,100),(200,200),3)
    pygame.display.flip()

pygame.quit()