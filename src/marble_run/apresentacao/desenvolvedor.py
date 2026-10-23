"""
desenvolvedor.py - Menu secreto DESENVOLVEDOR (codigo CIMA, BAIXO, DIREITA, ESQUERDA no menu).

    EDITAR RANKING   -> apagar, renomear, mudar pontos/fase, limpar uma dificuldade
    TESTE DOS MAPAS  -> joga qualquer mapa sem tempo, com atalhos para mostrar cada buff/debuff
"""
from __future__ import annotations

from .estados import ContextoDoJogo, Estado
from .menus import Botao, Opcao, TelaDeMenu
from .ranking import EstadoEditorDoRanking
from .vitrine import EstadoEscolhaDaApresentacao


class EstadoDesenvolvedor(TelaDeMenu):
    TITULO = "DESENVOLVEDOR"
    LARGURA_PAINEL = 240

    def __init__(self, jogo: ContextoDoJogo, retorno: Estado) -> None:
        self._retorno = retorno
        super().__init__(jogo)

    def _criar_opcoes(self) -> list[Opcao]:
        jogo = self._jogo
        return [
            Botao("EDITAR RANKING", lambda: jogo.mudar_estado(EstadoEditorDoRanking(jogo, self)),
                  "APAGAR, RENOMEAR, MUDAR PONTOS OU LIMPAR"),
            Botao("TESTE DOS MAPAS", lambda: jogo.mudar_estado(EstadoEscolhaDaApresentacao(jogo, self)),
                  "JOGA QUALQUER MAPA SEM TEMPO, COM ATALHOS"),
            Botao("VOLTAR", self._voltar),
        ]

    def _voltar(self) -> None:
        self._jogo.mudar_estado(self._retorno)

    def _subtitulo(self) -> str:
        return "AREA SECRETA - CUIDADO COM O QUE MEXE!"

    def _topo_painel(self) -> int:
        return 110
