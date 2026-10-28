"""
vitrine.py - TESTE DOS MAPAS (menu secreto DESENVOLVEDOR): a ARENA / modo criativo.

Escolhe um mapa (visual, fenomeno e roleta daquele mapa) e entra num QUADRADO
GIGANTE e aberto, sem tempo e sem game over, onde da para montar o que quiser:

    painel (direita)   abas MAPA / PERIGO / MONSTRO / ITEM e a ferramenta escolhida
    clique esquerdo    coloca (paredes, perigos e borracha: segure e arraste para "pintar")
    clique direito     apaga o que tiver no tile (ou derruba a parede)
    roda do mouse      troca a ferramenta      1..4  troca a aba
    C  liga/desliga o fenomeno   F  forca o fenomeno   9  roleta   R  limpa a arena   N  noite   TAB  painel
"""
from __future__ import annotations

import math

import pygame

from ..dominio.ambiente import Fenomeno, TipoDePerigo
from ..dominio.arena import Categoria, EditorDaArena, Especial, Ferramenta, ferramentas_da
from ..dominio.labirinto import Coordenada, LabirintoEditavel
from ..dominio.partida import Partida
from .cena import Cena
from .estados import ContextoDoJogo, Estado, EstadoJogando
from .icones import DESCRICOES_DOS_ITENS, icone, icone_da_caixa
from .interface import nome_do_mapa
from .menus import CINZA, CREME, DOURADO, FUNDO_PAINEL, HACHURA, LILAS, Botao, Opcao, Seletor, TelaDeMenu
from .pixelart import TAMANHO_CAMADA, CamadaPixel, caixa_rabiscada, semente_fervendo
from .sprites_monstros import SpritesDosMonstros

_MOLA = ("MOLA NA PAREDE", "SO DE IDA: ANDE CONTRA ELA")
EXPLICACOES: dict[str, tuple[tuple[str, str], ...]] = {
    "gelo": (("POCA D'AGUA", "CONGELA 2S"),
             ("PLACA DE GELO", "DESLIZA ATE BATER EM ALGO"),
             ("TEMPESTADE DE GELO", "NEVASCA: -40% VELOCIDADE"),
             ("BONECO DE NEVE", "BEM LENTO. RAIO CONGELANTE EM LINHA"),
             ("YETI", "PERSEGUE. O PISAO CRIA GELO EM VOLTA")),
    "fogo": (("FOGO", "ACENDE E APAGA. -1 CORACAO"),
             ("ERUPCAO", "SAIA DAS RACHADURAS!"),
             ("MAGMAN", "RASTRO DE LAVA. MERGULHA E SAI PERTO"),
             ("FORNALHA", "PARADA NO BECO. LABAREDA EM LINHA")),
    "deserto": (("AREIA MOVEDICA", "-60% DE VELOCIDADE"),
                ("TEMPESTADE", "-45% VELOCIDADE. A MUMIA SOME"),
                ("COBRA", "BOTE. VENENO: SETAS A TEMPO"),
                ("MUMIA", "PERSEGUE. LACO QUE PUXA 2 TILES")),
    "masmorra": (("TEIA DE ARANHA", "PRENDE ATE ACERTAR 4 SETAS"),
                 ("APAGAO", "A LUZ CAI PARA 30%"), _MOLA,
                 ("ARANHA", "COSPE TEIA. FOGE DA LANTERNA"),
                 ("MINOTAURO", "INVESTE EM LINHA E FICA TONTO")),
    "terra": (("TERREMOTO", "CONTROLES INVERTIDOS"),
              ("TOUPEIRA", "SAI DO CHAO: -5S. BURACO VIRA TUNEL"),
              ("GOLEM", "BLOQUEIA. SOCO EM AREA. CANSADO, DA PARA PASSAR")),
    "vento": (("RAJADA", "O VENTO EMPURRA"),
              ("AGUIA", "SOMBRA = MERGULHO. ROUBA 1 BUFF"),
              ("TORNADO", "JOGA PARA LONGE DO PORTAL")),
}

ABAS: tuple[Categoria, ...] = (Categoria.MAPA, Categoria.PERIGO, Categoria.MONSTRO, Categoria.ITEM)
NOMES_CURTOS_DOS_FENOMENOS: dict[Fenomeno, str] = {
    Fenomeno.TEMPESTADE_DE_AREIA: "TEMPESTADE", Fenomeno.TEMPESTADE_DE_GELO: "NEVASCA",
    Fenomeno.APAGAO: "APAGAO", Fenomeno.TERREMOTO: "TERREMOTO", Fenomeno.RAJADA: "RAJADA",
    Fenomeno.ERUPCAO: "ERUPCAO",
}
TECLAS_DAS_ABAS = {pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2, pygame.K_4: 3}
DESCRICOES_ESPECIAIS: dict[Especial, str] = {
    Especial.PAREDE: "LEVANTA UMA PAREDE. ARRASTE PARA FAZER MUROS",
    Especial.BORRACHA: "APAGA O QUE TIVER NO TILE (OU A PAREDE)",
    Especial.PORTAL: "MUDA O PORTAL DE LUGAR (TORNADO, PIPA E GENIO USAM)",
    Especial.CAIXA: "CAIXA ? COM A ROLETA DESTE MAPA",
}
DESCRICOES_DOS_PERIGOS: dict[TipoDePerigo, str] = {
    TipoDePerigo.AGUA: "CONGELA 2S (A BLUSA PROTEGE)",
    TipoDePerigo.GELO: "DESLIZA ATE BATER EM ALGO",
    TipoDePerigo.FOGO: "ACENDE E APAGA. QUEIMA: -1 CORACAO",
    TipoDePerigo.TEIA: "PRENDE ATE ACERTAR 4 SETAS",
    TipoDePerigo.AREIA_MOVEDICA: "-60% DE VELOCIDADE",
    TipoDePerigo.LAVA: "SEMPRE QUEIMA (BOTA E EXTINTOR)",
    TipoDePerigo.BURACO: "COLOQUE 2+: ENTRA NUM, SAI NO OUTRO",
}
DESCRICOES_DOS_MONSTROS: dict[str, str] = {
    "aranha": "COSPE TEIA. FOGE DA LANTERNA",
    "minotauro": "INVESTE EM LINHA RETA E FICA TONTO",
    "boneco_de_neve": "LENTO. RAIO CONGELANTE EM LINHA",
    "yeti": "CACA DE PERTO. PISAO CRIA GELO",
    "magman": "RASTRO DE LAVA. MERGULHA E SAI PERTO",
    "fornalha": "PARADA. LABAREDA EM LINHA",
    "aguia": "MERGULHA NA SOMBRA E ROUBA 1 BUFF",
    "tornado": "JOGA PARA LONGE DO PORTAL",
    "toupeira": "SAI DO CHAO: -5S. DEIXA BURACOS",
    "golem": "GUARDIAO SOLIDO. SOCO EM AREA",
    "cobra": "ESPREITA E DA O BOTE. VENENO",
    "mumia": "CACA DE PERTO. LACO QUE PUXA",
}


def quebrar_linhas(texto: str, largura: int) -> list[str]:
    """Quebra o texto em linhas de no maximo `largura` letras (sem cortar palavras)."""
    linhas, atual = [], ""
    for palavra in texto.split():
        if atual and len(atual) + 1 + len(palavra) > largura:
            linhas.append(atual)
            atual = palavra
        else:
            atual = f"{atual} {palavra}".strip()
    if atual:
        linhas.append(atual)
    return linhas


class EstadoEscolhaDaApresentacao(TelaDeMenu):
    TITULO = "TESTE DOS MAPAS"
    LARGURA_PAINEL = 320

    def __init__(self, jogo: ContextoDoJogo, retorno: Estado) -> None:
        self._retorno = retorno
        self._temas = jogo.servicos.cenas.nomes_dos_temas
        self._tema = 0
        super().__init__(jogo)

    @property
    def _nome_do_tema(self) -> str:
        return self._temas[self._tema]

    def _criar_opcoes(self) -> list[Opcao]:
        def mudar(passos: int) -> None:
            self._tema = (self._tema + passos) % len(self._temas)

        return [
            Seletor("MAPA", lambda: nome_do_mapa(self._nome_do_tema), mudar,
                    "ESQUERDA/DIREITA PARA TROCAR O MAPA"),
            Botao("COMECAR", self._comecar, "ARENA LIVRE: CONSTRUA E TESTE TUDO"),
            Botao("VOLTAR", self._voltar),
        ]

    def _comecar(self) -> None:
        self._jogo.mudar_estado(EstadoApresentacao.nova(self._jogo, self._nome_do_tema))

    def _voltar(self) -> None:
        self._jogo.mudar_estado(self._retorno)

    def _subtitulo(self) -> str:
        return "ESCOLHA O VISUAL, O FENOMENO E A ROLETA DA ARENA"

    def _desenhar_extras(self, c: pygame.Surface) -> None:
        quadro = pygame.Rect(60, 190, TAMANHO_CAMADA[0] - 120, 104)
        caixa_rabiscada(c, quadro, LILAS, FUNDO_PAINEL, semente_fervendo(7, self._tempo), hachura=HACHURA)
        y = quadro.top + 8
        for nome, descricao in EXPLICACOES.get(self._nome_do_tema, ()):
            self._fonte.escrever(c, nome, 1, DOURADO, canto=(quadro.left + 10, y))
            for linha in quebrar_linhas(descricao, 36):
                self._fonte.escrever(c, linha, 1, CREME, canto=(quadro.left + 112, y))
                y += 10
            y += 3




def _icone_do_perigo(tipo: TipoDePerigo, tamanho: int) -> pygame.Surface:
    s = pygame.Surface((16, 16), pygame.SRCALPHA)
    if tipo is TipoDePerigo.AGUA:
        pygame.draw.ellipse(s, (60, 130, 210), (1, 4, 14, 9))
        pygame.draw.ellipse(s, (170, 225, 255), (1, 4, 14, 9), 1)
    elif tipo is TipoDePerigo.GELO:
        s.fill((170, 225, 255), (1, 1, 14, 14))
        pygame.draw.line(s, (255, 255, 255), (3, 11), (8, 4), 2)
    elif tipo is TipoDePerigo.FOGO:
        pygame.draw.polygon(s, (220, 60, 20), [(2, 15), (4, 7), (8, 1), (12, 7), (14, 15)])
        pygame.draw.polygon(s, (255, 200, 80), [(5, 15), (8, 7), (11, 15)])
    elif tipo is TipoDePerigo.TEIA:
        for x0, y0, x1, y1 in ((1, 1, 15, 15), (15, 1, 1, 15), (1, 8, 15, 8), (8, 1, 8, 15)):
            pygame.draw.line(s, (230, 230, 240), (x0, y0), (x1, y1), 1)
        pygame.draw.circle(s, (230, 230, 240), (8, 8), 5, 1)
    elif tipo is TipoDePerigo.AREIA_MOVEDICA:
        pygame.draw.ellipse(s, (205, 170, 105), (0, 3, 16, 11))
        pygame.draw.ellipse(s, (140, 105, 55), (4, 6, 8, 5), 1)
    elif tipo is TipoDePerigo.LAVA:
        pygame.draw.ellipse(s, (110, 25, 5), (0, 3, 16, 11))
        pygame.draw.ellipse(s, (255, 130, 30), (2, 5, 12, 7))
    else:  # buraco
        pygame.draw.ellipse(s, (110, 80, 50), (0, 3, 16, 11))
        pygame.draw.ellipse(s, (15, 10, 8), (3, 5, 10, 7))
    return pygame.transform.scale(s, (tamanho, tamanho))


def _icone_especial(especial: Especial, tamanho: int) -> pygame.Surface:
    if especial is Especial.CAIXA:
        return icone_da_caixa(tamanho)
    s = pygame.Surface((16, 16), pygame.SRCALPHA)
    if especial is Especial.PAREDE:
        s.fill((110, 70, 50), (0, 0, 16, 16))
        for y in (0, 5, 10):
            pygame.draw.line(s, (60, 36, 26), (0, y + 4), (15, y + 4), 1)
            desloc = 4 if y == 5 else 0
            for x in (desloc, desloc + 8):
                pygame.draw.line(s, (60, 36, 26), (x, y), (x, y + 4), 1)
    elif especial is Especial.BORRACHA:
        pygame.draw.polygon(s, (240, 120, 150), [(1, 10), (8, 3), (15, 9), (8, 15)])
        pygame.draw.polygon(s, (90, 110, 200), [(1, 10), (4, 7), (11, 13), (8, 15)])
        pygame.draw.polygon(s, (40, 20, 30), [(1, 10), (8, 3), (15, 9), (8, 15)], 1)
    else:  # portal
        pygame.draw.circle(s, (150, 90, 255), (8, 8), 7, 2)
        pygame.draw.circle(s, (90, 220, 255), (8, 8), 4)
        pygame.draw.circle(s, (255, 255, 255), (8, 8), 2)
    return pygame.transform.scale(s, (tamanho, tamanho))


class EstadoApresentacao(EstadoJogando):
    """Arena do teste dos mapas: o jogo normal + um EDITOR (paleta, mouse e atalhos)."""

    LARGURA_DO_PAINEL = 178
    FOCO_COM_PAINEL = 0.31   # jogador no meio da area livre, a esquerda do painel
    ICONE = 16
    CELULA = 20
    POR_LINHA = 8
    LUZ_DA_NOITE = 0.4  # a noite da arena e bem escura: so os olhos dos monstros brilhando

    def __init__(self, jogo: ContextoDoJogo, partida: Partida, cena: Cena) -> None:
        super().__init__(jogo, partida, cena)
        self._camada = CamadaPixel()
        self._sprites = SpritesDosMonstros()
        self._mostrar_painel = True
        self._noite = False
        self._tempo = 0.0
        self._aba = 0
        self._indice = {categoria: 0 for categoria in ABAS}
        self._mouse: tuple[int, int] | None = None
        self._botao: int | None = None     # 1 = colocando, 3 = apagando
        self._ultimo_tile: Coordenada | None = None
        self._icones: dict[tuple, pygame.Surface] = {}
        fase = partida.fase
        self._editor = (EditorDaArena(fase.labirinto, fase.ambiente, fase.jogador)
                        if isinstance(fase.labirinto, LabirintoEditavel) else None)
        self._focar_camera()
        self._cena.enquadrar(instantaneo=True)

    @classmethod
    def nova(cls, jogo: ContextoDoJogo, tema: str) -> EstadoApresentacao:
        partida = jogo.nova_apresentacao(tema)
        return cls(jogo, partida, jogo.servicos.cenas.criar(partida.fase))

    def reiniciar(self) -> EstadoJogando:
        return EstadoApresentacao.nova(self._jogo, self._partida.fase.tema)

    @property
    def ferramenta(self) -> Ferramenta:
        categoria = ABAS[self._aba]
        opcoes = ferramentas_da(categoria)
        return opcoes[self._indice[categoria] % len(opcoes)]

    # ------------------------------------------------------------------
    # Entrada
    # ------------------------------------------------------------------
    def tratar_evento(self, evento: pygame.event.Event) -> None:
        if evento.type == pygame.KEYDOWN:
            self._tecla(evento.key)
        elif evento.type == pygame.MOUSEMOTION:
            self._mouse = evento.pos
            if self._botao is not None:
                self._usar_no_mouse(arrastando=True)
        elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button in (1, 3):
            self._mouse = evento.pos
            if evento.button == 1 and self._clicou_no_painel(evento.pos):
                return
            self._botao = evento.button
            self._ultimo_tile = None
            self._usar_no_mouse(arrastando=False)
        elif evento.type == pygame.MOUSEBUTTONUP:
            self._botao = None
        elif evento.type == pygame.MOUSEWHEEL and evento.y:
            self._trocar_ferramenta(-1 if evento.y > 0 else 1)

    def _tecla(self, tecla: int) -> None:
        fase = self._partida.fase
        if tecla in TECLAS_DAS_ABAS:
            self._aba = TECLAS_DAS_ABAS[tecla]
        elif tecla == pygame.K_9:
            fase.abrir_caixa_magica()
        elif tecla == pygame.K_f:
            fase.ambiente.forcar_fenomeno()
        elif tecla == pygame.K_c:
            self._alternar_fenomeno()
        elif tecla == pygame.K_r and self._editor is not None:
            self._editor.limpar_tudo()
        elif tecla == pygame.K_n:
            self._noite = not self._noite
            self._cena.ajustar_luz(self.LUZ_DA_NOITE if self._noite else 1.0)
        elif tecla == pygame.K_TAB:
            self._mostrar_painel = not self._mostrar_painel
            self._focar_camera()

    def _trocar_ferramenta(self, passos: int) -> None:
        categoria = ABAS[self._aba]
        self._indice[categoria] = (self._indice[categoria] + passos) % len(ferramentas_da(categoria))

    def _alternar_fenomeno(self) -> None:
        ambiente = self._partida.fase.ambiente
        ambiente.ligar_fenomeno(not ambiente.fenomeno_ligado)

    def _retangulo_do_fenomeno(self) -> pygame.Rect:
        quadro = self._quadro()
        return pygame.Rect(quadro.left + 7, quadro.bottom - 96, quadro.width - 14, 14)

    def _usar_no_mouse(self, arrastando: bool) -> None:
        if self._editor is None or self._mouse is None or self._no_painel(self._mouse):
            return
        tile = self._cena.tile_na_tela(self._mouse)
        if tile is None or tile == self._ultimo_tile:
            return
        if self._botao == 3:
            self._editor.apagar(tile)
        elif not arrastando or self.ferramenta.pinta_arrastando:
            self._editor.aplicar(self.ferramenta, tile)
        else:
            return
        self._ultimo_tile = tile

    # ------------------------------------------------------------------
    # Painel
    # ------------------------------------------------------------------
    def _quadro(self) -> pygame.Rect:
        return pygame.Rect(TAMANHO_CAMADA[0] - self.LARGURA_DO_PAINEL - 4, 48, self.LARGURA_DO_PAINEL, 268)

    def _no_painel(self, pos: tuple[int, int]) -> bool:
        return self._mostrar_painel and self._quadro().collidepoint(CamadaPixel.da_tela(pos))

    def _retangulos_das_abas(self) -> list[pygame.Rect]:
        quadro = self._quadro()
        x, y = quadro.left + 7, quadro.top + 22
        retangulos = []
        for categoria in ABAS:
            largura = len(categoria.value) * 6 + 6
            retangulos.append(pygame.Rect(x, y, largura, 13))
            x += largura + 3
        return retangulos

    def _retangulo_da_ferramenta(self, indice: int) -> pygame.Rect:
        quadro = self._quadro()
        coluna, linha = indice % self.POR_LINHA, indice // self.POR_LINHA
        return pygame.Rect(quadro.left + 9 + coluna * self.CELULA, quadro.top + 42 + linha * self.CELULA,
                           self.CELULA - 2, self.CELULA - 2)

    def _clicou_no_painel(self, pos: tuple[int, int]) -> bool:
        if not self._no_painel(pos):
            return False
        ponto = CamadaPixel.da_tela(pos)
        if self._partida.fase.ambiente.fenomeno is not None and self._retangulo_do_fenomeno().collidepoint(ponto):
            self._alternar_fenomeno()
            return True
        for i, retangulo in enumerate(self._retangulos_das_abas()):
            if retangulo.collidepoint(ponto):
                self._aba = i
                return True
        categoria = ABAS[self._aba]
        for i in range(len(ferramentas_da(categoria))):
            if self._retangulo_da_ferramenta(i).collidepoint(ponto):
                self._indice[categoria] = i
                return True
        return True  # clicou no painel, mas fora dos botoes: nao edita o mapa por baixo

    def _icone(self, ferramenta: Ferramenta, tamanho: int) -> pygame.Surface:
        chave = (ferramenta, tamanho)
        if chave not in self._icones:
            if ferramenta.monstro is not None:
                img = self._sprites.icone(ferramenta.monstro, tamanho)
            elif ferramenta.item is not None:
                img = icone(ferramenta.item, tamanho)
            elif ferramenta.perigo is not None:
                img = _icone_do_perigo(ferramenta.perigo, tamanho)
            else:
                img = _icone_especial(ferramenta.especial, tamanho)
            self._icones[chave] = img
        return self._icones[chave]

    @staticmethod
    def _descricao(ferramenta: Ferramenta) -> str:
        if ferramenta.item is not None:
            return DESCRICOES_DOS_ITENS[ferramenta.item][1]
        if ferramenta.perigo is not None:
            return DESCRICOES_DOS_PERIGOS[ferramenta.perigo]
        if ferramenta.monstro is not None:
            return DESCRICOES_DOS_MONSTROS[ferramenta.monstro.value]
        return DESCRICOES_ESPECIAIS[ferramenta.especial]

    # ------------------------------------------------------------------
    # Ciclo
    # ------------------------------------------------------------------
    def _focar_camera(self) -> None:
        if self._mostrar_painel:
            self._cena.focar(self.FOCO_COM_PAINEL, prender_nas_bordas=False)
        else:
            self._cena.focar(0.5)

    def atualizar(self, dt: float) -> None:
        self._tempo += dt
        super().atualizar(dt)

    def desenhar(self, tela: pygame.Surface) -> None:
        self._cena.desenhar(tela, com_escuridao=self._noite and self._servicos.preferencias.escuridao)
        self._servicos.hud.desenhar(tela, self._partida)
        self._desenhar_cursor(tela)
        self._camada.limpar()
        c = self._camada.superficie
        fonte = self._servicos.fonte_pixel
        if self._mostrar_painel:
            self._desenhar_painel(c)
        else:
            fonte.escrever(c, "TAB: MOSTRAR PAINEL", 1, CINZA, canto=(6, TAMANHO_CAMADA[1] - 12))
        self._camada.apresentar(tela)

    def _desenhar_cursor(self, tela: pygame.Surface) -> None:
        """Previa no tile embaixo do mouse: o icone da ferramenta (ou um X vermelho apagando)."""
        if self._editor is None or self._mouse is None or self._no_painel(self._mouse):
            return
        tile = self._cena.tile_na_tela(self._mouse)
        if tile is None:
            return
        ret = self._cena.retangulo_do_tile(tile)
        if not self._editor.pode_editar(tile):
            pygame.draw.rect(tela, (120, 120, 130), ret, 1)
            return
        apagando = self._botao == 3
        cor = (255, 80, 70) if apagando else (255, 240, 150)
        veu = pygame.Surface(ret.size, pygame.SRCALPHA)
        veu.fill((*cor, 45))
        tela.blit(veu, ret)
        pygame.draw.rect(tela, cor, ret, 2)
        if apagando:
            pygame.draw.line(tela, cor, ret.topleft, ret.bottomright, 3)
            pygame.draw.line(tela, cor, ret.topright, ret.bottomleft, 3)
            return
        img = self._icone(self.ferramenta, max(16, int(ret.w * 0.7))).copy()
        img.set_alpha(190 + int(50 * abs(math.sin(self._tempo * 7))))
        tela.blit(img, img.get_rect(center=ret.center))

    def _desenhar_painel(self, c: pygame.Surface) -> None:
        fonte = self._servicos.fonte_pixel
        quadro = self._quadro()
        caixa_rabiscada(c, quadro, LILAS, (24, 18, 40, 248), semente_fervendo(3, self._tempo), hachura=HACHURA)
        x, y = quadro.left + 8, quadro.top + 8
        fonte.escrever(c, f"ARENA: {nome_do_mapa(self._partida.fase.tema)}", 1, DOURADO, canto=(x, y))
        for i, (categoria, ret) in enumerate(zip(ABAS, self._retangulos_das_abas())):
            ativa = i == self._aba
            pygame.draw.rect(c, (80, 50, 120) if ativa else (36, 26, 56), ret, border_radius=3)
            pygame.draw.rect(c, DOURADO if ativa else LILAS, ret, 1, border_radius=3)
            fonte.escrever(c, categoria.value, 1, DOURADO if ativa else CREME, canto=(ret.x + 3, ret.y + 3))

        categoria = ABAS[self._aba]
        ferramentas = ferramentas_da(categoria)
        escolhida = self._indice[categoria] % len(ferramentas)
        for i, ferramenta in enumerate(ferramentas):
            ret = self._retangulo_da_ferramenta(i)
            ativa = i == escolhida
            pygame.draw.rect(c, (90, 60, 130) if ativa else (30, 22, 46), ret, border_radius=3)
            if ativa:
                pygame.draw.rect(c, DOURADO, ret.inflate(2, 2), 1, border_radius=3)
            img = self._icone(ferramenta, self.ICONE)
            c.blit(img, img.get_rect(center=ret.center))

        linhas = (len(ferramentas) + self.POR_LINHA - 1) // self.POR_LINHA
        y = quadro.top + 46 + linhas * self.CELULA
        ferramenta = ferramentas[escolhida]
        fonte.escrever(c, ferramenta.nome, 1, (255, 170, 120), canto=(x, y))
        y += 10
        for linha in quebrar_linhas(self._descricao(ferramenta), 27):
            fonte.escrever(c, linha, 1, CREME, canto=(x + 2, y))
            y += 9

        ambiente = self._partida.fase.ambiente
        if ambiente.fenomeno is not None:  # botao: liga/desliga o fenomeno do mapa
            ret = self._retangulo_do_fenomeno()
            ligado = ambiente.fenomeno_ligado
            pygame.draw.rect(c, (40, 90, 50) if ligado else (90, 36, 40), ret, border_radius=3)
            pygame.draw.rect(c, (150, 240, 150) if ligado else (255, 120, 110), ret, 1, border_radius=3)
            nome = NOMES_CURTOS_DOS_FENOMENOS.get(ambiente.fenomeno, "FENOMENO")
            fonte.escrever(c, f"C {nome}: {'LIGADO' if ligado else 'DESLIGADO'}", 1, CREME,
                           canto=(ret.x + 4, ret.y + 4))

        y = quadro.bottom - 76
        ajuda = (("ESQ", "COLOCAR / ARRASTAR"), ("DIR", "APAGAR"), ("RODA", "FERRAMENTA  1-4: ABA"),
                 ("R", "LIMPAR A ARENA"), ("F", "FENOMENO JA  9: ROLETA"),
                 ("N", f"NOITE: {'SIM' if self._noite else 'NAO'}"), ("TAB", "ESCONDER O PAINEL"))
        for tecla, texto in ajuda:
            fonte.escrever(c, tecla, 1, LILAS, canto=(x, y))
            fonte.escrever(c, texto, 1, CREME, canto=(x + 28, y))
            y += 10
