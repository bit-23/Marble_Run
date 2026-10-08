"""
jogador.py - O personagem (cachorro de cartola): movimento, colisao e sprites.

Os sprites ficam em  assets/images/jogador/  com os nomes gerados por
tools/preparar_sprites.py:
    baixo_0..7.png  cima_0..7.png  direita_0..7.png  esquerda_0..7.png  parado.png
"""
import os
from pathlib import Path
import pygame

# Localiza dinamicamente a pasta assets na raiz do projeto (uma acima de src)
PASTA_SRC = Path(__file__).resolve().parent
PASTA_SPRITES = PASTA_SRC.parent / "assets" / "images" / "jogador"

# Caso seus assets estejam por engano dentro da pasta src/, este fallback garante que funcione:
if not PASTA_SPRITES.exists() and (PASTA_SRC / "assets").exists():
    PASTA_SPRITES = PASTA_SRC / "assets" / "images" / "jogador"

DIRECOES = ("baixo", "cima", "direita", "esquerda")
FRAMES_POR_DIRECAO = 8
FPS_ANIMACAO = 12          # frames de animacao por segundo
VELOCIDADE = 210           # pixels por segundo

# Altura (em pixels na tela) de cada animacao. Os desenhos de lado sao maiores
# que os de frente/costas, entao ajustamos para o cachorro parecer do mesmo tamanho.
ALTURAS = {"baixo": 58, "cima": 58, "direita": 70, "esquerda": 70}

# Hitbox (pes do personagem) - menor que o desenho, para passar folgado nos corredores
HB_LARGURA = 26
HB_ALTURA = 16

def _carregar(nome, altura):
    """Carrega uma imagem isolada e resolve problemas de superfícies inválidas no Linux/Windows."""
    caminho_arquivo = PASTA_SPRITES / nome
    
    # Se o arquivo físico de imagem real não existir, gera um sprite temporário estilizado 
    # para evitar que o seu jogo trave com FileNotFoundError!
    if not caminho_arquivo.exists():
        s = pygame.Surface((32, altura), pygame.SRCALPHA)
        pygame.draw.circle(s, (0, 180, 255), (16, altura // 2), 14)
        return s

    try:
        # 2. Carrega o arquivo do disco
        img_bruta = pygame.image.load(str(caminho_arquivo))
        
        # 3. Força a criação de uma cópia limpa na memória RAM do Python.
        largura_original, altura_original = img_bruta.get_size()
        img = pygame.Surface((largura_original, altura_original), pygame.SRCALPHA)
        img.blit(img_bruta, (0, 0))
        
        try:
            img = img.convert_alpha()
        except pygame.error:
            pass
            
        # 5. Faz o redimensionamento matemático
        largura = max(1, round(img.get_width() * altura / img.get_height()))
        return pygame.transform.scale(img, (largura, altura))
        
    except pygame.error as e:
        print(f"\n[ERRO DO PYGAME] Falha crítica ao processar a imagem: {nome}")
        print(f"Caminho completo tentado: {caminho_arquivo}")
        raise e


class Jogador:
    _sprites = None  # cache compartilhado: carrega do disco so uma vez

    @classmethod
    def carregar_sprites(cls):
        """Carrega e armazena os sprites na memória de forma estrita apenas sob demanda."""
        if cls._sprites is None:
            cls._sprites = {}
            for d in DIRECOES:
                cls._sprites[d] = [_carregar(f"{d}_{i}.png", ALTURAS[d]) for i in range(FRAMES_POR_DIRECAO)]
            cls._sprites["parado"] = _carregar("parado.png", ALTURAS["baixo"])
        return cls._sprites

    def __init__(self, x, y):
        """(x, y) = posicao dos PES do personagem, em pixels do mapa."""
        self.x = float(x)
        self.y = float(y)
        self.direcao = "baixo"
        self.andando = False
        self.tempo_anim = 0.0

    @property
    def sprites(self):
        """Acesso dinâmico e seguro aos sprites carregados em tempo de execução."""
        return self.carregar_sprites()

    # ------------------------------------------------------------------
    def rect(self):
        r = pygame.Rect(0, 0, HB_LARGURA, HB_ALTURA)
        r.midbottom = (round(self.x), round(self.y))
        return r

    def _ler_teclas(self, teclas):
        dx = int(teclas[pygame.K_RIGHT] or teclas[pygame.K_d]) - int(teclas[pygame.K_LEFT] or teclas[pygame.K_a])
        dy = int(teclas[pygame.K_DOWN] or teclas[pygame.K_s]) - int(teclas[pygame.K_UP] or teclas[pygame.K_w])
        return dx, dy

    def _escolher_direcao(self, dx, dy):
        horizontal = "direita" if dx > 0 else "esquerda"
        vertical = "baixo" if dy > 0 else "cima"
        if dx and not dy:
            self.direcao = horizontal
        elif dy and not dx:
            self.direcao = vertical
        elif dx and dy and self.direcao not in (horizontal, vertical):
            self.direcao = horizontal

    def _mover_eixo(self, delta, eixo, cenario):
        """Anda `delta` pixels em um eixo, parando (encostando) na parede."""
        passo = 1.0 if delta > 0 else -1.0
        restante = abs(delta)
        while restante > 0:
            p = passo * min(1.0, restante)
            if eixo == "x":
                self.x += p
            else:
                self.y += p
            if cenario.colide(self.rect()):
                if eixo == "x":
                    self.x -= p
                else:
                    self.y -= p
                return
            restante -= 1.0

    def atualizar(self, dt, cenario, teclas=None):
        if teclas is None:
            teclas = pygame.key.get_pressed()
        dx, dy = self._ler_teclas(teclas)
        self.andando = bool(dx or dy)

        if self.andando:
            self._escolher_direcao(dx, dy)
            norma = (dx * dx + dy * dy) ** 0.5  # diagonal nao pode ser mais rapida
            self._mover_eixo(dx / norma * VELOCIDADE * dt, "x", cenario)
            self._mover_eixo(dy / norma * VELOCIDADE * dt, "y", cenario)
            self.tempo_anim += dt * FPS_ANIMACAO
        else:
            self.tempo_anim = 0.0

    # ------------------------------------------------------------------
    def imagem_atual(self):
        if not self.andando and self.direcao == "baixo":
            return self.sprites["parado"]
        quadro = int(self.tempo_anim) % FRAMES_POR_DIRECAO
        return self.sprites[self.direcao][quadro]

    def desenhar(self, tela, camera):
        # Desempacota a tupla da câmera se ela for passada junta para evitar erro de assinatura
        if isinstance(camera, tuple):
            cam_x, cam_y = camera
        else:
            cam_x = camera
            cam_y = arguments[2] # Fallback de segurança se chamar individualmente
            
        img = self.imagem_atual()
        pos = img.get_rect(midbottom=(round(self.x) - cam_x, round(self.y) - cam_y + 2))
        
        # Sombrinha ellipse no chão abaixo do cachorro
        sombra = pygame.Surface((30, 10), pygame.SRCALPHA)
        pygame.draw.ellipse(sombra, (0, 0, 0, 90), sombra.get_rect())
        tela.blit(sombra, sombra.get_rect(midbottom=(pos.centerx, pos.bottom + 2)))
        tela.blit(img, pos)
