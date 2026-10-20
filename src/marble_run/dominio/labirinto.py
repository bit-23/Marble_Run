"""
labirinto.py - O labirinto como MODELO (entidade de dominio), sem desenho.

Antes a classe Cenario misturava a grade, as colisoes e o desenho com
pygame. Agora o Labirinto so responde perguntas sobre o mapa; quem desenha
e a apresentacao (Responsabilidade Unica).
"""
from __future__ import annotations

from typing import NamedTuple, Sequence

from .geometria import Caixa

TAMANHO_TILE = 56  # lado de cada quadrado do labirinto, em pixels do mapa


class Coordenada(NamedTuple):
    """Posicao de um tile na grade (imutavel, comparavel e usavel em sets/dicts)."""

    coluna: int
    linha: int


class Labirinto:
    """Grade de paredes e chao + consultas espaciais.

    Encapsulamento: a grade e copiada para tuplas (somente leitura) e so e
    acessada por metodos com significado - eh_parede, colide, area_da_saida.
    Ninguem de fora consegue "abrir um buraco" na parede.
    """

    def __init__(self, paredes: Sequence[Sequence[bool]], entrada: Coordenada,
                 saida: Coordenada, distancia_minima: int, tamanho_tile: int = TAMANHO_TILE) -> None:
        self._paredes = tuple(tuple(bool(celula) for celula in linha) for linha in paredes)
        self._linhas = len(self._paredes)
        self._colunas = len(self._paredes[0])
        self._entrada = entrada
        self._saida = saida
        self._distancia_minima = distancia_minima
        self._tile = tamanho_tile

    # ------------------------------------------------------------------
    # Dados (somente leitura)
    # ------------------------------------------------------------------
    @property
    def colunas(self) -> int:
        return self._colunas

    @property
    def linhas(self) -> int:
        return self._linhas

    @property
    def tamanho_tile(self) -> int:
        return self._tile

    @property
    def largura(self) -> int:
        """Largura total em pixels do mapa."""
        return self._colunas * self._tile

    @property
    def altura(self) -> int:
        return self._linhas * self._tile

    @property
    def entrada(self) -> Coordenada:
        return self._entrada

    @property
    def saida(self) -> Coordenada:
        return self._saida

    @property
    def distancia_minima(self) -> int:
        """Tamanho (em tiles) do menor caminho entre a entrada e a saida."""
        return self._distancia_minima

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------
    def eh_parede(self, coluna: int, linha: int) -> bool:
        """Fora da grade conta como parede: ninguem escapa pelas bordas."""
        if coluna < 0 or linha < 0 or coluna >= self._colunas or linha >= self._linhas:
            return True
        return self._paredes[linha][coluna]

    def colide(self, caixa: Caixa) -> bool:
        """True se a caixa (em pixels do mapa) encosta em alguma parede."""
        t = self._tile
        for linha in range(caixa.topo // t, (caixa.base - 1) // t + 1):
            for coluna in range(caixa.esquerda // t, (caixa.direita - 1) // t + 1):
                if self.eh_parede(coluna, linha):
                    return True
        return False

    def centro_do_tile(self, tile: Coordenada) -> tuple[int, int]:
        meio = self._tile // 2
        return tile.coluna * self._tile + meio, tile.linha * self._tile + meio

    def area_da_saida(self) -> Caixa:
        """Area do portal (um pouco menor que o tile, para nao ser 'injusto')."""
        centro_x, centro_y = self.centro_do_tile(self._saida)
        lado = self._tile - 16
        return Caixa.pelo_centro(centro_x, centro_y, lado, lado)
