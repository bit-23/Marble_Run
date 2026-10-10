"""
jogador.py - O personagem como entidade de dominio: posicao, direcao e movimento.

Antes a classe Jogador lia o teclado, carregava sprites do disco, se
desenhava e ainda calculava colisoes. Agora ela so conhece as REGRAS de
movimento: recebe uma intencao (Vetor2) e um MapaDeColisao. Ler teclas e
desenhar ficaram na apresentacao (Responsabilidade Unica).
"""
from __future__ import annotations

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


class Jogador:
    """Personagem controlavel.

    Encapsulamento: posicao, direcao e "andando" sao somente leitura. A unica
    forma de mudar o estado e `mover`, que sempre respeita as paredes.
    """

    VELOCIDADE = 210.0   # pixels por segundo
    LARGURA_HITBOX = 26  # hitbox = so os pes (menor que o desenho, para
    ALTURA_HITBOX = 16   # passar folgado nos corredores)

    def __init__(self, x: float, y: float, velocidade: float = VELOCIDADE) -> None:
        """(x, y) = posicao dos PES do personagem, em pixels do mapa."""
        self._x = float(x)
        self._y = float(y)
        self._velocidade = velocidade
        self._direcao = Direcao.BAIXO
        self._andando = False

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

    def caixa_de_colisao(self) -> Caixa:
        return Caixa.pela_base(round(self._x), round(self._y), self.LARGURA_HITBOX, self.ALTURA_HITBOX)

    # ------------------------------------------------------------------
    # Comportamento
    # ------------------------------------------------------------------
    def mover(self, intencao: Vetor2, dt: float, mapa: MapaDeColisao) -> None:
        """Anda `dt` segundos na direcao pedida, deslizando nas paredes."""
        self._andando = not intencao.eh_nulo
        if not self._andando:
            return
        self._virar_para(intencao)
        norma = intencao.norma  # diagonal nao pode ser mais rapida
        self._deslizar(intencao.x / norma * self._velocidade * dt, _Eixo.X, mapa)
        self._deslizar(intencao.y / norma * self._velocidade * dt, _Eixo.Y, mapa)

    def _virar_para(self, intencao: Vetor2) -> None:
        horizontal = Direcao.DIREITA if intencao.x > 0 else Direcao.ESQUERDA
        vertical = Direcao.BAIXO if intencao.y > 0 else Direcao.CIMA
        if intencao.x and not intencao.y:
            self._direcao = horizontal
        elif intencao.y and not intencao.x:
            self._direcao = vertical
        elif self._direcao not in (horizontal, vertical):  # diagonal: so vira se precisar
            self._direcao = horizontal

    def _deslizar(self, delta: float, eixo: _Eixo, mapa: MapaDeColisao) -> None:
        """Anda `delta` pixels em um eixo, de 1 em 1 pixel, parando ao encostar na parede."""
        passo = 1.0 if delta > 0 else -1.0
        restante = abs(delta)
        while restante > 0:
            p = passo * min(1.0, restante)
            self._deslocar(eixo, p)
            if mapa.colide(self.caixa_de_colisao()):
                self._deslocar(eixo, -p)
                return
            restante -= 1.0

    def _deslocar(self, eixo: _Eixo, pixels: float) -> None:
        if eixo is _Eixo.X:
            self._x += pixels
        else:
            self._y += pixels
