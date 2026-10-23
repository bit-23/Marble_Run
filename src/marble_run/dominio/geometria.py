"""
geometria.py - Objetos de valor (Value Objects) usados pelas regras.

Sao imutaveis (frozen): duas instancias com os mesmos dados sao iguais e
ninguem consegue altera-las por engano depois de criadas. Substituem as
tuplas soltas e o pygame.Rect que o dominio usava antes.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Vetor2:
    """Uma direcao/intencao de movimento. Ex.: Vetor2(1, 0) = para a direita."""

    x: float = 0.0
    y: float = 0.0

    @property
    def eh_nulo(self) -> bool:
        return not (self.x or self.y)

    @property
    def norma(self) -> float:
        return (self.x * self.x + self.y * self.y) ** 0.5


@dataclass(frozen=True)
class Caixa:
    """Retangulo alinhado aos eixos, em pixels do mapa (hitbox, area da saida)."""

    x: int
    y: int
    largura: int
    altura: int

    @classmethod
    def pela_base(cls, centro_x: int, base: int, largura: int, altura: int) -> Caixa:
        """Caixa 'em pe' sobre o ponto (centro_x, base) - ideal para os pes do personagem."""
        return cls(centro_x - largura // 2, base - altura, largura, altura)

    @classmethod
    def pelo_centro(cls, centro_x: int, centro_y: int, largura: int, altura: int) -> Caixa:
        return cls(centro_x - largura // 2, centro_y - altura // 2, largura, altura)

    @property
    def esquerda(self) -> int:
        return self.x

    @property
    def direita(self) -> int:
        return self.x + self.largura

    @property
    def topo(self) -> int:
        return self.y

    @property
    def base(self) -> int:
        return self.y + self.altura

    def intersecta(self, outra: Caixa) -> bool:
        """True se houver sobreposicao de area (so encostar na borda nao conta)."""
        return (self.esquerda < outra.direita and outra.esquerda < self.direita
                and self.topo < outra.base and outra.topo < self.base)
