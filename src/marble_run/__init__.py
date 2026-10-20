"""
Marble Run - pacote principal do jogo, organizado em camadas.

    apresentacao ----------> dominio          (as setas mostram quem
         ^                      ^              depende de quem)
         |                      |
         +---- infraestrutura --+

* dominio:        as regras do jogo (labirinto, jogador, tempo, pontos...).
                  NAO importa pygame nem nenhuma outra camada: pode ser
                  lido e testado sozinho.
* apresentacao:   tudo o que o jogador ve, ouve e aperta; maquina de estados
                  das telas (menu, jogando, pausado, vitoria, derrota).
* infraestrutura: detalhes tecnicos (disco, placa de som, caminhos). So
                  IMPLEMENTA contratos definidos no dominio
                  (RepositorioDeRecorde) e na apresentacao (ServicoAudio).

Quem escolhe as classes concretas e liga as pecas e o main.py
(Composition Root). Nenhum outro modulo cria dependencias "na mao".
"""
