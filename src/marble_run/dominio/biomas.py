"""
biomas.py - O que cada tipo de mapa tem de especial (configuracao + sorteio).

Um Bioma e so DADOS (quais perigos, quais premios na roleta, qual fenomeno,
quantas molas). `criar_ambiente` espalha tudo pelo labirinto com o
sorteador da fase: mesma semente => mesmas caixas nos mesmos lugares.

    gelo     -> pocas que congelam + placas de gelo (desliza ate bater) | blusa, banana
    deserto  -> areia movedica + tempestade de areia + sol forte (mais luz) | flauta
    fogo     -> fogo (Zelda) + erupcao (jatos de lava perto do jogador)   | flauta
    masmorra -> teias de aranha + apagao
    terra    -> terremoto (controles invertidos)
    vento    -> rajadas de vento
    todos    -> molas nas paredes + caixas "?" (relogio, lanterna, estrela, bussola, cafe)

A Dificuldade decide QUANTO de cada coisa aparece em cada fase: nas fases
tranquilas ha poucos perigos e nenhum fenomeno; depois tudo aumenta.

No TESTE DOS MAPAS (vitrine) tudo e colocado colado na entrada, para
mostrar cada coisa sem precisar procurar pelo labirinto.

Qual tema usa qual bioma e decidido no main.py (Composition Root).
"""
from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass

from .ambiente import (ITENS_COMUNS, OPOSTA, Ambiente, CaixaSurpresa, Fenomeno, MolaDeParede, Perigo,
                       TipoDeItem, TipoDePerigo)
from .jogador import Direcao
from .labirinto import Coordenada, Labirinto
from .regras import Dificuldade

PESO_DOS_ITENS_PROPRIOS = 3  # buffs do proprio mapa saem mais na roleta


@dataclass(frozen=True)
class RegraDePerigo:
    """Quantos perigos de um tipo espalhar: 1 a cada N tiles de chao (no minimo `minimo`).

    `tamanho_maximo` > 1 = o perigo nasce em TRECHOS de corredor (placas de gelo).
    """

    tipo: TipoDePerigo
    tiles_por_perigo: int
    minimo: int
    tamanho_maximo: int = 1


@dataclass(frozen=True)
class Bioma:
    perigos: tuple[RegraDePerigo, ...] = ()
    itens_proprios: tuple[TipoDeItem, ...] = ()
    fenomeno: Fenomeno | None = None
    aderencia: float | None = None   # None = chao normal; numero = escorregadio
    fator_de_tempo: float = 1.0      # tempo extra para compensar os debuffs
    fator_de_visao: float = 1.0      # deserto: sol forte, enxerga mais longe
    itens_comuns: tuple[tuple[TipoDeItem, int], ...] = ITENS_COMUNS
    tiles_por_caixa: int = 140
    tiles_por_mola: int = 70         # 1 par de molas (ida e volta) a cada N tiles de chao
    distancia_segura: int = 2        # nada nasce colado na entrada

    # ------------------------------------------------------------------
    # Biomas prontos
    # ------------------------------------------------------------------
    @classmethod
    def neutro(cls) -> Bioma:
        return cls()

    @classmethod
    def gelado(cls) -> Bioma:
        return cls(perigos=(RegraDePerigo(TipoDePerigo.AGUA, 45, 2),
                            RegraDePerigo(TipoDePerigo.GELO, 70, 2, tamanho_maximo=4)),
                   itens_proprios=(TipoDeItem.BLUSA, TipoDeItem.BANANA), fator_de_tempo=1.15)

    @classmethod
    def desertico(cls) -> Bioma:
        return cls(perigos=(RegraDePerigo(TipoDePerigo.AREIA_MOVEDICA, 40, 3),),
                   itens_proprios=(TipoDeItem.FLAUTA,),
                   fenomeno=Fenomeno.TEMPESTADE_DE_AREIA, fator_de_tempo=1.15, fator_de_visao=1.25)

    @classmethod
    def vulcanico(cls) -> Bioma:
        return cls(perigos=(RegraDePerigo(TipoDePerigo.FOGO, 35, 3),),
                   itens_proprios=(TipoDeItem.FLAUTA,),
                   fenomeno=Fenomeno.ERUPCAO, fator_de_tempo=1.2)

    @classmethod
    def masmorra(cls) -> Bioma:
        return cls(perigos=(RegraDePerigo(TipoDePerigo.TEIA, 70, 2),),  # teia e rara: prende ate acertar as setas
                   fenomeno=Fenomeno.APAGAO, fator_de_tempo=1.1)

    @classmethod
    def terroso(cls) -> Bioma:
        return cls(fenomeno=Fenomeno.TERREMOTO, fator_de_tempo=1.1)

    @classmethod
    def ventoso(cls) -> Bioma:
        return cls(fenomeno=Fenomeno.RAJADA, fator_de_tempo=1.1)

    # ------------------------------------------------------------------
    def premios(self, dificuldade: Dificuldade | None = None) -> tuple[tuple[TipoDeItem, int], ...]:
        """O que pode sair na roleta deste mapa (com pesos)."""
        vetados = set(dificuldade.itens_vetados) if dificuldade else set()
        proprios = [(tipo, PESO_DOS_ITENS_PROPRIOS) for tipo in self.itens_proprios]
        return tuple((tipo, peso) for tipo, peso in proprios + list(self.itens_comuns) if tipo not in vetados)

    def criar_ambiente(self, labirinto: Labirinto, rng: random.Random,
                       dificuldade: Dificuldade | None = None, vitrine: bool = False, fase: int = 1) -> Ambiente:
        dificuldade = dificuldade if dificuldade is not None else Dificuldade()
        if vitrine:  # teste dos mapas: tudo ligado, como no meio do jogo
            fator_perigos, ritmo, fenomeno = 1.0, 1.0, self.fenomeno
        else:
            fator_perigos = dificuldade.perigos(fase)
            ritmo = dificuldade.ritmo_dos_fenomenos(fase)
            fenomeno = self.fenomeno if dificuldade.tem_fenomenos(fase) else None
        chao = self._tiles_de_chao(labirinto)
        terreno = _Terreno(labirinto, [t for t in chao if self._pode_ocupar(t, labirinto, vitrine)],
                           rng, perto_da_entrada=vitrine)

        molas = self._colocar_molas(labirinto, terreno, rng, len(chao), vitrine)
        perigos = []
        restantes = [[regra, 2 if vitrine else max(max(1, round(regra.minimo * fator_perigos)),
                                                    int(len(chao) / regra.tiles_por_perigo * fator_perigos))]
                     for regra in self.perigos]
        while any(quantidade > 0 for _, quantidade in restantes):  # intercala os tipos
            for par in restantes:
                if par[1] > 0:
                    par[1] -= 1
                    perigos += self._colocar_perigo(par[0], labirinto, terreno, rng)

        caixas = []
        for _ in range(3 if vitrine else 2 + len(chao) // self.tiles_por_caixa):
            tile = terreno.retirar()
            if tile is None:
                break
            caixas.append(CaixaSurpresa(tile, labirinto.centro_do_tile(tile)))

        return Ambiente(labirinto, caixas, perigos, molas, self.aderencia, fenomeno,
                        random.Random(rng.random()), ritmo_fenomenos=ritmo, premios=self.premios(dificuldade))

    # ------------------------------------------------------------------
    def _colocar_perigo(self, regra: RegraDePerigo, labirinto: Labirinto, terreno: _Terreno,
                        rng: random.Random) -> list[Perigo]:
        tile = terreno.retirar()
        if tile is None:
            return []
        trecho = [tile]
        if regra.tamanho_maximo > 1:  # cresce em linha reta pelo corredor
            dx, dy = rng.choice(((1, 0), (-1, 0), (0, 1), (0, -1)))
            for _ in range(rng.randint(1, regra.tamanho_maximo - 1)):
                proximo = Coordenada(trecho[-1].coluna + dx, trecho[-1].linha + dy)
                if not terreno.retirar_se_livre(proximo):
                    break
                trecho.append(proximo)
        defasagem = rng.uniform(0, Perigo.CICLO_DO_FOGO)
        return [Perigo(regra.tipo, t, labirinto.centro_do_tile(t), defasagem) for t in trecho]

    def _colocar_molas(self, labirinto: Labirinto, terreno: _Terreno, rng: random.Random,
                       tiles_de_chao: int, vitrine: bool) -> list[MolaDeParede]:
        """Pares de molas (ida e volta) dos dois lados de uma parede fina."""
        pares = self._pares_de_molas(labirinto)
        if vitrine:
            pares.sort(key=lambda par: terreno.distancia(par[0]) + terreno.distancia(par[2]))
        else:
            rng.shuffle(pares)
        quantidade = 2 if vitrine else max(1, tiles_de_chao // self.tiles_por_mola)
        usados: set[Coordenada] = set()
        molas: list[MolaDeParede] = []
        for a, direcao, b in pares:
            if len(molas) >= quantidade * 2:
                break
            if a in usados or b in usados or a == labirinto.saida or b == labirinto.saida:
                continue
            usados.update((a, b))
            terreno.retirar_se_livre(a)  # tiles da mola ficam sem perigos/caixas, para ficar claro
            terreno.retirar_se_livre(b)
            t = labirinto.tamanho_tile
            molas.append(MolaDeParede(a, direcao, b, t))
            molas.append(MolaDeParede(b, OPOSTA[direcao], a, t))
        return molas

    @staticmethod
    def _pares_de_molas(labirinto: Labirinto) -> list[tuple[Coordenada, Direcao, Coordenada]]:
        """Todo chao A com uma parede no meio e chao B logo depois: A |#| B."""
        pares = []
        for linha in range(1, labirinto.linhas - 1):
            for coluna in range(1, labirinto.colunas - 1):
                if labirinto.eh_parede(coluna, linha):
                    continue
                for direcao, (dx, dy) in ((Direcao.DIREITA, (1, 0)), (Direcao.BAIXO, (0, 1))):
                    parede = (coluna + dx, linha + dy)
                    destino = Coordenada(coluna + 2 * dx, linha + 2 * dy)
                    borda = not (0 < parede[0] < labirinto.colunas - 1 and 0 < parede[1] < labirinto.linhas - 1)
                    if not borda and labirinto.eh_parede(*parede) and not labirinto.eh_parede(*destino):
                        pares.append((Coordenada(coluna, linha), direcao, destino))
        return pares

    @staticmethod
    def _tiles_de_chao(labirinto: Labirinto) -> list[Coordenada]:
        return [Coordenada(coluna, linha)
                for linha in range(labirinto.linhas) for coluna in range(labirinto.colunas)
                if not labirinto.eh_parede(coluna, linha)]

    def _pode_ocupar(self, tile: Coordenada, labirinto: Labirinto, vitrine: bool) -> bool:
        entrada = labirinto.entrada
        segura = 0 if vitrine else self.distancia_segura
        perto_da_entrada = abs(tile.coluna - entrada.coluna) + abs(tile.linha - entrada.linha) <= segura
        return not perto_da_entrada and tile != labirinto.saida


class _Terreno:
    """Tiles ainda livres para colocar coisas (em ordem aleatoria ou do mais perto da entrada)."""

    def __init__(self, labirinto: Labirinto, livres: list[Coordenada], rng: random.Random,
                 perto_da_entrada: bool) -> None:
        self._distancias = self._calcular_distancias(labirinto)
        if perto_da_entrada:  # retirar() pega do fim da lista: o mais perto fica por ultimo
            livres.sort(key=lambda t: -self.distancia(t))
        else:
            rng.shuffle(livres)
        self._ordem = livres
        self._livres = set(livres)

    def distancia(self, tile: Coordenada) -> int:
        return self._distancias.get(tile, 10 ** 6)

    def retirar(self) -> Coordenada | None:
        while self._ordem:
            tile = self._ordem.pop()
            if tile in self._livres:
                self._livres.discard(tile)
                return tile
        return None

    def retirar_se_livre(self, tile: Coordenada) -> bool:
        if tile not in self._livres:
            return False
        self._livres.discard(tile)
        return True

    @staticmethod
    def _calcular_distancias(labirinto: Labirinto) -> dict[Coordenada, int]:
        """BFS a partir da entrada (passos andando pelo labirinto)."""
        distancias = {labirinto.entrada: 0}
        fila = deque([labirinto.entrada])
        while fila:
            atual = fila.popleft()
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                vizinho = Coordenada(atual.coluna + dx, atual.linha + dy)
                if vizinho not in distancias and not labirinto.eh_parede(*vizinho):
                    distancias[vizinho] = distancias[atual] + 1
                    fila.append(vizinho)
        return distancias
