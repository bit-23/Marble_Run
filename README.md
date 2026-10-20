# Marble_Run 
 Criação de jogo, projeto de faculdade Unimax 
<img width="1354" height="745" alt="image" src="https://github.com/user-attachments/assets/508837eb-a416-4a96-8013-39ac331058d9" />

## Como jogar

```powershell
cd "Marble_Run-main\src"
python main.py
```

Menu principal: **JOGAR** (nome + dificuldade), **RANKING**, **CONFIGURAÇÕES** (zoom, tela cheia, tremor de tela, FPS e
lista de controles), **SOM** (volume da música, dos efeitos e mudo) e **SAIR**. Durante a partida, **ESC** abre o
menu de pausa: continuar, reiniciar, configurações, som, menu principal ou sair. Os menus aceitam teclado, controle e mouse.

As configurações ficam salvas em `~/.marble_run/config.json`.

| Dificuldade | Tempo | Luz | Perigos e fenômenos |
|-------------|-------|-----|---------------------|
| Fácil | +40% | mais luz | menos perigos, fenômenos mais espaçados |
| Normal | padrão | padrão | padrão |
| Difícil | -25% | menos luz | mais perigos, fenômenos mais frequentes |
| Insano | metade (com uma folga mínima de 15% sobre o caminho perfeito) | sem luz extra e sem lanterna | muitos perigos |

## Controles

| Ação | Teclado | Controle |
|------|---------|----------|
| Mover / navegar nos menus | WASD / setas | Analógico esquerdo / direcional |
| Pular na mola | ande contra a mola presa na parede | idem |
| Sair da teia | setas / WASD na ordem mostrada | direcional |
| Olhar em volta (câmera) | T F G H / numérico 8 4 5 6 | Analógico direito |
| Zoom | + / - | RB / LB |
| Pausar (menu de pausa) | ESC / P | Start |
| Luz / Som | L / M | X / Y |

## Regras gerais

- **Curva de dificuldade:** as fases 1 a 3 são tranquilas, com muito tempo, labirinto pequeno, bastante luz, poucos perigos e
  nenhum fenômeno. A partir da fase 4 tudo piora aos poucos (o labirinto cresce mais rápido que o tempo, a luz diminui, os
  perigos aumentam e os fenômenos ficam mais frequentes) até chegar no máximo na fase 12. Os números ficam em
  `Dificuldade`, em `src/marble_run/dominio/regras.py`, e as dificuldades (Fácil/Normal/Difícil/Insano) multiplicam essa curva.
- **Mapas em blocos de 3 fases:** você joga 3 fases seguidas no mesmo mapa (1–3, 4–6, 7–9...). Depois o mapa troca, e nunca
  para o mesmo do bloco anterior. O HUD mostra o progresso (ex.: `MAPA: GELO 2/3`).
- **Vida:** 3 corações. O fogo tira 1 coração. Sem corações (ou sem tempo), a partida acaba. Sair de um labirinto devolve 1 coração.
- **Molas nas paredes (todos os mapas):** ficam em pares, dos dois lados de uma parede fina. Ande contra uma delas para pular a parede em arco.
- **Caixas "?" (todos os mapas):** ao encostar, o jogo pausa e uma roleta gira até parar em um buff.

## Buffs e debuffs por mapa

| Mapa | Debuffs | Buffs extras na roleta |
|------|---------|------------------------|
| Gelo | Poças d'água congelam por 2s; placas de gelo fazem deslizar girando até bater em algo (estilo Pokémon FireRed) | Blusa (não congela nem desliza, 10s), Banana (+50% velocidade, 5s) |
| Deserto | Areia movediça (-60% velocidade); tempestade de areia periódica (-45% velocidade). Sol forte: enxerga 25% mais longe | Flauta (acalma a tempestade, 8s) |
| Fogo | Fogo estilo Zelda (acende/apaga; queimou = -1 coração e corre descontrolado por 1,5s); erupção periódica: o chão racha perto do jogador e vira jato de lava (saia de cima!) | Flauta (apaga o fogo e a lava, 8s) |
| Masmorra | Teias de aranha (raras; prendem até você acertar uma sequência de 4 setas em ordem — errou, recomeça); apagão periódico (luz cai para 30%) | — |
| Terra | Terremoto periódico (tela treme e controles invertidos) | — |
| Vento | Rajadas de vento periódicas que empurram o jogador | — |

Buffs da roleta em **todos** os mapas: Relógio (+10s), Lanterna (+60% de visão, 12s),
Estrela (imune a todos os debuffs, 6s), Bússola (seta para a saída, 15s) e Café (+30% de velocidade e imune a lentidão, 8s).

## Ranking

A opção **RANKING** do menu mostra o top 10 de cada dificuldade em abas (**FÁCIL / NORMAL / DIFÍCIL / INSANO**;
esquerda/direita ou clique troca a aba). Cada jogador tem a sua melhor pontuação guardada separadamente em cada dificuldade
(`~/.marble_run/pontuacoes.sqlite3`). Pontuações de versões antigas, que não tinham dificuldade, entram como NORMAL.

## Menu desenvolvedor (secreto)

No menu principal, aperte **CIMA, BAIXO, DIREITA, ESQUERDA**. A opção **DESENVOLVEDOR** surge de uma explosão de
pixels (fica liberada até fechar o jogo) e tem duas ferramentas:

- **EDITAR RANKING**: escolha a aba, selecione um jogador para renomear, mudar pontos/fase ou apagar, ou limpe a aba
  inteira. Ações que não têm volta pedem confirmação.
- **TESTE DOS MAPAS**: escolha o mapa e jogue num labirinto pequeno, **sem limite de tempo e sem game over**, com todos
  os perigos, molas e caixas perto da entrada e um painel explicando cada coisa.

| Tecla (teste dos mapas) | Efeito |
|-------|--------|
| 1 a 8 | Aplica um buff na hora (blusa, banana, flauta, relógio, lanterna, estrela, bússola, café) |
| 9 | Abre a roleta |
| F | Força o fenômeno do mapa (tempestade, erupção, apagão, terremoto, rajada) |
| R | Gera outro labirinto do mesmo mapa |
| TAB | Esconde/mostra o painel |

As regras ficam em `src/marble_run/dominio/ambiente.py` e o que cada mapa sorteia em `src/marble_run/dominio/biomas.py`.
