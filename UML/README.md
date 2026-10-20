# Marble Run – Diagramas UML (PlantUML)

    diagrams/
    ├── class/classes.puml                  diagrama de classes (dominio / infraestrutura / apresentacao)
    └── sequence/
        ├── 01_iniciar_jogo.puml            main.py / Composition Root
        ├── 02_game_loop.puml               um quadro do loop
        ├── 03_iniciar_partida.puml         Menu -> Jogando (gera o labirinto)
        ├── 04_concluir_fase.puml           movimento, colisão, pontuação, próxima fase
        └── 05_tempo_esgotado.puml          derrota, recorde e reboot
    (PNGs em diagrams/*/png/)

Regerar os PNGs (Java + Graphviz + plantuml.jar):

    ./scripts/render.sh /caminho/plantuml.jar
