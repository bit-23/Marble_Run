"""
ambiente.py - Caixas surpresa (BUFFS), perigos (DEBUFFS) e fenomenos de cada fase.

    CaixaSurpresa -> caixa "?" no chao; ao abrir, sorteia um buff (a roleta e so visual)
    MolaDeParede  -> mola presa na parede: andou contra ela, pula para o outro lado
    Perigo        -> tile perigoso (agua que congela, fogo, teia, areia movedica,
                     placa de gelo que faz deslizar ate bater em algo)
    Fenomeno      -> evento periodico do mapa (tempestade de areia, tempestade de gelo,
                     apagao, terremoto, rajada de vento, erupcao de lava), controlado por
                     um CicloDeEvento
    Condicoes     -> efeitos temporarios no jogador (congelado, cafe, estrela...)
    Monstro       -> (monstros.py) cada mapa tem 2; eles pedem ao Ambiente para
                     `golpear` o jogador e o Ambiente aplica as protecoes dos itens

O Ambiente junta tudo isso e responde as duas perguntas que a Fase faz a
cada quadro: "como o jogador pode se mover agora?" (locomocao) e "o que
aconteceu depois que ele se moveu?" (ocorrencias). Nada aqui importa pygame.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import Iterable, Sequence

from .caminhos import caminho, distancias, manhattan
from .contratos import MapaDeColisao
from .geometria import Caixa, Vetor2
from .jogador import Direcao, Jogador, Locomocao
from .labirinto import Coordenada, Labirinto, LabirintoEditavel
from .monstros import Golpe, Monstro, Rastro


class TipoDeItem(Enum):
    """Os buffs que podem sair na roleta da caixa surpresa."""

    BLUSA = "blusa"
    FLAUTA = "flauta"
    RELOGIO = "relogio"
    LANTERNA = "lanterna"
    ESTRELA = "estrela"
    BUSSOLA = "bussola"
    CAFE = "cafe"
    CORACAO = "coracao"  # +1 coracao (com a vida cheia vira tempo extra)
    EXTINTOR = "extintor"            # fogo: apaga fogo/lava em volta e apaga os monstros de fogo
    BOTA = "bota"                    # fogo: bota de obsidiana, imune a fogo e lava
    GUARDA_CHUVA = "guarda_chuva"    # vento: imune a rajada, tornado e aguia
    PIPA = "pipa"                    # vento: o vento empurra PARA o portal
    TAPETE = "tapete"                # deserto: flutua e voa por cima de 1 parede
    GENIO = "genio"                  # deserto: escolhe 1 de 3 desejos
    BROCA = "broca"                  # terra: atravessa ate 2 paredes
    CAPACETE = "capacete"            # terra: terremoto nao inverte, luz extra, imune a toupeira/golem


class Desejo(Enum):
    """Os 3 desejos do Genio da Lampada."""

    TEMPO = "tempo"            # +20 segundos
    CAMINHO = "caminho"        # setas no chao mostrando o melhor caminho (3.5s)
    TELEPORTE = "teleporte"    # pula alguns tiles para mais perto do portal


class TipoDePerigo(Enum):
    AGUA = "agua"
    FOGO = "fogo"
    TEIA = "teia"
    AREIA_MOVEDICA = "areia_movedica"
    GELO = "gelo"  # placa de gelo: desliza ate bater em algo (estilo Pokemon)
    LAVA = "lava"  # rastro do magman: sempre queima
    BURACO = "buraco"  # toca da toupeira: entrar num leva a outro


class Fenomeno(Enum):
    TEMPESTADE_DE_AREIA = "tempestade_de_areia"
    TEMPESTADE_DE_GELO = "tempestade_de_gelo"  # nevasca: deixa o jogador lento
    APAGAO = "apagao"
    TERREMOTO = "terremoto"
    RAJADA = "rajada"
    ERUPCAO = "erupcao"  # jatos de lava sobem de alguns tiles perto do jogador


class Condicao(Enum):
    """Efeitos temporarios no jogador (buffs e debuffs com cronometro)."""

    CONGELADO = auto()
    QUEIMANDO = auto()   # pegando fogo: corre descontrolado
    PROTEGIDO = auto()   # instantes de folga depois de se queimar
    BLUSA = auto()
    CAFE = auto()
    LANTERNA = auto()
    ESTRELA = auto()
    BUSSOLA = auto()
    CALMARIA = auto()    # efeito da flauta (acalma a tempestade e faz os monstros dormirem)
    BOTA = auto()
    GUARDA_CHUVA = auto()
    PIPA = auto()
    TAPETE = auto()
    BROCA = auto()
    CAPACETE = auto()
    CAMINHO = auto()     # genio: setas do melhor caminho
    TONTO = auto()       # controles invertidos (tornado, onda de choque)
    CAIDO = auto()       # caiu no buraco da toupeira: parado
    INVULNERAVEL = auto()  # instantes de folga depois de levar dano de monstro


DURACOES: dict[Condicao, float] = {
    Condicao.CONGELADO: 2.0,
    Condicao.QUEIMANDO: 1.5,
    Condicao.PROTEGIDO: 2.5,
    Condicao.BLUSA: 10.0,
    Condicao.CAFE: 8.0,
    Condicao.LANTERNA: 12.0,
    Condicao.ESTRELA: 6.0,
    Condicao.BUSSOLA: 15.0,
    Condicao.CALMARIA: 8.0,
    Condicao.BOTA: 8.0,
    Condicao.GUARDA_CHUVA: 10.0,
    Condicao.PIPA: 12.0,
    Condicao.TAPETE: 8.0,
    Condicao.BROCA: 15.0,
    Condicao.CAPACETE: 12.0,
    Condicao.CAMINHO: 3.5,
    Condicao.TONTO: 1.2,
    Condicao.CAIDO: 1.0,
    Condicao.INVULNERAVEL: 1.5,
}

CONDICAO_DO_ITEM: dict[TipoDeItem, Condicao] = {
    TipoDeItem.BLUSA: Condicao.BLUSA,
    TipoDeItem.CAFE: Condicao.CAFE,
    TipoDeItem.LANTERNA: Condicao.LANTERNA,
    TipoDeItem.ESTRELA: Condicao.ESTRELA,
    TipoDeItem.BUSSOLA: Condicao.BUSSOLA,
    TipoDeItem.FLAUTA: Condicao.CALMARIA,
    TipoDeItem.BOTA: Condicao.BOTA,
    TipoDeItem.GUARDA_CHUVA: Condicao.GUARDA_CHUVA,
    TipoDeItem.PIPA: Condicao.PIPA,
    TipoDeItem.TAPETE: Condicao.TAPETE,
    TipoDeItem.BROCA: Condicao.BROCA,
    TipoDeItem.CAPACETE: Condicao.CAPACETE,
}
ITEM_DA_CONDICAO: dict[Condicao, TipoDeItem] = {c: i for i, c in CONDICAO_DO_ITEM.items()}
ITEM_DA_CONDICAO[Condicao.CAMINHO] = TipoDeItem.GENIO

# Buffs que a aguia consegue roubar (estrela e guarda-chuva impedem o roubo)
BUFFS_ROUBAVEIS: tuple[Condicao, ...] = (
    Condicao.BLUSA, Condicao.CAFE, Condicao.LANTERNA, Condicao.BUSSOLA, Condicao.CALMARIA, Condicao.BOTA,
    Condicao.PIPA, Condicao.TAPETE, Condicao.BROCA, Condicao.CAPACETE, Condicao.CAMINHO,
)
CARGAS_DE_PAREDE: dict[TipoDeItem, int] = {TipoDeItem.TAPETE: 1, TipoDeItem.BROCA: 2}

# (item, peso no sorteio) que podem sair em QUALQUER mapa.
# Os outros (lanterna, bussola, cafe, blusa, flauta...) sao exclusivos de um mapa (veja biomas.py).
ITENS_COMUNS: tuple[tuple[TipoDeItem, float], ...] = (
    (TipoDeItem.RELOGIO, 3),
    (TipoDeItem.CORACAO, 2),
    (TipoDeItem.ESTRELA, 1),  # a mais forte: mais rara
)


class HistoricoDaRoleta:
    """Memoria da roleta entre caixas (e entre fases): o que saiu ha pouco tem MUITO menos chance.

    O ultimo premio fica com 10% do peso; os anteriores (ate MEMORIA) com 35%.
    """

    MEMORIA = 3

    def __init__(self) -> None:
        self._ultimos: list[TipoDeItem] = []

    @property
    def ultimos(self) -> tuple[TipoDeItem, ...]:
        return tuple(self._ultimos)

    def peso(self, tipo: TipoDeItem, peso: float) -> float:
        if self._ultimos and self._ultimos[-1] is tipo:
            return peso * 0.1
        if tipo in self._ultimos:
            return peso * 0.35
        return peso

    def registrar(self, tipo: TipoDeItem) -> None:
        self._ultimos = (self._ultimos + [tipo])[-self.MEMORIA:]

# (intervalo entre inicios, duracao, aviso antes de comecar) em segundos
CICLOS_DOS_FENOMENOS: dict[Fenomeno, tuple[float, float, float]] = {
    Fenomeno.TEMPESTADE_DE_AREIA: (13.5, 4.0, 2.0),
    Fenomeno.TEMPESTADE_DE_GELO: (13.5, 4.0, 2.0),
    Fenomeno.APAGAO: (15.5, 3.0, 1.5),
    Fenomeno.TERREMOTO: (16.5, 4.0, 2.0),
    Fenomeno.RAJADA: (10.0, 1.6, 1.2),
    Fenomeno.ERUPCAO: (11.0, 1.4, 1.8),
}

DELTAS_DA_DIRECAO: dict[Direcao, tuple[int, int]] = {
    Direcao.CIMA: (0, -1),
    Direcao.BAIXO: (0, 1),
    Direcao.ESQUERDA: (-1, 0),
    Direcao.DIREITA: (1, 0),
}
OPOSTA: dict[Direcao, Direcao] = {
    Direcao.CIMA: Direcao.BAIXO, Direcao.BAIXO: Direcao.CIMA,
    Direcao.ESQUERDA: Direcao.DIREITA, Direcao.DIREITA: Direcao.ESQUERDA,
}


def vetor_da_direcao(direcao: Direcao) -> Vetor2:
    dx, dy = DELTAS_DA_DIRECAO[direcao]
    return Vetor2(dx, dy)


class TipoDeOcorrencia(Enum):
    CAIXA_ABERTA = auto()     # a tela mostra a roleta parando em `item`
    BUFF_APLICADO = auto()    # buff dado direto (modo teste dos mapas)
    CONGELOU = auto()
    FICOU_PRESO = auto()
    TECLA_CERTA = auto()      # acertou uma seta da sequencia da teia
    TECLA_ERRADA = auto()     # errou: a sequencia volta do comeco
    SOLTOU_DA_TEIA = auto()
    QUEIMOU = auto()
    PULOU = auto()
    COMECOU_A_DESLIZAR = auto()
    FENOMENO_COMECOU = auto()
    MONSTRO_ATACOU = auto()       # -1 coracao (mordida, chifrada, onda de choque)
    GOLPE_BLOQUEADO = auto()      # um item protegeu (guarda-chuva contra a aguia...)
    ENVENENOU = auto()            # picada da cobra: acerte as setas a tempo
    CUROU_VENENO = auto()
    VENENO_FEZ_EFEITO = auto()    # nao acertou a tempo: -1 coracao
    ARREMESSADO = auto()          # tornado
    PUXADO = auto()               # laco da mumia
    ROUBOU_BUFF = auto()          # aguia levou `item`
    CAIU_NO_BURACO = auto()       # toupeira: -5s
    ATRAVESSOU_TUNEL = auto()     # entrou num buraco e saiu em outro
    ATRAVESSOU_PAREDE = auto()    # tapete (`item`)
    COMECOU_A_PERFURAR = auto()   # broca encostou na parede
    QUEBROU_PAREDE = auto()       # broca: a parede virou chao
    DESEJO_REALIZADO = auto()     # genio


@dataclass(frozen=True)
class Ocorrencia:
    """Algo que aconteceu na fase (som, tremor de tela, roleta, dano...)."""

    tipo: TipoDeOcorrencia
    item: TipoDeItem | None = None
    fenomeno: Fenomeno | None = None
    segundos: float = 0.0  # ajuste no cronometro (relogio)
    dano: int = 0          # coracoes perdidos (fogo)
    cura: int = 0          # coracoes ganhos (coracao bonus)


# ======================================================================
class DesafioDaTeia:
    """Preso na teia: so sai acertando a sequencia de setas, em ordem.

    Errou uma seta = a sequencia volta do comeco (mas continua a mesma).
    """

    TAMANHO = 4

    def __init__(self, sequencia: Sequence[Direcao]) -> None:
        if not sequencia:
            raise ValueError("a sequencia precisa de ao menos uma seta")
        self._sequencia = tuple(sequencia)
        self._acertos = 0
        self._erros = 0

    @classmethod
    def sortear(cls, rng: random.Random) -> DesafioDaTeia:
        return cls([rng.choice(tuple(Direcao)) for _ in range(cls.TAMANHO)])

    @property
    def sequencia(self) -> tuple[Direcao, ...]:
        return self._sequencia

    @property
    def acertos(self) -> int:
        return self._acertos

    @property
    def erros(self) -> int:
        return self._erros

    @property
    def concluido(self) -> bool:
        return self._acertos >= len(self._sequencia)

    def apertar(self, direcao: Direcao) -> bool:
        """True se acertou a proxima seta."""
        if self.concluido:
            return True
        if direcao is self._sequencia[self._acertos]:
            self._acertos += 1
            return True
        self._acertos = 0
        self._erros += 1
        return False


class CaixaSurpresa:
    """Caixa "?" (roleta) ou, se tiver `conteudo`, um item especifico largado no chao (arena)."""

    LADO = 30  # area de coleta, em pixels do mapa

    def __init__(self, tile: Coordenada, centro: tuple[int, int], conteudo: TipoDeItem | None = None) -> None:
        self._tile = tile
        self._centro = centro
        self._conteudo = conteudo
        self._aberta = False

    @property
    def conteudo(self) -> TipoDeItem | None:
        return self._conteudo

    @property
    def tile(self) -> Coordenada:
        return self._tile

    @property
    def centro(self) -> tuple[int, int]:
        return self._centro

    @property
    def aberta(self) -> bool:
        return self._aberta

    def area(self) -> Caixa:
        return Caixa.pelo_centro(self._centro[0], self._centro[1], self.LADO, self.LADO)

    def abrir(self) -> None:
        self._aberta = True


class MolaDeParede:
    """Mola presa na parede entre dois corredores: A |parede| B.

    So dispara se o jogador estiver ANDANDO CONTRA a parede (virado para ela)
    e encostado na faixa da mola - passar ao lado nao faz pular sem querer.
    """

    PROFUNDIDADE = 14  # faixa do tile, colada na parede, que aciona a mola

    def __init__(self, tile: Coordenada, direcao: Direcao, destino: Coordenada, tamanho_tile: int) -> None:
        self._tile = tile
        self._direcao = direcao
        self._destino = destino
        self._tamanho_tile = tamanho_tile
        self._ultimo_uso = -10.0

    @property
    def tile(self) -> Coordenada:
        return self._tile

    @property
    def direcao(self) -> Direcao:
        """Para onde a mola lanca (= de que lado do tile fica a parede)."""
        return self._direcao

    @property
    def destino(self) -> Coordenada:
        return self._destino

    @property
    def ultimo_uso(self) -> float:
        return self._ultimo_uso

    def area(self) -> Caixa:
        t, p = self._tamanho_tile, self.PROFUNDIDADE
        x, y = self._tile.coluna * t, self._tile.linha * t
        faixas = {
            Direcao.DIREITA: Caixa(x + t - p, y, p, t),
            Direcao.ESQUERDA: Caixa(x, y, p, t),
            Direcao.CIMA: Caixa(x, y, t, p),
            Direcao.BAIXO: Caixa(x, y + t - p, t, p),
        }
        return faixas[self._direcao]

    def acionar(self, tempo: float) -> None:
        self._ultimo_uso = tempo


class Perigo:
    CICLO_DO_FOGO = 3.2   # segundos de um ciclo aceso + apagado
    FOGO_ACESO = 1.8      # ... dos quais fica aceso
    LADOS = {
        TipoDePerigo.AGUA: 40,
        TipoDePerigo.FOGO: 34,
        TipoDePerigo.TEIA: 40,
        TipoDePerigo.AREIA_MOVEDICA: 44,
        TipoDePerigo.GELO: 56,
        TipoDePerigo.LAVA: 36,
        TipoDePerigo.BURACO: 30,
    }

    def __init__(self, tipo: TipoDePerigo, tile: Coordenada, centro: tuple[int, int],
                 defasagem: float = 0.0, expira_em: float | None = None) -> None:
        self._tipo = tipo
        self._tile = tile
        self._centro = centro
        self._defasagem = defasagem
        self._expira_em = expira_em
        self._ativo = True

    @property
    def expira_em(self) -> float | None:
        """Momento (tempo do Ambiente) em que o rastro some. None = permanente."""
        return self._expira_em

    def renovar(self, expira_em: float) -> None:
        self._expira_em = expira_em
        self._ativo = True

    @property
    def tipo(self) -> TipoDePerigo:
        return self._tipo

    @property
    def tile(self) -> Coordenada:
        return self._tile

    @property
    def centro(self) -> tuple[int, int]:
        return self._centro

    @property
    def ativo(self) -> bool:
        """False quando o perigo ja foi desfeito (ex.: teia rasgada)."""
        return self._ativo

    def area(self) -> Caixa:
        lado = self.LADOS[self._tipo]
        return Caixa.pelo_centro(self._centro[0], self._centro[1], lado, lado)

    def momento_do_ciclo(self, tempo: float) -> float:
        """Segundos desde o inicio do ciclo atual do fogo (0 = acabou de acender)."""
        return (tempo + self._defasagem) % self.CICLO_DO_FOGO

    def fogo_aceso(self, tempo: float) -> bool:
        return self._tipo is TipoDePerigo.FOGO and self.momento_do_ciclo(tempo) < self.FOGO_ACESO

    def desfazer(self) -> None:
        self._ativo = False


class CicloDeEvento:
    """Relogio de um fenomeno periodico: calmo -> aviso -> ativo -> calmo..."""

    RAMPA = 0.5  # segundos para o efeito chegar na forca total (e para sumir)

    def __init__(self, intervalo: float, duracao: float, aviso: float) -> None:
        if duracao + aviso >= intervalo:
            raise ValueError("duracao + aviso precisa ser menor que o intervalo")
        self._intervalo = intervalo
        self._duracao = duracao
        self._aviso = aviso
        self._tempo = 0.0

    @property
    def _posicao(self) -> float:
        return self._tempo % self._intervalo

    @property
    def _inicio(self) -> float:
        return self._intervalo - self._duracao

    @property
    def ativo(self) -> bool:
        return self._posicao >= self._inicio

    @property
    def em_aviso(self) -> bool:
        return self._inicio - self._aviso <= self._posicao < self._inicio

    @property
    def progresso_do_aviso(self) -> float:
        """0 no comeco do aviso, 1 quando o fenomeno esta para comecar."""
        if not self.em_aviso:
            return 0.0
        return (self._posicao - (self._inicio - self._aviso)) / self._aviso

    @property
    def restante(self) -> float:
        return self._intervalo - self._posicao if self.ativo else 0.0

    @property
    def intensidade(self) -> float:
        """0..1 - sobe e desce suave nas pontas (para efeitos nao darem tranco)."""
        if not self.ativo:
            return 0.0
        dentro = self._posicao - self._inicio
        return min(1.0, dentro / self.RAMPA, self.restante / self.RAMPA)

    def atualizar(self, dt: float) -> bool:
        """Avanca o relogio. Devolve True no quadro em que o fenomeno comeca."""
        antes = self.ativo
        self._tempo += dt
        return self.ativo and not antes

    def adiantar(self) -> None:
        """Pula direto para o comeco do proximo fenomeno (modo apresentacao)."""
        ciclo_atual = self._tempo - self._posicao
        if self.ativo:
            ciclo_atual += self._intervalo
        self._tempo = ciclo_atual + self._inicio - 1e-3


class Condicoes:
    """Cronometros dos efeitos ativos no jogador."""

    def __init__(self) -> None:
        self._restantes: dict[Condicao, float] = {}

    def aplicar(self, condicao: Condicao, duracao: float | None = None) -> None:
        """Liga (ou renova) o efeito - pegar outro igual nunca encurta o tempo."""
        duracao = DURACOES[condicao] if duracao is None else duracao
        self._restantes[condicao] = max(self._restantes.get(condicao, 0.0), duracao)

    def remover(self, condicao: Condicao) -> None:
        self._restantes.pop(condicao, None)

    def ativa(self, condicao: Condicao) -> bool:
        return self._restantes.get(condicao, 0.0) > 0

    def restante(self, condicao: Condicao) -> float:
        return max(0.0, self._restantes.get(condicao, 0.0))

    def ativas(self) -> tuple[tuple[Condicao, float], ...]:
        return tuple(self._restantes.items())

    def atualizar(self, dt: float) -> None:
        for condicao in list(self._restantes):
            self._restantes[condicao] -= dt
            if self._restantes[condicao] <= 0:
                del self._restantes[condicao]


# ======================================================================
class Ambiente:
    """Tudo o que ha de especial em uma fase alem das paredes.

    E o dono das regras de buff/debuff: a Fase so pede a `locomocao()`
    antes de mover o jogador e recolhe as `Ocorrencia`s depois.
    """

    BONUS_RELOGIO = 10.0
    DANO_DO_FOGO = 1
    VELOCIDADE_EM_PANICO = 1.25     # pegando fogo corre mais rapido (e sem rumo)
    TROCA_DE_RUMO = 0.28            # segundos ate mudar de direcao no panico
    VELOCIDADE_DESLIZANDO = 1.8
    DURACAO_DO_SALTO = 0.45
    VELOCIDADE_CAFE = 1.3
    LENTIDAO_TEMPESTADE = 0.45      # tira 45% da velocidade
    LENTIDAO_NEVASCA = 0.4          # tempestade de gelo: tira 40% da velocidade
    LENTIDAO_AREIA = 0.6
    MELHORA_DA_BLUSA = 3.0          # chao escorregadio: 3x mais aderencia
    VISAO_LANTERNA = 1.6
    QUEDA_VISAO_APAGAO = 0.7        # luz cai para 30%
    FORCA_RAJADA = 170.0            # pixels/s empurrando o jogador
    JATOS_DE_LAVA = 3               # tiles que entram em erupcao de cada vez ...
    ALCANCE_DA_ERUPCAO = 3          # ... sorteados ate esta distancia (em tiles) do jogador
    LAVA_QUEIMA_A_PARTIR = 0.3      # intensidade do jato a partir da qual ja queima
    DIRECOES = (Vetor2(1, 0), Vetor2(-1, 0), Vetor2(0, 1), Vetor2(0, -1))
    # itens novos
    VISAO_CAPACETE = 1.3
    RAIO_DO_EXTINTOR = 3            # tiles
    EXTINTOR_APAGA_MONSTRO = 5.0    # segundos que o magman fica de pedra / a fornalha apagada
    DURACAO_DA_TRAVESSIA = 0.5      # tapete passando por cima da parede
    DURACAO_DA_PERFURACAO = 0.7     # broca quebrando uma parede
    BONUS_DO_GENIO = 20.0
    PASSOS_DO_TELEPORTE = 6
    # monstros
    DANO_DO_MONSTRO = 1
    FORCA_DA_MORDIDA = 260.0        # empurraozinho (pixels/s) depois da mordida
    FORCA_DA_CHIFRADA = 480.0
    FORCA_DO_LACO = 380.0           # ~2 tiles em 0.3s
    DURACAO_DO_LACO = 0.3
    TONTURA_DA_ONDA = 2.0
    TEMPO_DO_VENENO = 6.0           # segundos para acertar as setas
    TEMPO_PERDIDO_NO_BURACO = 5.0
    ALCANCE_DO_ARREMESSO = 4        # tiles
    DURACAO_DO_ARREMESSO = 0.7
    MAXIMO_DE_BURACOS = 4
    ESPERA_DO_TUNEL = 1.5

    def __init__(self, labirinto: Labirinto, caixas: Iterable[CaixaSurpresa] = (),
                 perigos: Iterable[Perigo] = (), molas: Iterable[MolaDeParede] = (),
                 aderencia: float | None = None, fenomeno: Fenomeno | None = None,
                 sorteio: random.Random | None = None, ritmo_fenomenos: float = 1.0,
                 premios: Sequence[tuple[TipoDeItem, float]] = ITENS_COMUNS,
                 monstros: Iterable[Monstro] = (), historico: HistoricoDaRoleta | None = None) -> None:
        if not premios:
            raise ValueError("a roleta precisa de ao menos um premio")
        self._labirinto = labirinto
        self._caixas = tuple(caixas)
        self._perigos = tuple(perigos)
        self._molas = tuple(molas)
        self._monstros = tuple(monstros)
        self._aderencia = aderencia
        self._fenomeno = fenomeno
        self._ciclo = self._criar_ciclo(fenomeno, ritmo_fenomenos) if fenomeno else None
        self._sorteio = sorteio if sorteio is not None else random.Random()
        self._premios = tuple(premios)
        self._condicoes = Condicoes()
        self._tempo = 0.0
        self._sobre: set[int] = set()  # id() dos perigos que o jogador esta pisando
        self._na_areia = False
        self._direcao_rajada = Vetor2(1, 0)
        self._deslizando: Direcao | None = None
        self._desafio_da_teia: DesafioDaTeia | None = None
        self._veneno: float | None = None  # segundos para acertar as setas (picada de cobra)
        self._rumo_em_panico = Vetor2(1, 0)
        self._proxima_troca_de_rumo = 0.0
        self._jatos_de_lava: tuple[Coordenada, ...] = ()
        self._jatos_sorteados = False
        self._rastros: list[Perigo] = []  # perigos temporarios deixados pelos monstros
        self._jogador: Jogador | None = None
        self._novas: list[Ocorrencia] = []  # golpes dos monstros neste quadro
        self._empurrao = Vetor2()
        self._empurrao_ate = 0.0
        self._cargas_de_parede = 0
        self._caminho: tuple[Coordenada, ...] = ()
        self._caminho_calculado_em: Coordenada | None = None
        self._distancias_da_saida: dict[Coordenada, int] | None = None
        self._tunel_livre_em = 0.0
        self._extintor: tuple[float, float, float] | None = None  # (x, y, momento) para a tela
        self._perfuracao: list | None = None  # [tile da parede, segundos perfurando]
        self._ciclo_desligado: CicloDeEvento | None = None  # fenomeno desligado na arena
        self._historico = historico if historico is not None else HistoricoDaRoleta()

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------
    @property
    def labirinto(self) -> Labirinto:
        return self._labirinto

    @property
    def perfuracao(self) -> tuple[Coordenada, float] | None:
        """(parede sendo perfurada, progresso 0..1) enquanto a broca trabalha."""
        if self._perfuracao is None:
            return None
        return self._perfuracao[0], min(1.0, self._perfuracao[1] / self.DURACAO_DA_PERFURACAO)

    @property
    def caixas(self) -> tuple[CaixaSurpresa, ...]:
        return self._caixas

    @property
    def perigos(self) -> tuple[Perigo, ...]:
        return self._perigos

    @property
    def rastros(self) -> tuple[Perigo, ...]:
        """Perigos temporarios (lava, teia, gelo, buracos) deixados pelos monstros."""
        return tuple(p for p in self._rastros if p.ativo)

    @property
    def monstros(self) -> tuple[Monstro, ...]:
        return self._monstros

    @property
    def molas(self) -> tuple[MolaDeParede, ...]:
        return self._molas

    @property
    def premios(self) -> tuple[TipoDeItem, ...]:
        """Tudo o que pode sair na roleta deste mapa (as fatias da roleta)."""
        return tuple(tipo for tipo, _ in self._premios)

    @property
    def tempo(self) -> float:
        return self._tempo

    @property
    def fenomeno(self) -> Fenomeno | None:
        return self._fenomeno

    @property
    def ciclo(self) -> CicloDeEvento | None:
        return self._ciclo

    @property
    def direcao_da_rajada(self) -> Vetor2:
        return self._direcao_rajada

    @property
    def na_areia(self) -> bool:
        return self._na_areia and not self.imune_a_lentidao

    @property
    def deslizando(self) -> bool:
        return self._deslizando is not None

    @property
    def desafio_da_teia(self) -> DesafioDaTeia | None:
        """Sequencia de setas que o jogador precisa acertar (teia ou veneno; None = livre)."""
        return self._desafio_da_teia

    @property
    def envenenado(self) -> bool:
        return self._veneno is not None

    @property
    def veneno_restante(self) -> float:
        return max(0.0, self._veneno or 0.0)

    @property
    def cargas_de_parede(self) -> int:
        """Quantas paredes ainda da para atravessar (tapete: 1, broca: 2)."""
        return self._cargas_de_parede

    @property
    def melhor_caminho(self) -> tuple[Coordenada, ...]:
        """Tiles do jogador ate o portal (so enquanto o desejo do genio estiver ativo)."""
        return self._caminho if self._condicoes.ativa(Condicao.CAMINHO) else ()

    @property
    def extintor(self) -> tuple[float, float, float] | None:
        """(x, y, momento) do ultimo jato de extintor (para a tela desenhar a espuma)."""
        return self._extintor

    def condicao_ativa(self, condicao: Condicao) -> bool:
        return self._condicoes.ativa(condicao)

    def condicoes_ativas(self) -> tuple[tuple[Condicao, float], ...]:
        return self._condicoes.ativas()

    @property
    def jatos_de_lava(self) -> tuple[Coordenada, ...]:
        """Tiles marcados pela erupcao (rachando no aviso, jorrando lava quando ativa)."""
        return self._jatos_de_lava

    @property
    def imune_a_debuffs(self) -> bool:
        return self._condicoes.ativa(Condicao.ESTRELA)

    @property
    def imune_a_lentidao(self) -> bool:
        return self.imune_a_debuffs or self._condicoes.ativa(Condicao.CAFE)

    @property
    def imune_ao_frio(self) -> bool:
        """Blusa (ou estrela): nao congela na agua e nao desliza no gelo."""
        return self.imune_a_debuffs or self._condicoes.ativa(Condicao.BLUSA)

    @property
    def imune_ao_fogo(self) -> bool:
        """Estrela, flauta (apaga o fogo) ou bota de obsidiana."""
        return self.imune_a_debuffs or self.fogo_apagado or self._condicoes.ativa(Condicao.BOTA)

    @property
    def flutuando(self) -> bool:
        """Tapete magico: passa por cima do que esta no chao."""
        return self._condicoes.ativa(Condicao.TAPETE)

    # --- ContextoDosMonstros -------------------------------------------
    @property
    def jogador(self) -> Jogador:
        return self._jogador

    @property
    def tile_do_jogador(self) -> Coordenada:
        return self._tile_dos_pes(self._jogador.caixa_de_colisao())

    @property
    def monstros_dormindo(self) -> bool:
        return self._condicoes.ativa(Condicao.CALMARIA)

    @property
    def luz_forte(self) -> bool:
        return self._condicoes.ativa(Condicao.LANTERNA)

    @property
    def forca_da_tempestade(self) -> float:
        if self._fenomeno is not Fenomeno.TEMPESTADE_DE_AREIA or self._ciclo is None:
            return 0.0
        return self._ciclo.intensidade

    @property
    def fogo_apagado(self) -> bool:
        return self._condicoes.ativa(Condicao.CALMARIA)

    @property
    def travado(self) -> bool:
        return (self._condicoes.ativa(Condicao.CONGELADO) or self._condicoes.ativa(Condicao.CAIDO)
                or self._desafio_da_teia is not None)

    @property
    def fenomeno_neutralizado(self) -> bool:
        """O fenomeno acontece, mas nao afeta o jogador (estrela, flauta, cafe, guarda-chuva, capacete...)."""
        if self.imune_a_debuffs:
            return True
        c = self._condicoes
        if self._fenomeno is Fenomeno.TEMPESTADE_DE_AREIA:
            return self.fogo_apagado or self.imune_a_lentidao
        if self._fenomeno is Fenomeno.TEMPESTADE_DE_GELO:
            return self.imune_a_lentidao
        if self._fenomeno is Fenomeno.ERUPCAO:
            return self.imune_ao_fogo
        if self._fenomeno is Fenomeno.RAJADA:
            return c.ativa(Condicao.GUARDA_CHUVA)
        if self._fenomeno is Fenomeno.TERREMOTO:
            return c.ativa(Condicao.CAPACETE)
        return False

    def intensidade_do_fenomeno(self) -> float:
        """Forca com que o fenomeno esta afetando o jogador AGORA (0..1)."""
        if self._ciclo is None or self.fenomeno_neutralizado:
            return 0.0
        return self._ciclo.intensidade

    def locomocao(self) -> Locomocao:
        """Como o jogador pode se mover neste quadro."""
        c = self._condicoes
        if self._deslizando is not None:  # placa de gelo: sem controle ate bater
            return Locomocao(multiplicador=self.VELOCIDADE_DESLIZANDO,
                             intencao_forcada=vetor_da_direcao(self._deslizando))

        multiplicador = 1.0
        if c.ativa(Condicao.CAFE):
            multiplicador *= self.VELOCIDADE_CAFE
        forca = self.intensidade_do_fenomeno()
        if self._fenomeno is Fenomeno.TEMPESTADE_DE_AREIA:
            multiplicador *= 1 - self.LENTIDAO_TEMPESTADE * forca
        elif self._fenomeno is Fenomeno.TEMPESTADE_DE_GELO:
            multiplicador *= 1 - self.LENTIDAO_NEVASCA * forca
        if self.na_areia:
            multiplicador *= 1 - self.LENTIDAO_AREIA

        intencao_forcada = None
        if c.ativa(Condicao.QUEIMANDO):
            intencao_forcada = self._rumo_em_panico
            multiplicador = max(multiplicador, 1.0) * self.VELOCIDADE_EM_PANICO

        aderencia = self._aderencia
        if aderencia is not None and c.ativa(Condicao.BLUSA):
            aderencia *= self.MELHORA_DA_BLUSA

        arrasto = Vetor2()
        if self._fenomeno is Fenomeno.RAJADA and forca > 0:
            direcao = self._direcao_da_pipa() if c.ativa(Condicao.PIPA) else self._direcao_rajada
            arrasto = Vetor2(direcao.x * self.FORCA_RAJADA * forca, direcao.y * self.FORCA_RAJADA * forca)
        if self._tempo < self._empurrao_ate:
            arrasto = Vetor2(arrasto.x + self._empurrao.x, arrasto.y + self._empurrao.y)
        return Locomocao(
            multiplicador=multiplicador,
            aderencia=aderencia,
            travado=self.travado or self._perfuracao is not None,
            invertido=(self._fenomeno is Fenomeno.TERREMOTO and forca > 0) or c.ativa(Condicao.TONTO),
            arrasto=arrasto,
            intencao_forcada=intencao_forcada,
        )

    def multiplicador_de_visao(self) -> float:
        visao = self.VISAO_LANTERNA if self._condicoes.ativa(Condicao.LANTERNA) else 1.0
        if self._condicoes.ativa(Condicao.CAPACETE):
            visao *= self.VISAO_CAPACETE
        if self._fenomeno is Fenomeno.APAGAO:
            visao *= 1 - self.QUEDA_VISAO_APAGAO * self.intensidade_do_fenomeno()
        return visao

    def mapa_de_colisao(self, jogador: Jogador) -> MapaDeColisao:
        """Paredes + monstros solidos (golem). Quem ja esta encostado no jogador nao prende."""
        atual = jogador.caixa_de_colisao()
        solidos = [m.area_solida() for m in self._monstros if m.solido]
        solidos = [c for c in solidos if not c.intersecta(atual)]
        return _MapaComObstaculos(self._labirinto, solidos) if solidos else self._labirinto

    # ------------------------------------------------------------------
    # Comandos
    # ------------------------------------------------------------------
    def atualizar(self, dt: float, jogador: Jogador) -> list[Ocorrencia]:
        """Avanca relogios e aplica o que o jogador encostou. Devolve o que aconteceu."""
        ocorrencias: list[Ocorrencia] = []
        self._novas = []
        self._jogador = jogador
        self._tempo += dt
        self._condicoes.atualizar(dt)
        self._atualizar_veneno(dt)
        if not (self._condicoes.ativa(Condicao.TAPETE) or self._condicoes.ativa(Condicao.BROCA)):
            self._cargas_de_parede = 0
        quebrou = self._avancar_perfuracao(dt)
        if quebrou is not None:
            ocorrencias.append(quebrou)
        if self._ciclo is not None and self._ciclo.atualizar(dt):
            if self._fenomeno is Fenomeno.RAJADA:
                self._direcao_rajada = self._sorteio.choice(self.DIRECOES)
            ocorrencias.append(Ocorrencia(TipoDeOcorrencia.FENOMENO_COMECOU, fenomeno=self._fenomeno))
        if self._fenomeno is Fenomeno.ERUPCAO:
            self._marcar_jatos_de_lava(jogador)
        self._atualizar_panico(jogador)
        if self._deslizando is not None and (jogador.bateu or self.travado):
            self._deslizando = None  # bateu em algo: para de deslizar
        self._rastros = [p for p in self._rastros
                         if p.ativo and (p.expira_em is None or p.expira_em > self._tempo)]
        if self._condicoes.ativa(Condicao.CAMINHO) or self._condicoes.ativa(Condicao.PIPA):
            self._atualizar_caminho(jogador)
        for monstro in self._monstros:
            monstro.atualizar(dt, self)
        if jogador.pulando:
            return ocorrencias + self._novas  # no ar nao encosta em nada

        caixa = jogador.caixa_de_colisao()
        queimou_na_lava = self._lava_queimando(caixa)
        if queimou_na_lava is not None:
            ocorrencias.append(queimou_na_lava)
        for surpresa in self._caixas:
            if not surpresa.aberta and caixa.intersecta(surpresa.area()):
                surpresa.abrir()
                if surpresa.conteudo is not None:  # item largado no chao: pega direto, sem roleta
                    ocorrencias.append(self._dar_premio(surpresa.conteudo, TipoDeOcorrencia.BUFF_APLICADO))
                else:
                    ocorrencias.append(self._dar_premio(self.sortear_premio(), TipoDeOcorrencia.CAIXA_ABERTA))

        for mola in self._molas:
            if jogador.direcao is mola.direcao and caixa.intersecta(mola.area()):
                if self._lancar(mola, jogador):
                    ocorrencias.append(Ocorrencia(TipoDeOcorrencia.PULOU))
                    return ocorrencias + self._novas
        atravessou = self._tentar_atravessar_parede(jogador)
        if atravessou is not None:
            ocorrencias.append(atravessou)
            return ocorrencias + self._novas

        self._na_areia = False
        sobre_agora: set[int] = set()
        for perigo in self._perigos + tuple(self._rastros):
            if not perigo.ativo or not self._encostou(perigo, jogador, caixa):
                continue
            sobre_agora.add(id(perigo))
            ocorrencia = self._pisar(perigo, id(perigo) not in self._sobre, jogador)
            if ocorrencia is not None:
                ocorrencias.append(ocorrencia)
        self._sobre = sobre_agora
        return ocorrencias + self._novas

    def sortear_premio(self) -> TipoDeItem:
        """Roleta com MEMORIA: o que saiu ha pouco fica bem mais raro (menos item repetido)."""
        tipos, pesos = zip(*self._premios)
        pesos = [self._historico.peso(tipo, peso) for tipo, peso in zip(tipos, pesos)]
        premio = self._sorteio.choices(tipos, weights=pesos)[0]
        self._historico.registrar(premio)
        return premio

    def aplicar_premio(self, tipo: TipoDeItem) -> Ocorrencia:
        """Da o buff direto, sem caixa (usado no modo apresentacao)."""
        return self._dar_premio(tipo, TipoDeOcorrencia.BUFF_APLICADO)

    def abrir_caixa_virtual(self) -> Ocorrencia:
        """Sorteia e aplica um premio como se uma caixa "?" fosse aberta."""
        return self._dar_premio(self.sortear_premio(), TipoDeOcorrencia.CAIXA_ABERTA)

    def realizar_desejo(self, desejo: Desejo, jogador: Jogador) -> Ocorrencia:
        """Genio da lampada: o jogador escolheu um dos 3 desejos."""
        self._jogador = jogador
        if desejo is Desejo.TEMPO:
            return Ocorrencia(TipoDeOcorrencia.DESEJO_REALIZADO, item=TipoDeItem.GENIO, segundos=self.BONUS_DO_GENIO)
        if desejo is Desejo.CAMINHO:
            self._condicoes.aplicar(Condicao.CAMINHO)
            self._caminho_calculado_em = None
            self._atualizar_caminho(jogador)
        else:
            self._teleportar_para_perto_do_portal(jogador)
        return Ocorrencia(TipoDeOcorrencia.DESEJO_REALIZADO, item=TipoDeItem.GENIO)

    def forcar_fenomeno(self) -> None:
        """Faz o fenomeno do mapa comecar ja (modo teste dos mapas). Se estava desligado, liga."""
        self.ligar_fenomeno(True)
        if self._ciclo is not None:
            self._ciclo.adiantar()

    @property
    def fenomeno_ligado(self) -> bool:
        return self._ciclo_desligado is None

    def ligar_fenomeno(self, ligado: bool) -> None:
        """Arena do teste dos mapas: liga/desliga a tempestade, o apagao, o terremoto..."""
        if ligado and self._ciclo_desligado is not None:
            self._ciclo, self._ciclo_desligado = self._ciclo_desligado, None
        elif not ligado and self._ciclo is not None:
            self._ciclo_desligado, self._ciclo = self._ciclo, None
            self._jatos_de_lava = ()
            self._jatos_sorteados = False

    def apertar(self, direcao: Direcao) -> Ocorrencia | None:
        """Seta apertada enquanto esta preso na teia (fora da teia nao faz nada)."""
        desafio = self._desafio_da_teia
        if desafio is None:
            return None
        if not desafio.apertar(direcao):
            return Ocorrencia(TipoDeOcorrencia.TECLA_ERRADA)
        if desafio.concluido:
            self._desafio_da_teia = None
            if self._veneno is not None:
                self._veneno = None
                return Ocorrencia(TipoDeOcorrencia.CUROU_VENENO)
            return Ocorrencia(TipoDeOcorrencia.SOLTOU_DA_TEIA)
        return Ocorrencia(TipoDeOcorrencia.TECLA_CERTA)

    # ------------------------------------------------------------------
    # Monstros (ContextoDosMonstros)
    # ------------------------------------------------------------------
    def golpear(self, golpe: Golpe, monstro: Monstro) -> bool:
        """Um monstro acertou o jogador. Devolve False se alguma protecao segurou o golpe."""
        jogador = self._jogador
        if jogador is None or jogador.pulando or self.imune_a_debuffs or self.travado:
            return False  # preso/congelado/caido: os monstros nao "batem em quem esta no chao"
        c = self._condicoes
        if golpe is Golpe.QUEIMADURA:
            ocorrencia = self._queimar()
            if ocorrencia is not None:
                self._novas.append(ocorrencia)
            return ocorrencia is not None
        if golpe is Golpe.CONGELAMENTO:
            if self.imune_ao_frio or c.ativa(Condicao.CONGELADO):
                return False
            c.aplicar(Condicao.CONGELADO)
            self._deslizando = None
            jogador.parar()
            self._novas.append(Ocorrencia(TipoDeOcorrencia.CONGELOU))
            return True
        if golpe in (Golpe.TEIA, Golpe.VENENO):
            return self._prender(golpe, jogador)
        if golpe in (Golpe.ROUBO, Golpe.ARREMESSO) and c.ativa(Condicao.GUARDA_CHUVA):
            self._novas.append(Ocorrencia(TipoDeOcorrencia.GOLPE_BLOQUEADO, item=TipoDeItem.GUARDA_CHUVA))
            return False
        if golpe in (Golpe.BURACO, Golpe.ONDA_DE_CHOQUE) and c.ativa(Condicao.CAPACETE):
            self._novas.append(Ocorrencia(TipoDeOcorrencia.GOLPE_BLOQUEADO, item=TipoDeItem.CAPACETE))
            return False
        if golpe is Golpe.ROUBO:
            return self._roubar_buff(monstro)
        if golpe is Golpe.ARREMESSO:
            return self._arremessar(jogador)
        if golpe is Golpe.BURACO:
            if self.flutuando:
                return False
            c.aplicar(Condicao.CAIDO)
            jogador.parar()
            self._deslizando = None
            self._novas.append(Ocorrencia(TipoDeOcorrencia.CAIU_NO_BURACO, segundos=-self.TEMPO_PERDIDO_NO_BURACO))
            return True
        if golpe is Golpe.LACO:
            dx, dy = monstro.x - jogador.x, monstro.y - (jogador.y - Jogador.ALTURA_HITBOX / 2)
            self._empurrar(Vetor2(dx, dy), self.FORCA_DO_LACO, self.DURACAO_DO_LACO)
            self._novas.append(Ocorrencia(TipoDeOcorrencia.PUXADO))
            return True
        if golpe is Golpe.CHIFRADA:
            return self._ferir(monstro.direcao, self.FORCA_DA_CHIFRADA, 0.3)
        afastar = Vetor2(jogador.x - monstro.x, jogador.y - Jogador.ALTURA_HITBOX / 2 - monstro.y)
        if golpe is Golpe.ONDA_DE_CHOQUE:
            if not self._ferir(afastar, self.FORCA_DA_MORDIDA, 0.2):
                return False
            c.aplicar(Condicao.TONTO, self.TONTURA_DA_ONDA)
            return True
        return self._ferir(afastar, self.FORCA_DA_MORDIDA, 0.2)  # mordida

    # ------------------------------------------------------------------
    # Edicao (arena do teste dos mapas)
    # ------------------------------------------------------------------
    def colocar_perigo(self, tipo: TipoDePerigo, tile: Coordenada) -> None:
        """Troca o que houver no chao deste tile por um perigo permanente."""
        self._remover_do_chao(tile)
        defasagem = self._sorteio.uniform(0, Perigo.CICLO_DO_FOGO)
        self._perigos += (Perigo(tipo, tile, self._labirinto.centro_do_tile(tile), defasagem),)

    def colocar_caixa(self, tile: Coordenada, conteudo: TipoDeItem | None = None) -> None:
        """Caixa "?" (conteudo None) ou um item especifico largado no chao."""
        self._caixas = tuple(c for c in self._caixas if c.tile != tile)
        self._caixas += (CaixaSurpresa(tile, self._labirinto.centro_do_tile(tile), conteudo),)

    def colocar_monstro(self, monstro: Monstro) -> None:
        self._monstros += (monstro,)

    def limpar_tile(self, tile: Coordenada) -> bool:
        """Apaga tudo o que estiver neste tile (perigos, rastros, caixas, monstros). True se apagou algo."""
        antes = len(self._perigos) + len(self._rastros) + len(self._caixas) + len(self._monstros)
        self._remover_do_chao(tile)
        self._caixas = tuple(c for c in self._caixas if c.tile != tile)
        self._monstros = tuple(m for m in self._monstros if m.tile != tile and m.casa != tile)
        return len(self._perigos) + len(self._rastros) + len(self._caixas) + len(self._monstros) < antes

    def limpar_tudo(self) -> None:
        self._perigos, self._caixas, self._monstros, self._molas = (), (), (), ()
        self._rastros = []
        self.labirinto_mudou()

    def labirinto_mudou(self) -> None:
        """Paredes ou portal mudaram de lugar: esquece os caminhos ja calculados."""
        self._distancias_da_saida = None
        self._caminho_calculado_em = None
        self._caminho = ()

    def _remover_do_chao(self, tile: Coordenada) -> None:
        self._perigos = tuple(p for p in self._perigos if p.tile != tile)
        self._rastros = [p for p in self._rastros if p.tile != tile]

    def deixar_rastro(self, rastro: Rastro, tile: Coordenada, duracao: float) -> None:
        lab = self._labirinto
        if lab.eh_parede(*tile) or tile in (lab.entrada, lab.saida):
            return
        tipo = TIPO_DO_RASTRO[rastro]
        expira = None if math.isinf(duracao) else self._tempo + duracao
        for perigo in self._rastros:
            if perigo.tipo is tipo and perigo.tile == tile:
                perigo.renovar(expira if expira is not None else math.inf)
                return
        if tipo is TipoDePerigo.BURACO:
            buracos = [p for p in self._rastros if p.tipo is TipoDePerigo.BURACO]
            if len(buracos) >= self.MAXIMO_DE_BURACOS:
                self._rastros.remove(buracos[0])
        self._rastros.append(Perigo(tipo, tile, lab.centro_do_tile(tile), expira_em=expira))

    # ------------------------------------------------------------------
    @staticmethod
    def _criar_ciclo(fenomeno: Fenomeno, ritmo: float) -> CicloDeEvento:
        """ritmo < 1 encurta o intervalo entre um fenomeno e outro (dificuldade)."""
        intervalo, duracao, aviso = CICLOS_DOS_FENOMENOS[fenomeno]
        intervalo = max(intervalo * ritmo, duracao + aviso + 1.0)
        return CicloDeEvento(intervalo, duracao, aviso)

    def _dar_premio(self, tipo: TipoDeItem, como: TipoDeOcorrencia) -> Ocorrencia:
        if tipo is TipoDeItem.RELOGIO:
            return Ocorrencia(como, item=tipo, segundos=self.BONUS_RELOGIO)
        if tipo is TipoDeItem.CORACAO:
            return Ocorrencia(como, item=tipo, cura=1)
        if tipo is TipoDeItem.GENIO:  # o jogador escolhe o desejo numa tela propria
            return Ocorrencia(como, item=tipo)
        if tipo is TipoDeItem.EXTINTOR:
            self._usar_extintor()
            return Ocorrencia(como, item=tipo)
        self._condicoes.aplicar(CONDICAO_DO_ITEM[tipo])
        if tipo in CARGAS_DE_PAREDE:
            self._cargas_de_parede = max(self._cargas_de_parede, CARGAS_DE_PAREDE[tipo])
        return Ocorrencia(como, item=tipo)

    # --- itens ---------------------------------------------------------
    def _usar_extintor(self) -> None:
        """Apaga fogo e lava em volta (para sempre) e apaga o magman/fornalha por alguns segundos."""
        jogador = self._jogador
        if jogador is None:
            return
        centro = self._tile_dos_pes(jogador.caixa_de_colisao())
        raio = self.RAIO_DO_EXTINTOR
        for perigo in self._perigos + tuple(self._rastros):
            if perigo.tipo in (TipoDePerigo.FOGO, TipoDePerigo.LAVA) and manhattan(perigo.tile, centro) <= raio:
                perigo.desfazer()
        self._jatos_de_lava = tuple(t for t in self._jatos_de_lava if manhattan(t, centro) > raio)
        for monstro in self._monstros:
            if manhattan(monstro.tile, centro) <= raio:
                monstro.apagar(self.EXTINTOR_APAGA_MONSTRO)
        self._extintor = (jogador.x, jogador.y, self._tempo)

    def _tentar_atravessar_parede(self, jogador: Jogador) -> Ocorrencia | None:
        """Andou contra uma parede com carga: a BROCA comeca a perfurar; o TAPETE voa por cima (parede fina)."""
        if (self._cargas_de_parede <= 0 or not jogador.bateu or self.travado or self._deslizando is not None
                or self._perfuracao is not None):
            return None
        lab = self._labirinto
        tile = self._tile_dos_pes(jogador.caixa_de_colisao())
        dx, dy = DELTAS_DA_DIRECAO[jogador.direcao]
        parede = Coordenada(tile.coluna + dx, tile.linha + dy)
        destino = Coordenada(tile.coluna + 2 * dx, tile.linha + 2 * dy)
        borda = not (0 < parede.coluna < lab.colunas - 1 and 0 < parede.linha < lab.linhas - 1)
        if borda or not lab.eh_parede(*parede):
            return None
        if self._condicoes.ativa(Condicao.BROCA) and isinstance(lab, LabirintoEditavel):
            self._perfuracao = [parede, 0.0]  # a parede quebra de verdade quando terminar
            jogador.parar()
            self._deslizando = None
            return Ocorrencia(TipoDeOcorrencia.COMECOU_A_PERFURAR, item=TipoDeItem.BROCA)
        if lab.eh_parede(*destino):
            return None
        x, y = lab.centro_do_tile(destino)
        if not jogador.saltar(x, y + Jogador.ALTURA_DOS_PES, self.DURACAO_DA_TRAVESSIA, lab):
            return None
        self._cargas_de_parede -= 1
        item = TipoDeItem.BROCA if self._condicoes.ativa(Condicao.BROCA) else TipoDeItem.TAPETE
        return Ocorrencia(TipoDeOcorrencia.ATRAVESSOU_PAREDE, item=item)

    def _avancar_perfuracao(self, dt: float) -> Ocorrencia | None:
        """Broca girando contra a parede; no fim, a parede vira chao."""
        if self._perfuracao is None:
            return None
        self._perfuracao[1] += dt
        if self._perfuracao[1] < self.DURACAO_DA_PERFURACAO:
            return None
        tile = self._perfuracao[0]
        self._perfuracao = None
        if not self._labirinto.remover_parede(tile):
            return None
        self._cargas_de_parede -= 1
        if self._cargas_de_parede <= 0:
            self._condicoes.remover(Condicao.BROCA)  # acabou a broca: some da mao
        self.labirinto_mudou()
        return Ocorrencia(TipoDeOcorrencia.QUEBROU_PAREDE, item=TipoDeItem.BROCA)

    def _distancias_ate_a_saida(self) -> dict[Coordenada, int]:
        if self._distancias_da_saida is None:
            self._distancias_da_saida = distancias(self._labirinto, self._labirinto.saida)
        return self._distancias_da_saida

    def _atualizar_caminho(self, jogador: Jogador) -> None:
        """Melhor caminho ate o portal (recalcula so quando o jogador muda de tile)."""
        tile = self._tile_dos_pes(jogador.caixa_de_colisao())
        if tile != self._caminho_calculado_em:
            self._caminho = tuple(caminho(self._labirinto, tile, self._labirinto.saida))
            self._caminho_calculado_em = tile

    def _direcao_da_pipa(self) -> Vetor2:
        """Com a pipa, o vento sopra para o proximo passo do melhor caminho."""
        if len(self._caminho) < 2:
            return self._direcao_rajada
        a, b = self._caminho[0], self._caminho[1]
        return Vetor2(b.coluna - a.coluna, b.linha - a.linha)

    def _teleportar_para_perto_do_portal(self, jogador: Jogador) -> None:
        trajeto = caminho(self._labirinto, self._tile_dos_pes(jogador.caixa_de_colisao()), self._labirinto.saida)
        if len(trajeto) < 3:
            return
        destino = trajeto[min(self.PASSOS_DO_TELEPORTE, len(trajeto) - 2)]
        x, y = self._labirinto.centro_do_tile(destino)
        if jogador.posicionar(x, y + Jogador.ALTURA_DOS_PES, self._labirinto):
            jogador.parar()
            self._deslizando = None

    # --- golpes dos monstros -------------------------------------------
    def _ferir(self, direcao: Vetor2, forca: float, duracao: float) -> bool:
        c = self._condicoes
        if c.ativa(Condicao.INVULNERAVEL) or c.ativa(Condicao.PROTEGIDO):
            return False
        c.aplicar(Condicao.INVULNERAVEL)
        self._empurrar(direcao, forca, duracao)
        self._novas.append(Ocorrencia(TipoDeOcorrencia.MONSTRO_ATACOU, dano=self.DANO_DO_MONSTRO))
        return True

    def _empurrar(self, direcao: Vetor2, forca: float, duracao: float) -> None:
        if direcao.eh_nulo:
            return
        norma = direcao.norma
        self._empurrao = Vetor2(direcao.x / norma * forca, direcao.y / norma * forca)
        self._empurrao_ate = self._tempo + duracao
        self._deslizando = None

    def _prender(self, golpe: Golpe, jogador: Jogador) -> bool:
        """Teia (aranha) ou veneno (cobra): setas em ordem para se soltar."""
        if self._desafio_da_teia is not None or self.flutuando:
            return False
        self._desafio_da_teia = DesafioDaTeia.sortear(self._sorteio)
        self._deslizando = None
        jogador.parar()
        if golpe is Golpe.VENENO:
            self._veneno = self.TEMPO_DO_VENENO
            self._novas.append(Ocorrencia(TipoDeOcorrencia.ENVENENOU))
        else:
            self._novas.append(Ocorrencia(TipoDeOcorrencia.FICOU_PRESO))
        return True

    def _atualizar_veneno(self, dt: float) -> None:
        if self._veneno is None:
            return
        self._veneno -= dt
        if self._veneno <= 0:
            self._veneno = None
            self._desafio_da_teia = None
            self._novas.append(Ocorrencia(TipoDeOcorrencia.VENENO_FEZ_EFEITO, dano=self.DANO_DO_MONSTRO))

    def _roubar_buff(self, monstro: Monstro) -> bool:
        ativos = [c for c in BUFFS_ROUBAVEIS if self._condicoes.ativa(c)]
        if ativos:
            roubado = self._sorteio.choice(ativos)
            self._condicoes.remover(roubado)
            if roubado in (Condicao.TAPETE, Condicao.BROCA):
                self._cargas_de_parede = 0
            self._novas.append(Ocorrencia(TipoDeOcorrencia.ROUBOU_BUFF, item=ITEM_DA_CONDICAO[roubado]))
            return True
        if monstro.agressivo:
            return self._ferir(Vetor2(0, 1), self.FORCA_DA_MORDIDA, 0.15)
        self._novas.append(Ocorrencia(TipoDeOcorrencia.ROUBOU_BUFF))
        return True

    def _arremessar(self, jogador: Jogador) -> bool:
        """Tornado: joga o jogador alguns tiles para LONGE do portal (com a pipa, para PERTO)."""
        distancias_da_saida = self._distancias_ate_a_saida()
        atual = self._tile_dos_pes(jogador.caixa_de_colisao())
        d0 = distancias_da_saida.get(atual, 0)
        para_o_portal = self._condicoes.ativa(Condicao.PIPA)
        lab = self._labirinto
        candidatos = [t for t, d in distancias_da_saida.items()
                      if 2 <= manhattan(t, atual) <= self.ALCANCE_DO_ARREMESSO
                      and t not in (lab.saida, lab.entrada) and (d < d0 if para_o_portal else d > d0)]
        candidatos.sort(key=lambda t: (distancias_da_saida[t] if para_o_portal else -distancias_da_saida[t])
                        + self._sorteio.random() * 3)
        for tile in candidatos[:10]:
            x, y = lab.centro_do_tile(tile)
            if jogador.saltar(x, y + Jogador.ALTURA_DOS_PES, self.DURACAO_DO_ARREMESSO, lab):
                self._deslizando = None
                self._condicoes.aplicar(Condicao.TONTO)
                self._novas.append(Ocorrencia(TipoDeOcorrencia.ARREMESSADO,
                                              item=TipoDeItem.PIPA if para_o_portal else None))
                return True
        return False

    def _atravessar_tunel(self, entrada: Perigo, jogador: Jogador) -> Ocorrencia | None:
        buracos = [p for p in self._perigos + tuple(self._rastros) if p.tipo is TipoDePerigo.BURACO and p.ativo]
        if len(buracos) < 2 or self._tempo < self._tunel_livre_em or entrada not in buracos:
            return None
        saida = buracos[(buracos.index(entrada) + 1) % len(buracos)]
        x, y = saida.centro
        if not jogador.posicionar(x, y + Jogador.ALTURA_DOS_PES, self._labirinto):
            return None
        jogador.parar()
        self._tunel_livre_em = self._tempo + self.ESPERA_DO_TUNEL
        return Ocorrencia(TipoDeOcorrencia.ATRAVESSOU_TUNEL)

    def _atualizar_panico(self, jogador: Jogador) -> None:
        """Pegando fogo: troca de rumo toda hora (e quando bate na parede)."""
        if not self._condicoes.ativa(Condicao.QUEIMANDO):
            return
        if self._tempo >= self._proxima_troca_de_rumo or jogador.bateu:
            opcoes = [d for d in self.DIRECOES if d != self._rumo_em_panico]
            self._rumo_em_panico = self._sorteio.choice(opcoes)
            self._proxima_troca_de_rumo = self._tempo + self.TROCA_DE_RUMO

    def _lancar(self, mola: MolaDeParede, jogador: Jogador) -> bool:
        x, y = self._labirinto.centro_do_tile(mola.destino)
        if not jogador.saltar(x, y + Jogador.ALTURA_DOS_PES, self.DURACAO_DO_SALTO, self._labirinto):
            return False
        mola.acionar(self._tempo)
        self._deslizando = None
        return True

    def _encostou(self, perigo: Perigo, jogador: Jogador, caixa: Caixa) -> bool:
        if perigo.tipo is TipoDePerigo.GELO:  # placa: conta quando o centro dos pes esta nela
            return self._tile_dos_pes(caixa) == perigo.tile
        return caixa.intersecta(perigo.area())

    def _tile_dos_pes(self, caixa: Caixa) -> Coordenada:
        t = self._labirinto.tamanho_tile
        return Coordenada((caixa.esquerda + caixa.largura // 2) // t, (caixa.topo + caixa.altura // 2) // t)

    def _queimar(self) -> Ocorrencia | None:
        """Fogo e lava: -1 coracao e sai correndo descontrolado (com folga para nao queimar em seguida)."""
        if self.imune_ao_fogo or self._condicoes.ativa(Condicao.PROTEGIDO):
            return None
        self._condicoes.aplicar(Condicao.QUEIMANDO)
        self._condicoes.aplicar(Condicao.PROTEGIDO)
        self._deslizando = None
        self._proxima_troca_de_rumo = self._tempo  # ja sai correndo
        return Ocorrencia(TipoDeOcorrencia.QUEIMOU, dano=self.DANO_DO_FOGO)

    def _marcar_jatos_de_lava(self, jogador: Jogador) -> None:
        """No comeco do aviso, sorteia os tiles perto do jogador que vao entrar em erupcao."""
        ciclo = self._ciclo
        if ciclo is None or not (ciclo.em_aviso or ciclo.ativo):
            self._jatos_de_lava = ()
            self._jatos_sorteados = False
            return
        if self._jatos_sorteados:  # o extintor pode ter apagado alguns: nao sorteia de novo
            return
        self._jatos_sorteados = True
        perto = self._tile_dos_pes(jogador.caixa_de_colisao())
        a = self.ALCANCE_DA_ERUPCAO
        candidatos = [Coordenada(c, l)
                      for l in range(perto.linha - a, perto.linha + a + 1)
                      for c in range(perto.coluna - a, perto.coluna + a + 1)
                      if abs(c - perto.coluna) + abs(l - perto.linha) <= a and not self._labirinto.eh_parede(c, l)
                      and Coordenada(c, l) not in (self._labirinto.entrada, self._labirinto.saida)]
        self._jatos_de_lava = tuple(self._sorteio.sample(candidatos, min(self.JATOS_DE_LAVA, len(candidatos))))

    def _lava_queimando(self, caixa: Caixa) -> Ocorrencia | None:
        ciclo = self._ciclo
        if (self._fenomeno is not Fenomeno.ERUPCAO or ciclo is None or not ciclo.ativo
                or ciclo.intensidade < self.LAVA_QUEIMA_A_PARTIR):
            return None
        if self._tile_dos_pes(caixa) not in self._jatos_de_lava:
            return None
        return self._queimar()

    def _pisar(self, perigo: Perigo, acabou_de_entrar: bool, jogador: Jogador) -> Ocorrencia | None:
        if perigo.tipo in (TipoDePerigo.FOGO, TipoDePerigo.LAVA):
            if perigo.tipo is TipoDePerigo.LAVA or perigo.fogo_aceso(self._tempo):
                return self._queimar()
            return None
        if self.flutuando:  # tapete magico: passa por cima de tudo que esta no chao
            return None
        if perigo.tipo is TipoDePerigo.AREIA_MOVEDICA:
            self._na_areia = True
            return None
        if perigo.tipo is TipoDePerigo.BURACO:
            return self._atravessar_tunel(perigo, jogador) if acabou_de_entrar else None
        if self.imune_a_debuffs:
            return None

        if perigo.tipo is TipoDePerigo.AGUA:
            if acabou_de_entrar and not self.imune_ao_frio:
                self._condicoes.aplicar(Condicao.CONGELADO)
                self._deslizando = None
                jogador.parar()
                return Ocorrencia(TipoDeOcorrencia.CONGELOU)
        elif perigo.tipo is TipoDePerigo.GELO:
            if acabou_de_entrar and self._deslizando is None and jogador.esta_andando and not self.imune_ao_frio:
                return self._comecar_a_deslizar(perigo, jogador)
        elif perigo.tipo is TipoDePerigo.TEIA:
            if acabou_de_entrar and self._desafio_da_teia is None:
                self._desafio_da_teia = DesafioDaTeia.sortear(self._sorteio)
                self._deslizando = None
                perigo.desfazer()  # o jogador rasga a teia quando se solta
                jogador.parar()
                return Ocorrencia(TipoDeOcorrencia.FICOU_PRESO)
        return None

    def _comecar_a_deslizar(self, perigo: Perigo, jogador: Jogador) -> Ocorrencia:
        """Alinha o jogador no meio do corredor (para nao enroscar) e desliza para frente."""
        direcao = jogador.direcao
        x, y = perigo.centro
        if direcao in (Direcao.ESQUERDA, Direcao.DIREITA):
            jogador.posicionar(jogador.x, y + Jogador.ALTURA_DOS_PES, self._labirinto)
        else:
            jogador.posicionar(x, jogador.y, self._labirinto)
        self._deslizando = direcao
        return Ocorrencia(TipoDeOcorrencia.COMECOU_A_DESLIZAR)


TIPO_DO_RASTRO: dict[Rastro, TipoDePerigo] = {
    Rastro.LAVA: TipoDePerigo.LAVA,
    Rastro.TEIA: TipoDePerigo.TEIA,
    Rastro.GELO: TipoDePerigo.GELO,
    Rastro.BURACO: TipoDePerigo.BURACO,
}


class _MapaComObstaculos:
    """Paredes do labirinto + caixas solidas (monstros que bloqueiam o corredor)."""

    def __init__(self, labirinto: Labirinto, obstaculos: Sequence[Caixa]) -> None:
        self._labirinto = labirinto
        self._obstaculos = tuple(obstaculos)

    def colide(self, caixa: Caixa) -> bool:
        return self._labirinto.colide(caixa) or any(caixa.intersecta(o) for o in self._obstaculos)
