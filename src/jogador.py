import pygame
import sys
from jogador import Jogador
from cenario import Cenario # Importa o arquivo que acabamos de criar

class Jogo:
    def __init__(self):
        self.largura_tela = 800
        self.altura_tela = 600
        self.tela = pygame.display.set_mode((self.largura_tela, self.altura_tela))
        pygame.display.set_caption("Marble Run: Procedural")
        
        self.clock = pygame.time.Clock()
        self.fonte = pygame.font.SysFont("Arial", 26, bold=True)
        self.tempo_limite = 45.0
        
        self.resetar_nivel()

    def resetar_nivel(self):
        self.tempo_restante = self.tempo_limite
        
        # 1. Instancia o gerador procedural do cenário
        # Criamos um labirinto de 19 colunas por 13 linhas (cabe na tela de 800x600 usando blocos de 40px)
        self.cenario = Cenario(colunas=19, linhas=13, tamanho_bloco=40)
        
        # 2. Instancia o jogador na posição de Spawn calculada pelo labirinto
        self.jogador = Jogador(self.cenario.spawn_pos[0], self.cenario.spawn_pos[1])
        
        self.todas_sprites = pygame.sprite.Group()
        self.todas_sprites.add(self.jogador)
        print("Novo labirinto gerado proceduralmente!")

    def gerenciar_eventos(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r: # Forçar recriação com a tecla R
                    self.resetar_nivel()

    def atualizar(self, dt):
        self.tempo_restante -= dt
        
        if self.tempo_restante <= 0:
            self.resetar_nivel()
            
        # Atualiza a posição do jogador passando a lista de paredes do cenário para futuras colisões
        self.todas_sprites.update(dt, self.cenario.paredes_rects)
        
        # CONDIÇÃO DE VITÓRIA: Se o lobo encostar no retângulo verde de saída
        if self.jogador.rect.colliderect(self.cenario.saida_rect):
            print("Você venceu! Avançando para o próximo labirinto aleatório...")
            self.resetar_nivel()

    def desenhar(self):
        # Fundo do labirinto (Caminho livre - Cor escura)
        self.tela.fill((25, 25, 30))
        
        # 1. Desenha o labirinto gerado
        self.cenario.desenhar(self.tela)
        
        # 2. Desenha o personagem por cima do cenário
        self.todas_sprites.draw(self.tela)
        
        # 3. Desenha a interface do cronômetro
        texto_tempo = self.fonte.render(f"Tempo: {max(0.0, self.tempo_restante):.1f}s", True, (255, 215, 0))
        self.tela.blit(texto_tempo, (20, 540)) # Posicionado na barra inferior livre
        
        pygame.display.flip()

    def rodar(self):
        while True:
            dt = self.clock.tick(60) / 1000.0
            self.gerenciar_eventos()
            self.atualizar(dt)
            self.desenhar()
