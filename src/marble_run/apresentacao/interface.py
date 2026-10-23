"""
interface.py - Componentes de interface reutilizaveis: texto, HUD e painel.

Antes eram metodos privados de Jogo (_texto, _desenhar_hud, _painel).
Separados, cada tela usa o que precisa e as cores ganham nomes.
"""
from __future__ import annotations

from enum import Enum

import pygame

from ..dominio.ambiente import Ambiente, Condicao, Fenomeno, TipoDeItem
from ..dominio.partida import Partida
from .icones import icone

Cor = tuple[int, int, int]

DOURADO = (255, 214, 90)
BRANCO_SUAVE = (230, 230, 240)
CINZA_AZULADO = (140, 140, 170)
VERDE_CLARO = (120, 220, 150)


class Fonte(Enum):
    GIGANTE = 96
    GRANDE = 56
    MEDIA = 34
    PEQUENA = 24


class Tipografia:
    """Fontes do jogo + texto com sombra (todas as telas escrevem por aqui)."""

    COR_SOMBRA = (0, 0, 0)

    def __init__(self) -> None:
        self._fontes = {fonte: pygame.font.Font(None, fonte.value) for fonte in Fonte}

    def escrever(self, tela: pygame.Surface, texto: str, fonte: Fonte, cor: Cor, *,
                 centro: tuple[int, int] | None = None, canto: tuple[int, int] | None = None) -> None:
        """Escreve centralizado em `centro` ou a partir do canto superior esquerdo `canto`."""
        f = self._fontes[fonte]
        img = f.render(texto, True, cor)
        pos = img.get_rect(center=centro) if centro else img.get_rect(topleft=canto)
        tela.blit(f.render(texto, True, self.COR_SOMBRA), pos.move(2, 2))
        tela.blit(img, pos)

    def medir(self, texto: str, fonte: Fonte) -> tuple[int, int]:
        return self._fontes[fonte].size(texto)


# Como cada condicao aparece no HUD: icone do item que a causou ou um rotulo
ICONE_DA_CONDICAO: dict[Condicao, TipoDeItem] = {
    Condicao.BLUSA: TipoDeItem.BLUSA,
    Condicao.CAFE: TipoDeItem.CAFE,
    Condicao.LANTERNA: TipoDeItem.LANTERNA,
    Condicao.ESTRELA: TipoDeItem.ESTRELA,
    Condicao.BUSSOLA: TipoDeItem.BUSSOLA,
    Condicao.CALMARIA: TipoDeItem.FLAUTA,
    Condicao.BOTA: TipoDeItem.BOTA,
    Condicao.GUARDA_CHUVA: TipoDeItem.GUARDA_CHUVA,
    Condicao.PIPA: TipoDeItem.PIPA,
    Condicao.TAPETE: TipoDeItem.TAPETE,
    Condicao.BROCA: TipoDeItem.BROCA,
    Condicao.CAPACETE: TipoDeItem.CAPACETE,
    Condicao.CAMINHO: TipoDeItem.GENIO,
}
ROTULO_DA_CONDICAO: dict[Condicao, tuple[str, Cor]] = {
    Condicao.CONGELADO: ("CONGELADO", (130, 205, 255)),
    Condicao.QUEIMANDO: ("PEGANDO FOGO!", (255, 120, 60)),
    Condicao.TONTO: ("TONTO! Controles invertidos", (255, 220, 110)),
    Condicao.CAIDO: ("CAIU NO BURACO!", (220, 170, 110)),
}
# (aviso antes de comecar, enquanto acontece)
TEXTOS_DOS_FENOMENOS: dict[Fenomeno, tuple[str, str]] = {
    Fenomeno.TEMPESTADE_DE_AREIA: ("Uma tempestade de areia se aproxima...", "TEMPESTADE DE AREIA! Voce esta lento"),
    Fenomeno.TEMPESTADE_DE_GELO: ("O ar esta ficando gelado...", "TEMPESTADE DE GELO! Voce esta lento"),
    Fenomeno.APAGAO: ("As luzes estao tremulando...", "APAGAO!"),
    Fenomeno.TERREMOTO: ("O chao comeca a tremer...", "TERREMOTO! Controles invertidos"),
    Fenomeno.RAJADA: ("O vento esta ficando forte...", "RAJADA DE VENTO!"),
    Fenomeno.ERUPCAO: ("O chao esta rachando... SAIA DAS RACHADURAS!", "ERUPCAO! Cuidado com a lava"),
}

# coracao em pixel art (7x6)
_CORACAO = (".##.##.", "#######", "#######", ".#####.", "..###..", "...#...")

NOMES_DOS_MAPAS = {"masmorra": "MASMORRA", "gelo": "GELO", "fogo": "FOGO", "deserto": "DESERTO", "vento": "VENTO",
                   "terra": "TERRA"}


def nome_do_mapa(tema: str) -> str:
    return NOMES_DOS_MAPAS.get(tema, tema.upper())


class Hud:
    """Barra superior: fase, pontos, coracoes e relogio (+ semente no rodape)."""

    ALTURA = 44
    COR_FUNDO = (10, 8, 20)
    COR_TRILHO = (40, 36, 60)
    COR_MOLDURA = (200, 200, 220)
    PIXEL_DO_CORACAO = 3

    def __init__(self, tipografia: Tipografia, tamanho_tela: tuple[int, int]) -> None:
        self._tipografia = tipografia
        self._largura, self._altura = tamanho_tela
        self._coracoes = {cheio: self._criar_coracao(cheio) for cheio in (True, False)}

    def desenhar(self, tela: pygame.Surface, partida: Partida) -> None:
        escrever = self._tipografia.escrever
        fase = partida.fase
        pygame.draw.rect(tela, self.COR_FUNDO, (0, 0, self._largura, self.ALTURA))
        escrever(tela, f"FASE {partida.nivel}", Fonte.MEDIA, DOURADO, canto=(14, 10))
        escrever(tela, f"PONTOS {partida.pontos}", Fonte.MEDIA, BRANCO_SUAVE, canto=(150, 10))
        for i in range(partida.vida.maximo):
            coracao = self._coracoes[i < partida.vida.coracoes]
            tela.blit(coracao, (340 + i * (coracao.get_width() + 6), 12))

        barra = pygame.Rect(self._largura - 420, 12, 300, 20)
        if fase.tempo_ilimitado:  # modo apresentacao
            pygame.draw.rect(tela, (90, 160, 220), barra, border_radius=6)
            pygame.draw.rect(tela, self.COR_MOLDURA, barra, 2, border_radius=6)
            escrever(tela, "LIVRE", Fonte.MEDIA, (120, 200, 255), canto=(barra.right + 12, 10))
        else:
            fracao, restante = fase.fracao_de_tempo, fase.tempo_restante
            cor = self._cor_do_relogio(fracao, restante)
            pygame.draw.rect(tela, self.COR_TRILHO, barra, border_radius=6)
            pygame.draw.rect(tela, cor, (barra.x, barra.y, int(barra.w * fracao), barra.h), border_radius=6)
            pygame.draw.rect(tela, self.COR_MOLDURA, barra, 2, border_radius=6)
            escrever(tela, f"{max(0, int(restante + 0.99))}s", Fonte.MEDIA, cor, canto=(barra.right + 12, 10))
        escrever(tela, f"seed {fase.semente}", Fonte.PEQUENA, CINZA_AZULADO,
                 canto=(self._largura - 110, self._altura - 26))
        if not fase.tempo_ilimitado:
            escrever(tela, f"MAPA: {nome_do_mapa(fase.tema)} {fase.etapa_no_mapa}/{fase.fases_por_mapa}",
                     Fonte.PEQUENA, CINZA_AZULADO, canto=(12, self._altura - 26))
        self._desenhar_efeitos(tela, fase.ambiente)
        self._desenhar_fenomeno(tela, fase.ambiente)

    @classmethod
    def _criar_coracao(cls, cheio: bool) -> pygame.Surface:
        p = cls.PIXEL_DO_CORACAO
        s = pygame.Surface((7 * p, 6 * p), pygame.SRCALPHA)
        for y, linha in enumerate(_CORACAO):
            for x, pixel in enumerate(linha):
                if pixel == "#":
                    s.fill((230, 50, 60) if cheio else (60, 50, 80), (x * p, y * p, p, p))
        if cheio:
            s.fill((255, 170, 170), (1 * p, 1 * p, p, p))  # brilhinho
        return s

    # ------------------------------------------------------------------
    # Buffs e debuffs (fileira de "etiquetas" abaixo da barra)
    # ------------------------------------------------------------------
    def _desenhar_efeitos(self, tela: pygame.Surface, ambiente: Ambiente) -> None:
        x, y = 10, self.ALTURA + 6
        for condicao, restante in ambiente.condicoes_ativas():
            segundos = f"{int(restante + 0.99)}s"
            if condicao in ICONE_DA_CONDICAO:
                x = self._etiqueta(tela, x, y, segundos, (150, 230, 150), ICONE_DA_CONDICAO[condicao])
            elif condicao in ROTULO_DA_CONDICAO:
                rotulo, cor = ROTULO_DA_CONDICAO[condicao]
                x = self._etiqueta(tela, x, y, f"{rotulo} {segundos}", cor)
        if ambiente.desafio_da_teia is not None:
            if ambiente.envenenado:
                texto = f"ENVENENADO! Setas em ordem em {ambiente.veneno_restante:.0f}s"
                x = self._etiqueta(tela, x, y, texto, (140, 240, 90))
            else:
                x = self._etiqueta(tela, x, y, "PRESO NA TEIA! Aperte as setas em ordem", (225, 225, 235))
        if ambiente.cargas_de_parede:
            if ambiente.condicao_ativa(Condicao.BROCA):
                texto = f"BROCA: ande contra uma parede para QUEBRAR ({ambiente.cargas_de_parede})"
            else:
                texto = f"TAPETE: ande contra uma parede para voar por cima ({ambiente.cargas_de_parede})"
            x = self._etiqueta(tela, x, y, texto, (230, 190, 90))
        if ambiente.deslizando:
            x = self._etiqueta(tela, x, y, "DESLIZANDO NO GELO!", (170, 225, 255))
        if ambiente.na_areia:
            x = self._etiqueta(tela, x, y, "AREIA MOVEDICA: lento", (230, 190, 120))

    def _etiqueta(self, tela: pygame.Surface, x: int, y: int, texto: str, cor: Cor,
                  item: TipoDeItem | None = None) -> int:
        """Desenha [icone texto] e devolve o x onde a proxima etiqueta comeca."""
        largura_texto, _ = self._tipografia.medir(texto, Fonte.PEQUENA)
        espaco_icone = 26 if item else 0
        caixa = pygame.Rect(x, y, 12 + espaco_icone + largura_texto, 28)
        pygame.draw.rect(tela, self.COR_FUNDO, caixa, border_radius=8)
        pygame.draw.rect(tela, cor, caixa, 2, border_radius=8)
        if item:
            tela.blit(icone(item, 22), (x + 5, y + 3))
        self._tipografia.escrever(tela, texto, Fonte.PEQUENA, cor, canto=(x + 6 + espaco_icone, y + 6))
        return caixa.right + 6

    def _desenhar_fenomeno(self, tela: pygame.Surface, ambiente: Ambiente) -> None:
        ciclo, fenomeno = ambiente.ciclo, ambiente.fenomeno
        if ciclo is None or fenomeno is None:
            return
        aviso, ativo = TEXTOS_DOS_FENOMENOS[fenomeno]
        centro = (self._largura // 2, self.ALTURA + 62)
        if ciclo.ativo:
            if ambiente.fenomeno_neutralizado:
                texto, cor = f"{ativo.split('!')[0]}! (voce esta protegido)", (150, 230, 150)
            else:
                texto, cor = ativo + self._sufixo(ambiente), (255, 120, 90)
            self._tipografia.escrever(tela, texto, Fonte.MEDIA, cor, centro=centro)
        elif ciclo.em_aviso and int(ciclo.progresso_do_aviso * 6) % 2 == 0:  # pisca
            self._tipografia.escrever(tela, aviso, Fonte.MEDIA, (240, 200, 120), centro=centro)

    @staticmethod
    def _sufixo(ambiente: Ambiente) -> str:
        if ambiente.fenomeno is not Fenomeno.RAJADA:
            return ""
        d = ambiente.direcao_da_rajada
        lados = {(1, 0): "direita", (-1, 0): "esquerda", (0, 1): "baixo", (0, -1): "cima"}
        return f" Empurrando para {lados.get((round(d.x), round(d.y)), 'longe')}"

    @staticmethod
    def _cor_do_relogio(fracao: float, restante: float) -> Cor:
        if fracao < 0.25 and int(restante * 4) % 2:  # pisca quando o tempo esta no fim
            return (255, 130, 130)
        if fracao > 0.5:
            return (90, 200, 120)
        return (240, 190, 60) if fracao > 0.25 else (230, 70, 70)


class Painel:
    """Mensagem grande no meio da tela, sobre um veu escuro (pausa, vitoria...)."""

    OPACIDADE_VEU = 150

    def __init__(self, tipografia: Tipografia, tamanho_tela: tuple[int, int]) -> None:
        self._tipografia = tipografia
        self._centro = (tamanho_tela[0] // 2, tamanho_tela[1] // 2)
        self._veu = pygame.Surface(tamanho_tela, pygame.SRCALPHA)
        self._veu.fill((0, 0, 0, self.OPACIDADE_VEU))

    def desenhar(self, tela: pygame.Surface, titulo: str, linha1: str = "", linha2: str = "") -> None:
        tela.blit(self._veu, (0, 0))
        cx, cy = self._centro
        escrever = self._tipografia.escrever
        escrever(tela, titulo, Fonte.GIGANTE, DOURADO, centro=(cx, cy - 50))
        if linha1:
            escrever(tela, linha1, Fonte.MEDIA, (235, 235, 245), centro=(cx, cy + 20))
        if linha2:
            escrever(tela, linha2, Fonte.GRANDE, VERDE_CLARO, centro=(cx, cy + 80))
