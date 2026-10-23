"""
cena.py - Tudo o que se ve de UMA fase.

    Cena = Cenario (labirinto + tema + clima)
         + DesenhoDoAmbiente (itens, perigos, efeitos no jogador)
         + EfeitosDoFenomeno (tempestade de areia, rajada...)
         + AnimacaoDoJogador
         + Camera (suave, antecipa o movimento, olha em volta, treme e da zoom)
         + Escuridao

Composicao: a Cena nao herda de ninguem; ela junta objetos pequenos, cada
um com uma responsabilidade. Antes tudo isso vivia dentro de Jogo e Cenario.
Os estados Jogando, Pausado, Vitoria e Derrota compartilham a mesma Cena.
"""
from __future__ import annotations

import math
import random
from typing import Iterable, Protocol

import pygame

from ..dominio.ambiente import Ocorrencia, TipoDeOcorrencia
from ..dominio.geometria import Vetor2
from ..dominio.labirinto import Coordenada, Labirinto
from ..dominio.partida import Fase
from .bestiario import DesenhoDosMonstros
from .elementos import DesenhoDoAmbiente
from .fenomenos import EfeitosDoFenomeno
from .icones import DESCRICOES_DOS_ITENS
from .personagem import AnimacaoDoJogador, SpritesDoJogador
from .pixelart import FontePixel
from .temas import CatalogoDeTemas, Tema

Deslocamento = tuple[int, int]  # canto superior esquerdo da camera, em pixels do mapa
BRANCO = (255, 255, 255)


class PreferenciasDeVisao(Protocol):
    """O pedacinho das Preferencias que a Cena precisa (ISP)."""

    @property
    def zoom(self) -> float: ...

    @property
    def tremor(self) -> bool: ...


def _suavizar(rapidez: float, dt: float) -> float:
    """Fracao do caminho ate o alvo a percorrer neste quadro (independe do FPS)."""
    return 1.0 - math.exp(-rapidez * dt)


class Camera:
    """Decide qual pedaco do mapa aparece na tela.

    * segue o jogador SUAVE (sem trancos, nem quando ele pula com a mola);
    * ANTECIPA: mostra um pouco mais do lado para onde ele esta indo;
    * OLHAR em volta: o jogador pode deslocar a camera (analogico direito/TFGH);
    * TREMOR: impactos (fogo, mola) e tremor continuo (terremoto);
    * VISOR: tamanho da area vista, em pixels do mapa (muda com o zoom).
    """

    SUAVIDADE = 7.0               # quanto maior, mais rapido alcanca o jogador
    ANTECIPACAO = 0.3             # segundos "a frente" do jogador
    ANTECIPACAO_MAXIMA = 80.0     # pixels
    SUAVIDADE_ANTECIPACAO = 3.0
    ALCANCE_DO_OLHAR = 180.0      # pixels
    SUAVIDADE_DO_OLHAR = 6.0
    DESVIO_MAXIMO = 0.4           # fracao do visor: o jogador nunca sai da tela
    TREMOR_MAXIMO = 12.0          # pixels
    ALIVIO_DO_TREMOR = 1.8        # "trauma" perdido por segundo

    def __init__(self, largura_visor: int, altura_visor: int, sorteio: random.Random | None = None) -> None:
        self._largura = largura_visor
        self._altura = altura_visor
        self._x = 0.0
        self._y = 0.0
        self._antecipacao = [0.0, 0.0]
        self._olhar = [0.0, 0.0]
        self._trauma = 0.0
        self._balanco = (0, 0)
        self._sorteio = sorteio if sorteio is not None else random.Random()
        self._foco_x = 0.5          # onde o jogador fica na tela (0.5 = no meio)
        self._prender_nas_bordas = True

    @property
    def visor(self) -> tuple[int, int]:
        return self._largura, self._altura

    @property
    def deslocamento(self) -> Deslocamento:
        return round(self._x) + self._balanco[0], round(self._y) + self._balanco[1]

    def ajustar_visor(self, largura: int, altura: int) -> None:
        self._largura, self._altura = largura, altura

    def focar(self, fracao_x: float, prender_nas_bordas: bool) -> None:
        """Ex.: 0.3 = jogador mais para a esquerda (sobra espaco para um painel a direita)."""
        self._foco_x = fracao_x
        self._prender_nas_bordas = prender_nas_bordas

    def tremer(self, forca: float) -> None:
        """Impacto: soma 'trauma' (0..1). O tremor cresce com o quadrado dele."""
        self._trauma = min(1.0, self._trauma + forca)

    def atualizar_tremor(self, dt: float, continuo: float = 0.0, habilitado: bool = True) -> None:
        self._trauma = max(0.0, self._trauma - self.ALIVIO_DO_TREMOR * dt)
        amplitude = self.TREMOR_MAXIMO * max(self._trauma ** 2, continuo * 0.7)
        if amplitude < 0.5 or not habilitado:
            self._balanco = (0, 0)
            return
        self._balanco = (round(self._sorteio.uniform(-amplitude, amplitude)),
                         round(self._sorteio.uniform(-amplitude, amplitude)))

    def enquadrar(self, alvo_x: float, alvo_y: float, largura_mapa: int, altura_mapa: int,
                  dt: float = 0.0, velocidade: Vetor2 = Vetor2(), olhar: Vetor2 = Vetor2(),
                  instantaneo: bool = False) -> None:
        k_ante = 1.0 if instantaneo else _suavizar(self.SUAVIDADE_ANTECIPACAO, dt)
        k_olhar = 1.0 if instantaneo else _suavizar(self.SUAVIDADE_DO_OLHAR, dt)
        k_pos = 1.0 if instantaneo else _suavizar(self.SUAVIDADE, dt)

        ante_x, ante_y = velocidade.x * self.ANTECIPACAO, velocidade.y * self.ANTECIPACAO
        tamanho = math.hypot(ante_x, ante_y)
        if tamanho > self.ANTECIPACAO_MAXIMA:
            ante_x, ante_y = ante_x / tamanho * self.ANTECIPACAO_MAXIMA, ante_y / tamanho * self.ANTECIPACAO_MAXIMA
        self._antecipacao[0] += (ante_x - self._antecipacao[0]) * k_ante
        self._antecipacao[1] += (ante_y - self._antecipacao[1]) * k_ante

        forca = min(1.0, olhar.norma)
        olhar_x = olhar.x / olhar.norma * forca * self.ALCANCE_DO_OLHAR if forca else 0.0
        olhar_y = olhar.y / olhar.norma * forca * self.ALCANCE_DO_OLHAR if forca else 0.0
        self._olhar[0] += (olhar_x - self._olhar[0]) * k_olhar
        self._olhar[1] += (olhar_y - self._olhar[1]) * k_olhar

        limite_x, limite_y = self._largura * self.DESVIO_MAXIMO, self._altura * self.DESVIO_MAXIMO
        desvio_x = max(-limite_x, min(limite_x, self._antecipacao[0] + self._olhar[0]))
        desvio_y = max(-limite_y, min(limite_y, self._antecipacao[1] + self._olhar[1]))
        alvo_cam_x = self._eixo(alvo_x + desvio_x, self._largura, largura_mapa, self._foco_x)
        alvo_cam_y = self._eixo(alvo_y + desvio_y, self._altura, altura_mapa, 0.5)
        self._x += (alvo_cam_x - self._x) * k_pos
        self._y += (alvo_cam_y - self._y) * k_pos

    def _eixo(self, alvo: float, visor: int, mapa: int, foco: float) -> float:
        if not self._prender_nas_bordas:
            return alvo - visor * foco
        if mapa <= visor:  # mapa menor que a tela: centraliza
            return -(visor - mapa) / 2
        return max(0.0, min(alvo - visor * foco, float(mapa - visor)))  # senao, nao passa da borda


class Escuridao:
    """Veu escuro com um 'buraco' de luz em volta do jogador.

    O raio da luz muda durante a fase (lanterna, apagao): a luz e desenhada
    uma vez no raio base e so e redimensionada quando o raio muda.
    """

    OPACIDADE = 235

    def __init__(self, raio_base: float) -> None:
        self._veu: pygame.Surface | None = None
        self._luz_base = self._criar_luz(max(8, int(raio_base)))
        self._luz = self._luz_base
        self._raio = self._luz_base.get_width() // 2

    def desenhar(self, tela: pygame.Surface, centro: tuple[int, int], raio: float) -> None:
        if self._veu is None or self._veu.get_size() != tela.get_size():
            self._veu = pygame.Surface(tela.get_size(), pygame.SRCALPHA)
        raio = max(8, int(raio))
        if raio != self._raio:
            base = self._luz_base.get_width() // 2
            self._luz = self._luz_base if raio == base else pygame.transform.smoothscale(
                self._luz_base, (raio * 2, raio * 2))
            self._raio = raio
        self._veu.fill((0, 0, 0, self.OPACIDADE))
        self._veu.blit(self._luz, (centro[0] - raio, centro[1] - raio), special_flags=pygame.BLEND_RGBA_SUB)
        tela.blit(self._veu, (0, 0))

    @classmethod
    def _criar_luz(cls, raio: int) -> pygame.Surface:
        luz = pygame.Surface((raio * 2, raio * 2), pygame.SRCALPHA)
        for r in range(raio, 0, -2):
            k = min(1.0, (1 - r / raio) * 1.6) ** 0.9
            pygame.draw.circle(luz, (0, 0, 0, int(cls.OPACIDADE * k)), (raio, raio), r)
        return luz


class Cenario:
    """Desenha um Labirinto com a pele de um Tema.

    Guarda so estado VISUAL (relogio das animacoes e o clima). As regras
    (paredes, colisao, saida) continuam no Labirinto do dominio.
    """

    def __init__(self, labirinto: Labirinto, tema: Tema) -> None:
        self._labirinto = labirinto
        self._paleta = tema.paleta
        self._texturas = tema.texturas(labirinto.tamanho_tile)
        self._clima = tema.criar_clima()
        self._tempo = 0.0

    @property
    def cor_de_fundo(self) -> tuple[int, int, int]:
        return self._paleta.fundo

    def atualizar(self, dt: float) -> None:
        self._tempo += dt
        self._clima.atualizar(dt)

    def desenhar(self, tela: pygame.Surface, camera: Deslocamento) -> None:
        lab, t = self._labirinto, self._labirinto.tamanho_tile
        cam_x, cam_y = camera
        c0 = max(0, cam_x // t)
        c1 = min(lab.colunas, (cam_x + tela.get_width()) // t + 2)
        l0 = max(0, cam_y // t)
        l1 = min(lab.linhas, (cam_y + tela.get_height()) // t + 2)

        for linha in range(l0, l1):
            for coluna in range(c0, c1):
                pos = (coluna * t - cam_x, linha * t - cam_y)
                if lab.eh_parede(coluna, linha):
                    com_face = not lab.eh_parede(coluna, linha + 1)  # chao logo abaixo
                    tela.blit(self._texturas.parede_face if com_face else self._texturas.parede, pos)
                else:
                    tela.blit(self._texturas.pisos[(coluna * 7 + linha * 13) % 4], pos)

        self._desenhar_entrada(tela, camera)
        self._desenhar_portal(tela, camera)

    def desenhar_brilho_da_saida(self, tela: pygame.Surface, camera: Deslocamento) -> None:
        """Halo do portal desenhado POR CIMA da escuridao: serve de farol."""
        cx, cy = self._labirinto.centro_do_tile(self._labirinto.saida)
        pulso = 0.75 + 0.25 * math.sin(self._tempo * 3)
        img = self._texturas.brilho
        if pulso < 0.99:
            img = img.copy()
            img.fill((int(255 * pulso),) * 3, special_flags=pygame.BLEND_RGB_MULT)
        r = self._texturas.brilho.get_width() // 2
        tela.blit(img, (cx - camera[0] - r, cy - camera[1] - r), special_flags=pygame.BLEND_RGB_ADD)

    def desenhar_clima(self, tela: pygame.Surface, camera: Deslocamento) -> None:
        self._clima.desenhar(tela, camera)

    def _desenhar_entrada(self, tela: pygame.Surface, camera: Deslocamento) -> None:
        cx, cy = self._labirinto.centro_do_tile(self._labirinto.entrada)
        t = self._labirinto.tamanho_tile
        pygame.draw.circle(tela, self._paleta.entrada, (cx - camera[0], cy - camera[1]), t // 2 - 8, 2)

    def _desenhar_portal(self, tela: pygame.Surface, camera: Deslocamento) -> None:
        cx, cy = self._labirinto.centro_do_tile(self._labirinto.saida)
        cx, cy = cx - camera[0], cy - camera[1]
        pulso = 0.5 + 0.5 * math.sin(self._tempo * 4)
        r = int(self._labirinto.tamanho_tile * (0.30 + 0.06 * pulso))
        pygame.draw.circle(tela, self._paleta.portal_aro, (cx, cy), r + 6, 3)
        pygame.draw.circle(tela, self._paleta.portal_miolo, (cx, cy), r)
        pygame.draw.circle(tela, BRANCO, (cx, cy), max(2, r // 2))


class TextosFlutuantes:
    """Recados curtos que sobem da cabeca do jogador ("-5S", "ROUBOU A BLUSA!", "BLOQUEADO!")."""

    DURACAO = 1.4

    def __init__(self) -> None:
        self._fonte = FontePixel()
        self._textos: list[list] = []  # [texto, cor, tempo]

    def reagir(self, ocorrencias: Iterable[Ocorrencia]) -> None:
        for o in ocorrencias:
            recado = self._recado(o)
            if recado is not None:
                self._textos.append([recado[0], recado[1], 0.0])

    @staticmethod
    def _recado(o: Ocorrencia) -> tuple[str, tuple[int, int, int]] | None:
        nome = DESCRICOES_DOS_ITENS[o.item][0] if o.item is not None else ""
        if o.tipo is TipoDeOcorrencia.ROUBOU_BUFF:
            return (f"A AGUIA LEVOU: {nome}!" if nome else "A AGUIA NAO ACHOU NADA"), (255, 140, 120)
        if o.tipo is TipoDeOcorrencia.GOLPE_BLOQUEADO:
            return f"{nome} PROTEGEU!", (150, 240, 150)
        if o.tipo is TipoDeOcorrencia.CAIU_NO_BURACO:
            return f"{round(o.segundos)}S", (255, 120, 90)
        if o.tipo is TipoDeOcorrencia.ENVENENOU:
            return "ENVENENADO!", (140, 240, 90)
        if o.tipo is TipoDeOcorrencia.CUROU_VENENO:
            return "CURADO!", (150, 240, 150)
        if o.tipo is TipoDeOcorrencia.ARREMESSADO:
            return ("A PIPA AJUDOU!", (150, 220, 255)) if o.item else ("TORNADO!", (220, 230, 240))
        if o.tipo is TipoDeOcorrencia.ATRAVESSOU_TUNEL:
            return "TUNEL!", (220, 180, 120)
        if o.tipo is TipoDeOcorrencia.QUEBROU_PAREDE:
            return "CRACK!", (255, 200, 90)
        if o.tipo is TipoDeOcorrencia.DESEJO_REALIZADO:
            return ("+20S" if o.segundos else "DESEJO REALIZADO!"), (255, 220, 110)
        return None

    def atualizar(self, dt: float) -> None:
        for texto in self._textos:
            texto[2] += dt
        self._textos = [t for t in self._textos if t[2] < self.DURACAO]

    def desenhar(self, tela: pygame.Surface, x: int, y: int) -> None:
        for i, (texto, cor, tempo) in enumerate(self._textos):
            subida = round(tempo / self.DURACAO * 30)
            if tempo > self.DURACAO * 0.7 and int(tempo * 16) % 2:
                continue
            self._fonte.escrever(tela, texto, 2, cor, centro=(x, y - 110 - subida - i * 18))


class Cena:
    ALTURA_DA_LUZ = 20       # a luz fica na altura do rosto, nao dos pes
    SUAVIDADE_DA_LUZ = 5.0   # lanterna/apagao mudam a luz aos poucos
    DURACAO_DO_FLASH = 0.35  # tela pisca vermelho ao perder coracao
    TREMORES = {
        TipoDeOcorrencia.QUEIMOU: 0.6,
        TipoDeOcorrencia.PULOU: 0.3,
        TipoDeOcorrencia.CONGELOU: 0.25,
        TipoDeOcorrencia.FICOU_PRESO: 0.2,
        TipoDeOcorrencia.MONSTRO_ATACOU: 0.6,
        TipoDeOcorrencia.ARREMESSADO: 0.4,
        TipoDeOcorrencia.CAIU_NO_BURACO: 0.5,
        TipoDeOcorrencia.ATRAVESSOU_PAREDE: 0.3,
        TipoDeOcorrencia.PUXADO: 0.3,
        TipoDeOcorrencia.ENVENENOU: 0.2,
        TipoDeOcorrencia.QUEBROU_PAREDE: 0.7,
    }

    def __init__(self, fase: Fase, cenario: Cenario, animacao: AnimacaoDoJogador,
                 camera: Camera, escuridao: Escuridao, elementos: DesenhoDoAmbiente,
                 fenomenos: EfeitosDoFenomeno, visao: PreferenciasDeVisao,
                 tamanho_tela: tuple[int, int], monstros: DesenhoDosMonstros | None = None) -> None:
        self._fase = fase
        self._cenario = cenario
        self._animacao = animacao
        self._camera = camera
        self._escuridao = escuridao
        self._elementos = elementos
        self._fenomenos = fenomenos
        self._monstros = monstros if monstros is not None else DesenhoDosMonstros(fase.ambiente, fase.labirinto)
        self._textos = TextosFlutuantes()
        self._luz_extra = 1.0
        self._visao = visao
        self._tamanho_tela = tamanho_tela
        self._mundo: pygame.Surface | None = None  # tela intermediaria usada com zoom
        self._raio_da_luz = self._raio_alvo()
        self._flash = 0.0
        self._veu_do_flash: pygame.Surface | None = None
        self.enquadrar(instantaneo=True)

    def reagir(self, ocorrencias: Iterable[Ocorrencia]) -> None:
        """Impactos da partida viram tremor de tela (e dano vira flash vermelho)."""
        ocorrencias = tuple(ocorrencias)
        for ocorrencia in ocorrencias:
            self._camera.tremer(self.TREMORES.get(ocorrencia.tipo, 0.0))
            if ocorrencia.dano:
                self._flash = self.DURACAO_DO_FLASH
        self._textos.reagir(ocorrencias)

    def animar_ambiente(self, dt: float) -> None:
        """Portal pulsando, neve caindo, fogo... (continua ate na tela de vitoria)."""
        self._cenario.atualizar(dt)
        self._elementos.atualizar(dt)
        self._monstros.atualizar(dt)
        self._textos.atualizar(dt)
        self._fenomenos.atualizar(dt)
        tremor = self._fenomenos.tremor()
        if self._fase.ambiente.perfuracao is not None:  # a broca faz tudo tremer
            tremor = max(tremor, 0.3)
        self._camera.atualizar_tremor(dt, tremor, self._visao.tremor)
        self._raio_da_luz += (self._raio_alvo() - self._raio_da_luz) * _suavizar(self.SUAVIDADE_DA_LUZ, dt)
        self._flash = max(0.0, self._flash - dt)

    def animar_jogador(self, dt: float) -> None:
        jogador = self._fase.jogador
        self._animacao.atualizar(dt, jogador.esta_andando, self._fase.ambiente.deslizando,
                                 jogador.bateu)

    def focar(self, fracao_x: float, prender_nas_bordas: bool = True) -> None:
        self._camera.focar(fracao_x, prender_nas_bordas)

    def tile_na_tela(self, pos: tuple[int, int]) -> Coordenada | None:
        """Qual tile do mapa esta embaixo deste ponto da tela (mouse). None = fora do mapa."""
        visor, (largura, altura) = self._camera.visor, self._tamanho_tela
        camera = self._camera.deslocamento
        x = camera[0] + pos[0] * visor[0] / largura
        y = camera[1] + pos[1] * visor[1] / altura
        lab = self._fase.labirinto
        t = lab.tamanho_tile
        tile = Coordenada(int(x // t), int(y // t))
        return tile if 0 <= tile.coluna < lab.colunas and 0 <= tile.linha < lab.linhas else None

    def retangulo_do_tile(self, tile: Coordenada) -> pygame.Rect:
        """Onde este tile aparece na tela (com zoom)."""
        visor, (largura, altura) = self._camera.visor, self._tamanho_tela
        camera = self._camera.deslocamento
        t = self._fase.labirinto.tamanho_tile
        kx, ky = largura / visor[0], altura / visor[1]
        return pygame.Rect(round((tile.coluna * t - camera[0]) * kx), round((tile.linha * t - camera[1]) * ky),
                           round(t * kx), round(t * ky))

    def enquadrar(self, dt: float = 0.0, olhar: Vetor2 = Vetor2(), instantaneo: bool = False) -> None:
        zoom = self._visao.zoom
        self._camera.ajustar_visor(math.ceil(self._tamanho_tela[0] / zoom),
                                   math.ceil(self._tamanho_tela[1] / zoom))
        jogador, labirinto = self._fase.jogador, self._fase.labirinto
        self._camera.enquadrar(jogador.x, jogador.y, labirinto.largura, labirinto.altura,
                               dt, jogador.velocidade_atual, olhar, instantaneo)

    def desenhar(self, tela: pygame.Surface, com_escuridao: bool) -> None:
        mundo = self._superficie_do_mundo(tela)
        camera = self._camera.deslocamento
        jogador = self._fase.jogador
        mundo.fill(self._cenario.cor_de_fundo)
        self._cenario.desenhar(mundo, camera)
        self._elementos.desenhar_chao(mundo, camera)
        self._monstros.desenhar_avisos(mundo, camera)
        self._elementos.desenhar_sob_jogador(mundo, camera, jogador)
        self._monstros.desenhar_corpos(mundo, camera, atras_de=jogador.y)
        self._animacao.desenhar(mundo, jogador, camera)
        self._monstros.desenhar_corpos(mundo, camera, na_frente_de=jogador.y)
        self._elementos.desenhar_sobre_jogador(mundo, camera, jogador)
        self._monstros.desenhar_no_alto(mundo, camera)
        if com_escuridao:
            centro = (round(jogador.x) - camera[0], round(jogador.y) - camera[1] - self.ALTURA_DA_LUZ)
            self._escuridao.desenhar(mundo, centro, self._raio_da_luz)
            self._cenario.desenhar_brilho_da_saida(mundo, camera)
        self._elementos.desenhar_luzes(mundo, camera, jogador)
        if com_escuridao:
            self._monstros.desenhar_luzes(mundo, camera)
        self._textos.desenhar(mundo, round(jogador.x) - camera[0], round(jogador.y) - camera[1])
        if mundo is not tela:
            pygame.transform.scale(mundo, tela.get_size(), tela)
        self._cenario.desenhar_clima(tela, camera)
        self._fenomenos.desenhar(tela)
        if self._flash > 0:
            if self._veu_do_flash is None or self._veu_do_flash.get_size() != tela.get_size():
                self._veu_do_flash = pygame.Surface(tela.get_size(), pygame.SRCALPHA)
            self._veu_do_flash.fill((220, 30, 20, int(130 * self._flash / self.DURACAO_DO_FLASH)))
            tela.blit(self._veu_do_flash, (0, 0))

    def _raio_alvo(self) -> float:
        return (self._fase.raio_visao * self._fase.ambiente.multiplicador_de_visao()
                * self._fase.labirinto.tamanho_tile * self._luz_extra)

    def ajustar_luz(self, fator: float) -> None:
        """Multiplica o alcance da luz (a noite da arena usa menos de 1)."""
        self._luz_extra = fator

    def _superficie_do_mundo(self, tela: pygame.Surface) -> pygame.Surface:
        """Com zoom, o mapa e desenhado em outra superficie e depois esticado para a tela."""
        visor = self._camera.visor
        if visor == tela.get_size():
            return tela
        if self._mundo is None or self._mundo.get_size() != visor:
            self._mundo = pygame.Surface(visor, 0, tela)  # mesmo formato de pixel da tela
        return self._mundo


class FabricaDeCenas:
    """Factory: monta a Cena de uma Fase com o tema sorteado pelo dominio."""

    def __init__(self, temas: CatalogoDeTemas, sprites: SpritesDoJogador, tamanho_tela: tuple[int, int],
                 visao: PreferenciasDeVisao) -> None:
        self._temas = temas
        self._sprites = sprites
        self._tamanho_tela = tamanho_tela
        self._visao = visao

    @property
    def nomes_dos_temas(self) -> tuple[str, ...]:
        return self._temas.nomes

    def criar(self, fase: Fase) -> Cena:
        labirinto = fase.labirinto
        return Cena(
            fase,
            Cenario(labirinto, self._temas.obter(fase.tema)),
            AnimacaoDoJogador(self._sprites),
            Camera(*self._tamanho_tela),
            Escuridao(fase.raio_visao * labirinto.tamanho_tile),
            DesenhoDoAmbiente(fase.ambiente, labirinto),
            EfeitosDoFenomeno(fase.ambiente),
            self._visao,
            self._tamanho_tela,
            DesenhoDosMonstros(fase.ambiente, labirinto),
        )
