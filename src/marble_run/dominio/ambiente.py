"""
ambiente.py - Caixas surpresa (BUFFS), perigos (DEBUFFS) e fenomenos de cada fase.

    CaixaSurpresa -> caixa "?" no chao; ao abrir, sorteia um buff (a roleta e so visual)
    MolaDeParede  -> mola presa na parede: andou contra ela, pula para o outro lado
    Perigo        -> tile perigoso (agua que congela, fogo, teia, areia movedica,
                     placa de gelo que faz deslizar ate bater em algo)
    Fenomeno      -> evento periodico do mapa (tempestade de areia, apagao, terremoto,
                     rajada de vento, erupcao de lava), controlado por um CicloDeEvento
    Condicoes     -> efeitos temporarios no jogador (congelado, banana, estrela...)

O Ambiente junta tudo isso e responde as duas perguntas que a Fase faz a
cada quadro: "como o jogador pode se mover agora?" (locomocao) e "o que
aconteceu depois que ele se moveu?" (ocorrencias). Nada aqui importa pygame.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import Iterable, Sequence

from .geometria import Caixa, Vetor2
from .jogador import Direcao, Jogador, Locomocao
from .labirinto import Coordenada, Labirinto


class TipoDeItem(Enum):
    """Os buffs que podem sair na roleta da caixa surpresa."""

    BLUSA = "blusa"
    BANANA = "banana"
    FLAUTA = "flauta"
    RELOGIO = "relogio"
    LANTERNA = "lanterna"
    ESTRELA = "estrela"
    BUSSOLA = "bussola"
    CAFE = "cafe"


class TipoDePerigo(Enum):
    AGUA = "agua"
    FOGO = "fogo"
    TEIA = "teia"
    AREIA_MOVEDICA = "areia_movedica"
    GELO = "gelo"  # placa de gelo: desliza ate bater em algo (estilo Pokemon)


class Fenomeno(Enum):
    TEMPESTADE_DE_AREIA = "tempestade_de_areia"
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
    BANANA = auto()
    CAFE = auto()
    LANTERNA = auto()
    ESTRELA = auto()
    BUSSOLA = auto()
    CALMARIA = auto()    # efeito da flauta


DURACOES: dict[Condicao, float] = {
    Condicao.CONGELADO: 2.0,
    Condicao.QUEIMANDO: 1.5,
    Condicao.PROTEGIDO: 2.5,
    Condicao.BLUSA: 10.0,
    Condicao.BANANA: 5.0,
    Condicao.CAFE: 8.0,
    Condicao.LANTERNA: 12.0,
    Condicao.ESTRELA: 6.0,
    Condicao.BUSSOLA: 15.0,
    Condicao.CALMARIA: 8.0,
}

CONDICAO_DO_ITEM: dict[TipoDeItem, Condicao] = {
    TipoDeItem.BLUSA: Condicao.BLUSA,
    TipoDeItem.BANANA: Condicao.BANANA,
    TipoDeItem.CAFE: Condicao.CAFE,
    TipoDeItem.LANTERNA: Condicao.LANTERNA,
    TipoDeItem.ESTRELA: Condicao.ESTRELA,
    TipoDeItem.BUSSOLA: Condicao.BUSSOLA,
    TipoDeItem.FLAUTA: Condicao.CALMARIA,
}

# (item, peso no sorteio) que podem sair em QUALQUER mapa
ITENS_COMUNS: tuple[tuple[TipoDeItem, int], ...] = (
    (TipoDeItem.RELOGIO, 4),
    (TipoDeItem.LANTERNA, 3),
    (TipoDeItem.CAFE, 3),
    (TipoDeItem.BUSSOLA, 2),
    (TipoDeItem.ESTRELA, 1),
)

# (intervalo entre inicios, duracao, aviso antes de comecar) em segundos
CICLOS_DOS_FENOMENOS: dict[Fenomeno, tuple[float, float, float]] = {
    Fenomeno.TEMPESTADE_DE_AREIA: (12.0, 4.0, 2.0),
    Fenomeno.APAGAO: (14.0, 3.0, 1.5),
    Fenomeno.TERREMOTO: (15.0, 4.0, 2.0),
    Fenomeno.RAJADA: (9.0, 1.6, 1.2),
    Fenomeno.ERUPCAO: (8.0, 1.4, 1.8),
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


@dataclass(frozen=True)
class Ocorrencia:
    """Algo que aconteceu na fase (som, tremor de tela, roleta, dano...)."""

    tipo: TipoDeOcorrencia
    item: TipoDeItem | None = None
    fenomeno: Fenomeno | None = None
    segundos: float = 0.0  # ajuste no cronometro (relogio)
    dano: int = 0          # coracoes perdidos (fogo)


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
    LADO = 30  # area de coleta, em pixels do mapa

    def __init__(self, tile: Coordenada, centro: tuple[int, int]) -> None:
        self._tile = tile
        self._centro = centro
        self._aberta = False

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
    }

    def __init__(self, tipo: TipoDePerigo, tile: Coordenada, centro: tuple[int, int],
                 defasagem: float = 0.0) -> None:
        self._tipo = tipo
        self._tile = tile
        self._centro = centro
        self._defasagem = defasagem
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
    VELOCIDADE_BANANA = 1.5
    VELOCIDADE_CAFE = 1.3
    LENTIDAO_TEMPESTADE = 0.45      # tira 45% da velocidade
    LENTIDAO_AREIA = 0.6
    MELHORA_DA_BLUSA = 3.0          # chao escorregadio: 3x mais aderencia
    VISAO_LANTERNA = 1.6
    QUEDA_VISAO_APAGAO = 0.7        # luz cai para 30%
    FORCA_RAJADA = 170.0            # pixels/s empurrando o jogador
    JATOS_DE_LAVA = 5               # tiles que entram em erupcao de cada vez ...
    ALCANCE_DA_ERUPCAO = 4          # ... sorteados ate esta distancia (em tiles) do jogador
    LAVA_QUEIMA_A_PARTIR = 0.3      # intensidade do jato a partir da qual ja queima
    DIRECOES = (Vetor2(1, 0), Vetor2(-1, 0), Vetor2(0, 1), Vetor2(0, -1))

    def __init__(self, labirinto: Labirinto, caixas: Iterable[CaixaSurpresa] = (),
                 perigos: Iterable[Perigo] = (), molas: Iterable[MolaDeParede] = (),
                 aderencia: float | None = None, fenomeno: Fenomeno | None = None,
                 sorteio: random.Random | None = None, ritmo_fenomenos: float = 1.0,
                 premios: Sequence[tuple[TipoDeItem, int]] = ITENS_COMUNS) -> None:
        if not premios:
            raise ValueError("a roleta precisa de ao menos um premio")
        self._labirinto = labirinto
        self._caixas = tuple(caixas)
        self._perigos = tuple(perigos)
        self._molas = tuple(molas)
        self._aderencia = aderencia
        self._fenomeno = fenomeno
        self._ciclo = self._criar_ciclo(fenomeno, ritmo_fenomenos) if fenomeno else None
        self._sorteio = sorteio if sorteio is not None else random.Random()
        self._premios = tuple(premios)
        self._condicoes = Condicoes()
        self._tempo = 0.0
        self._sobre: set[int] = set()  # perigos que o jogador esta pisando
        self._na_areia = False
        self._direcao_rajada = Vetor2(1, 0)
        self._deslizando: Direcao | None = None
        self._desafio_da_teia: DesafioDaTeia | None = None
        self._rumo_em_panico = Vetor2(1, 0)
        self._proxima_troca_de_rumo = 0.0
        self._jatos_de_lava: tuple[Coordenada, ...] = ()

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------
    @property
    def caixas(self) -> tuple[CaixaSurpresa, ...]:
        return self._caixas

    @property
    def perigos(self) -> tuple[Perigo, ...]:
        return self._perigos

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
        """Sequencia de setas que o jogador precisa acertar (None = nao esta preso)."""
        return self._desafio_da_teia

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
    def fogo_apagado(self) -> bool:
        return self._condicoes.ativa(Condicao.CALMARIA)

    @property
    def travado(self) -> bool:
        return self._condicoes.ativa(Condicao.CONGELADO) or self._desafio_da_teia is not None

    @property
    def fenomeno_neutralizado(self) -> bool:
        """O fenomeno acontece, mas nao afeta o jogador (estrela, flauta, cafe...)."""
        if self.imune_a_debuffs:
            return True
        if self._fenomeno is Fenomeno.TEMPESTADE_DE_AREIA:
            return self.fogo_apagado or self.imune_a_lentidao
        if self._fenomeno is Fenomeno.ERUPCAO:
            return self.fogo_apagado
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
        if c.ativa(Condicao.BANANA):
            multiplicador *= self.VELOCIDADE_BANANA
        if c.ativa(Condicao.CAFE):
            multiplicador *= self.VELOCIDADE_CAFE
        forca = self.intensidade_do_fenomeno()
        if self._fenomeno is Fenomeno.TEMPESTADE_DE_AREIA:
            multiplicador *= 1 - self.LENTIDAO_TEMPESTADE * forca
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
            arrasto = Vetor2(self._direcao_rajada.x * self.FORCA_RAJADA * forca,
                             self._direcao_rajada.y * self.FORCA_RAJADA * forca)
        return Locomocao(
            multiplicador=multiplicador,
            aderencia=aderencia,
            travado=self.travado,
            invertido=self._fenomeno is Fenomeno.TERREMOTO and forca > 0,
            arrasto=arrasto,
            intencao_forcada=intencao_forcada,
        )

    def multiplicador_de_visao(self) -> float:
        visao = self.VISAO_LANTERNA if self._condicoes.ativa(Condicao.LANTERNA) else 1.0
        if self._fenomeno is Fenomeno.APAGAO:
            visao *= 1 - self.QUEDA_VISAO_APAGAO * self.intensidade_do_fenomeno()
        return visao

    # ------------------------------------------------------------------
    # Comandos
    # ------------------------------------------------------------------
    def atualizar(self, dt: float, jogador: Jogador) -> list[Ocorrencia]:
        """Avanca relogios e aplica o que o jogador encostou. Devolve o que aconteceu."""
        ocorrencias: list[Ocorrencia] = []
        self._tempo += dt
        self._condicoes.atualizar(dt)
        if self._ciclo is not None and self._ciclo.atualizar(dt):
            if self._fenomeno is Fenomeno.RAJADA:
                self._direcao_rajada = self._sorteio.choice(self.DIRECOES)
            ocorrencias.append(Ocorrencia(TipoDeOcorrencia.FENOMENO_COMECOU, fenomeno=self._fenomeno))
        if self._fenomeno is Fenomeno.ERUPCAO:
            self._marcar_jatos_de_lava(jogador)
        self._atualizar_panico(jogador)
        if self._deslizando is not None and (jogador.bateu or self.travado):
            self._deslizando = None  # bateu em algo: para de deslizar
        if jogador.pulando:
            return ocorrencias  # no ar nao encosta em nada

        caixa = jogador.caixa_de_colisao()
        queimou_na_lava = self._lava_queimando(caixa)
        if queimou_na_lava is not None:
            ocorrencias.append(queimou_na_lava)
        for surpresa in self._caixas:
            if not surpresa.aberta and caixa.intersecta(surpresa.area()):
                surpresa.abrir()
                premio = self.sortear_premio()
                ocorrencias.append(self._dar_premio(premio, TipoDeOcorrencia.CAIXA_ABERTA))

        for mola in self._molas:
            if jogador.direcao is mola.direcao and caixa.intersecta(mola.area()):
                if self._lancar(mola, jogador):
                    ocorrencias.append(Ocorrencia(TipoDeOcorrencia.PULOU))
                    return ocorrencias

        self._na_areia = False
        sobre_agora: set[int] = set()
        for indice, perigo in enumerate(self._perigos):
            if not perigo.ativo or not self._encostou(perigo, jogador, caixa):
                continue
            sobre_agora.add(indice)
            ocorrencia = self._pisar(perigo, indice not in self._sobre, jogador)
            if ocorrencia is not None:
                ocorrencias.append(ocorrencia)
        self._sobre = sobre_agora
        return ocorrencias

    def sortear_premio(self) -> TipoDeItem:
        tipos, pesos = zip(*self._premios)
        return self._sorteio.choices(tipos, weights=pesos)[0]

    def aplicar_premio(self, tipo: TipoDeItem) -> Ocorrencia:
        """Da o buff direto, sem caixa (usado no modo apresentacao)."""
        return self._dar_premio(tipo, TipoDeOcorrencia.BUFF_APLICADO)

    def abrir_caixa_virtual(self) -> Ocorrencia:
        """Sorteia e aplica um premio como se uma caixa "?" fosse aberta."""
        return self._dar_premio(self.sortear_premio(), TipoDeOcorrencia.CAIXA_ABERTA)

    def forcar_fenomeno(self) -> None:
        """Faz o fenomeno do mapa comecar ja (modo teste dos mapas)."""
        if self._ciclo is not None:
            self._ciclo.adiantar()

    def apertar(self, direcao: Direcao) -> Ocorrencia | None:
        """Seta apertada enquanto esta preso na teia (fora da teia nao faz nada)."""
        desafio = self._desafio_da_teia
        if desafio is None:
            return None
        if not desafio.apertar(direcao):
            return Ocorrencia(TipoDeOcorrencia.TECLA_ERRADA)
        if desafio.concluido:
            self._desafio_da_teia = None
            return Ocorrencia(TipoDeOcorrencia.SOLTOU_DA_TEIA)
        return Ocorrencia(TipoDeOcorrencia.TECLA_CERTA)

    # ------------------------------------------------------------------
    @staticmethod
    def _criar_ciclo(fenomeno: Fenomeno, ritmo: float) -> CicloDeEvento:
        """ritmo < 1 encurta o intervalo entre um fenomeno e outro (dificuldade)."""
        intervalo, duracao, aviso = CICLOS_DOS_FENOMENOS[fenomeno]
        intervalo = max(intervalo * ritmo, duracao + aviso + 1.0)
        return CicloDeEvento(intervalo, duracao, aviso)

    def _dar_premio(self, tipo: TipoDeItem, como: TipoDeOcorrencia) -> Ocorrencia:
        segundos = 0.0
        if tipo is TipoDeItem.RELOGIO:
            segundos = self.BONUS_RELOGIO
        else:
            self._condicoes.aplicar(CONDICAO_DO_ITEM[tipo])
        return Ocorrencia(como, item=tipo, segundos=segundos)

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
        if self.imune_a_debuffs or self.fogo_apagado or self._condicoes.ativa(Condicao.PROTEGIDO):
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
            return
        if self._jatos_de_lava:
            return
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
        if perigo.tipo is TipoDePerigo.AREIA_MOVEDICA:
            self._na_areia = True
            return None
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
            if acabou_de_entrar:
                self._desafio_da_teia = DesafioDaTeia.sortear(self._sorteio)
                self._deslizando = None
                perigo.desfazer()  # o jogador rasga a teia quando se solta
                jogador.parar()
                return Ocorrencia(TipoDeOcorrencia.FICOU_PRESO)
        elif perigo.tipo is TipoDePerigo.FOGO:
            if perigo.fogo_aceso(self._tempo):
                return self._queimar()
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
