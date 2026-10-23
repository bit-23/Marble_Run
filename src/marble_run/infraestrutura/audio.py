"""
audio.py - Implementacoes do contrato ServicoAudio + sintese de sons 8-bit.

Se existirem arquivos em  assets/sound/  eles sao usados:
    musica.ogg (ou .mp3/.wav)   passo.wav   vitoria.wav   derrota.wav   alerta.wav
    item  relogio  flauta  mola  congelar  queimar  teia  tempestade  terremoto  rajada  apagao
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
            Efeito.ITEM: self._item,
            Efeito.RELOGIO: self._relogio,
            Efeito.FLAUTA: self._flauta,
            Efeito.MOLA: self._mola,
            Efeito.CONGELAR: self._congelar,
            Efeito.QUEIMAR: self._queimar,
            Efeito.TEIA: self._teia,
            Efeito.TEMPESTADE: self._tempestade,
            Efeito.TERREMOTO: self._terremoto,
            Efeito.RAJADA: self._rajada,
            Efeito.APAGAO: self._apagao,
            Efeito.ERUPCAO: self._erupcao,
            Efeito.MENU: self._menu,
            Efeito.CONFIRMAR: self._confirmar,
            Efeito.DESLIZAR: self._deslizar,
            Efeito.TIQUE: self._tique,
            Efeito.PREMIO: self._premio,
            Efeito.SEGREDO: self._segredo,
            Efeito.ERRO: self._erro,
            Efeito.MONSTRO: self._monstro,
            Efeito.MAGIA: self._magia,
            Efeito.GUINCHO: self._guincho,
            Efeito.SIBILO: self._sibilo,
            Efeito.BROCA: self._broca,
            Efeito.EXTINTOR: self._extintor,
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

    def _arpejo(self, notas: Sequence[tuple[str, int]], passo: float, dur: float,
                forma: FormaDeOnda, volume: float) -> pygame.mixer.Sound:
        s = self._sint
        return self._para_sound(s.mixar(passo * len(notas) + dur, [
            (i * passo, s.onda(s.frequencia(n, o), dur, 0.28, forma)) for i, (n, o) in enumerate(notas)]), volume)

    def _item(self) -> pygame.mixer.Sound:
        return self._arpejo([("E", 5), ("B", 5)], 0.06, 0.1, FormaDeOnda.QUADRADA, 0.5)

    def _relogio(self) -> pygame.mixer.Sound:
        return self._arpejo([("C", 6), ("G", 5), ("C", 6), ("G", 5)], 0.08, 0.06, FormaDeOnda.TRIANGULO, 0.6)

    def _flauta(self) -> pygame.mixer.Sound:
        """Melodia 'encantadora' curtinha (seno = som de flauta)."""
        notas = [("A", 5), ("C", 6), ("E", 6), ("D", 6), ("C", 6), ("A", 5), ("B", 5), ("E", 6)]
        return self._arpejo(notas, 0.13, 0.22, FormaDeOnda.SENO, 0.8)

    def _mola(self) -> pygame.mixer.Sound:
        return self._para_sound(self._sint.onda(180, 0.28, 0.35, FormaDeOnda.QUADRADA, 900), 0.45)

    def _congelar(self) -> pygame.mixer.Sound:
        s = self._sint
        return self._para_sound(s.mixar(0.45, [
            (0, s.onda(2200, 0.4, 0.15, FormaDeOnda.TRIANGULO, 1400)),
            (0.05, s.onda(3100, 0.3, 0.1, FormaDeOnda.SENO, 2500)),
            (0, s.onda(0, 0.15, 0.12, FormaDeOnda.RUIDO))]), 0.5)

    def _queimar(self) -> pygame.mixer.Sound:
        s = self._sint
        return self._para_sound(s.mixar(0.4, [
            (0, s.onda(0, 0.4, 0.3, FormaDeOnda.RUIDO)),
            (0, s.onda(300, 0.25, 0.25, FormaDeOnda.QUADRADA, 90))]), 0.55)

    def _teia(self) -> pygame.mixer.Sound:
        return self._para_sound(self._sint.onda(520, 0.25, 0.25, FormaDeOnda.TRIANGULO, 260), 0.5)

    def _tempestade(self) -> pygame.mixer.Sound:
        s = self._sint
        return self._para_sound(s.mixar(1.2, [
            (0, s.onda(0, 1.2, 0.25, FormaDeOnda.RUIDO)),
            (0, s.onda(140, 1.0, 0.12, FormaDeOnda.SENO, 260))]), 0.5)

    def _terremoto(self) -> pygame.mixer.Sound:
        s = self._sint
        return self._para_sound(s.mixar(1.2, [
            (0, s.onda(48, 1.2, 0.45, FormaDeOnda.QUADRADA, 36)),
            (0, s.onda(0, 1.0, 0.18, FormaDeOnda.RUIDO))]), 0.6)

    def _rajada(self) -> pygame.mixer.Sound:
        s = self._sint
        return self._para_sound(s.mixar(0.8, [
            (0, s.onda(0, 0.8, 0.22, FormaDeOnda.RUIDO)),
            (0, s.onda(400, 0.7, 0.08, FormaDeOnda.SENO, 900))]), 0.45)

    def _apagao(self) -> pygame.mixer.Sound:
        return self._para_sound(self._sint.onda(330, 0.6, 0.3, FormaDeOnda.TRIANGULO, 110), 0.5)

    def _erupcao(self) -> pygame.mixer.Sound:
        """Ronco grave + chiado de lava subindo."""
        s = self._sint
        return self._para_sound(s.mixar(1.0, [
            (0, s.onda(60, 0.9, 0.4, FormaDeOnda.QUADRADA, 90)),
            (0.1, s.onda(0, 0.8, 0.25, FormaDeOnda.RUIDO)),
            (0.1, s.onda(200, 0.6, 0.12, FormaDeOnda.SENO, 700))]), 0.55)

    def _menu(self) -> pygame.mixer.Sound:
        return self._para_sound(self._sint.onda(660, 0.04, 0.25, FormaDeOnda.QUADRADA), 0.35)

    def _confirmar(self) -> pygame.mixer.Sound:
        return self._arpejo([("G", 5), ("D", 6)], 0.05, 0.08, FormaDeOnda.QUADRADA, 0.45)

    def _deslizar(self) -> pygame.mixer.Sound:
        s = self._sint
        return self._para_sound(s.mixar(0.5, [
            (0, s.onda(1800, 0.5, 0.12, FormaDeOnda.TRIANGULO, 900)),
            (0, s.onda(0, 0.3, 0.08, FormaDeOnda.RUIDO))]), 0.45)

    def _tique(self) -> pygame.mixer.Sound:
        return self._para_sound(self._sint.onda(1400, 0.025, 0.25, FormaDeOnda.QUADRADA), 0.3)

    def _erro(self) -> pygame.mixer.Sound:
        s = self._sint
        return self._para_sound(s.mixar(0.25, [
            (0, s.onda(140, 0.12, 0.3, FormaDeOnda.QUADRADA)),
            (0.12, s.onda(110, 0.12, 0.3, FormaDeOnda.QUADRADA))]), 0.5)

    def _premio(self) -> pygame.mixer.Sound:
        return self._arpejo([("C", 5), ("E", 5), ("G", 5), ("C", 6), ("E", 6)], 0.06, 0.14,
                            FormaDeOnda.QUADRADA, 0.55)

    def _monstro(self) -> pygame.mixer.Sound:
        """Rugido grave + pancada."""
        s = self._sint
        return self._para_sound(s.mixar(0.5, [
            (0, s.onda(110, 0.45, 0.4, FormaDeOnda.QUADRADA, 55)),
            (0, s.onda(0, 0.2, 0.3, FormaDeOnda.RUIDO))]), 0.6)

    def _magia(self) -> pygame.mixer.Sound:
        notas = [("C", 6), ("G", 5), ("E", 6), ("B", 5), ("G", 6)]
        return self._arpejo(notas, 0.05, 0.2, FormaDeOnda.SENO, 0.6)

    def _guincho(self) -> pygame.mixer.Sound:
        return self._para_sound(self._sint.onda(1800, 0.35, 0.25, FormaDeOnda.TRIANGULO, 900), 0.45)

    def _sibilo(self) -> pygame.mixer.Sound:
        s = self._sint
        return self._para_sound(s.mixar(0.5, [(0, s.onda(0, 0.5, 0.25, FormaDeOnda.RUIDO))]), 0.4)

    def _broca(self) -> pygame.mixer.Sound:
        s = self._sint
        return self._para_sound(s.mixar(0.5, [
            (0, s.onda(220, 0.5, 0.25, FormaDeOnda.QUADRADA, 260)),
            (0, s.onda(0, 0.5, 0.15, FormaDeOnda.RUIDO))]), 0.5)

    def _extintor(self) -> pygame.mixer.Sound:
        s = self._sint
        return self._para_sound(s.mixar(0.7, [
            (0, s.onda(0, 0.7, 0.3, FormaDeOnda.RUIDO)),
            (0, s.onda(2500, 0.5, 0.05, FormaDeOnda.SENO, 1800))]), 0.5)

    def _segredo(self) -> pygame.mixer.Sound:
        """Fanfarra de "codigo secreto" + explosao."""
        s = self._sint
        notas = [("G", 4), ("C", 5), ("E", 5), ("G", 5), ("C", 6)]
        partes = [(i * 0.07, s.onda(s.frequencia(n, o), 0.12, 0.25, FormaDeOnda.QUADRADA))
                  for i, (n, o) in enumerate(notas)]
        partes.append((0.35, s.onda(0, 0.45, 0.35, FormaDeOnda.RUIDO)))
        partes.append((0.35, s.onda(120, 0.4, 0.3, FormaDeOnda.QUADRADA, 40)))
        return self._para_sound(s.mixar(0.9, partes), 0.6)

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
        # volume "de fabrica" de cada som; o volume escolhido pelo jogador multiplica este
        self._base_efeitos = {efeito: som.get_volume() for efeito, som in self._efeitos.items()}
        self._base_musica = musica.get_volume() if musica is not None else 1.0

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
        self.definir_mudo(not self._mudo)

    def definir_mudo(self, mudo: bool) -> None:
        self._mudo = mudo
        if self._canal_musica:
            if self._mudo:
                self._canal_musica.pause()
            else:
                self._canal_musica.unpause()

    def definir_volumes(self, musica: float, efeitos: float) -> None:
        musica, efeitos = max(0.0, min(1.0, musica)), max(0.0, min(1.0, efeitos))
        if self._musica is not None:
            self._musica.set_volume(self._base_musica * musica)
        for efeito, som in self._efeitos.items():
            som.set_volume(self._base_efeitos[efeito] * efeitos)


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

    def definir_mudo(self, mudo: bool) -> None:
        pass

    def definir_volumes(self, musica: float, efeitos: float) -> None:
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
