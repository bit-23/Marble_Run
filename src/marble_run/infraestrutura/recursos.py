"""
recursos.py - ONDE ficam os arquivos do jogo (sprites, sons, recorde).

Antes cada modulo calculava seus caminhos com Path(__file__) e tinha seus
proprios "fallbacks". Agora existe um unico responsavel por isso -
inclusive para o executavel gerado pelo PyInstaller (sys._MEIPASS).
"""
from __future__ import annotations

import sys
from pathlib import Path


class LocalizadorDeRecursos:
    def __init__(self, pasta_src: Path) -> None:
        self._pasta_src = pasta_src
        # assets na raiz do projeto (se alguem mover) ou dentro de src/ (padrao)
        self._pasta_assets = self._primeira_existente(pasta_src.parent / "assets", pasta_src / "assets")

    @classmethod
    def detectar(cls) -> LocalizadorDeRecursos:
        """Descobre a pasta src, rodando pelo codigo-fonte ou pelo .exe."""
        if getattr(sys, "frozen", False):
            base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
            return cls(base / "src" if (base / "src").exists() else base)
        return cls(Path(__file__).resolve().parents[2])  # .../src/marble_run/infraestrutura -> .../src

    @property
    def pasta_sprites_jogador(self) -> Path:
        return self._pasta_assets / "images" / "jogador"

    @property
    def pasta_sons(self) -> Path:
        return self._pasta_assets / "sound"

    @property
    def arquivo_recorde(self) -> Path:
        return self._pasta_src / "recorde.txt"

    @staticmethod
    def _primeira_existente(*candidatas: Path) -> Path:
        return next((pasta for pasta in candidatas if pasta.exists()), candidatas[-1])
