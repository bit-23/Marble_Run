"""
servicos.py - Objetos compartilhados pelas telas do jogo.

ServicosDoJogo e um "Parameter Object": em vez de cada Estado receber dez
parametros (ou buscar variaveis globais), recebe um pacote imutavel com
os colaboradores ja montados pelo main.py (injecao de dependencias).
"""
from __future__ import annotations

from dataclasses import dataclass

from ..dominio.regras import Recorde
from .cena import FabricaDeCenas
from .contratos import Controle
from .interface import Hud, Painel, Tipografia
from .personagem import SpritesDoJogador
from .sonorizacao import RitmoDePassos


class Preferencias:
    """Opcoes que o jogador liga/desliga durante o jogo."""

    def __init__(self, escuridao: bool = True) -> None:
        self._escuridao = escuridao

    @property
    def escuridao(self) -> bool:
        return self._escuridao

    def alternar_escuridao(self) -> None:
        self._escuridao = not self._escuridao


@dataclass(frozen=True)
class ServicosDoJogo:
    titulo: str
    tipografia: Tipografia
    hud: Hud
    painel: Painel
    cenas: FabricaDeCenas
    sprites: SpritesDoJogador
    controle: Controle
    passos: RitmoDePassos
    recorde: Recorde
    preferencias: Preferencias
