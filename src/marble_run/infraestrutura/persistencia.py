"""Implementacoes concretas dos repositorios de persistencia."""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from ..apresentacao.contratos import RepositorioDePreferencias
from ..dominio.contratos import EdicaoDoRanking, EntradaDoRanking, RepositorioDePontuacao, RepositorioDeRecorde
from ..dominio.regras import NivelDeDificuldade


class PreferenciasEmJson(RepositorioDePreferencias):
    """Guarda as configuracoes (volume, zoom, dificuldade...) em um arquivo JSON."""

    def __init__(self, caminho: Path) -> None:
        self._caminho = caminho

    def carregar(self) -> dict[str, object]:
        try:
            dados = json.loads(self._caminho.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return dados if isinstance(dados, dict) else {}

    def salvar(self, dados: dict[str, object]) -> None:
        try:
            self._caminho.parent.mkdir(parents=True, exist_ok=True)
            self._caminho.write_text(json.dumps(dados, indent=2, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass  # sem permissao de escrita: o jogo continua, so nao lembra


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


class PontuacoesEmSQLite(RepositorioDePontuacao, EdicaoDoRanking):
    """Ranking: melhor pontuacao de cada jogador EM CADA dificuldade, num banco SQLite local.

    Bancos de versoes antigas (tabela `pontuacoes`, sem dificuldade) sao
    migrados uma unica vez: as pontuacoes antigas entram como NORMAL.
    """

    def __init__(self, caminho: Path) -> None:
        self._caminho = caminho
        self._caminho.parent.mkdir(parents=True, exist_ok=True)
        with self._conectar() as banco:
            banco.execute(
                """CREATE TABLE IF NOT EXISTS ranking (
                    jogador TEXT NOT NULL COLLATE NOCASE,
                    dificuldade TEXT NOT NULL,
                    pontos INTEGER NOT NULL,
                    fase INTEGER NOT NULL,
                    PRIMARY KEY (jogador, dificuldade)
                )"""
            )
            self._migrar_versao_antiga(banco)

    # ------------------------------------------------------------------
    # RepositorioDePontuacao
    # ------------------------------------------------------------------
    def carregar_melhor(self, jogador: str, dificuldade: NivelDeDificuldade) -> tuple[int, int]:
        with self._conectar() as banco:
            linha = banco.execute(
                "SELECT pontos, fase FROM ranking WHERE jogador = ? AND dificuldade = ?",
                (self._nome(jogador), dificuldade.value),
            ).fetchone()
        return (int(linha[0]), int(linha[1])) if linha else (0, 0)

    def salvar_melhor(self, jogador: str, dificuldade: NivelDeDificuldade, pontos: int, fase: int) -> None:
        with self._conectar() as banco:
            banco.execute(
                """INSERT INTO ranking (jogador, dificuldade, pontos, fase) VALUES (?, ?, ?, ?)
                   ON CONFLICT(jogador, dificuldade) DO UPDATE SET
                       pontos = excluded.pontos,
                       fase = excluded.fase
                   WHERE excluded.pontos > ranking.pontos""",
                (self._nome(jogador), dificuldade.value, max(0, int(pontos)), max(0, int(fase))),
            )

    def ranking(self, dificuldade: NivelDeDificuldade, limite: int = 10) -> list[EntradaDoRanking]:
        with self._conectar() as banco:
            linhas = banco.execute(
                """SELECT jogador, pontos, fase FROM ranking WHERE dificuldade = ?
                   ORDER BY pontos DESC, fase DESC, jogador LIMIT ?""",
                (dificuldade.value, limite),
            ).fetchall()
        return [EntradaDoRanking(nome, int(pontos), int(fase)) for nome, pontos, fase in linhas]

    # ------------------------------------------------------------------
    # EdicaoDoRanking (tela de desenvolvedor)
    # ------------------------------------------------------------------
    def apagar(self, jogador: str, dificuldade: NivelDeDificuldade) -> None:
        with self._conectar() as banco:
            banco.execute("DELETE FROM ranking WHERE jogador = ? AND dificuldade = ?",
                          (self._nome(jogador), dificuldade.value))

    def atualizar(self, jogador: str, dificuldade: NivelDeDificuldade, novo_nome: str,
                  pontos: int, fase: int) -> bool:
        antigo, novo = self._nome(jogador), novo_nome.strip() or self._nome(jogador)
        with self._conectar() as banco:
            if novo.casefold() != antigo.casefold():
                ocupado = banco.execute("SELECT 1 FROM ranking WHERE jogador = ? AND dificuldade = ?",
                                        (novo, dificuldade.value)).fetchone()
                if ocupado:
                    return False
            banco.execute(
                "UPDATE ranking SET jogador = ?, pontos = ?, fase = ? WHERE jogador = ? AND dificuldade = ?",
                (novo, max(0, int(pontos)), max(0, int(fase)), antigo, dificuldade.value),
            )
        return True

    def limpar(self, dificuldade: NivelDeDificuldade) -> None:
        with self._conectar() as banco:
            banco.execute("DELETE FROM ranking WHERE dificuldade = ?", (dificuldade.value,))

    # ------------------------------------------------------------------
    @staticmethod
    def _nome(jogador: str) -> str:
        return jogador.strip() or "Jogador"

    @staticmethod
    def _migrar_versao_antiga(banco: sqlite3.Connection) -> None:
        antiga = banco.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'pontuacoes'").fetchone()
        if antiga:
            banco.execute(
                """INSERT OR IGNORE INTO ranking (jogador, dificuldade, pontos, fase)
                   SELECT jogador, ?, pontos, fase FROM pontuacoes""",
                (NivelDeDificuldade.NORMAL.value,),
            )
            banco.execute("DROP TABLE pontuacoes")  # senao jogador apagado no editor "voltaria" sozinho

    @contextmanager
    def _conectar(self) -> Iterator[sqlite3.Connection]:
        banco = sqlite3.connect(self._caminho)
        try:
            with banco:
                yield banco
        finally:
            banco.close()
