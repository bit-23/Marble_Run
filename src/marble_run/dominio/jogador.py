"""
jogador.py - O personagem como entidade de dominio: posicao, direcao e movimento.

Antes a classe Jogador lia o teclado, carregava sprites do disco, se
desenhava e ainda calculava colisoes. Agora ela so conhece as REGRAS de
movimento: recebe uma intencao (Vetor2) e um MapaDeColisao. Ler teclas e
desenhar ficaram na apresentacao (Responsabilidade Unica).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from .contratos import MapaDeColisao
from .geometria import Caixa, Vetor2


class Direcao(Enum):
    """Para onde o personagem esta virado (o valor e o prefixo dos sprites)."""

    BAIXO = "baixo"
    CIMA = "cima"
    DIREITA = "direita"
    ESQUERDA = "esquerda"


class _Eixo(Enum):
    X = "x"
    Y = "y"


@dataclass(frozen=True)
class Locomocao:
    """Como o jogador pode se mover NESTE quadro (decidido pelo Ambiente da fase).

    aderencia: None = controle total (para e vira na hora). Um numero = chao
    escorregadio: quanto menor, mais o personagem "patina" (gelo).
    """

    multiplicador: float = 1.0       # cafe acelera; tempestades/areia freiam
    aderencia: float | None = None
    travado: bool = False            # congelado ou preso na teia
    invertido: bool = False          # terremoto: controles trocados
    arrasto: Vetor2 = Vetor2()       # rajada de vento: pixels/s somados ao movimento
    intencao_forcada: Vetor2 | None = None  # pegando fogo / deslizando no gelo: o controle e ignorado


class Jogador:
    """Personagem controlavel.

    Encapsulamento: posicao, direcao e "andando" sao somente leitura. O estado
    so muda por `mover`, `saltar`, `posicionar` e `parar`, que sempre
    respeitam as paredes.
    """

    VELOCIDADE = 210.0   # pixels por segundo
    LARGURA_HITBOX = 26  # hitbox = so os pes (menor que o desenho, para
    ALTURA_HITBOX = 16   # passar folgado nos corredores)
    ALTURA_DOS_PES = 12  # os pes ficam um pouco abaixo do centro do tile
    LIMIAR_DESLIZANDO = 30.0  # abaixo disso (px/s) o deslize no gelo nao conta como andar

    def __init__(self, x: float, y: float, velocidade: float = VELOCIDADE) -> None:
        """(x, y) = posicao dos PES do personagem, em pixels do mapa."""
        self._x = float(x)
        self._y = float(y)
        self._velocidade = velocidade
        self._direcao = Direcao.BAIXO
        self._andando = False
        self._bateu = False
        self._vx = 0.0
        self._vy = 0.0
        # pulo da mola: (origem, destino, segundos decorridos, duracao)
        self._salto: tuple[tuple[float, float], tuple[float, float], float, float] | None = None

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------
    @property
    def x(self) -> float:
        return self._x

    @property
    def y(self) -> float:
        return self._y

    @property
    def velocidade(self) -> float:
        return self._velocidade

    @property
    def direcao(self) -> Direcao:
        return self._direcao

    @property
    def esta_andando(self) -> bool:
        return self._andando

    @property
    def bateu(self) -> bool:
        """True se o ultimo movimento foi barrado por uma parede."""
        return self._bateu

    @property
    def pulando(self) -> bool:
        return self._salto is not None

    @property
    def altura_do_salto(self) -> float:
        """0 no chao, 1 no ponto mais alto do pulo (a tela desenha o arco)."""
        if self._salto is None:
            return 0.0
        _, _, decorrido, duracao = self._salto
        return math.sin(math.pi * min(1.0, decorrido / duracao))

    @property
    def velocidade_atual(self) -> Vetor2:
        """Velocidade de verdade neste instante, em pixels/s (a camera usa para antecipar)."""
        if self._salto is not None:
            (x0, y0), (x1, y1), _, duracao = self._salto
            return Vetor2((x1 - x0) / duracao, (y1 - y0) / duracao)
        return Vetor2(self._vx, self._vy)

    def caixa_de_colisao(self) -> Caixa:
        return Caixa.pela_base(round(self._x), round(self._y), self.LARGURA_HITBOX, self.ALTURA_HITBOX)

    # ------------------------------------------------------------------
    # Comportamento
    # ------------------------------------------------------------------
    def mover(self, intencao: Vetor2, dt: float, mapa: MapaDeColisao,
              locomocao: Locomocao = Locomocao()) -> None:
        """Anda `dt` segundos na direcao pedida, deslizando nas paredes."""
        self._bateu = False
        if self._salto is not None:  # no ar: segue o arco do pulo, sem controle
            self._avancar_salto(dt)
            return
        if locomocao.travado:
            self.parar()
            return
        if locomocao.intencao_forcada is not None:
            intencao = locomocao.intencao_forcada
        elif locomocao.invertido:
            intencao = Vetor2(-intencao.x, -intencao.y)

        alvo_x = alvo_y = 0.0
        if not intencao.eh_nulo:
            self._virar_para(intencao)
            norma = intencao.norma  # diagonal nao pode ser mais rapida
            rapidez = self._velocidade * locomocao.multiplicador
            alvo_x, alvo_y = intencao.x / norma * rapidez, intencao.y / norma * rapidez

        if locomocao.aderencia is None:
            self._vx, self._vy = alvo_x, alvo_y
        else:  # chao escorregadio: a velocidade so se aproxima aos poucos do pedido
            k = 1.0 - math.exp(-locomocao.aderencia * dt)
            self._vx += (alvo_x - self._vx) * k
            self._vy += (alvo_y - self._vy) * k
            if math.hypot(self._vx, self._vy) < 1.0:
                self._vx = self._vy = 0.0

        self._andando = (not intencao.eh_nulo
                         or math.hypot(self._vx, self._vy) > self.LIMIAR_DESLIZANDO)
        dx = (self._vx + locomocao.arrasto.x) * dt
        dy = (self._vy + locomocao.arrasto.y) * dt
        bateu_x, bateu_y = self._deslocar_com_paredes(dx, dy, mapa)
        if bateu_x:
            self._vx = 0.0
        if bateu_y:
            self._vy = 0.0
        self._bateu = (bateu_x and bool(alvo_x)) or (bateu_y and bool(alvo_y))

    def saltar(self, x: float, y: float, duracao: float, mapa: MapaDeColisao) -> bool:
        """Pulo em arco ate (x, y) - por cima de paredes. False se nao couber no destino."""
        if self._salto is not None or not self._cabe_em(x, y, mapa):
            return False
        self._salto = ((self._x, self._y), (float(x), float(y)), 0.0, duracao)
        self._vx = self._vy = 0.0
        self._andando = False
        return True

    def posicionar(self, x: float, y: float, mapa: MapaDeColisao) -> bool:
        """Ajuste instantaneo de posicao (ex.: alinhar no corredor). False se nao couber."""
        if not self._cabe_em(x, y, mapa):
            return False
        self._x, self._y = float(x), float(y)
        return True

    def parar(self) -> None:
        self._vx = self._vy = 0.0
        self._andando = False

    def _cabe_em(self, x: float, y: float, mapa: MapaDeColisao) -> bool:
        antes = self._x, self._y
        self._x, self._y = float(x), float(y)
        cabe = not mapa.colide(self.caixa_de_colisao())
        self._x, self._y = antes
        return cabe

    def _avancar_salto(self, dt: float) -> None:
        (x0, y0), (x1, y1), decorrido, duracao = self._salto
        decorrido += dt
        k = min(1.0, decorrido / duracao)
        self._x, self._y = x0 + (x1 - x0) * k, y0 + (y1 - y0) * k
        self._andando = False
        self._salto = None if k >= 1.0 else ((x0, y0), (x1, y1), decorrido, duracao)

    def _deslocar_com_paredes(self, dx: float, dy: float, mapa: MapaDeColisao) -> tuple[bool, bool]:
        bateu_x = self._deslizar(dx, _Eixo.X, mapa) if dx else False
        bateu_y = self._deslizar(dy, _Eixo.Y, mapa) if dy else False
        return bateu_x, bateu_y

    def _virar_para(self, intencao: Vetor2) -> None:
        horizontal = Direcao.DIREITA if intencao.x > 0 else Direcao.ESQUERDA
        vertical = Direcao.BAIXO if intencao.y > 0 else Direcao.CIMA
        if intencao.x and not intencao.y:
            self._direcao = horizontal
        elif intencao.y and not intencao.x:
            self._direcao = vertical
        elif self._direcao not in (horizontal, vertical):  # diagonal: so vira se precisar
            self._direcao = horizontal

    def _deslizar(self, delta: float, eixo: _Eixo, mapa: MapaDeColisao) -> bool:
        """Anda `delta` pixels em um eixo, de 1 em 1 pixel. Devolve True se bateu na parede."""
        passo = 1.0 if delta > 0 else -1.0
        restante = abs(delta)
        while restante > 0:
            p = passo * min(1.0, restante)
            self._deslocar(eixo, p)
            if mapa.colide(self.caixa_de_colisao()):
                self._deslocar(eixo, -p)
                return True
            restante -= 1.0
        return False

    def _deslocar(self, eixo: _Eixo, pixels: float) -> None:
        if eixo is _Eixo.X:
            self._x += pixels
        else:
            self._y += pixels
