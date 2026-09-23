"""
song.py - Som do jogo.

Se existirem arquivos em  assets/sound/  eles sao usados:
    musica.ogg (ou .mp3/.wav)   passo.wav   vitoria.wav   derrota.wav   alerta.wav
Se NAO existirem, o proprio codigo sintetiza sons simples (estilo 8-bit).
Ou seja: o jogo tem som mesmo sem nenhum arquivo de audio, e se nao houver
placa de som ele simplesmente fica mudo (sem quebrar).
"""
import math
import random
from array import array
from pathlib import Path

import pygame

PASTA_SOM = Path(__file__).resolve().parent / "assets" / "sound"
EXTENSOES = (".ogg", ".wav", ".mp3")


def _freq(nota, oitava):
    semitons = {"C": -9, "C#": -8, "D": -7, "D#": -6, "E": -5, "F": -4,
                "F#": -3, "G": -2, "G#": -1, "A": 0, "A#": 1, "B": 2}[nota]
    return 440.0 * 2 ** ((semitons + 12 * (oitava - 4)) / 12)


class GerenciadorSom:
    def __init__(self):
        self.ativo = False
        self.mudo = False
        self.efeitos = {}
        self.musica = None
        self.canal_musica = None
        try:
            init = pygame.mixer.get_init()
            if not init or init[1] != -16:  # precisamos de 16 bits para sintetizar
                pygame.mixer.quit()
                pygame.mixer.init(22050, -16, 1, 512)
            self.taxa, _, self.canais = pygame.mixer.get_init()
            self.ativo = True
        except pygame.error as erro:
            print(f"[som] audio indisponivel, jogo ficara mudo ({erro})")
            return
        self._preparar_efeitos()
        self._preparar_musica()

    # ------------------------------------------------------------------
    # Sintese de ondas
    # ------------------------------------------------------------------
    def _onda(self, freq, dur, vol=0.4, forma="seno", freq_fim=None):
        """Gera `dur` segundos de uma onda. Retorna lista de floats (-1..1)."""
        n = int(self.taxa * dur)
        saida = []
        fase = 0.0
        for i in range(n):
            f = freq if freq_fim is None else freq + (freq_fim - freq) * i / n
            fase = (fase + f / self.taxa) % 1.0
            if forma == "seno":
                v = math.sin(2 * math.pi * fase)
            elif forma == "quadrada":
                v = 1.0 if fase < 0.5 else -1.0
            elif forma == "triangulo":
                v = 4 * abs(fase - 0.5) - 1
            else:  # ruido
                v = random.uniform(-1, 1)
            ataque = min(1.0, i / (0.004 * self.taxa))
            queda = (1 - i / n) ** 1.5
            saida.append(v * vol * ataque * queda)
        return saida

    def _mixar(self, total_seg, partes):
        """partes = [(inicio_em_segundos, amostras), ...]"""
        buf = [0.0] * int(self.taxa * total_seg)
        for inicio, amostras in partes:
            off = int(inicio * self.taxa)
            for i, v in enumerate(amostras):
                if off + i < len(buf):
                    buf[off + i] += v
        return buf

    def _para_sound(self, amostras, volume=1.0):
        dados = array("h")
        for v in amostras:
            s = int(max(-1.0, min(1.0, v)) * 32767)
            dados.extend([s] * self.canais)
        som = pygame.mixer.Sound(buffer=dados.tobytes())
        som.set_volume(volume)
        return som

    # ------------------------------------------------------------------
    # Carregar arquivos (se existirem) ou sintetizar
    # ------------------------------------------------------------------
    def _arquivo(self, nome):
        for ext in EXTENSOES:
            caminho = PASTA_SOM / (nome + ext)
            if caminho.exists():
                return caminho
        return None

    def _preparar_efeitos(self):
        sintese = {
            "passo": lambda: self._para_sound(self._mixar(0.07, [
                (0, self._onda(0, 0.07, 0.22, "ruido")),
                (0, self._onda(95, 0.07, 0.35, "seno"))]), 0.5),
            "vitoria": lambda: self._para_sound(self._mixar(0.6, [
                (i * 0.1, self._onda(_freq(n, o), 0.16, 0.28, "quadrada"))
                for i, (n, o) in enumerate([("C", 5), ("E", 5), ("G", 5), ("C", 6)])]), 0.7),
            "derrota": lambda: self._para_sound(self._mixar(1.2, [
                (i * 0.28, self._onda(_freq(n, o), 0.3, 0.3, "triangulo", _freq(n, o) * 0.94))
                for i, (n, o) in enumerate([("E", 4), ("D#", 4), ("D", 4), ("A", 3)])]), 0.8),
            "alerta": lambda: self._para_sound(self._onda(880, 0.09, 0.3, "quadrada"), 0.5),
        }
        for nome, criar in sintese.items():
            arq = self._arquivo(nome)
            try:
                self.efeitos[nome] = pygame.mixer.Sound(str(arq)) if arq else criar()
            except pygame.error as erro:
                print(f"[som] falha ao carregar '{nome}': {erro}")

    def _preparar_musica(self):
        arq = self._arquivo("musica")
        try:
            if arq:
                self.musica = pygame.mixer.Sound(str(arq))
            else:
                self.musica = self._sintetizar_musica()
            self.musica.set_volume(0.35)
        except pygame.error as erro:
            print(f"[som] falha ao preparar musica: {erro}")

    def _sintetizar_musica(self):
        """Loop de ~9s: baixo + arpejo em La menor (Am - F - C - G)."""
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
                               self._onda(_freq(*baixo), colcheia * 3.6, 0.20, "quadrada")))
            for i, idx in enumerate(padrao):
                partes.append((t0 + i * colcheia,
                               self._onda(_freq(*acorde[idx]), colcheia * 1.4, 0.16, "triangulo")))
        return self._para_sound(self._mixar(32 * colcheia, partes))

    # ------------------------------------------------------------------
    # API usada pelo jogo
    # ------------------------------------------------------------------
    def tocar(self, nome):
        if self.ativo and not self.mudo and nome in self.efeitos:
            self.efeitos[nome].play()

    def iniciar_musica(self):
        if self.ativo and self.musica and self.canal_musica is None:
            self.canal_musica = self.musica.play(loops=-1)
            if self.mudo and self.canal_musica:
                self.canal_musica.pause()

    def alternar_mudo(self):
        self.mudo = not self.mudo
        if self.canal_musica:
            if self.mudo:
                self.canal_musica.pause()
            else:
                self.canal_musica.unpause()