"""
main.py - Inicializador do jogo.

Como rodar (dentro da pasta src):
    python main.py
"""
import os
import sys

# 1. Isola completamente o Python para olhar APENAS a pasta src/
diretorio_src = os.path.dirname(os.path.abspath(__file__))
diretorio_raiz = os.path.dirname(diretorio_src)

# Remove caminhos conflitantes da busca do Python
for caminho in [diretorio_raiz, "", "."]:
    if caminho in sys.path:
        sys.path.remove(caminho)

# Insere a pasta src na primeira posição de busca absoluta
if diretorio_src not in sys.path:
    sys.path.insert(0, diretorio_src)

# 2. SEGREDO DO ERRO: Se existir um arquivo 'song.py' intruso na raiz, deleta ele
arquivo_conflito = os.path.join(diretorio_raiz, "song.py")
if os.path.exists(arquivo_conflito):
    try:
        os.remove(arquivo_conflito)
    except OSError:
        pass

import pygame
import pygame.mixer

# Configurar o audio ANTES do pygame.init() evita atraso nos sons
pygame.mixer.pre_init(22050, -16, 1, 512)
pygame.init()

# Agora o Python é forçado a ler os arquivos corretos da pasta src/
from jogo import Jogo  # noqa: E402
from song import GerenciadorSom  # noqa: E402

LARGURA, ALTURA = 960, 640
FPS = 60
TITULO = "Marble Run"


def main():
    tela = pygame.display.set_mode((LARGURA, ALTURA))
    pygame.display.set_caption(TITULO)
    
    # -------------------------------------------------------------------------
    # CORREÇÃO PARA LINUX (FEDORA / WAYLAND):
    pygame.event.pump()
    pygame.display.flip()
    # -------------------------------------------------------------------------

    relogio = pygame.time.Clock()

    som = GerenciadorSom()
    som.iniciar_musica()  # Inicia a trilha sonora gerada proceduralmente do seu song.py
    jogo = Jogo(tela, som, TITULO)

    while not jogo.sair:
        dt = min(relogio.tick(FPS) / 1000.0, 0.05)

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
