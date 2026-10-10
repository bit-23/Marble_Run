"""
audio.py - Implementacoes do contrato ServicoAudio + sintese de sons 8-bit.

Se existirem arquivos em  assets/sound/  eles sao usados:
    musica.ogg (ou .mp3/.wav)   passo.wav   vitoria.wav   derrota.wav   alerta.wav
Se NAO existirem, o proprio codigo sintetiza sons simples (estilo 8-bit).

Antes uma unica classe (GerenciadorSom) iniciava o mixer, sintetizava ondas,
procurava arquivos, guardava os sons, tocava - e testava `self.ativo` em
todo metodo. Agora cada responsabilidade tem sua classe:
    Sintetizador   -> matematica das ondas (nao depende de pygame)
    BancoDeSons    -> monta cada som (arquivo ou "receita" sintetizada)
    AudioPygame    -> toca, pausa e silencia
    AudioMudo      -> Null Object para quando nao ha placa de som
    FabricaDeAudio -> decide qual dos dois o jogo vai usar
"""
from __future__ import annotations

import math
import random
from array import array
from enum import Enum
from pathlib import Path
from typing import Callable, Sequence

import pygame

from ..apresentacao.contratos import Efeito, ServicoAudio

Amostras = list[float]


class FormaDeOnda(Enum):
    SENO = "seno"
    QUADRADA = "quadrada"
    TRIANGULO = "triangulo"
    RUIDO = "ruido"


class Sintetizador:
    """Gera ondas simples como listas de amostras (floats entre -1 e 1)."""

    SEMITONS = {"C": -9, "C#": -8, "D": -7, "D#": -6, "E": -5, "F": -4,
                "F#": -3, "G": -2, "G#": -1, "A": 0, "A#": 1, "B": 2}

    def __init__(self, taxa: int, aleatorio: random.Random | None = None) -> None:
        self._taxa = taxa
        self._aleatorio = aleatorio if aleatorio is not None else random.Random()
        # tabela de despacho: cada forma de onda sabe calcular sua amostra
        self._formas: dict[FormaDeOnda, Callable[[float], float]] = {
            FormaDeOnda.SENO: lambda fase: math.sin(2 * math.pi * fase),
            FormaDeOnda.QUADRADA: lambda fase: 1.0 if fase < 0.5 else -1.0,
            FormaDeOnda.TRIANGULO: lambda fase: 4 * abs(fase - 0.5) - 1,
            FormaDeOnda.RUIDO: lambda _fase: self._aleatorio.uniform(-1, 1),
        }

    @classmethod
    def frequencia(cls, nota: str, oitava: int) -> float:
        return 440.0 * 2 ** ((cls.SEMITONS[nota] + 12 * (oitava - 4)) / 12)

    def onda(self, freq: float, dur: float, vol: float = 0.4,
             forma: FormaDeOnda = FormaDeOnda.SENO, freq_fim: float | None = None) -> Amostras:
        """Gera `dur` segundos de uma onda, com ataque rapido e queda suave."""
        amostra = self._formas[forma]
        n = int(self._taxa * dur)
        saida = []
        fase = 0.0
        for i in range(n):
            f = freq if freq_fim is None else freq + (freq_fim - freq) * i / n
            fase = (fase + f / self._taxa) % 1.0
            ataque = min(1.0, i / (0.004 * self._taxa))
            queda = (1 - i / n) ** 1.5
            saida.append(amostra(fase) * vol * ataque * queda)
        return saida

    def mixar(self, duracao: float, partes: Sequence[tuple[float, Amostras]]) -> Amostras:
        """Soma varias trilhas. partes = [(inicio_em_segundos, amostras), ...]"""
        buf = [0.0] * int(self._taxa * duracao)
        for inicio, amostras in partes:
            off = int(inicio * self._taxa)
            for i, v in enumerate(amostras):
                if off + i < len(buf):
                    buf[off + i] += v
        return buf


class BancoDeSons:
    """Monta os sons do jogo: arquivo de assets/sound/ se existir, senao sintese."""

    EXTENSOES = (".ogg", ".wav", ".mp3")
    VOLUME_MUSICA = 0.35

    def __init__(self, pasta: Path, sintetizador: Sintetizador, canais: int) -> None:
        self._pasta = pasta
        self._sint = sintetizador
        self._canais = canais
        self._receitas: dict[Efeito, Callable[[], pygame.mixer.Sound]] = {
            Efeito.PASSO: self._passo,
            Efeito.VITORIA: self._vitoria,
            Efeito.DERROTA: self._derrota,
            Efeito.ALERTA: self._alerta,
        }

    def efeitos(self) -> dict[Efeito, pygame.mixer.Sound]:
        sons = {}
        for efeito, receita in self._receitas.items():
            arquivo = self._arquivo(efeito.value)
            try:
                sons[efeito] = pygame.mixer.Sound(str(arquivo)) if arquivo else receita()
            except pygame.error as erro:
                print(f"[som] falha ao carregar '{efeito.value}': {erro}")
        return sons

    def musica(self) -> pygame.mixer.Sound | None:
        arquivo = self._arquivo("musica")
        try:
            musica = pygame.mixer.Sound(str(arquivo)) if arquivo else self._sintetizar_musica()
            musica.set_volume(self.VOLUME_MUSICA)
            return musica
        except pygame.error as erro:
            print(f"[som] falha ao preparar musica: {erro}")
            return None

    # ------------------------------------------------------------------
    # Receitas 8-bit
    # ------------------------------------------------------------------
    def _passo(self) -> pygame.mixer.Sound:
        s = self._sint
        return self._para_sound(s.mixar(0.07, [
            (0, s.onda(0, 0.07, 0.22, FormaDeOnda.RUIDO)),
            (0, s.onda(95, 0.07, 0.35, FormaDeOnda.SENO))]), 0.5)

    def _vitoria(self) -> pygame.mixer.Sound:
        s = self._sint
        notas = [("C", 5), ("E", 5), ("G", 5), ("C", 6)]
        return self._para_sound(s.mixar(0.6, [
            (i * 0.1, s.onda(s.frequencia(n, o), 0.16, 0.28, FormaDeOnda.QUADRADA))
            for i, (n, o) in enumerate(notas)]), 0.7)

    def _derrota(self) -> pygame.mixer.Sound:
        s = self._sint
        notas = [("E", 4), ("D#", 4), ("D", 4), ("A", 3)]
        return self._para_sound(s.mixar(1.2, [
            (i * 0.28, s.onda(s.frequencia(n, o), 0.3, 0.3, FormaDeOnda.TRIANGULO, s.frequencia(n, o) * 0.94))
            for i, (n, o) in enumerate(notas)]), 0.8)

    def _alerta(self) -> pygame.mixer.Sound:
        return self._para_sound(self._sint.onda(880, 0.09, 0.3, FormaDeOnda.QUADRADA), 0.5)

    def _sintetizar_musica(self) -> pygame.mixer.Sound:
        """Loop de ~9s: baixo + arpejo em La menor (Am - F - C - G)."""
        s = self._sint
        colcheia = 60 / 110 / 2
        progressao = [
            (("A", 2), [("A", 3), ("C", 4), ("E", 4)]),
            (("F", 2), [("F", 3), ("A", 3), ("C", 4)]),
            (("C", 3), [("C", 4), ("E", 4), ("G", 4)]),
            (("G", 2), [("G", 3), ("B", 3), ("D", 4)]),
        ]
        padrao = [0, 1, 2, 1, 0, 1, 2, 1]
        partes = []
        for c, (baixo, acorde) in enumerate(progressao):
            t0 = c * 8 * colcheia
            for b in (0, 4):  # baixo nas batidas 1 e 3
                partes.append((t0 + b * colcheia,
                               s.onda(s.frequencia(*baixo), colcheia * 3.6, 0.20, FormaDeOnda.QUADRADA)))
            for i, idx in enumerate(padrao):
                partes.append((t0 + i * colcheia,
                               s.onda(s.frequencia(*acorde[idx]), colcheia * 1.4, 0.16, FormaDeOnda.TRIANGULO)))
        return self._para_sound(s.mixar(32 * colcheia, partes))

    # ------------------------------------------------------------------
    def _para_sound(self, amostras: Amostras, volume: float = 1.0) -> pygame.mixer.Sound:
        dados = array("h")
        for v in amostras:
            pcm = int(max(-1.0, min(1.0, v)) * 32767)
            dados.extend([pcm] * self._canais)
        som = pygame.mixer.Sound(buffer=dados.tobytes())
        som.set_volume(volume)
        return som

    def _arquivo(self, nome: str) -> Path | None:
        for extensao in self.EXTENSOES:
            caminho = self._pasta / (nome + extensao)
            if caminho.exists():
                return caminho
        return None


class AudioPygame(ServicoAudio):
    """Toca efeitos e musica com pygame.mixer."""

    def __init__(self, efeitos: dict[Efeito, pygame.mixer.Sound],
                 musica: pygame.mixer.Sound | None) -> None:
        self._efeitos = dict(efeitos)
        self._musica = musica
        self._canal_musica: pygame.mixer.Channel | None = None
        self._mudo = False

    def tocar(self, efeito: Efeito) -> None:
        som = self._efeitos.get(efeito)
        if som is not None and not self._mudo:
            som.play()

    def iniciar_musica(self) -> None:
        if self._musica is None or self._canal_musica is not None:
            return
        self._canal_musica = self._musica.play(loops=-1)
        if self._mudo and self._canal_musica:
            self._canal_musica.pause()

    def alternar_mudo(self) -> None:
        self._mudo = not self._mudo
        if self._canal_musica:
            if self._mudo:
                self._canal_musica.pause()
            else:
                self._canal_musica.unpause()


class AudioMudo(ServicoAudio):
    """Null Object: cumpre o contrato sem fazer nada.

    Com ele, nenhum outro codigo precisa perguntar "tem som?" - basta
    chamar os metodos normalmente (polimorfismo no lugar de if/else).
    """

    def tocar(self, efeito: Efeito) -> None:
        pass

    def iniciar_musica(self) -> None:
        pass

    def alternar_mudo(self) -> None:
        pass


class FabricaDeAudio:
    """Factory: entrega o ServicoAudio certo para esta maquina."""

    TAXA, FORMATO, CANAIS, BUFFER = 22050, -16, 1, 512  # 16 bits: necessario para sintetizar

    @classmethod
    def pre_configurar(cls) -> None:
        """Chamar ANTES de pygame.init(): evita atraso nos sons."""
        pygame.mixer.pre_init(cls.TAXA, cls.FORMATO, cls.CANAIS, cls.BUFFER)

    @classmethod
    def criar(cls, pasta_sons: Path) -> ServicoAudio:
        try:
            taxa, canais = cls._iniciar_mixer()
        except pygame.error as erro:
            print(f"[som] audio indisponivel, jogo ficara mudo ({erro})")
            return AudioMudo()
        banco = BancoDeSons(pasta_sons, Sintetizador(taxa), canais)
        return AudioPygame(banco.efeitos(), banco.musica())

    @classmethod
    def _iniciar_mixer(cls) -> tuple[int, int]:
        config = pygame.mixer.get_init()
        if not config or config[1] != cls.FORMATO:
            pygame.mixer.quit()
            pygame.mixer.init(cls.TAXA, cls.FORMATO, cls.CANAIS, cls.BUFFER)
        taxa, _, canais = pygame.mixer.get_init()
        return taxa, canais
