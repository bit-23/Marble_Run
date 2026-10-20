# Marble Run

Jogo de labirinto procedural desenvolvido em Python e Pygame como projeto acadêmico da Unimax. Cada fase cria um mapa novo: encontre a saída antes que o tempo termine, acumule pontos e tente chegar mais longe na próxima corrida.

**Documentação:** [bit-23.github.io/Marble_Run](https://bit-23.github.io/Marble_Run/)

## Comece a jogar

Requisitos: Python 3.10 ou superior e `pip`.

```bash
python -m venv .venv
```

Ative o ambiente virtual:

```bash
# Linux / macOS
source .venv/bin/activate
```

```powershell
# Windows PowerShell
.venv\Scripts\Activate.ps1
```

Instale as dependências e inicie o jogo:

```bash
python -m pip install -r requirements.txt
python src/main.py
```

O jogo abre uma janela de 960 × 640 pixels. No menu, digite seu nome e pressione **Enter** para começar. Para detalhes de instalação, consulte a [documentação](https://bit-23.github.io/Marble_Run/docs/instalacao).

## Controles rápidos

- **Mover:** setas ou WASD; também aceita controles compatíveis com SDL.
- **Pausar / voltar:** Esc ou P. Na pausa, Q volta ao menu.
- **Som / escuridão:** M / L durante a partida.

Veja a página [Como jogar](https://bit-23.github.io/Marble_Run/docs/como-jogar) para todos os controles.

## Estrutura do código

```text
src/
├── main.py                     # Entrada e composição das dependências
├── marble_run/
│   ├── dominio/                 # Regras, labirinto, jogador e pontuação
│   ├── apresentacao/            # Telas, entrada, HUD, temas e áudio
│   └── infraestrutura/          # Recursos e persistência
└── assets/images/jogador/       # Sprites do personagem
```

O domínio não depende do Pygame. A camada de apresentação cuida da interface, enquanto a infraestrutura implementa persistência em arquivo/SQLite e áudio. Os diagramas PlantUML estão em `UML/diagrams/`.

## Tecnologias

- Python 3.10+
- [pygame-ce](https://pyga.me/)
- SQLite, incluído na biblioteca padrão do Python
