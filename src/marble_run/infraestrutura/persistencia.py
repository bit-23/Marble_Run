"""
persistencia.py - Implementacao concreta do RepositorioDeRecorde em arquivo.
"""
from __future__ import annotations

from pathlib import Path

from ..dominio.contratos import RepositorioDeRecorde


class RecordeEmArquivo(RepositorioDeRecorde):
    """Guarda a melhor fase em um arquivo de texto (ex.: src/recorde.txt)."""

    def __init__(self, caminho: Path) -> None:
        self._caminho = caminho

    def carregar(self) -> int:
        try:
            return int(self._caminho.read_text().strip())
        except (OSError, ValueError):
            return 0

    def salvar(self, fase: int) -> None:
        try:
            self._caminho.write_text(str(fase))
        except OSError:
            pass  # sem permissao de escrita: o jogo continua, so nao salva
