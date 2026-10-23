"""
partida.py - Fase, fabrica de fases e a Partida (corrida estilo roguelike).

Fluxo:  fase 1 -> (achou a saida) -> fase 2 (maior, menos tempo, menos luz)
                -> ... o MAPA (tema) so muda a cada 3 fases (1-3, 4-6, 7-9...)
                -> (tempo acabou ou coracoes acabaram) -> fim da partida; ENTER = REBOOT
                   com labirinto totalmente novo, de volta a fase 1.
"""
from __future__ import annotations

import random
from enum import Enum, auto
from typing import Callable, Mapping, Sequence

from .ambiente import Ambiente, Desejo, HistoricoDaRoleta, Ocorrencia, TipoDeItem
from .biomas import Bioma
from .contratos import OuvinteDaPartida
from .geometria import Vetor2
from .geradores import GeradorDeLabirinto
from .jogador import Direcao, Jogador
from .labirinto import Labirinto
from .regras import Cronometro, Dificuldade, Placar, ResultadoDaFase, Vida


class Fase:
    """Um labirinto jogavel: mapa + jogador + cronometro + ambiente (itens/perigos)."""

    def __init__(self, numero: int, semente: int, tema: str, labirinto: Labirinto,
                 jogador: Jogador, cronometro: Cronometro, raio_visao: float,
                 ambiente: Ambiente | None = None, etapa_no_mapa: int = 1, fases_por_mapa: int = 1) -> None:
        self._numero = numero
        self._semente = semente
        self._tema = tema
        self._labirinto = labirinto
        self._jogador = jogador
        self._cronometro = cronometro
        self._raio_visao = raio_visao
        self._ambiente = ambiente if ambiente is not None else Ambiente(labirinto)
        self._etapa_no_mapa = etapa_no_mapa
        self._fases_por_mapa = fases_por_mapa
        self._pendentes: list[Ocorrencia] = []

    @property
    def numero(self) -> int:
        return self._numero

    @property
    def semente(self) -> int:
        return self._semente

    @property
    def tema(self) -> str:
        """Nome do tema visual sorteado (o dominio nao sabe como ele e desenhado)."""
        return self._tema

    @property
    def etapa_no_mapa(self) -> int:
        """Ex.: 2 = segunda fase seguida neste mapa."""
        return self._etapa_no_mapa

    @property
    def fases_por_mapa(self) -> int:
        return self._fases_por_mapa

    @property
    def ultima_no_mapa(self) -> bool:
        """Depois desta, o mapa muda."""
        return self._etapa_no_mapa >= self._fases_por_mapa

    @property
    def labirinto(self) -> Labirinto:
        return self._labirinto

    @property
    def jogador(self) -> Jogador:
        return self._jogador

    @property
    def raio_visao(self) -> float:
        """Alcance BASE da luz, em tiles (lanterna e apagao mudam via ambiente)."""
        return self._raio_visao

    @property
    def ambiente(self) -> Ambiente:
        return self._ambiente

    @property
    def tempo_restante(self) -> float:
        return self._cronometro.restante

    @property
    def fracao_de_tempo(self) -> float:
        return self._cronometro.fracao_restante

    @property
    def tempo_esgotado(self) -> bool:
        return self._cronometro.esgotado

    @property
    def tempo_ilimitado(self) -> bool:
        return self._cronometro.ilimitado

    def avancar(self, dt: float, intencao: Vetor2) -> bool:
        """Move o jogador, aplica buffs/debuffs e desconta o tempo. Devolve True se for hora de alertar."""
        mapa = self._ambiente.mapa_de_colisao(self._jogador)
        self._jogador.mover(intencao, dt, mapa, self._ambiente.locomocao())
        for ocorrencia in self._ambiente.atualizar(dt, self._jogador):
            self._registrar(ocorrencia)
        return self._cronometro.avancar(dt)

    def aplicar_premio(self, tipo: TipoDeItem) -> None:
        """Buff direto, sem caixa (modo teste dos mapas)."""
        self._registrar(self._ambiente.aplicar_premio(tipo))

    def realizar_desejo(self, desejo: Desejo) -> None:
        """Genio da lampada: o jogador escolheu o desejo na tela do genio."""
        self._registrar(self._ambiente.realizar_desejo(desejo, self._jogador))

    def ganhar_tempo(self, segundos: float) -> None:
        self._cronometro.ajustar(segundos)

    def apertar(self, direcao: Direcao) -> None:
        """Seta apertada (so conta enquanto esta preso na teia)."""
        ocorrencia = self._ambiente.apertar(direcao)
        if ocorrencia is not None:
            self._registrar(ocorrencia)

    def abrir_caixa_magica(self) -> None:
        """Como se tivesse encostado numa caixa "?" (modo apresentacao: mostra a roleta)."""
        self._registrar(self._ambiente.abrir_caixa_virtual())

    def recolher_ocorrencias(self) -> tuple[Ocorrencia, ...]:
        """Entrega (e esquece) o que aconteceu desde a ultima vez que alguem perguntou."""
        ocorrencias, self._pendentes = tuple(self._pendentes), []
        return ocorrencias

    def jogador_na_saida(self) -> bool:
        return self._jogador.caixa_de_colisao().intersecta(self._labirinto.area_da_saida())

    def _registrar(self, ocorrencia: Ocorrencia) -> None:
        if ocorrencia.segundos:
            self._cronometro.ajustar(ocorrencia.segundos)
        self._pendentes.append(ocorrencia)


class FabricaDeFases:
    """Factory: monta fases cada vez mais dificeis.

    Composicao: COMO gerar o mapa (GeradorDeLabirinto), QUANTO dificultar
    (Dificuldade) e O QUE cada tema tem de especial (Bioma) sao objetos
    injetados - podem ser trocados sem mexer aqui.

    vitrine=True: modo APRESENTACAO - labirinto pequeno, sem limite de tempo
    e com todos os perigos/caixas do mapa colados na entrada.

    O mapa (tema) so muda a cada `fases_por_mapa` fases: 1-3 no mesmo mapa,
    4-6 em outro (nunca repete o anterior), e assim por diante.
    """

    LIMITE_SEMENTE = 1_000_000
    ALTURA_DOS_PES = Jogador.ALTURA_DOS_PES
    TAMANHO_DA_VITRINE = (8, 6)
    TAMANHO_DA_ARENA = (28, 18)  # tiles de chao
    FASES_POR_MAPA = 3

    def __init__(self, gerador: GeradorDeLabirinto, dificuldade: Dificuldade,
                 temas: Sequence[str], sorteio: random.Random | None = None,
                 biomas: Mapping[str, Bioma] | None = None, vitrine: bool = False,
                 fases_por_mapa: int = FASES_POR_MAPA, gerador_da_arena: GeradorDeLabirinto | None = None,
                 tamanho_da_arena: tuple[int, int] = TAMANHO_DA_ARENA) -> None:
        if not temas:
            raise ValueError("informe ao menos um tema")
        if fases_por_mapa < 1:
            raise ValueError("fases_por_mapa precisa ser pelo menos 1")
        self._gerador = gerador
        self._historico = HistoricoDaRoleta()  # a roleta lembra dos premios de uma fase para outra
        self._gerador_da_arena = gerador_da_arena
        self._tamanho_da_arena = tamanho_da_arena
        self._dificuldade = dificuldade
        self._temas = tuple(temas)
        self._sorteio = sorteio if sorteio is not None else random.SystemRandom()
        self._biomas = dict(biomas or {})
        self._vitrine = vitrine
        self._fases_por_mapa = fases_por_mapa
        self._temas_por_bloco: dict[int, str] = {}  # bloco de fases -> mapa sorteado

    @property
    def dificuldade(self) -> Dificuldade:
        return self._dificuldade

    @property
    def vitrine(self) -> bool:
        return self._vitrine

    @property
    def em_arena(self) -> bool:
        """Teste dos mapas na ARENA editavel (quadrado aberto) em vez de labirinto."""
        return self._vitrine and self._gerador_da_arena is not None

    @property
    def fases_por_mapa(self) -> int:
        return self._fases_por_mapa

    def tema_da_fase(self, numero: int) -> str:
        """O mapa da fase: sorteado no comeco de cada bloco e mantido ate o bloco acabar."""
        bloco = (numero - 1) // self._fases_por_mapa
        if bloco not in self._temas_por_bloco:
            anterior = self._temas_por_bloco.get(bloco - 1)
            opcoes = [tema for tema in self._temas if tema != anterior] or list(self._temas)
            self._temas_por_bloco[bloco] = self._sorteio.choice(opcoes)
        return self._temas_por_bloco[bloco]

    def etapa_no_mapa(self, numero: int) -> int:
        """1, 2 ou 3: quantas fases ja foram (contando esta) no mapa atual."""
        return (numero - 1) % self._fases_por_mapa + 1

    def criar(self, numero: int) -> Fase:
        tema = self.tema_da_fase(numero)
        semente = self._sorteio.randrange(self.LIMITE_SEMENTE)
        rng = random.Random(semente)  # mesma semente => mesmo labirinto e itens
        bioma = self._biomas.get(tema, Bioma.neutro())
        if self.em_arena:  # teste dos mapas: quadrado aberto e editavel, comeca vazio
            labirinto = self._gerador_da_arena.gerar(*self._tamanho_da_arena, rng)
            ambiente = bioma.criar_arena(labirinto, rng, self._dificuldade, historico=self._historico)
        else:
            colunas, linhas = self.TAMANHO_DA_VITRINE if self._vitrine else self._dificuldade.tamanho(numero)
            labirinto = self._gerador.gerar(colunas, linhas, rng)
            ambiente = bioma.criar_ambiente(labirinto, rng, self._dificuldade, vitrine=self._vitrine, fase=numero,
                                            historico=self._historico)

        centro_x, centro_y = labirinto.centro_do_tile(labirinto.entrada)
        jogador = Jogador(centro_x, centro_y + self.ALTURA_DOS_PES)
        if self._vitrine:
            cronometro = Cronometro.sem_limite()
        else:
            distancia = labirinto.distancia_minima * labirinto.tamanho_tile
            tempo = self._dificuldade.tempo_limite(numero, distancia, jogador.velocidade) * bioma.fator_de_tempo
            cronometro = Cronometro(tempo)
        return Fase(numero, semente, tema, labirinto, jogador, cronometro,
                    self._dificuldade.raio_visao(numero) * bioma.fator_de_visao, ambiente,
                    etapa_no_mapa=self.etapa_no_mapa(numero), fases_por_mapa=self._fases_por_mapa)


class SituacaoDaPartida(Enum):
    EM_ANDAMENTO = auto()
    FASE_CONCLUIDA = auto()
    TEMPO_ESGOTADO = auto()
    SEM_VIDA = auto()


class Partida:
    """Uma corrida completa: fase 1, 2, 3... ate o tempo (ou os coracoes) acabar.

    E a raiz do agregado: de fora ninguem mexe no cronometro, no placar, na
    vida ou na posicao do jogador. Tudo passa por `atualizar` e
    `avancar_para_proxima_fase`, que garantem as regras (ex.: nao da para
    pular de fase sem concluir a atual). Os acontecimentos sao avisados aos
    ouvintes (Observer), sem a Partida saber se alguem toca som ou salva recorde.
    """

    def __init__(self, fabrica: FabricaDeFases, placar: Placar | None = None, vida: Vida | None = None) -> None:
        self._fabrica = fabrica
        self._placar = placar if placar is not None else Placar()
        self._vida = vida if vida is not None else Vida(fabrica.dificuldade.coracoes)
        self._ouvintes: list[OuvinteDaPartida] = []
        self._fase = fabrica.criar(1)
        self._situacao = SituacaoDaPartida.EM_ANDAMENTO
        self._ultimo_resultado: ResultadoDaFase | None = None
        self._ocorrencias: tuple[Ocorrencia, ...] = ()

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------
    @property
    def fase(self) -> Fase:
        return self._fase

    @property
    def nivel(self) -> int:
        return self._fase.numero

    @property
    def pontos(self) -> int:
        return self._placar.pontos

    @property
    def dificuldade(self) -> Dificuldade:
        return self._fabrica.dificuldade

    @property
    def vida(self) -> Vida:
        return self._vida

    @property
    def vitrine(self) -> bool:
        """Modo apresentacao: nao tem fim de jogo (coracoes voltam, tempo nao acaba)."""
        return self._fabrica.vitrine

    @property
    def em_arena(self) -> bool:
        """Arena editavel: encostar no portal nao encerra a fase (senao perde o que foi montado)."""
        return self._fabrica.em_arena

    @property
    def situacao(self) -> SituacaoDaPartida:
        return self._situacao

    @property
    def ultimo_resultado(self) -> ResultadoDaFase | None:
        return self._ultimo_resultado

    @property
    def ocorrencias(self) -> tuple[Ocorrencia, ...]:
        """O que aconteceu no ultimo `atualizar` (a tela usa para tremer, roleta...)."""
        return self._ocorrencias

    # ------------------------------------------------------------------
    # Comandos
    # ------------------------------------------------------------------
    def inscrever(self, ouvinte: OuvinteDaPartida) -> None:
        self._ouvintes.append(ouvinte)

    def atualizar(self, dt: float, intencao: Vetor2) -> None:
        self._ocorrencias = ()
        if self._situacao is not SituacaoDaPartida.EM_ANDAMENTO:
            return
        alertar = self._fase.avancar(dt, intencao)
        self._ocorrencias = self._fase.recolher_ocorrencias()
        for ocorrencia in self._ocorrencias:
            self._avisar(lambda ouvinte, o=ocorrencia: ouvinte.ao_ocorrer(o))
            if ocorrencia.dano:
                self._vida.perder(ocorrencia.dano)
            if ocorrencia.cura:
                self._curar(ocorrencia.cura)
        if alertar:
            restante = self._fase.tempo_restante
            self._avisar(lambda ouvinte: ouvinte.ao_alertar_tempo(restante))

        if self._vida.acabou:
            if self.vitrine:
                self._vida.recuperar(self._vida.maximo)
            else:
                self._encerrar_sem_vida()
        elif self._fase.jogador_na_saida() and not self.em_arena:
            self._concluir_fase()
        elif self._fase.tempo_esgotado:
            self._encerrar_por_tempo()

    def avancar_para_proxima_fase(self) -> None:
        if self._situacao is not SituacaoDaPartida.FASE_CONCLUIDA:
            raise RuntimeError("so da para avancar depois de concluir a fase atual")
        self._fase = self._fabrica.criar(self._fase.numero + 1)
        self._vida.recuperar(self._fabrica.dificuldade.cura_por_fase)  # premio por sair do labirinto
        self._situacao = SituacaoDaPartida.EM_ANDAMENTO

    def apertar(self, direcao: Direcao) -> None:
        """Seta apertada (para sair da teia). O aviso sai no proximo `atualizar`."""
        if self._situacao is SituacaoDaPartida.EM_ANDAMENTO:
            self._fase.apertar(direcao)

    # ------------------------------------------------------------------
    def _concluir_fase(self) -> None:
        resultado = self._placar.registrar_conclusao(self._fase.numero, self._fase.tempo_restante)
        self._ultimo_resultado = resultado
        self._situacao = SituacaoDaPartida.FASE_CONCLUIDA
        self._avisar(lambda ouvinte: ouvinte.ao_concluir_fase(resultado))

    def _encerrar_por_tempo(self) -> None:
        self._situacao = SituacaoDaPartida.TEMPO_ESGOTADO
        fase = self._fase.numero
        self._avisar(lambda ouvinte: ouvinte.ao_esgotar_tempo(fase))

    def _curar(self, coracoes: int) -> None:
        """Coracao bonus: recupera vida. Com a vida cheia ele simplesmente some."""
        self._vida.recuperar(coracoes)

    def _encerrar_sem_vida(self) -> None:
        self._situacao = SituacaoDaPartida.SEM_VIDA
        fase = self._fase.numero
        self._avisar(lambda ouvinte: ouvinte.ao_perder_todas_as_vidas(fase))

    def _avisar(self, evento: Callable[[OuvinteDaPartida], None]) -> None:
        for ouvinte in self._ouvintes:
            evento(ouvinte)
