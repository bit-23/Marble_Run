"""
biomas.py - O que cada tipo de mapa tem de especial (configuracao + sorteio).

Um Bioma e so DADOS (quais perigos, quais premios na roleta, qual fenomeno,
quantas molas). `criar_ambiente` espalha tudo pelo labirinto com o
sorteador da fase: mesma semente => mesmas caixas nos mesmos lugares.

    gelo     -> pocas que congelam + placas de gelo (espalhadas) + tempestade de gelo | blusa, cafe
                monstros: boneco de neve sombrio, yeti
    deserto  -> areia movedica + tempestade de areia + sol forte (mais luz) | flauta, tapete, genio
                monstros: cobra, mumia
    fogo     -> fogo (Zelda) + erupcao (jatos de lava perto do jogador)    | extintor, bota de obsidiana
                monstros: magman, fornalha
    masmorra -> teias de aranha + apagao + molas SO DE IDA                  | lanterna, bussola
                monstros: aranha, minotauro
    terra    -> terremoto (controles invertidos)                            | broca, capacete
                monstros: toupeira, golem
    vento    -> rajadas de vento                                            | guarda-chuva, pipa
                monstros: aguia, tornado
    todos    -> caixas "?" (poucas e longe umas das outras) com relogio, coracao e estrela

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

from .ambiente import (ITENS_COMUNS, OPOSTA, Ambiente, CaixaSurpresa, Fenomeno, HistoricoDaRoleta, MolaDeParede,
                       Perigo, TipoDeItem, TipoDePerigo)
from .caminhos import manhattan, tiles_em_linha, vizinhos_livres
from .jogador import Direcao
from .labirinto import Coordenada, Labirinto
from .monstros import Monstro, TipoDeMonstro, criar_monstro
from .regras import Dificuldade

PESO_DOS_ITENS_PROPRIOS = 3  # buffs do proprio mapa saem mais na roleta


def _longe_de(tile: Coordenada, outros, distancia: int) -> bool:
    return all(abs(tile.coluna - o.coluna) + abs(tile.linha - o.linha) >= distancia for o in outros)


def _saida_do_beco(labirinto: Labirinto, tile: Coordenada) -> tuple[int, int]:
    vizinho = vizinhos_livres(labirinto, tile)[0]
    return vizinho.coluna - tile.coluna, vizinho.linha - tile.linha


@dataclass(frozen=True)
class RegraDePerigo:
    """Quantos perigos de um tipo espalhar: 1 a cada N tiles de chao (no minimo `minimo`).

    `tamanho_maximo` > 1 = o perigo nasce em TRECHOS de corredor (placas de gelo).
    `distancia_minima` > 0 = cada trecho fica pelo menos a essa distancia (em tiles) dos outros do mesmo tipo.
    """

    tipo: TipoDePerigo
    tiles_por_perigo: int
    minimo: int
    tamanho_maximo: int = 1
    distancia_minima: int = 0


@dataclass(frozen=True)
class Bioma:
    perigos: tuple[RegraDePerigo, ...] = ()
    itens_proprios: tuple[TipoDeItem, ...] = ()
    fenomeno: Fenomeno | None = None
    aderencia: float | None = None   # None = chao normal; numero = escorregadio
    fator_de_tempo: float = 1.0      # tempo extra para compensar os debuffs
    fator_de_visao: float = 1.0      # deserto: sol forte, enxerga mais longe
    itens_comuns: tuple[tuple[TipoDeItem, int], ...] = ITENS_COMUNS
    tiles_por_caixa: int = 150
    distancia_entre_caixas: int = 6  # em tiles: as caixas ficam espalhadas pelo mapa
    tiles_por_mola: int | None = None  # None = sem molas; numero = 1 mola (so de ida) a cada N tiles de chao
    distancia_do_portal: int = 5     # molas nao nascem perto da saida
    distancia_segura: int = 2        # nada nasce colado na entrada
    monstros: tuple[TipoDeMonstro, ...] = ()
    distancia_dos_monstros: int = 8  # passos andando ate a entrada (o jogador nao comeca cercado)

    # ------------------------------------------------------------------
    # Biomas prontos
    # ------------------------------------------------------------------
    @classmethod
    def neutro(cls) -> Bioma:
        return cls()

    @classmethod
    def gelado(cls) -> Bioma:
        return cls(perigos=(RegraDePerigo(TipoDePerigo.AGUA, 45, 2),
                            RegraDePerigo(TipoDePerigo.GELO, 110, 1, tamanho_maximo=3, distancia_minima=6)),
                   itens_proprios=(TipoDeItem.BLUSA, TipoDeItem.CAFE),
                   fenomeno=Fenomeno.TEMPESTADE_DE_GELO, fator_de_tempo=1.15,
                   monstros=(TipoDeMonstro.BONECO_DE_NEVE, TipoDeMonstro.YETI))

    @classmethod
    def desertico(cls) -> Bioma:
        return cls(perigos=(RegraDePerigo(TipoDePerigo.AREIA_MOVEDICA, 40, 3),),
                   itens_proprios=(TipoDeItem.FLAUTA, TipoDeItem.TAPETE, TipoDeItem.GENIO),
                   fenomeno=Fenomeno.TEMPESTADE_DE_AREIA, fator_de_tempo=1.15, fator_de_visao=1.25,
                   monstros=(TipoDeMonstro.COBRA, TipoDeMonstro.MUMIA))

    @classmethod
    def vulcanico(cls) -> Bioma:
        return cls(perigos=(RegraDePerigo(TipoDePerigo.FOGO, 35, 3),),
                   itens_proprios=(TipoDeItem.EXTINTOR, TipoDeItem.BOTA),
                   fenomeno=Fenomeno.ERUPCAO, fator_de_tempo=1.2,
                   monstros=(TipoDeMonstro.MAGMAN, TipoDeMonstro.FORNALHA))

    @classmethod
    def masmorra(cls) -> Bioma:
        return cls(perigos=(RegraDePerigo(TipoDePerigo.TEIA, 70, 2),),  # teia e rara: prende ate acertar as setas
                   itens_proprios=(TipoDeItem.LANTERNA, TipoDeItem.BUSSOLA),
                   fenomeno=Fenomeno.APAGAO, fator_de_tempo=1.1, tiles_por_mola=70,
                   monstros=(TipoDeMonstro.ARANHA, TipoDeMonstro.MINOTAURO))

    @classmethod
    def terroso(cls) -> Bioma:
        return cls(itens_proprios=(TipoDeItem.BROCA, TipoDeItem.CAPACETE),
                   fenomeno=Fenomeno.TERREMOTO, fator_de_tempo=1.1,
                   monstros=(TipoDeMonstro.TOUPEIRA, TipoDeMonstro.GOLEM))

    @classmethod
    def ventoso(cls) -> Bioma:
        return cls(itens_proprios=(TipoDeItem.GUARDA_CHUVA, TipoDeItem.PIPA),
                   fenomeno=Fenomeno.RAJADA, fator_de_tempo=1.1,
                   monstros=(TipoDeMonstro.AGUIA, TipoDeMonstro.TORNADO))

    # ------------------------------------------------------------------
    def premios(self, dificuldade: Dificuldade | None = None) -> tuple[tuple[TipoDeItem, float], ...]:
        """O que pode sair na roleta deste mapa (com pesos)."""
        vetados = set(dificuldade.itens_vetados) if dificuldade else set()
        proprios = [(tipo, PESO_DOS_ITENS_PROPRIOS) for tipo in self.itens_proprios]
        return tuple((tipo, peso) for tipo, peso in proprios + list(self.itens_comuns) if tipo not in vetados)

    def criar_ambiente(self, labirinto: Labirinto, rng: random.Random,
                       dificuldade: Dificuldade | None = None, vitrine: bool = False, fase: int = 1,
                       historico: HistoricoDaRoleta | None = None) -> Ambiente:
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
        perigos: list[Perigo] = []
        restantes = [[regra, 2 if vitrine else max(max(1, round(regra.minimo * fator_perigos)),
                                                    int(len(chao) / regra.tiles_por_perigo * fator_perigos))]
                     for regra in self.perigos]
        while any(quantidade > 0 for _, quantidade in restantes):  # intercala os tipos
            for par in restantes:
                if par[1] > 0:
                    par[1] -= 1
                    perigos += self._colocar_perigo(par[0], labirinto, terreno, rng, perigos, vitrine)

        caixas: list[CaixaSurpresa] = []
        afastamento = 0 if vitrine else self.distancia_entre_caixas
        for _ in range(3 if vitrine else 2 + len(chao) // self.tiles_por_caixa):
            tile = terreno.retirar_longe_de([c.tile for c in caixas], afastamento)
            if tile is None:
                break
            caixas.append(CaixaSurpresa(tile, labirinto.centro_do_tile(tile)))

        quantidade = len(self.monstros) if vitrine else dificuldade.monstros(fase)
        monstros = self._colocar_monstros(labirinto, terreno, rng, quantidade, dificuldade.monstros_agressivos,
                                          vitrine)
        return Ambiente(labirinto, caixas, perigos, molas, self.aderencia, fenomeno,
                        random.Random(rng.random()), ritmo_fenomenos=ritmo, premios=self.premios(dificuldade),
                        monstros=monstros, historico=historico)

    def criar_arena(self, labirinto: Labirinto, rng: random.Random,
                    dificuldade: Dificuldade | None = None, historico: HistoricoDaRoleta | None = None) -> Ambiente:
        """Arena do teste dos mapas: vazia (o jogador monta tudo), mas com o fenomeno e a roleta do mapa."""
        return Ambiente(labirinto, aderencia=self.aderencia, fenomeno=self.fenomeno,
                        sorteio=random.Random(rng.random()), premios=self.premios(dificuldade), historico=historico)

    # ------------------------------------------------------------------
    def _colocar_monstros(self, labirinto: Labirinto, terreno: _Terreno, rng: random.Random, quantidade: int,
                          agressivos: bool, vitrine: bool) -> list[Monstro]:
        """Longe da entrada (o jogador nao comeca cercado) e longe uns dos outros.

        A fornalha (parada e solida) so nasce no FIM de um beco: assim nunca fecha o unico caminho.
        """
        if not self.monstros or quantidade <= 0:
            return []
        tipos = list(self.monstros) if quantidade >= len(self.monstros) else rng.sample(self.monstros, quantidade)
        while len(tipos) < quantidade:
            tipos.append(rng.choice(self.monstros))
        minimo = 3 if vitrine else self.distancia_dos_monstros
        livres = [t for t in terreno.livres() if terreno.distancia(t) >= minimo
                  and manhattan(t, labirinto.saida) >= 3]
        if vitrine:
            livres.sort(key=terreno.distancia)
        else:
            rng.shuffle(livres)
        afastamento = 3 if vitrine else 6
        monstros: list[Monstro] = []
        for tipo in tipos:
            opcoes = [t for t in livres if all(manhattan(t, m.tile) >= afastamento for m in monstros)]
            if tipo is TipoDeMonstro.FORNALHA:
                opcoes = [t for t in opcoes if len(vizinhos_livres(labirinto, t)) == 1
                          and len(tiles_em_linha(labirinto, t, _saida_do_beco(labirinto, t), 3)) >= 2]
            if not opcoes:
                continue
            tile = opcoes[0]
            terreno.retirar_se_livre(tile)
            livres.remove(tile)
            monstros.append(criar_monstro(tipo, tile, labirinto, random.Random(rng.random()), agressivos))
        return monstros

    # ------------------------------------------------------------------
    def _colocar_perigo(self, regra: RegraDePerigo, labirinto: Labirinto, terreno: _Terreno,
                        rng: random.Random, ja_colocados: list[Perigo], vitrine: bool) -> list[Perigo]:
        afastamento = 0 if vitrine else regra.distancia_minima
        vizinhos = [p.tile for p in ja_colocados if p.tipo is regra.tipo] if afastamento else []
        tile = terreno.retirar_longe_de(vizinhos, afastamento)
        if tile is None:
            return []
        trecho = [tile]
        if regra.tamanho_maximo > 1:  # cresce em linha reta pelo corredor
            dx, dy = rng.choice(((1, 0), (-1, 0), (0, 1), (0, -1)))
            for _ in range(rng.randint(1, regra.tamanho_maximo - 1)):
                proximo = Coordenada(trecho[-1].coluna + dx, trecho[-1].linha + dy)
                if not _longe_de(proximo, vizinhos, afastamento) or not terreno.retirar_se_livre(proximo):
                    break
                trecho.append(proximo)
        defasagem = rng.uniform(0, Perigo.CICLO_DO_FOGO)
        return [Perigo(regra.tipo, t, labirinto.centro_do_tile(t), defasagem) for t in trecho]

    def _colocar_molas(self, labirinto: Labirinto, terreno: _Terreno, rng: random.Random,
                       tiles_de_chao: int, vitrine: bool) -> list[MolaDeParede]:
        """Molas SO DE IDA presas numa parede fina (A |#| B lanca de A para B, sem volta)."""
        if self.tiles_por_mola is None:
            return []
        pares = self._pares_de_molas(labirinto)
        if vitrine:
            pares.sort(key=lambda par: terreno.distancia(par[0]) + terreno.distancia(par[2]))
        else:
            rng.shuffle(pares)
            pares = [par for par in pares if _longe_de(par[0], [labirinto.saida], self.distancia_do_portal)
                     and _longe_de(par[2], [labirinto.saida], self.distancia_do_portal)]
        quantidade = 2 if vitrine else max(1, tiles_de_chao // self.tiles_por_mola)
        usados: set[Coordenada] = set()
        molas: list[MolaDeParede] = []
        for a, direcao, b in pares:
            if len(molas) >= quantidade:
                break
            if a in usados or b in usados or a == labirinto.saida or b == labirinto.saida:
                continue
            if not vitrine and rng.random() < 0.5:  # sorteia para que lado a mola lanca
                a, direcao, b = b, OPOSTA[direcao], a
            usados.update((a, b))
            terreno.retirar_se_livre(a)  # tiles da mola ficam sem perigos/caixas, para ficar claro
            terreno.retirar_se_livre(b)
            molas.append(MolaDeParede(a, direcao, b, labirinto.tamanho_tile))
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

    def livres(self) -> list[Coordenada]:
        return [t for t in self._ordem if t in self._livres]

    def retirar(self) -> Coordenada | None:
        return self.retirar_longe_de((), 0)

    def retirar_longe_de(self, outros: list[Coordenada] | tuple[Coordenada, ...], distancia: int) -> Coordenada | None:
        """Proximo tile livre a pelo menos `distancia` tiles (Manhattan) de todos os `outros`."""
        for indice in range(len(self._ordem) - 1, -1, -1):
            tile = self._ordem[indice]
            if tile not in self._livres:
                del self._ordem[indice]
            elif _longe_de(tile, outros, distancia):
                del self._ordem[indice]
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
