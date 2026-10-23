# Marble_Run 
 Criação de jogo, projeto de faculdade Unimax 
<img width="1354" height="745" alt="image" src="https://github.com/user-attachments/assets/508837eb-a416-4a96-8013-39ac331058d9" />

<p align="center">
  <a href="https://fedora.tailc00c53.ts.net/">
    <img src="../my-website/static/img/docusaurus.png" alt="Documentação do Marble Run feita com Docusaurus" width="100" />
  </a>
  <br />
  <a href="https://fedora.tailc00c53.ts.net/"><strong>Acesse a documentação do Marble Run</strong></a>
</p>

## Como jogar

```powershell
cd "Marble_Run-main\src"
python main.py
```

Menu principal: **JOGAR** (nome + dificuldade), **RANKING**, **CONFIGURAÇÕES** (zoom, tela cheia, tremor de tela, FPS e
lista de controles), **SOM** (volume da música, dos efeitos e mudo) e **SAIR**. Durante a partida, **ESC** abre o
menu de pausa: continuar, reiniciar, configurações, som, menu principal ou sair. Os menus aceitam teclado, controle e mouse.

As configurações ficam salvas em `~/.marble_run/config.json`.

| Dificuldade | Tempo | Luz | Perigos e fenômenos | Monstros | Vida |
|-------------|-------|-----|---------------------|----------|------|
| Fácil | +30% | +1 tile de luz | 25% menos perigos, fenômenos mais espaçados | no máximo 1 | 3 corações, +1 ao passar de fase |
| Normal | padrão (já bem mais apertado que antes) | padrão | padrão | 1 a partir da fase 4, 2 a partir da 7 | 3 corações, +1 ao passar de fase |
| Difícil | -20% | -0,8 tile de luz | 35% mais perigos, fenômenos mais frequentes; labirinto começa maior | 1 a partir da fase 3, 2 a partir da 5; mais rápidos e atacam mais | 3 corações, **sem cura** ao passar de fase |
| Insano | -40% (folga mínima de só 8% sobre o caminho perfeito) | luz fixa e mínima, sem lanterna | 60% mais perigos, fenômenos bem frequentes; labirinto começa ainda maior | **3 já na fase 2**; mais rápidos e atacam mais | **2 corações**, sem cura |

## Controles

| Ação | Teclado | Controle |
|------|---------|----------|
| Mover / navegar nos menus | WASD / setas | Analógico esquerdo / direcional |
| Pular na mola (masmorra) | ande contra a mola presa na parede | idem |
| Sair da teia / curar o veneno | setas / WASD na ordem mostrada | direcional |
| Olhar em volta (câmera) | T F G H / numérico 8 4 5 6 | Analógico direito |
| Zoom | + / - | RB / LB |
| Pausar (menu de pausa) | ESC / P | Start |
| Luz / Som | L / M | X / Y |

## Regras gerais

- **Curva de dificuldade:** no Normal as fases 1 a 3 são mais calmas (labirinto pequeno, mais luz, menos perigos e
  nenhum fenômeno), mas já com o tempo contado. A partir da fase 4 tudo piora aos poucos (o labirinto cresce mais rápido
  que o tempo, a luz diminui, os perigos aumentam e os fenômenos ficam mais frequentes) até chegar no máximo na fase 10.
  No Difícil a calmaria dura só 2 fases e no Insano só 1. Os números ficam em `Dificuldade`, em
  `src/marble_run/dominio/regras.py`, e cada dificuldade (Fácil/Normal/Difícil/Insano) muda essa curva.
- **Mapas em blocos de 3 fases:** você joga 3 fases seguidas no mesmo mapa (1–3, 4–6, 7–9...). Depois o mapa troca, e nunca
  para o mesmo do bloco anterior. O HUD mostra o progresso (ex.: `MAPA: GELO 2/3`).
- **Vida:** 3 corações (2 no Insano). Fogo, lava e monstros tiram 1 coração. Sem corações (ou sem tempo), a partida acaba.
  No Fácil e no Normal, sair de um labirinto devolve 1 coração; no Difícil e no Insano, não.
- **Molas nas paredes (só na Masmorra):** ficam de um lado de uma parede fina e são **só de ida** (não tem mola de volta).
  Ande contra ela para pular a parede em arco. Nunca nascem perto do portal.
- **Caixas "?" (todos os mapas):** espalhadas (2 + 1 a cada 150 tiles de chão, longe umas das outras). Ao encostar, o jogo
  pausa e uma roleta gira até parar em um buff. A roleta tem **memória**: o último prêmio fica com só 10% da chance e os
  dois anteriores com 35% (vale de uma fase para outra), então quase não repete.
- **Monstros:** cada mapa tem 2. Nenhum nas fases 1 a 3, 1 nas fases 4 a 6 e 2 da fase 7 em diante (Fácil: no máximo 1;
  Insano: +1). No Difícil e no Insano eles atacam mais vezes. **Cada um patrulha o próprio território** (perto de onde
  nasceu) e evita entrar no seu tile, para não encurralar. Só o Yeti e a Múmia caçam, e mesmo assim só de perto e por
  poucos segundos: depois cansam e desistem. Todo ataque tem **aviso** antes: o monstro incha, treme e fica vermelho,
  os tiles do ataque piscam e a sombra da águia aparece. Depois de levar dano você fica um instante invulnerável, e quem
  está preso (teia, veneno, congelado) não apanha. A Estrela deixa imune a todos.

## Buffs e debuffs por mapa

| Mapa | Debuffs | Buffs exclusivos na roleta |
|------|---------|------------------------|
| Gelo | Poças d'água congelam por 2s; placas de gelo (poucas e espalhadas) fazem deslizar girando até bater em algo (estilo Pokémon FireRed); tempestade de gelo periódica (-40% velocidade) | Blusa (não congela nem desliza, 10s), Café (+30% velocidade e imune a lentidão, 8s) |
| Deserto | Areia movediça (-60% velocidade); tempestade de areia periódica (-45% velocidade). Sol forte: enxerga 25% mais longe | Flauta (acalma a tempestade e os monstros dormem, 8s), Tapete Mágico (flutua 8s e voa por cima de 1 parede), Gênio da Lâmpada (escolha: +20s, setas do melhor caminho por 3,5s ou teleporte para perto do portal) |
| Fogo | Fogo estilo Zelda (acende/apaga; queimou = -1 coração e corre descontrolado por 1,5s); erupção periódica: o chão racha perto do jogador e vira jato de lava (saia de cima!) | Extintor (apaga fogo e lava em volta; o Magman vira pedra e a Fornalha apaga por 5s), Bota de Obsidiana (imune a fogo e lava, 8s) |
| Masmorra | Teias de aranha (raras; prendem até você acertar uma sequência de 4 setas em ordem — errou, recomeça); apagão periódico (luz cai para 30%) | Lanterna (+60% de visão e a aranha foge, 12s — vetada no Insano), Bússola (seta para a saída, 15s) |
| Terra | Terremoto periódico (tela treme e controles invertidos) | Broca (o personagem segura a broca; ande contra uma parede e ela **quebra a parede de verdade**, até 2 paredes, 15s), Capacete de Mineiro (terremoto não inverte, +30% de luz, imune à toupeira e ao golem, 12s) |
| Vento | Rajadas de vento periódicas que empurram o jogador | Guarda-Chuva (imune a rajada, tornado e águia, 10s), Pipa (rajada e tornado levam para o portal, 12s) |

Buffs da roleta em **todos** os mapas: Relógio (+10s), Estrela (imune a debuffs e monstros, 6s) e
Coração Bônus (+1 coração; com a vida cheia ele simplesmente some).

## Monstros

| Mapa | Monstro | O que faz | Como se proteger |
|------|---------|-----------|------------------|
| Masmorra | Aranha | Cospe teia em linha reta (prende; a teia que erra fica 10s no chão) | Lanterna (ela foge) |
| | Minotauro | Te vê num corredor reto, raspa o pé e investe até a parede (-1 coração); depois fica tonto 2s | Sair da linha dele |
| Gelo | Boneco de Neve Sombrio | Anda bem devagar e sopra um raio congelante em linha (congela 2s) | Blusa |
| | Yeti | Caça de perto (por pouco tempo); o pisão cria placas de gelo em volta; encostou, -1 coração | Café, Blusa |
| Fogo | Magman | Deixa rastro de lava (3s); mergulha e sai do chão perto de você (bolhas avisam) | Extintor, Bota |
| | Fornalha | Parada no fim de um beco; solta labareda em linha (no Difícil/Insano, nas 4 direções) | Bota, Extintor |
| Vento | Abutre (Águia) | Circula sobre o território, por cima das paredes; se você passar perto, a sombra marca o mergulho que rouba 1 buff | Guarda-Chuva |
| | Tornado | Vaga pelo território; encostou, te joga para longe do portal e deixa tonto (sem dano) | Guarda-Chuva, Pipa (inverte) |
| Terra | Toupeira | Cava pelo território; se você passar perto, sai do chão embaixo de você: -5s. Os buracos viram túneis (entrar em um leva a outro) | Capacete, Tapete |
| | Golem | Guardião lento e sólido: não persegue, mas se você chegar perto ele para e soca o chão em área (-1 coração e controles invertidos). Depois do soco fica cansado e dá para passar | Capacete, Broca |
| Deserto | Cobra | Patrulha; te vendo perto e em linha, espreita e dá o bote. Picada = veneno: acerte as setas em 6s ou perde 1 coração | Tapete, Flauta |
| | Múmia | Caça de perto (por pouco tempo) e joga a faixa como laço (puxa 2 tiles); na tempestade de areia fica invisível e mais rápida | Flauta |

Os monstros são pixel art animada: andam saltitando, respiram pesado, têm tiques nervosos, babam veneno ou lava, ficam
vermelhos de raiva antes de atacar e os **olhos brilham no escuro** (mais fortes quando você chega perto).

O desenho completo (itens, monstros e balanceamento) está em [docs/design.md](docs/design.md).

## Ranking

A opção **RANKING** do menu mostra o top 10 de cada dificuldade em abas (**FÁCIL / NORMAL / DIFÍCIL / INSANO**;
esquerda/direita ou clique troca a aba). Cada jogador tem a sua melhor pontuação guardada separadamente em cada dificuldade
(`~/.marble_run/pontuacoes.sqlite3`). Pontuações de versões antigas, que não tinham dificuldade, entram como NORMAL.

## Menu desenvolvedor (secreto)

No menu principal, aperte **CIMA, BAIXO, DIREITA, ESQUERDA**. A opção **DESENVOLVEDOR** surge de uma explosão de
pixels (fica liberada até fechar o jogo) e tem duas ferramentas:

- **EDITAR RANKING**: escolha a aba, selecione um jogador para renomear, mudar pontos/fase ou apagar, ou limpe a aba
  inteira. Ações que não têm volta pedem confirmação.
- **TESTE DOS MAPAS (ARENA)**: escolha o mapa (visual, fenômeno e roleta) e entre num **quadrado gigante e aberto**, sem
  limite de tempo e sem game over, para montar o que quiser. O painel da direita tem 4 abas:
  **MAPA** (parede, borracha, mudar o portal, caixa "?"), **PERIGO** (água, placa de gelo, fogo, teia, areia movediça,
  lava, buraco), **MONSTRO** (os 12, de qualquer mapa) e **ITEM** (qualquer item largado no chão: encostou, pegou).

| Comando (arena) | Efeito |
|-------|--------|
| Clique esquerdo | Coloca a ferramenta escolhida no tile (paredes, perigos e borracha: segure e arraste para "pintar") |
| Clique direito | Apaga o que tiver no tile (se não tiver nada, derruba a parede) |
| Roda do mouse / 1 a 4 | Troca a ferramenta / troca a aba (ou clique no painel) |
| R | Limpa a arena inteira |
| C | Liga/desliga o fenômeno do mapa (também dá para clicar no botão do painel) |
| F | Força o fenômeno do mapa agora (se estiver desligado, liga) |
| 9 | Abre a roleta |
| N | Noite: escurece a arena (para ver os olhos dos monstros brilhando) |
| TAB | Esconde/mostra o painel |

O portal da arena não encerra a fase (para não perder o que foi montado).

As regras ficam em `src/marble_run/dominio/ambiente.py` (itens e golpes), os monstros em
`src/marble_run/dominio/monstros.py` e o que cada mapa sorteia em `src/marble_run/dominio/biomas.py`.

## Testes

```powershell
cd "Marble_Run-main\src"
python -m unittest test.test_ambiente test.test_monstros test.test_arena test.test_ranking
```
