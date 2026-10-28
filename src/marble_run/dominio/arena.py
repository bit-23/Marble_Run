"""
arena.py - O EDITOR da arena do teste dos mapas (menu secreto DESENVOLVEDOR).

A arena e um quadrado aberto onde da para:
    MAPA     -> levantar/derrubar paredes, apagar coisas, mudar o portal, colocar caixas "?"
    PERIGO   -> agua, placa de gelo, fogo, teia, areia movedica, lava, buraco
    MONSTRO  -> qualquer um dos 12 monstros (de qualquer mapa)
    ITEM     -> qualquer item largado no chao (pega encostando, sem roleta)

O editor so VALIDA e aplica no Labirinto/Ambiente do dominio; quem desenha
a paleta e le o mouse e a apresentacao (vitrine.py).
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum

from .ambiente import Ambiente, TipoDeItem, TipoDePerigo
from .geometria import Caixa
from .jogador import Jogador
from .labirinto import Coordenada, LabirintoEditavel
from .monstros import TipoDeMonstro, criar_monstro


class Categoria(Enum):
    MAPA = "MAPA"
    PERIGO = "PERIGO"
    MONSTRO = "MONSTRO"
    ITEM = "ITEM"


class Especial(Enum):
    PAREDE = "parede"
    BORRACHA = "borracha"
    PORTAL = "portal"
    CAIXA = "caixa"


@dataclass(frozen=True)
class Ferramenta:
    categoria: Categoria
    nome: str
    especial: Especial | None = None
    perigo: TipoDePerigo | None = None
    monstro: TipoDeMonstro | None = None
    item: TipoDeItem | None = None

    @property
    def pinta_arrastando(self) -> bool:
        """Paredes, borracha e perigos podem ser "pintados" segurando o botao."""
        return self.especial in (Especial.PAREDE, Especial.BORRACHA) or self.perigo is not None


NOMES_DOS_PERIGOS: dict[TipoDePerigo, str] = {
    TipoDePerigo.AGUA: "POCA D'AGUA", TipoDePerigo.GELO: "PLACA DE GELO", TipoDePerigo.FOGO: "FOGO",
    TipoDePerigo.TEIA: "TEIA", TipoDePerigo.AREIA_MOVEDICA: "AREIA MOVEDICA", TipoDePerigo.LAVA: "LAVA",
    TipoDePerigo.BURACO: "BURACO (TUNEL)",
}
NOMES_DOS_MONSTROS: dict[TipoDeMonstro, str] = {
    TipoDeMonstro.ARANHA: "ARANHA", TipoDeMonstro.MINOTAURO: "MINOTAURO", TipoDeMonstro.BONECO_DE_NEVE: "BONECO DE NEVE",
    TipoDeMonstro.YETI: "YETI", TipoDeMonstro.MAGMAN: "MAGMAN", TipoDeMonstro.FORNALHA: "FORNALHA",
    TipoDeMonstro.AGUIA: "AGUIA", TipoDeMonstro.TORNADO: "TORNADO", TipoDeMonstro.TOUPEIRA: "TOUPEIRA",
    TipoDeMonstro.GOLEM: "GOLEM", TipoDeMonstro.COBRA: "COBRA", TipoDeMonstro.MUMIA: "MUMIA",
}

FERRAMENTAS: tuple[Ferramenta, ...] = (
    Ferramenta(Categoria.MAPA, "PAREDE", Especial.PAREDE),
    Ferramenta(Categoria.MAPA, "BORRACHA", Especial.BORRACHA),
    Ferramenta(Categoria.MAPA, "PORTAL", Especial.PORTAL),
    Ferramenta(Categoria.MAPA, "CAIXA ?", Especial.CAIXA),
    *(Ferramenta(Categoria.PERIGO, nome, perigo=tipo) for tipo, nome in NOMES_DOS_PERIGOS.items()),
    *(Ferramenta(Categoria.MONSTRO, nome, monstro=tipo) for tipo, nome in NOMES_DOS_MONSTROS.items()),
    *(Ferramenta(Categoria.ITEM, tipo.value.replace("_", "-").upper(), item=tipo) for tipo in TipoDeItem),
)


def ferramentas_da(categoria: Categoria) -> tuple[Ferramenta, ...]:
    return tuple(f for f in FERRAMENTAS if f.categoria is categoria)


class EditorDaArena:
    def __init__(self, labirinto: LabirintoEditavel, ambiente: Ambiente, jogador: Jogador,
                 sorteio: random.Random | None = None) -> None:
        self._lab = labirinto
        self._ambiente = ambiente
        self._jogador = jogador
        self._sorteio = sorteio if sorteio is not None else random.Random()

    def pode_editar(self, tile: Coordenada) -> bool:
        return not self._lab.na_borda(tile)

    def aplicar(self, ferramenta: Ferramenta, tile: Coordenada) -> bool:
        """Usa a ferramenta no tile. False se nao der (borda, em cima do jogador, parede...)."""
        if not self.pode_editar(tile):
            return False
        if ferramenta.especial is Especial.BORRACHA:
            return self.apagar(tile)
        if ferramenta.especial is Especial.PAREDE:
            return self._levantar_parede(tile)
        if self._lab.eh_parede(*tile):
            return False
        if ferramenta.especial is Especial.PORTAL:
            if not self._lab.mover_saida(tile):
                return False
            self._ambiente.limpar_tile(tile)
            self._ambiente.labirinto_mudou()
            return True
        if tile in (self._lab.entrada, self._lab.saida):
            return False
        if ferramenta.especial is Especial.CAIXA:
            self._ambiente.colocar_caixa(tile)
        elif ferramenta.perigo is not None:
            self._ambiente.colocar_perigo(ferramenta.perigo, tile)
        elif ferramenta.monstro is not None:
            monstro = criar_monstro(ferramenta.monstro, tile, self._lab, random.Random(self._sorteio.random()))
            self._ambiente.colocar_monstro(monstro)
        elif ferramenta.item is not None:
            self._ambiente.colocar_caixa(tile, ferramenta.item)
        return True

    def apagar(self, tile: Coordenada) -> bool:
        """Apaga o que tiver no tile; se nao tiver nada, derruba a parede."""
        if not self.pode_editar(tile):
            return False
        if self._ambiente.limpar_tile(tile):
            return True
        if self._lab.remover_parede(tile):
            self._ambiente.labirinto_mudou()
            return True
        return False

    def limpar_tudo(self) -> None:
        """Arena vazia de novo (so as bordas)."""
        for linha in range(self._lab.linhas):
            for coluna in range(self._lab.colunas):
                self._lab.remover_parede(Coordenada(coluna, linha))
        self._ambiente.limpar_tudo()

    def _levantar_parede(self, tile: Coordenada) -> bool:
        t = self._lab.tamanho_tile
        if Caixa(tile.coluna * t, tile.linha * t, t, t).intersecta(self._jogador.caixa_de_colisao()):
            return False  # nunca prende o jogador dentro da parede
        if not self._lab.colocar_parede(tile):
            return False
        self._ambiente.limpar_tile(tile)
        self._ambiente.labirinto_mudou()
        return True
