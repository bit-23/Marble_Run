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
import sys

import pygame

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
    pygame.event.pump()  # correcao para Linux (Fedora / Wayland)
    pygame.display.flip()

    Aplicacao(montar_jogo(tela), tela, FPS).executar()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()