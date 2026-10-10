"""
main.py - Ponto de entrada e COMPOSITION ROOT do Marble Run.

Este e o unico lugar que conhece as classes CONCRETAS: aqui elas sao
criadas e ligadas umas as outras (injecao de dependencias pelo construtor).
O resto do codigo conversa apenas por abstracoes - ServicoAudio,
RepositorioDeRecorde, GeradorDeLabirinto, Controle, Estado, Clima...
Trocar uma peca (outro algoritmo de labirinto, salvar recorde na nuvem,
jogar com joystick) e mudar UMA linha aqui.

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

<<<<<<< HEAD
from marble_run.apresentacao.cena import FabricaDeCenas
from marble_run.apresentacao.entrada import ControleTeclado, MapaDeTeclas
from marble_run.apresentacao.interface import Hud, Painel, Tipografia
from marble_run.apresentacao.jogo import Aplicacao, Jogo
from marble_run.apresentacao.personagem import SpritesDoJogador
from marble_run.apresentacao.servicos import Preferencias, ServicosDoJogo
from marble_run.apresentacao.sonorizacao import RitmoDePassos, SonsDaPartida
from marble_run.apresentacao.temas import CatalogoDeTemas
from marble_run.dominio.geradores import GeradorBacktracker
from marble_run.dominio.partida import FabricaDeFases
from marble_run.dominio.regras import Dificuldade, Recorde
from marble_run.infraestrutura.audio import FabricaDeAudio
from marble_run.infraestrutura.persistencia import RecordeEmArquivo
from marble_run.infraestrutura.recursos import LocalizadorDeRecursos
=======
# Configurar o audio ANTES do pygame.init() evita atraso nos sons
pygame.mixer.pre_init(22050, -16, 1, 512)
pygame.init()

# Agora o Python é forçado a ler os arquivos corretos da pasta src/
from jogo import Jogo  # noqa: E402
from song import GerenciadorSom  # noqa: E402
>>>>>>> a9e3d27584c4a1d0d0544cdf2043481107ee4d8c

LARGURA, ALTURA = 960, 640
FPS = 60
TITULO = "Marble Run"


def montar_jogo(tela: pygame.Surface) -> Jogo:
    """Monta o grafo de objetos do jogo (Composition Root)."""
    recursos = LocalizadorDeRecursos.detectar()
    tamanho = tela.get_size()

    # Infraestrutura: detalhes tecnicos escondidos atras de contratos
    audio = FabricaDeAudio.criar(recursos.pasta_sons)  # AudioPygame ou AudioMudo
    recorde = Recorde(RecordeEmArquivo(recursos.arquivo_recorde))

    # Dominio: regras puras, montadas por composicao
    temas = CatalogoDeTemas.padrao()
    fases = FabricaDeFases(GeradorBacktracker(), Dificuldade(), temas.nomes)

    # Apresentacao
    tipografia = Tipografia()
    sprites = SpritesDoJogador(recursos.pasta_sprites_jogador)
    servicos = ServicosDoJogo(
        titulo=TITULO,
        tipografia=tipografia,
        hud=Hud(tipografia, tamanho),
        painel=Painel(tipografia, tamanho),
        cenas=FabricaDeCenas(temas, sprites, tamanho),
        sprites=sprites,
        controle=ControleTeclado(),
        passos=RitmoDePassos(audio),
        recorde=recorde,
        preferencias=Preferencias(),
    )
    return Jogo(servicos, fases,
                ouvintes=(recorde, SonsDaPartida(audio)),  # Observers da partida
                audio=audio, teclas=MapaDeTeclas())


def main() -> None:
    FabricaDeAudio.pre_configurar()  # configurar o audio ANTES do pygame.init() evita atraso nos sons
    pygame.init()
    tela = pygame.display.set_mode((LARGURA, ALTURA))
    pygame.display.set_caption(TITULO)
<<<<<<< HEAD
    pygame.event.pump()  # correcao para Linux (Fedora / Wayland)
=======
    
    # -------------------------------------------------------------------------
    # CORREÇÃO PARA LINUX (FEDORA / WAYLAND):
    pygame.event.pump()
>>>>>>> a9e3d27584c4a1d0d0544cdf2043481107ee4d8c
    pygame.display.flip()

<<<<<<< HEAD
    Aplicacao(montar_jogo(tela), tela, FPS).executar()
=======
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
>>>>>>> a9e3d27584c4a1d0d0544cdf2043481107ee4d8c

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
