"""
monstros.py - Os monstros de cada mapa (so REGRAS; o desenho fica na apresentacao).

    masmorra -> Aranha (cospe teia)        | Minotauro (investida em linha reta)
    gelo     -> Boneco de Neve (raio gelo)  | Yeti (pisao que cria placas de gelo)
    fogo     -> Magman (rastro de lava)     | Fornalha (labareda em linha)
    vento    -> Aguia (rouba buff)          | Tornado (arremessa para longe do portal)
    terra    -> Toupeira (abre buracos)     | Golem (onda de choque; bloqueia corredores)
    deserto  -> Cobra (veneno)              | Mumia (laco que puxa; some na tempestade)

Todo ataque tem AVISO antes (estado AVISANDO), para o jogador conseguir reagir.
O monstro nao mexe no jogador diretamente: ele pede ao ContextoDosMonstros
(o Ambiente) para `golpear` ou `deixar_rastro`, e o Ambiente decide as
protecoes (estrela, blusa, bota, guarda-chuva, capacete, tapete...).
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import Callable, Protocol

from .caminhos import linha_de_visao, manhattan, proximo_passo, tiles_em_linha, vizinhos_livres
from .geometria import Caixa, Vetor2
from .jogador import Jogador
from .labirinto import Coordenada, Labirinto


class TipoDeMonstro(Enum):
    ARANHA = "aranha"
    MINOTAURO = "minotauro"
    BONECO_DE_NEVE = "boneco_de_neve"
    YETI = "yeti"
    MAGMAN = "magman"
    FORNALHA = "fornalha"
    AGUIA = "aguia"
    TORNADO = "tornado"
    TOUPEIRA = "toupeira"
    GOLEM = "golem"
    COBRA = "cobra"
    MUMIA = "mumia"


class Golpe(Enum):
    MORDIDA = auto()         # -1 coracao (e um empurraozinho)
    CHIFRADA = auto()        # -1 coracao + empurrao forte
    QUEIMADURA = auto()      # fogo: -1 coracao e corre sem controle (bota protege)
    CONGELAMENTO = auto()    # congela 2s (blusa protege)
    TEIA = auto()            # preso ate acertar as setas
    VENENO = auto()          # setas para se curar a tempo (tapete protege)
    ROUBO = auto()           # leva um buff ativo (guarda-chuva protege)
    ARREMESSO = auto()       # joga para longe do portal (guarda-chuva protege, pipa inverte)
    BURACO = auto()          # cai: -5s e fica parado (capacete protege)
    ONDA_DE_CHOQUE = auto()  # -1 coracao + controles invertidos (capacete protege)
    LACO = auto()            # puxa o jogador ate o monstro


class Rastro(Enum):
    """Perigos temporarios que os monstros deixam no chao."""

    LAVA = auto()
    TEIA = auto()
    GELO = auto()
    BURACO = auto()


class EstadoDoMonstro(Enum):
    ANDANDO = auto()
    AVISANDO = auto()    # se preparando para atacar (a tela mostra o aviso)
    ATACANDO = auto()
    ATORDOADO = auto()   # minotauro depois de bater na parede
    DORMINDO = auto()    # flauta
    ESCONDIDO = auto()   # magman mergulhado na lava
    APAGADO = auto()     # extintor: magman vira pedra, fornalha apaga


class ContextoDosMonstros(Protocol):
    """O que o monstro pode perguntar e pedir ao mundo (o Ambiente cumpre este contrato)."""

    @property
    def labirinto(self) -> Labirinto: ...

    @property
    def jogador(self) -> Jogador: ...

    @property
    def tile_do_jogador(self) -> Coordenada: ...

    @property
    def monstros_dormindo(self) -> bool: ...

    @property
    def luz_forte(self) -> bool: ...

    @property
    def forca_da_tempestade(self) -> float: ...

    def golpear(self, golpe: Golpe, monstro: Monstro) -> bool: ...

    def deixar_rastro(self, rastro: Rastro, tile: Coordenada, duracao: float) -> None: ...


@dataclass
class Projetil:
    """Bola de teia voando em linha reta."""

    x: float
    y: float
    dx: int
    dy: int


Escolha = Callable[["ContextoDosMonstros"], "Coordenada | None"]


class Monstro:
    """Base: patrulha o proprio TERRITORIO (perto de onde nasceu), ataca com aviso e machuca quem encosta.

    Ninguem fica grudado no jogador: quem caca (yeti, mumia) so caca de perto, dentro do territorio
    e por pouco tempo (FOLEGO); depois cansa e volta a patrulhar. Ao vagar, o monstro evita entrar
    no tile do jogador, para nao encurralar ninguem no corredor.
    """

    TIPO: TipoDeMonstro
    VELOCIDADE = 0.5            # fracao da velocidade do jogador
    LADO = 34                   # area de contato, em pixels
    LADO_SOLIDO = 0             # > 0 = o jogador nao atravessa (golem)
    RECARGA = 5.0               # segundos entre ataques
    RECARGA_INICIAL: tuple[float, float] | None = None  # None = entre 1.5s e RECARGA
    RECARGA_DO_CONTATO = 2.5
    GOLPE_DE_CONTATO: Golpe | None = Golpe.MORDIDA
    RAIO_DO_TERRITORIO = 5      # tiles (Manhattan) em volta de onde nasceu
    ALCANCE_DA_CACA = 0         # 0 = nunca persegue; > 0 = persegue quem chegar ate esta distancia
    FOLEGO = 3.0                # segundos perseguindo ...
    DESCANSO_DA_CACA = 5.0      # ... e depois desiste por este tempo
    VELOCIDADE_AGRESSIVO = 1.2  # dificil/insano: 20% mais rapidos

    def __init__(self, tile: Coordenada, labirinto: Labirinto, sorteio: random.Random,
                 agressivo: bool = False) -> None:
        self._lab = labirinto
        self._rng = sorteio
        self._agressivo = agressivo
        self._x, self._y = (float(v) for v in labirinto.centro_do_tile(tile))
        self._tile = tile
        self._casa = tile
        self._destino = tile
        self._anterior: Coordenada | None = None
        self._estado = EstadoDoMonstro.ANDANDO
        self._tempo_no_estado = 0.0
        self._duracao_do_estado = 0.0
        self._recarga = sorteio.uniform(*(self.RECARGA_INICIAL or (1.5, self.RECARGA)))  # nao atacam juntos
        self._recarga_contato = 0.0
        self._direcao = Vetor2(0, 1)
        self._passo_do_ataque = (0, 1)
        self._tiles_do_ataque: tuple[Coordenada, ...] = ()
        self._alvo: tuple[float, float] | None = None
        self._folego = self.FOLEGO
        self._descanso_da_caca = 0.0
        self._cacando = False

    # ------------------------------------------------------------------
    # Consultas (a tela le tudo isto)
    # ------------------------------------------------------------------
    @property
    def tipo(self) -> TipoDeMonstro:
        return self.TIPO

    @property
    def casa(self) -> Coordenada:
        """Onde nasceu: o centro do territorio que ele patrulha."""
        return self._casa

    @property
    def cacando(self) -> bool:
        return self._cacando

    @property
    def x(self) -> float:
        return self._x

    @property
    def y(self) -> float:
        return self._y

    @property
    def tile(self) -> Coordenada:
        t = self._lab.tamanho_tile
        return Coordenada(int(self._x) // t, int(self._y) // t)

    @property
    def estado(self) -> EstadoDoMonstro:
        return self._estado

    @property
    def progresso(self) -> float:
        """0..1 do estado atual (aviso enchendo, ataque acontecendo...)."""
        if self._duracao_do_estado <= 0:
            return 0.0
        return min(1.0, self._tempo_no_estado / self._duracao_do_estado)

    @property
    def tempo_no_estado(self) -> float:
        return self._tempo_no_estado

    @property
    def direcao(self) -> Vetor2:
        return self._direcao

    @property
    def tiles_do_ataque(self) -> tuple[Coordenada, ...]:
        """Tiles que o ataque vai pegar (aviso) ou esta pegando (ataque)."""
        return self._tiles_do_ataque

    @property
    def alvo(self) -> tuple[float, float] | None:
        """Ponto do mergulho (aguia) ou onde vai sair do chao (magman/toupeira), em pixels."""
        return self._alvo

    @property
    def projeteis(self) -> tuple[Projetil, ...]:
        return ()

    @property
    def agressivo(self) -> bool:
        return self._agressivo

    @property
    def solido(self) -> bool:
        return self.LADO_SOLIDO > 0

    @property
    def visivel(self) -> bool:
        return self._estado is not EstadoDoMonstro.ESCONDIDO

    def area(self) -> Caixa:
        return Caixa.pelo_centro(round(self._x), round(self._y), self.LADO, self.LADO)

    def area_solida(self) -> Caixa:
        return Caixa.pelo_centro(round(self._x), round(self._y), self.LADO_SOLIDO, self.LADO_SOLIDO)

    # ------------------------------------------------------------------
    # Comandos
    # ------------------------------------------------------------------
    def atualizar(self, dt: float, ctx: ContextoDosMonstros) -> None:
        if ctx.monstros_dormindo and self._estado is not EstadoDoMonstro.APAGADO:
            if self._estado is not EstadoDoMonstro.DORMINDO:
                self._ao_dormir()
                self._mudar(EstadoDoMonstro.DORMINDO)
            return
        if self._estado is EstadoDoMonstro.DORMINDO:
            self._mudar(EstadoDoMonstro.ANDANDO)
        self._tempo_no_estado += dt
        self._recarga = max(0.0, self._recarga - dt)
        self._recarga_contato = max(0.0, self._recarga_contato - dt)
        self._atualizar_folego(dt)
        if self._lab.eh_parede(*self._destino):  # alguem construiu uma parede no caminho (arena)
            self._destino = self._tile
        if self._estado is EstadoDoMonstro.APAGADO:
            if self._tempo_no_estado >= self._duracao_do_estado:
                self._mudar(EstadoDoMonstro.ANDANDO)
                self._recarga = self.RECARGA
            return
        self._agir(dt, ctx)
        self._checar_contato(ctx)

    def apagar(self, segundos: float) -> None:
        """Extintor por perto. So o magman e a fornalha ligam para isso."""

    # ------------------------------------------------------------------
    # Para as subclasses
    # ------------------------------------------------------------------
    def _agir(self, dt: float, ctx: ContextoDosMonstros) -> None:
        self._andar(dt, ctx, self._vagar)

    def _golpe_de_contato(self) -> Golpe | None:
        return self.GOLPE_DE_CONTATO

    def _pode_encostar(self) -> bool:
        return self._estado not in (EstadoDoMonstro.DORMINDO, EstadoDoMonstro.ESCONDIDO,
                                    EstadoDoMonstro.APAGADO, EstadoDoMonstro.ATORDOADO)

    def _ao_dormir(self) -> None:
        self._tiles_do_ataque = ()
        self._alvo = None

    def _mudar(self, estado: EstadoDoMonstro, duracao: float = 0.0) -> None:
        self._estado = estado
        self._tempo_no_estado = 0.0
        self._duracao_do_estado = duracao

    def _fim_do_estado(self) -> bool:
        return self._tempo_no_estado >= self._duracao_do_estado

    def _recarregar(self) -> None:
        self._recarga = self.RECARGA * (0.7 if self._agressivo else 1.0)

    def _multiplicador_de_velocidade(self, ctx: ContextoDosMonstros) -> float:
        return self.VELOCIDADE_AGRESSIVO if self._agressivo else 1.0

    def _checar_contato(self, ctx: ContextoDosMonstros) -> None:
        golpe = self._golpe_de_contato()
        if golpe is None or self._recarga_contato > 0 or not self._pode_encostar():
            return
        if self.area().intersecta(ctx.jogador.caixa_de_colisao()):
            self._recarga_contato = self.RECARGA_DO_CONTATO if ctx.golpear(golpe, self) else 0.5

    # ------------------------------------------------------------------
    # Movimento pela grade (de centro de tile em centro de tile)
    # ------------------------------------------------------------------
    def _andar(self, dt: float, ctx: ContextoDosMonstros, escolher: Escolha, rapidez: float | None = None) -> None:
        if rapidez is None:
            rapidez = self.VELOCIDADE * Jogador.VELOCIDADE * self._multiplicador_de_velocidade(ctx)
        restante = rapidez * dt
        while restante > 0:
            tx, ty = self._lab.centro_do_tile(self._destino)
            dx, dy = tx - self._x, ty - self._y
            distancia = math.hypot(dx, dy)
            if distancia > 1e-6:
                self._direcao = Vetor2(dx / distancia, dy / distancia)
            if distancia > restante:
                self._x += dx / distancia * restante
                self._y += dy / distancia * restante
                return
            self._x, self._y = float(tx), float(ty)
            restante -= distancia
            if self._destino != self._tile:
                self._anterior = self._tile
            self._tile = self._destino
            proximo = escolher(ctx)
            if proximo is None or proximo == self._tile:
                return
            self._destino = proximo

    def _chegou(self) -> bool:
        return self._destino == self._tile and self.tile == self._tile

    def _opcoes(self) -> list[Coordenada]:
        """Vizinhos de chao (monstro nunca fica parado no portal)."""
        return [t for t in vizinhos_livres(self._lab, self._tile) if t != self._lab.saida]

    def _vagar(self, ctx: ContextoDosMonstros) -> Coordenada | None:
        """Passeia pelo territorio. Evita voltar pelo mesmo caminho e evita o tile do jogador (nao encurrala)."""
        opcoes = self._opcoes()
        no_territorio = [t for t in opcoes if manhattan(t, self._casa) <= self.RAIO_DO_TERRITORIO]
        if no_territorio:
            opcoes = no_territorio
        elif opcoes:  # longe de casa (empurrado, arena editada...): volta para o territorio
            return min(opcoes, key=lambda t: manhattan(t, self._casa))
        if len(opcoes) > 1 and ctx.tile_do_jogador in opcoes:
            opcoes.remove(ctx.tile_do_jogador)
        if len(opcoes) > 1 and self._anterior in opcoes:
            opcoes.remove(self._anterior)  # so volta se for beco sem saida
        return self._rng.choice(opcoes) if opcoes else None

    def _quer_cacar(self, ctx: ContextoDosMonstros) -> bool:
        """So caca de perto, dentro do proprio territorio e enquanto tiver folego."""
        if self.ALCANCE_DA_CACA <= 0 or self._descanso_da_caca > 0 or self._folego <= 0:
            return False
        jogador = ctx.tile_do_jogador
        return (manhattan(self._tile, jogador) <= self.ALCANCE_DA_CACA
                and manhattan(jogador, self._casa) <= self.RAIO_DO_TERRITORIO + 2)

    def _cacar_ou_vagar(self, ctx: ContextoDosMonstros) -> Coordenada | None:
        self._cacando = self._quer_cacar(ctx)
        return self._perseguir(ctx) if self._cacando else self._vagar(ctx)

    def _atualizar_folego(self, dt: float) -> None:
        if self._cacando:
            self._folego -= dt
            if self._folego <= 0:  # cansou: desiste e volta a patrulhar
                self._cacando = False
                self._descanso_da_caca = self.DESCANSO_DA_CACA
        elif self._descanso_da_caca > 0:
            self._descanso_da_caca -= dt
            if self._descanso_da_caca <= 0:
                self._folego = self.FOLEGO

    def _perseguir(self, ctx: ContextoDosMonstros) -> Coordenada | None:
        passo = proximo_passo(self._lab, self._tile, ctx.tile_do_jogador)
        if passo is None or passo == self._lab.saida:
            return self._vagar(ctx)
        return passo

    def _fugir(self, ctx: ContextoDosMonstros) -> Coordenada | None:
        opcoes = self._opcoes()
        if not opcoes:
            return None
        return max(opcoes, key=lambda t: manhattan(t, ctx.tile_do_jogador) + self._rng.random() * 0.5)

    def _area_em_volta(self, raio: int) -> tuple[Coordenada, ...]:
        """Tiles de chao ate `raio` passos (Manhattan) do monstro."""
        c, l = self._tile
        lab = self._lab
        return tuple(Coordenada(c + dx, l + dy)
                     for dy in range(-raio, raio + 1) for dx in range(-raio, raio + 1)
                     if abs(dx) + abs(dy) <= raio and not lab.eh_parede(c + dx, l + dy)
                     and Coordenada(c + dx, l + dy) not in (lab.entrada, lab.saida))

    def _voar_para(self, x: float, y: float, rapidez: float, dt: float) -> None:
        """Movimento livre (por cima/por baixo das paredes), preso dentro do mapa."""
        dx, dy = x - self._x, y - self._y
        distancia = math.hypot(dx, dy)
        if distancia > 1e-6:
            self._direcao = Vetor2(dx / distancia, dy / distancia)
            passo = min(distancia, rapidez * dt)
            self._x += dx / distancia * passo
            self._y += dy / distancia * passo
        t = self._lab.tamanho_tile
        self._x = min(max(self._x, t * 1.5), self._lab.largura - t * 1.5)
        self._y = min(max(self._y, t * 1.5), self._lab.altura - t * 1.5)

    def _posicionar_no_tile(self, tile: Coordenada) -> None:
        self._x, self._y = (float(v) for v in self._lab.centro_do_tile(tile))
        self._tile = self._destino = tile
        self._anterior = None


# ======================================================================
# Masmorra
# ======================================================================
class Aranha(Monstro):
    """Anda pelos corredores e cospe TEIA em linha reta. Foge da lanterna."""

    TIPO = TipoDeMonstro.ARANHA
    VELOCIDADE = 0.45
    RECARGA = 5.0
    RECARGA_DO_CONTATO = 4.0
    GOLPE_DE_CONTATO = Golpe.TEIA
    ALCANCE = 6
    AVISO = 0.7
    VELOCIDADE_DA_TEIA = 330.0
    DURACAO_DA_TEIA = 10.0
    MEDO_DA_LUZ = 4  # tiles

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._projeteis: list[Projetil] = []
        self._com_medo = False

    @property
    def projeteis(self) -> tuple[Projetil, ...]:
        return tuple(self._projeteis)

    @property
    def com_medo(self) -> bool:
        return self._com_medo

    def _agir(self, dt: float, ctx: ContextoDosMonstros) -> None:
        self._mover_projeteis(dt, ctx)
        self._com_medo = ctx.luz_forte and manhattan(self.tile, ctx.tile_do_jogador) <= self.MEDO_DA_LUZ
        if self._estado is EstadoDoMonstro.AVISANDO:
            if self._com_medo:
                self._mudar(EstadoDoMonstro.ANDANDO)
            elif self._fim_do_estado():
                self._projeteis.append(Projetil(self._x, self._y, *self._passo_do_ataque))
                self._recarregar()
                self._mudar(EstadoDoMonstro.ANDANDO)
            return
        self._andar(dt, ctx, self._decidir)

    def _decidir(self, ctx: ContextoDosMonstros) -> Coordenada | None:
        if self._com_medo:
            return self._fugir(ctx)
        if self._recarga == 0:
            passo = linha_de_visao(self._lab, self._tile, ctx.tile_do_jogador, self.ALCANCE)
            if passo is not None:
                self._passo_do_ataque = passo
                self._direcao = Vetor2(*passo)
                self._mudar(EstadoDoMonstro.AVISANDO, self.AVISO)
                return None
        return self._vagar(ctx)

    def _pode_encostar(self) -> bool:
        return super()._pode_encostar() and not self._com_medo

    def _mover_projeteis(self, dt: float, ctx: ContextoDosMonstros) -> None:
        t = self._lab.tamanho_tile
        vivos = []
        for p in self._projeteis:
            p.x += p.dx * self.VELOCIDADE_DA_TEIA * dt
            p.y += p.dy * self.VELOCIDADE_DA_TEIA * dt
            tile = Coordenada(int(p.x) // t, int(p.y) // t)
            if self._lab.eh_parede(*tile):  # bateu: a teia gruda no chao antes da parede
                ctx.deixar_rastro(Rastro.TEIA, Coordenada(tile.coluna - p.dx, tile.linha - p.dy),
                                  self.DURACAO_DA_TEIA)
                continue
            if Caixa.pelo_centro(round(p.x), round(p.y), 16, 16).intersecta(ctx.jogador.caixa_de_colisao()):
                ctx.golpear(Golpe.TEIA, self)
                continue
            vivos.append(p)
        self._projeteis = vivos


class Minotauro(Monstro):
    """Viu o jogador num corredor reto: raspa o pe e INVESTE ate bater na parede (e fica tonto)."""

    TIPO = TipoDeMonstro.MINOTAURO
    VELOCIDADE = 0.5
    LADO = 40
    RECARGA = 3.0
    ALCANCE = 8
    AVISO = 1.0
    VELOCIDADE_DA_INVESTIDA = 2.1
    TONTURA = 2.0

    def _agir(self, dt: float, ctx: ContextoDosMonstros) -> None:
        if self._estado is EstadoDoMonstro.AVISANDO:
            if self._fim_do_estado():
                linha = tiles_em_linha(self._lab, self._tile, self._passo_do_ataque, 99)
                self._destino = linha[-1] if linha else self._tile
                self._mudar(EstadoDoMonstro.ATACANDO)
            return
        if self._estado is EstadoDoMonstro.ATACANDO:
            rapidez = self.VELOCIDADE_DA_INVESTIDA * Jogador.VELOCIDADE
            self._andar(dt, ctx, lambda _ctx: None, rapidez)
            if self._chegou():
                self._anterior = None
                self._mudar(EstadoDoMonstro.ATORDOADO, self.TONTURA)
            return
        if self._estado is EstadoDoMonstro.ATORDOADO:
            if self._fim_do_estado():
                self._recarregar()
                self._mudar(EstadoDoMonstro.ANDANDO)
            return
        self._andar(dt, ctx, self._decidir)

    def _decidir(self, ctx: ContextoDosMonstros) -> Coordenada | None:
        if self._recarga == 0:
            passo = linha_de_visao(self._lab, self._tile, ctx.tile_do_jogador, self.ALCANCE)
            if passo is not None:
                self._passo_do_ataque = passo
                self._direcao = Vetor2(*passo)
                self._mudar(EstadoDoMonstro.AVISANDO, self.AVISO)
                return None
        return self._vagar(ctx)

    def _golpe_de_contato(self) -> Golpe | None:
        return Golpe.CHIFRADA if self._estado is EstadoDoMonstro.ATACANDO else Golpe.MORDIDA


# ======================================================================
# Gelo
# ======================================================================
class BonecoDeNeve(Monstro):
    """Anda MUITO devagar e sopra um raio congelante em linha reta."""

    TIPO = TipoDeMonstro.BONECO_DE_NEVE
    VELOCIDADE = 0.15
    LADO = 38
    RECARGA = 4.5
    RECARGA_DO_CONTATO = 4.0
    GOLPE_DE_CONTATO = Golpe.CONGELAMENTO
    ALCANCE = 7
    AVISO = 1.0
    DURACAO_DO_RAIO = 0.45

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._acertou = False

    def _agir(self, dt: float, ctx: ContextoDosMonstros) -> None:
        if self._estado is EstadoDoMonstro.AVISANDO:
            if self._fim_do_estado():
                self._acertou = False
                self._mudar(EstadoDoMonstro.ATACANDO, self.DURACAO_DO_RAIO)
            return
        if self._estado is EstadoDoMonstro.ATACANDO:
            if not self._acertou and ctx.tile_do_jogador in self._tiles_do_ataque:
                self._acertou = True
                ctx.golpear(Golpe.CONGELAMENTO, self)
            if self._fim_do_estado():
                self._tiles_do_ataque = ()
                self._recarregar()
                self._mudar(EstadoDoMonstro.ANDANDO)
            return
        self._andar(dt, ctx, self._decidir)

    def _decidir(self, ctx: ContextoDosMonstros) -> Coordenada | None:
        if self._recarga == 0:
            passo = linha_de_visao(self._lab, self._tile, ctx.tile_do_jogador, self.ALCANCE)
            if passo is not None:
                self._direcao = Vetor2(*passo)
                self._tiles_do_ataque = tuple(tiles_em_linha(self._lab, self._tile, passo, self.ALCANCE))
                self._mudar(EstadoDoMonstro.AVISANDO, self.AVISO)
                return None
        return self._vagar(ctx)


class Yeti(Monstro):
    """Persegue devagar; o PISAO cria placas de gelo em volta. Encostou: -1 coracao."""

    TIPO = TipoDeMonstro.YETI
    VELOCIDADE = 0.5
    LADO = 42
    RECARGA = 6.0
    ALCANCE_DA_CACA = 5
    AVISO = 0.8
    RAIO_DO_PISAO = 2
    DURACAO_DO_GELO = 6.0

    def _agir(self, dt: float, ctx: ContextoDosMonstros) -> None:
        if self._estado is EstadoDoMonstro.AVISANDO:
            if self._fim_do_estado():
                for tile in self._tiles_do_ataque:
                    ctx.deixar_rastro(Rastro.GELO, tile, self.DURACAO_DO_GELO)
                self._tiles_do_ataque = ()
                self._recarregar()
                self._mudar(EstadoDoMonstro.ANDANDO)
            return
        self._andar(dt, ctx, self._decidir)

    def _decidir(self, ctx: ContextoDosMonstros) -> Coordenada | None:
        distancia = manhattan(self._tile, ctx.tile_do_jogador)
        if self._recarga == 0 and distancia <= self.RAIO_DO_PISAO:
            self._tiles_do_ataque = self._area_em_volta(self.RAIO_DO_PISAO)
            self._mudar(EstadoDoMonstro.AVISANDO, self.AVISO)
            return None
        return self._cacar_ou_vagar(ctx)


# ======================================================================
# Fogo
# ======================================================================
class Magman(Monstro):
    """Deixa RASTRO DE LAVA e as vezes mergulha e sai do chao perto do jogador (bolhas avisam)."""

    TIPO = TipoDeMonstro.MAGMAN
    VELOCIDADE = 0.45
    LADO = 36
    RECARGA = 8.0
    GOLPE_DE_CONTATO = Golpe.QUEIMADURA
    DURACAO_DA_LAVA = 3.0
    AFUNDAR = 0.6
    SUBMERSO = 1.2
    ALCANCE_DO_MERGULHO = 6

    def apagar(self, segundos: float) -> None:
        if self._estado is EstadoDoMonstro.ESCONDIDO and self._alvo is not None:
            self._sair_do_chao()
        self._tiles_do_ataque = ()
        self._alvo = None
        self._mudar(EstadoDoMonstro.APAGADO, segundos)

    def _agir(self, dt: float, ctx: ContextoDosMonstros) -> None:
        if self._estado is EstadoDoMonstro.AVISANDO:  # afundando na lava
            if self._fim_do_estado():
                alvo = self._sortear_saida(ctx)
                if alvo is None:
                    self._recarregar()
                    self._mudar(EstadoDoMonstro.ANDANDO)
                    return
                self._tiles_do_ataque = (alvo,)
                self._alvo = tuple(float(v) for v in self._lab.centro_do_tile(alvo))
                self._mudar(EstadoDoMonstro.ESCONDIDO, self.SUBMERSO)
            return
        if self._estado is EstadoDoMonstro.ESCONDIDO:
            if self._fim_do_estado():
                self._sair_do_chao()
                ctx.deixar_rastro(Rastro.LAVA, self._tile, self.DURACAO_DA_LAVA)
            return
        self._andar(dt, ctx, self._decidir)

    def _sair_do_chao(self) -> None:
        self._posicionar_no_tile(self._tiles_do_ataque[0])
        self._tiles_do_ataque = ()
        self._alvo = None
        self._recarregar()
        self._mudar(EstadoDoMonstro.ANDANDO)

    def _decidir(self, ctx: ContextoDosMonstros) -> Coordenada | None:
        ctx.deixar_rastro(Rastro.LAVA, self._tile, self.DURACAO_DA_LAVA)
        if self._recarga == 0 and manhattan(self._tile, ctx.tile_do_jogador) <= self.ALCANCE_DO_MERGULHO:
            self._mudar(EstadoDoMonstro.AVISANDO, self.AFUNDAR)
            return None
        return self._vagar(ctx)

    def _sortear_saida(self, ctx: ContextoDosMonstros) -> Coordenada | None:
        jogador = ctx.tile_do_jogador
        lab = self._lab
        opcoes = [Coordenada(jogador.coluna + dx, jogador.linha + dy)
                  for dy in range(-3, 4) for dx in range(-3, 4) if 2 <= abs(dx) + abs(dy) <= 3]
        opcoes = [t for t in opcoes if not lab.eh_parede(*t) and t not in (lab.entrada, lab.saida)]
        return self._rng.choice(opcoes) if opcoes else None


class Fornalha(Monstro):
    """Torre parada no fim de um corredor: fica vermelha e solta uma LABAREDA em linha reta."""

    TIPO = TipoDeMonstro.FORNALHA
    VELOCIDADE = 0.0
    LADO = 52
    LADO_SOLIDO = 40
    RECARGA = 3.5
    GOLPE_DE_CONTATO = Golpe.QUEIMADURA
    ALCANCE = 5
    ALCANCE_AGRESSIVO = 4
    AVISO = 1.0
    DURACAO_DA_LABAREDA = 1.2

    def apagar(self, segundos: float) -> None:
        self._tiles_do_ataque = ()
        self._mudar(EstadoDoMonstro.APAGADO, segundos)

    def _agir(self, dt: float, ctx: ContextoDosMonstros) -> None:
        if self._estado is EstadoDoMonstro.AVISANDO:
            if self._fim_do_estado():
                self._mudar(EstadoDoMonstro.ATACANDO, self.DURACAO_DA_LABAREDA)
            return
        if self._estado is EstadoDoMonstro.ATACANDO:
            if ctx.tile_do_jogador in self._tiles_do_ataque:
                ctx.golpear(Golpe.QUEIMADURA, self)
            if self._fim_do_estado():
                self._tiles_do_ataque = ()
                self._recarregar()
                self._mudar(EstadoDoMonstro.ANDANDO)
            return
        if self._recarga > 0:
            return
        if self._agressivo and manhattan(self._tile, ctx.tile_do_jogador) <= self.ALCANCE + 1:
            tiles = [t for passo in ((1, 0), (-1, 0), (0, 1), (0, -1))
                     for t in tiles_em_linha(self._lab, self._tile, passo, self.ALCANCE_AGRESSIVO)]
        else:
            passo = linha_de_visao(self._lab, self._tile, ctx.tile_do_jogador, self.ALCANCE)
            tiles = tiles_em_linha(self._lab, self._tile, passo, self.ALCANCE) if passo else []
            if passo:
                self._direcao = Vetor2(*passo)
        if tiles:
            self._tiles_do_ataque = tuple(tiles)
            self._mudar(EstadoDoMonstro.AVISANDO, self.AVISO)


# ======================================================================
# Vento
# ======================================================================
class Aguia(Monstro):
    """Voa por cima das paredes. A SOMBRA no chao avisa o mergulho que ROUBA um buff."""

    TIPO = TipoDeMonstro.AGUIA
    VELOCIDADE = 0.55
    RECARGA = 6.0
    GOLPE_DE_CONTATO = None
    AVISO = 1.0
    MERGULHO = 0.3
    RAIO_DA_SOMBRA = 26
    ALCANCE = 4  # tiles

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._angulo = self._rng.uniform(0, math.tau)

    @property
    def altura_de_voo(self) -> float:
        """1 = voando alto, 0 = no chao (mergulho)."""
        if self._estado is EstadoDoMonstro.ATACANDO:
            return 0.0
        if self._estado is EstadoDoMonstro.AVISANDO:
            return 1.0 - 0.4 * self.progresso
        return 1.0

    def _ao_dormir(self) -> None:
        super()._ao_dormir()
        self._recarregar()

    def _agir(self, dt: float, ctx: ContextoDosMonstros) -> None:
        rapidez = self.VELOCIDADE * Jogador.VELOCIDADE
        jogador = ctx.jogador
        centro_do_jogador = (jogador.x, jogador.y - Jogador.ALTURA_HITBOX / 2)
        if self._estado is EstadoDoMonstro.AVISANDO:
            self._voar_para(*self._alvo, rapidez * 2.2, dt)
            if self._fim_do_estado():
                self._x, self._y = self._alvo
                self._mudar(EstadoDoMonstro.ATACANDO, self.MERGULHO)
            return
        if self._estado is EstadoDoMonstro.ATACANDO:
            if self._fim_do_estado():
                lado = self.RAIO_DA_SOMBRA * 2
                sombra = Caixa.pelo_centro(round(self._alvo[0]), round(self._alvo[1]), lado, lado)
                if sombra.intersecta(jogador.caixa_de_colisao()):
                    ctx.golpear(Golpe.ROUBO, self)
                self._alvo = None
                self._recarregar()
                self._mudar(EstadoDoMonstro.ANDANDO)
            return
        t = self._lab.tamanho_tile
        self._angulo += dt * 0.9
        casa_x, casa_y = self._lab.centro_do_tile(self._casa)  # circula sobre o proprio territorio
        self._voar_para(casa_x + math.cos(self._angulo) * t * 2.5,
                        casa_y + math.sin(self._angulo) * t * 1.8, rapidez, dt)
        perto = math.hypot(self._x - centro_do_jogador[0], self._y - centro_do_jogador[1]) < self.ALCANCE * t
        if self._recarga == 0 and perto:
            self._alvo = centro_do_jogador
            self._mudar(EstadoDoMonstro.AVISANDO, self.AVISO)


class Tornado(Monstro):
    """Vaga pelo territorio; encostou, ARREMESSA o jogador para longe do portal (nao da dano)."""

    TIPO = TipoDeMonstro.TORNADO
    VELOCIDADE = 0.6
    LADO = 36
    RECARGA_DO_CONTATO = 4.0
    GOLPE_DE_CONTATO = Golpe.ARREMESSO


# ======================================================================
# Terra
# ======================================================================
class Toupeira(Monstro):
    """Cava por baixo da terra (atravessa paredes) pelo territorio. Se o jogador passar perto,
    vai ate ele por baixo da terra, sai do chao embaixo dele e deixa um BURACO."""

    TIPO = TipoDeMonstro.TOUPEIRA
    VELOCIDADE = 0.35
    RECARGA = 6.0
    GOLPE_DE_CONTATO = None
    AVISO = 0.9
    EMERGIR = 0.8
    PERTO = 1.3  # tiles
    FAREJAR = 4  # tiles: so vai atras do jogador se ele estiver ate aqui

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._ponto: tuple[float, float] | None = None

    @property
    def subterranea(self) -> bool:
        return self._estado is not EstadoDoMonstro.ATACANDO

    def _agir(self, dt: float, ctx: ContextoDosMonstros) -> None:
        rapidez = self.VELOCIDADE * Jogador.VELOCIDADE
        if self._estado is EstadoDoMonstro.AVISANDO:
            self._voar_para(*self._alvo, rapidez * 1.5, dt)
            if self._fim_do_estado():
                alvo = self._tiles_do_ataque[0]
                self._posicionar_no_tile(alvo)
                if ctx.tile_do_jogador == alvo:
                    ctx.golpear(Golpe.BURACO, self)
                ctx.deixar_rastro(Rastro.BURACO, alvo, math.inf)
                self._mudar(EstadoDoMonstro.ATACANDO, self.EMERGIR)
            return
        if self._estado is EstadoDoMonstro.ATACANDO:
            if self._fim_do_estado():
                self._tiles_do_ataque = ()
                self._alvo = None
                self._recarregar()
                self._mudar(EstadoDoMonstro.ANDANDO)
            return
        jogador = ctx.jogador
        alvo_x, alvo_y = jogador.x, jogador.y - Jogador.ALTURA_HITBOX / 2
        t = self._lab.tamanho_tile
        farejou = (math.hypot(self._x - alvo_x, self._y - alvo_y) < self.FAREJAR * t
                   and manhattan(ctx.tile_do_jogador, self._casa) <= self.RAIO_DO_TERRITORIO + 2)
        if farejou:
            self._voar_para(alvo_x, alvo_y, rapidez, dt)
        else:
            self._patrulhar(rapidez, dt)
        perto = math.hypot(self._x - alvo_x, self._y - alvo_y) < self.PERTO * t
        alvo = ctx.tile_do_jogador
        if self._recarga == 0 and perto and alvo not in (self._lab.entrada, self._lab.saida):
            self._tiles_do_ataque = (alvo,)
            self._alvo = tuple(float(v) for v in self._lab.centro_do_tile(alvo))
            self._mudar(EstadoDoMonstro.AVISANDO, self.AVISO)

    def _patrulhar(self, rapidez: float, dt: float) -> None:
        """Cava ate um ponto sorteado do territorio; chegou, sorteia outro."""
        if self._ponto is None or math.hypot(self._x - self._ponto[0], self._y - self._ponto[1]) < 4:
            r = self.RAIO_DO_TERRITORIO
            c = self._casa.coluna + self._rng.randint(-r, r)
            l = self._casa.linha + self._rng.randint(-r, r)
            self._ponto = tuple(float(v) for v in self._lab.centro_do_tile(Coordenada(c, l)))
        self._voar_para(*self._ponto, rapidez * 0.7, dt)


class Golem(Monstro):
    """GUARDIAO lento e SOLIDO: patrulha o territorio sem perseguir. Se o jogador chega perto,
    para, encara e soca o chao (onda de choque em volta).

    Depois do soco fica CANSADO alguns segundos e deixa de ser solido: e a hora de passar por ele.
    """

    TIPO = TipoDeMonstro.GOLEM
    VELOCIDADE = 0.28
    LADO = 48
    LADO_SOLIDO = 38
    RECARGA = 5.0
    AVISO = 1.2
    DURACAO_DA_ONDA = 0.35
    DESCANSO = 2.5
    RAIO = 2

    @property
    def solido(self) -> bool:
        return self._estado is not EstadoDoMonstro.ATORDOADO

    def _agir(self, dt: float, ctx: ContextoDosMonstros) -> None:
        if self._estado is EstadoDoMonstro.AVISANDO:
            if self._fim_do_estado():
                if ctx.tile_do_jogador in self._tiles_do_ataque:
                    ctx.golpear(Golpe.ONDA_DE_CHOQUE, self)
                self._mudar(EstadoDoMonstro.ATACANDO, self.DURACAO_DA_ONDA)
            return
        if self._estado is EstadoDoMonstro.ATACANDO:
            if self._fim_do_estado():
                self._tiles_do_ataque = ()
                self._mudar(EstadoDoMonstro.ATORDOADO, self.DESCANSO)
            return
        if self._estado is EstadoDoMonstro.ATORDOADO:
            if self._fim_do_estado():
                self._recarregar()
                self._mudar(EstadoDoMonstro.ANDANDO)
            return
        self._andar(dt, ctx, self._decidir)

    def _decidir(self, ctx: ContextoDosMonstros) -> Coordenada | None:
        jogador = ctx.tile_do_jogador
        distancia = manhattan(self._tile, jogador)
        if self._recarga == 0 and distancia <= self.RAIO:
            self._tiles_do_ataque = self._area_em_volta(self.RAIO)
            self._mudar(EstadoDoMonstro.AVISANDO, self.AVISO)
            return None
        if distancia <= self.RAIO + 1:
            self._direcao = Vetor2(jogador.coluna - self._tile.coluna, jogador.linha - self._tile.linha)
            return None  # jogador por perto: para e espera a hora do soco
        return self._vagar(ctx)


# ======================================================================
# Deserto
# ======================================================================
class Cobra(Monstro):
    """Patrulha o territorio. Viu o jogador perto e em linha: ESPREITA e da o BOTE (2 tiles). Picada = veneno."""

    TIPO = TipoDeMonstro.COBRA
    VELOCIDADE = 0.6
    LADO = 32
    RECARGA = 4.0
    RECARGA_DO_CONTATO = 5.0
    GOLPE_DE_CONTATO = Golpe.VENENO
    ALCANCE_DO_BOTE = 2
    AVISO = 0.5
    VELOCIDADE_DO_BOTE = 1.9

    def _agir(self, dt: float, ctx: ContextoDosMonstros) -> None:
        if self._estado is EstadoDoMonstro.AVISANDO:
            if self._fim_do_estado():
                linha = tiles_em_linha(self._lab, self._tile, self._passo_do_ataque, self.ALCANCE_DO_BOTE)
                self._destino = linha[-1] if linha else self._tile
                self._mudar(EstadoDoMonstro.ATACANDO)
            return
        if self._estado is EstadoDoMonstro.ATACANDO:
            self._andar(dt, ctx, lambda _ctx: None, self.VELOCIDADE_DO_BOTE * Jogador.VELOCIDADE)
            if self._chegou():
                self._recarregar()
                self._mudar(EstadoDoMonstro.ANDANDO)
            return
        self._andar(dt, ctx, self._decidir)

    def _decidir(self, ctx: ContextoDosMonstros) -> Coordenada | None:
        passo = linha_de_visao(self._lab, self._tile, ctx.tile_do_jogador, self.ALCANCE_DO_BOTE + 1)
        if passo is not None:
            self._passo_do_ataque = passo
            self._direcao = Vetor2(*passo)
            if self._recarga == 0 and manhattan(self._tile, ctx.tile_do_jogador) <= self.ALCANCE_DO_BOTE:
                self._mudar(EstadoDoMonstro.AVISANDO, self.AVISO)
            return None  # espreitando: parada, encarando o jogador
        return self._vagar(ctx)


class Mumia(Monstro):
    """Persegue de perto (pouco folego) e joga a FAIXA como laco (puxa 2 tiles). Na tempestade some e corre."""

    TIPO = TipoDeMonstro.MUMIA
    VELOCIDADE = 0.42
    LADO = 38
    RECARGA = 5.0
    RECARGA_INICIAL = (0.5, 1.5)
    ALCANCE_DO_LACO = 4
    AVISO = 0.8
    DURACAO_DO_LACO = 0.3
    ALCANCE_DA_CACA = 5
    TEMPESTADE_FORTE = 0.3

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._na_tempestade = False

    @property
    def visivel(self) -> bool:
        return not self._na_tempestade

    def _multiplicador_de_velocidade(self, ctx: ContextoDosMonstros) -> float:
        return super()._multiplicador_de_velocidade(ctx) * (1.6 if self._na_tempestade else 1.0)

    def _agir(self, dt: float, ctx: ContextoDosMonstros) -> None:
        self._na_tempestade = ctx.forca_da_tempestade > self.TEMPESTADE_FORTE
        if self._estado is EstadoDoMonstro.AVISANDO:
            if self._fim_do_estado():
                if linha_de_visao(self._lab, self._tile, ctx.tile_do_jogador, self.ALCANCE_DO_LACO + 1):
                    ctx.golpear(Golpe.LACO, self)
                self._mudar(EstadoDoMonstro.ATACANDO, self.DURACAO_DO_LACO)
            return
        if self._estado is EstadoDoMonstro.ATACANDO:
            if self._fim_do_estado():
                self._tiles_do_ataque = ()
                self._recarregar()
                self._mudar(EstadoDoMonstro.ANDANDO)
            return
        self._andar(dt, ctx, self._decidir)

    def _decidir(self, ctx: ContextoDosMonstros) -> Coordenada | None:
        distancia = manhattan(self._tile, ctx.tile_do_jogador)
        if self._recarga == 0 and distancia >= 2:
            passo = linha_de_visao(self._lab, self._tile, ctx.tile_do_jogador, self.ALCANCE_DO_LACO)
            if passo is not None:
                self._direcao = Vetor2(*passo)
                self._tiles_do_ataque = tuple(tiles_em_linha(self._lab, self._tile, passo, distancia))
                self._mudar(EstadoDoMonstro.AVISANDO, self.AVISO)
                return None
        return self._cacar_ou_vagar(ctx)


# ======================================================================
CLASSES_DOS_MONSTROS: dict[TipoDeMonstro, type[Monstro]] = {
    classe.TIPO: classe for classe in (Aranha, Minotauro, BonecoDeNeve, Yeti, Magman, Fornalha,
                                       Aguia, Tornado, Toupeira, Golem, Cobra, Mumia)
}


def criar_monstro(tipo: TipoDeMonstro, tile: Coordenada, labirinto: Labirinto, sorteio: random.Random,
                  agressivo: bool = False) -> Monstro:
    return CLASSES_DOS_MONSTROS[tipo](tile, labirinto, sorteio, agressivo)
