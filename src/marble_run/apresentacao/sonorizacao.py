"""
sonorizacao.py - Quando tocar cada som (o COMO tocar fica no ServicoAudio).

Antes a classe Jogo chamava `self.som.tocar("vitoria")` no meio das regras.
Agora a Partida so avisa o que aconteceu e estes objetos decidem o som.
"""
from __future__ import annotations

from ..dominio.ambiente import Fenomeno, Ocorrencia, TipoDeItem, TipoDeOcorrencia
from ..dominio.contratos import OuvinteDaPartida
from ..dominio.regras import ResultadoDaFase
from .contratos import Efeito, ServicoAudio


class SonsDaPartida(OuvinteDaPartida):
    """Observer: traduz acontecimentos da partida em efeitos sonoros."""

    SONS_DAS_OCORRENCIAS = {
        TipoDeOcorrencia.CONGELOU: Efeito.CONGELAR,
        TipoDeOcorrencia.FICOU_PRESO: Efeito.TEIA,
        TipoDeOcorrencia.QUEIMOU: Efeito.QUEIMAR,
        TipoDeOcorrencia.PULOU: Efeito.MOLA,
        TipoDeOcorrencia.COMECOU_A_DESLIZAR: Efeito.DESLIZAR,
        TipoDeOcorrencia.CAIXA_ABERTA: Efeito.CONFIRMAR,  # a roleta toca o resto
        TipoDeOcorrencia.TECLA_CERTA: Efeito.TIQUE,
        TipoDeOcorrencia.TECLA_ERRADA: Efeito.ERRO,
        TipoDeOcorrencia.SOLTOU_DA_TEIA: Efeito.CONFIRMAR,
        TipoDeOcorrencia.MONSTRO_ATACOU: Efeito.MONSTRO,
        TipoDeOcorrencia.GOLPE_BLOQUEADO: Efeito.CONFIRMAR,
        TipoDeOcorrencia.ENVENENOU: Efeito.SIBILO,
        TipoDeOcorrencia.CUROU_VENENO: Efeito.CONFIRMAR,
        TipoDeOcorrencia.VENENO_FEZ_EFEITO: Efeito.MONSTRO,
        TipoDeOcorrencia.ARREMESSADO: Efeito.RAJADA,
        TipoDeOcorrencia.PUXADO: Efeito.TEIA,
        TipoDeOcorrencia.ROUBOU_BUFF: Efeito.GUINCHO,
        TipoDeOcorrencia.CAIU_NO_BURACO: Efeito.TERREMOTO,
        TipoDeOcorrencia.ATRAVESSOU_TUNEL: Efeito.MAGIA,
        TipoDeOcorrencia.DESEJO_REALIZADO: Efeito.MAGIA,
        TipoDeOcorrencia.COMECOU_A_PERFURAR: Efeito.BROCA,
        TipoDeOcorrencia.QUEBROU_PAREDE: Efeito.TERREMOTO,
    }
    SONS_DOS_ITENS = {
        TipoDeItem.FLAUTA: Efeito.FLAUTA,
        TipoDeItem.RELOGIO: Efeito.RELOGIO,
        TipoDeItem.GENIO: Efeito.MAGIA,
        TipoDeItem.EXTINTOR: Efeito.EXTINTOR,
        TipoDeItem.BROCA: Efeito.BROCA,
    }
    SONS_DOS_FENOMENOS = {
        Fenomeno.TEMPESTADE_DE_AREIA: Efeito.TEMPESTADE,
        Fenomeno.TEMPESTADE_DE_GELO: Efeito.TEMPESTADE,
        Fenomeno.TERREMOTO: Efeito.TERREMOTO,
        Fenomeno.RAJADA: Efeito.RAJADA,
        Fenomeno.APAGAO: Efeito.APAGAO,
        Fenomeno.ERUPCAO: Efeito.ERUPCAO,
    }

    @classmethod
    def som_do_premio(cls, item: TipoDeItem | None) -> Efeito:
        return cls.SONS_DOS_ITENS.get(item, Efeito.PREMIO)

    def __init__(self, audio: ServicoAudio) -> None:
        self._audio = audio

    def ao_alertar_tempo(self, segundos_restantes: float) -> None:
        self._audio.tocar(Efeito.ALERTA)

    def ao_concluir_fase(self, resultado: ResultadoDaFase) -> None:
        self._audio.tocar(Efeito.VITORIA)

    def ao_esgotar_tempo(self, fase_alcancada: int) -> None:
        self._audio.tocar(Efeito.DERROTA)

    def ao_perder_todas_as_vidas(self, fase_alcancada: int) -> None:
        self._audio.tocar(Efeito.DERROTA)

    def ao_ocorrer(self, ocorrencia: Ocorrencia) -> None:
        if ocorrencia.tipo is TipoDeOcorrencia.BUFF_APLICADO:
            self._audio.tocar(self.som_do_premio(ocorrencia.item))
        elif ocorrencia.tipo is TipoDeOcorrencia.ATRAVESSOU_PAREDE:
            self._audio.tocar(Efeito.MAGIA)
        elif ocorrencia.tipo is TipoDeOcorrencia.FENOMENO_COMECOU:
            efeito = self.SONS_DOS_FENOMENOS.get(ocorrencia.fenomeno)
            if efeito is not None:
                self._audio.tocar(efeito)
        elif ocorrencia.tipo in self.SONS_DAS_OCORRENCIAS:
            self._audio.tocar(self.SONS_DAS_OCORRENCIAS[ocorrencia.tipo])


class RitmoDePassos:
    """Toca o som de passo em intervalos regulares enquanto o jogador anda."""

    INTERVALO = 0.26  # segundos entre dois passos

    def __init__(self, audio: ServicoAudio, intervalo: float = INTERVALO) -> None:
        self._audio = audio
        self._intervalo = intervalo
        self._espera = 0.0

    def atualizar(self, dt: float, andando: bool) -> None:
        if not andando:
            self._espera = 0.0
            return
        self._espera -= dt
        if self._espera <= 0:
            self._audio.tocar(Efeito.PASSO)
            self._espera = self._intervalo
