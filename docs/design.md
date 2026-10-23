# Marble Run: documento de design (itens, monstros e balanceamento)

Legenda de status: ✅ implementado · 🕓 planejado (ainda não implementado)

Regra de design: **cada mapa tem 2 itens exclusivos, um contra o perigo do mapa e um contra os monstros.**
Todo ataque de monstro tem **aviso antes** (o monstro treme com um "!", os tiles do ataque piscam, a sombra da águia
aparece, a terra treme...), para ser justo.

---

## 1. Balanceamento geral ✅

| Regra | Onde mexer |
|---|---|
| Metade das caixas "?" e depois **mais caixas de novo** (`2 + chão/150`, mínimo 6 tiles entre elas) | `Bioma.tiles_por_caixa` em [biomas.py](../src/marble_run/dominio/biomas.py) |
| Caixas longe umas das outras (mínimo 6 tiles) | `Bioma.distancia_entre_caixas` |
| Molas só na Masmorra, só de ida (lado sorteado) e nunca a menos de 5 tiles do portal | `Bioma.tiles_por_mola`, `Bioma.distancia_do_portal` |
| Placas de gelo: 1 trecho a cada 110 tiles, até 3 em linha, 6 tiles entre trechos | `RegraDePerigo(GELO, ..., distancia_minima=6)` |
| Fenômenos um pouco mais raros (principalmente a erupção) | `CICLOS_DOS_FENOMENOS` em [ambiente.py](../src/marble_run/dominio/ambiente.py) |
| Banana removida; Relógio, Estrela e Coração Bônus em todos os mapas | `ITENS_COMUNS` |
| Roleta com memória (último prêmio 10% da chance, os 2 anteriores 35%; passa de uma fase para outra) | `HistoricoDaRoleta` |
| Coração Bônus com a vida cheia: some (não vira tempo) | `Partida._curar` |
| Monstros: 0 nas fases 1–3, 1 nas fases 4–6, 2 da fase 7 em diante (Normal) | `Dificuldade.monstros()` em [regras.py](../src/marble_run/dominio/regras.py) |

### Dificuldades (mais difíceis) ✅

Tempo para um caminho de 30 tiles (fase 1 → fase 10). Antes, o Normal dava 52s na fase 1.

| | Tempo | Luz (tiles) | Perigos | Monstros | Vida |
|---|---|---|---|---|---|
| Fácil | 42,6s → 19,2s | 8 → 4,2 | ×0,45 → ×1,35 | no máximo 1 | 3, +1 por fase |
| Normal | 32,8s → 14,8s | 7 → 3,2 | ×0,6 → ×1,8 | fase 4: 1, fase 7: 2 | 3, +1 por fase |
| Difícil | 26,2s → 12,2s | 6,2 → 2,5 | ×0,8 → ×2,4 | fase 3: 1, fase 5: 2 (mais rápidos e agressivos) | 3, sem cura |
| Insano | 19,7s → 11,0s | 2,4 fixa, sem lanterna | ×1 → ×2,9 | fase 2: 3 (rápidos e agressivos) | **2**, sem cura |

A curva chega no máximo na fase 10 (antes 12); o Difícil e o Insano também começam com o labirinto maior.

### Fenômenos (intervalo entre um e outro)

| Fenômeno | Antes | Agora |
|---|---|---|
| Erupção (Fogo) | 8s, 5 jatos, alcance 4 | **11s, 3 jatos, alcance 3** |
| Tempestade de areia (Deserto) | 12s | 13,5s |
| **Tempestade de gelo (Gelo)** | — | 13,5s, -40% de velocidade (o Café protege) |
| Apagão (Masmorra) | 14s | 15,5s |
| Terremoto (Terra) | 15s | 16,5s |
| Rajada (Vento) | 9s | 10s |

---

## 2. Itens ✅

**Todos os mapas:** Relógio (+10s) · Estrela (imune a debuffs e monstros, 6s) ·
Coração Bônus (+1 coração; com a vida cheia vira +10s)

| Mapa | Item | Efeito |
|---|---|---|
| **Masmorra** | Lanterna | +60% de visão e a aranha foge da luz (12s). *Vetada no Insano* |
| | Bússola | Seta apontando o portal (15s) |
| **Gelo** | Blusa | Não congela nem desliza: poças, placas, raio do Boneco de Neve (10s) |
| | Café | +30% de velocidade e imune a lentidão, inclusive a tempestade de gelo (8s) |
| **Deserto** | Flauta | Acalma a tempestade de areia **e faz os monstros dormirem** (8s) |
| | Tapete Mágico | Flutua 8s (passa por cima da areia movediça, das teias, dos buracos e da cobra) e **voa por cima de 1 parede** |
| | Gênio da Lâmpada | Pausa o jogo e o gênio (pixel art animada: turbante com joia, olhos dourados, braços cruzados e cauda de fumaça saindo da lâmpada) oferece 1 desejo: **+20s** · **melhor caminho** (setas douradas no chão do jogador até o portal, 3,5s) · **teleporte 6 passos para perto do portal** |
| **Fogo** | Extintor | Apaga para sempre fogo e lava num raio de 3 tiles; o Magman vira pedra e a Fornalha apaga por 5s |
| | Bota de Obsidiana | Imune a fogo, lava, erupção e labareda (8s) |
| **Vento** | Guarda-Chuva | Imune a rajadas, ao tornado e ao mergulho da águia (10s) |
| | Pipa | A rajada sopra seguindo o melhor caminho até o portal, e o tornado joga **para perto** do portal (12s) |
| **Terra** | Broca | O personagem **segura a broca**; andando contra uma parede ela gira, a parede racha e **quebra de verdade** (vira chão). Até 2 paredes (15s); sem carga, a broca some da mão |
| | Capacete de Mineiro | O terremoto não inverte os controles, +30% de luz, imune à toupeira e à onda de choque do golem (12s) |

---

## 3. Monstros ✅

| Mapa | Monstro | Poder | Contra-ataque |
|---|---|---|---|
| **Masmorra** | Aranha | Anda pelos corredores e **cospe teia em linha reta**; acertou = preso nas setas; errou = a teia fica 10s no chão | Lanterna (foge) |
| | Minotauro | Te vê num corredor reto, raspa o pé por 1s e **investe até a parede**: -1 coração e empurrão. Bateu na parede: **tonto por 2s** | Sair da linha dele |
| **Gelo** | Boneco de Neve Sombrio | Anda **extremamente devagar** (15% da velocidade do jogador); aviso de 1s e **raio congelante** em linha (congela 2s) | Blusa |
| | Yeti | Persegue devagar; **pisão cria placas de gelo** em volta (6s); encostou: -1 coração | Café, Blusa |
| **Fogo** | Magman | **Rastro de lava** (3s); mergulha e reaparece 2–3 tiles do jogador (bolhas avisam) | Extintor, Bota |
| | Fornalha | Torre sólida, sempre no **fim de um beco** (nunca fecha o caminho); fica vermelha e **solta labareda** em linha (4 direções no Difícil/Insano) | Bota, Extintor |
| **Vento** | Águia | Voa por cima das paredes; a **sombra no chão** marca o mergulho; pegou: **rouba 1 buff ativo** (-1 coração no Difícil/Insano se não houver buff) | Guarda-Chuva |
| | Tornado | Encostou: **joga até 4 tiles para longe do portal** + tontura de 1,2s. Não dá dano | Guarda-Chuva, Pipa |
| **Terra** | Toupeira | Cava por baixo da terra (atravessa paredes; só aparece o montinho); sai embaixo do jogador: **-5s** e fica caído 1s. Os **buracos viram túneis**: entrar em um leva ao próximo (até 4) | Capacete, Tapete |
| | Golem | Lento e **sólido** (bloqueia o corredor); persegue e dá **soco no chão** em área: -1 coração e controles invertidos 2s. **Depois do soco fica cansado 2,5s e deixa de ser sólido**: é a hora de passar | Capacete, Broca |
| **Deserto** | Cobra | Dá o **bote** (2 tiles); picada = **veneno**: aparecem 4 setas e uma barra de 6s; errou o tempo: -1 coração | Tapete, Flauta |
| | Múmia | Persegue; joga a **faixa como laço** e puxa 2 tiles; **na tempestade de areia fica invisível (só os olhos) e mais rápida** | Flauta |

Regras gerais dos monstros:
- **Território:** cada monstro patrulha até 5 tiles de onde nasceu e, vagando, evita entrar no tile do jogador
  (não encurrala ninguém no corredor).
- **Só o Yeti e a Múmia caçam**, e só se o jogador chegar a 5 tiles e estiver no território deles. Eles têm 3s de
  fôlego e depois desistem por 5s. A Cobra e o Golem não perseguem: param e esperam quando o jogador chega perto
  (espreitar / guardar). A Águia e a Toupeira circulam o território e só atacam quem passa perto.
- Nascem a pelo menos 8 passos da entrada, longe do portal e longe uns dos outros; nunca entram no portal.
- Depois de levar dano, o jogador fica 1,5s invulnerável.
- **Quem está travado (teia, veneno, congelado, caído) não apanha**: nada de apanhar sem poder fugir.
- A Estrela deixa imune a todos os monstros; a Flauta faz todos dormirem.

### Visual dos monstros ✅
Pixel art sombria em [sprites_monstros.py](../src/marble_run/apresentacao/sprites_monstros.py) (grades de letras,
2 a 4 quadros por monstro, contorno automático), animada em [bestiario.py](../src/marble_run/apresentacao/bestiario.py):
- andam saltitando, respiram pesado parados, piscam e têm tiques nervosos (tremem de repente, mais quando você está perto);
- aura escura pulsando em volta; baba, veneno ou lava pingando (aranha, cobra, yeti, magman, minotauro, múmia);
- antes de atacar: incham, tremem cada vez mais e ficam **vermelhos de raiva**; no ataque esticam;
- tontos balançam; dormindo fecham os olhos; o extintor deixa o Magman/Fornalha cinza (pedra);
- os **olhos brilham no escuro**, mais fortes quando o jogador chega perto ou o ataque vem.

---

## 4. Desenvolvedor

- ✅ **Arena / Modo Criativo** (teste dos mapas): quadrado aberto de 28×18 tiles, sem tempo e sem game over, com o
  visual, o fenômeno e a roleta do mapa escolhido. Paleta com 4 abas: **MAPA** (parede, borracha, portal, caixa "?"),
  **PERIGO** (7), **MONSTRO** (os 12) e **ITEM** (os 16, largados no chão). Clique esquerdo coloca (arrastar pinta),
  direito apaga, roda troca a ferramenta, R limpa, N escurece (noite), **C liga/desliga o fenômeno** (ou o botão do
  painel). Regras em
  [arena.py](../src/marble_run/dominio/arena.py): nunca prende o jogador numa parede, a borda e a entrada não mudam,
  e o portal não encerra a arena.
- 🕓 Ideias para depois: atravessar paredes (noclip) e salvar/carregar arenas montadas.

---

## Onde fica cada coisa no código

| O quê | Arquivo |
|---|---|
| Regras dos itens e dos golpes dos monstros | [ambiente.py](../src/marble_run/dominio/ambiente.py) |
| Comportamento de cada monstro | [monstros.py](../src/marble_run/dominio/monstros.py) |
| Caminhos (BFS, linha de visão) | [caminhos.py](../src/marble_run/dominio/caminhos.py) |
| O que cada mapa tem e onde nasce | [biomas.py](../src/marble_run/dominio/biomas.py) |
| Desenho dos monstros (vida/animação) | [bestiario.py](../src/marble_run/apresentacao/bestiario.py) |
| Pixel art dos monstros | [sprites_monstros.py](../src/marble_run/apresentacao/sprites_monstros.py) |
| Editor da arena (regras) / tela | [arena.py](../src/marble_run/dominio/arena.py) / [vitrine.py](../src/marble_run/apresentacao/vitrine.py) |
| Tela do Gênio | [genio.py](../src/marble_run/apresentacao/genio.py) |
| Testes | [test_monstros.py](../src/test/test_monstros.py), [test_arena.py](../src/test/test_arena.py) |
