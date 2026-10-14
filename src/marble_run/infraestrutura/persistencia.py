"""Implementacoes concretas dos repositorios de persistencia."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from ..dominio.contratos import RepositorioDePontuacao, RepositorioDeRecorde


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


class PontuacoesEmSQLite(RepositorioDePontuacao):
    """Guarda a melhor pontuacao por jogador em um banco SQLite local."""

    def __init__(self, caminho: Path) -> None:
        self._caminho = caminho
        self._caminho.parent.mkdir(parents=True, exist_ok=True)
        with self._conectar() as banco:
            banco.execute(
                """CREATE TABLE IF NOT EXISTS pontuacoes (
                    jogador TEXT PRIMARY KEY COLLATE NOCASE,
                    pontos INTEGER NOT NULL,
                    fase INTEGER NOT NULL
                )"""
            )

    def carregar_melhor(self, jogador: str) -> tuple[int, int]:
        with self._conectar() as banco:
            linha = banco.execute(
                "SELECT pontos, fase FROM pontuacoes WHERE jogador = ? COLLATE NOCASE",
                (jogador.strip().casefold(),),
            ).fetchone()
        return (int(linha[0]), int(linha[1])) if linha else (0, 0)

    def salvar_melhor(self, jogador: str, pontos: int, fase: int) -> None:
        nome = jogador.strip().casefold() or "jogador"
        with self._conectar() as banco:
            banco.execute(
                """INSERT INTO pontuacoes (jogador, pontos, fase) VALUES (?, ?, ?)
                   ON CONFLICT(jogador) DO UPDATE SET
                       pontos = excluded.pontos,
                       fase = excluded.fase
                   WHERE excluded.pontos > pontuacoes.pontos""",
                (nome, int(pontos), int(fase)),
            )

    @contextmanager
    def _conectar(self) -> Iterator[sqlite3.Connection]:
        banco = sqlite3.connect(self._caminho)
        try:
            with banco:
                yield banco
        finally:
            banco.close()
