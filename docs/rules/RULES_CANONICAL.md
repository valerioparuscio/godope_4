# Regolamento canonico — DOPE

Fonte primaria: `how_to_play_v056` (fornito dal game designer in chat il 2026-07-30,
4 pagine, sezioni A–D). Trascrizione fedele, senza reinterpretazione, secondo
`CLAUDE.md` sezione 2 — Fonti di verità.

I punti non coperti o ancora ambigui dopo questa trascrizione sono elencati in
`RULES_PENDING.md`, con riferimento alla sezione qui sotto quando pertinente.

> In Dope sarete i Boss di una Gang di criminali alle prime armi che cerca di
> farsi spazio nel mondo del malaffare in città. Nel corso di 4 giorni dovrete
> mettere in piedi il vostro giro di affari sporchi che vi consentirà di
> portare a termine il maggior numero di Jobs. Vince la Gang con più Respect.

## A) Componenti

### A1) Hoods (Quartieri)

Ci sono 10 Quartieri collegati da una rete di strade, più 2 Quartieri speciali,
Den e Jail.

Ciascun Hood ha 5 piazze ed è caratterizzato da un colore che indica un Contact.
Al centro del Quartiere c'è il mercato della Dope acquistabile dai Criminali.
Da un Quartiere i Criminali potranno vendere Merce solo al relativo Cliente.

**Den**

- Il Den è un Quartiere speciale in cui non sono permessi acquisti, vendite o risse.
- Un Criminale non può essere piazzato nel Den ma può raggiungerlo con uno
  spostamento da qualunque Quartiere.
- Un Criminale che entra nel Den fa pescare una carta a scelta e prende il
  nome di Gambler. **Decisione (2026-07-30):** il giocatore sceglie da quale
  mazzo Cliente pescare, poi la carta è casuale (pesca dalla cima del mazzo
  scelto).
- Dal Den i Gambler possono essere spostati in un qualunque Quartiere.
- Per ogni Gambler i giocatori possono partecipare ad un Poker per turno.
- **Decisione (2026-07-30):** il Den ospita al massimo 6 Gambler
  contemporaneamente.
- **Decisione (2026-08-15):** un giocatore non può avere più di 2 proprie
  pedine nel Den contemporaneamente — un limite individuale, in aggiunta
  al limite globale di 6.

**Jail**

- Il Commissariato è un Quartiere speciale in cui i Criminali entrano quando
  vengono arrestati, diventando Rats.
- Nei 6 slot del Commissariato vengono messi i Rats e le Merci requisite.
- I Rats possono corrompere Cops in qualunque Quartiere.
- Quando il Commissariato si riempie c'è l'Evasione e i 6 Rats tornano nei
  Covi, portandosi dietro la Merce su cui sono posizionati. **Decisione
  (2026-07-30):** il sesto Rat, quello che causa l'Evasione, non torna al
  Covo come Rat: evolve direttamente in Link dai Politici (vedi §A5). Sono
  quindi 5 i Rats che tornano ai Covi come pedine libere con la loro Merce.

### A2) Dope (Merci)

Ci sono 4 tipi di Dope, in quantità limitate: Camaleonte (14 pezzi), Rana (16
pezzi), Polpo (10 pezzi), Gufo (8 pezzi).

- Le Dope disponibili per l'acquisto sono impilate al centro di ogni
  Quartiere (max 3).
- Le Dope acquistate vanno posizionate nei Covi (max 3).
- Le Dope vendute vanno posizionate nei Punti di Vendita dei Clienti (max 3).

**Decisione (2026-07-30):** se una Dope acquistata, o recuperata da
un'Evasione, dovrebbe superare il limite di 3 pezzi per tipo nel Covo di
destinazione, l'azione avviene comunque e la Merce in eccesso va persa
(rimossa dal gioco).

**Decisione (2026-08-01):** confermato esplicitamente che il limite di 3 per
tipo nel Covo vale per Dope, Chip Poker e Cops/Feds (vedi §A7) — l'unica
cosa senza alcun limite nel Covo sono le pedine Criminale stesse (limitate
solo dal totale di 10 possedute da ciascun giocatore, non da una capienza
del Covo).

### A3) Prices (Prezzi)

I Prezzi delle Dope iniziano da 3, 1, 4, 6, nell'ordine Camaleonte, Rana,
Polpo, Gufo (stesso ordine di §A2).

**Decisione (2026-07-30):** il prezzo di ciascun tipo di Dope non è un
intero libero, ma un indice su un **tracciato di valori ammessi**, specifico
per tipo. "Sale di 1" / "scende di 1" (§A3, §C3, §C4, §C5) significa uno
step lungo questo tracciato, non +1/-1 in dollari:

| Dope | Tracciato prezzi (min → max) | Prezzo iniziale |
|---|---|---|
| Camaleonte | 2, 3, 4, 6, 8 | 3 |
| Rana | 0, 1, 3, 5 | 1 |
| Polpo | 3, 4, 5, 7, 9, 11 | 4 |
| Gufo | 4, 6, 8, 10, 12, 14 | 6 |

Tutti i tipi iniziano al secondo valore del proprio tracciato (indice 1). Il
minimo è il primo valore del tracciato, il massimo l'ultimo.

I Prezzi salgono di uno step per ogni:
- Dope acquistata
- Dope requisita

I prezzi scendono di uno step per ogni:
- Dope venduta

Inoltre, con la free-action "Marketing" i giocatori possono far salire o
scendere i Prezzi (di uno step per Stonk, §D3).

Se tutti i Prezzi arrivano al massimo del proprio tracciato, crolla il
mercato e i Prezzi scendono tutti al minimo (indice 0) del proprio
tracciato.

### A4) Spot (Punti di Vendita)

Ciascun Cliente ha due Spot che indicano le Dope a cui è interessato.
Ogni Spot può contenere al massimo 3 Dope.

### A5) Links (Connessioni)

Ciascun Contact ha 3 Links, posizioni/status privilegiate che possono essere
prese dai Criminali. **Decisione (2026-07-30):** i 3 Links di un Contact
corrispondono a 3 slot distinti, uno per livello (Grinta 1, 2, 3); ogni slot
può contenere una sola pedina. Di conseguenza non può mai esistere una
parità di livello minimo tra Link dello stesso Contact (rilevante per §C5,
arresto Feds).

**Correzione (2026-08-01):** i 3 slot di un Contact sono **condivisi fra
tutti i giocatori**, non un tracciato indipendente per ciascun giocatore —
non possono mai esistere contemporaneamente due pedine Link (di due
giocatori diversi) allo stesso livello dello stesso Contact. Quando un
giocatore inserisce un nuovo Link, lo scorrimento verso l'alto (ed
eventuale espulsione dal livello 3) si applica a qualunque pedina occupi
quei livelli, indipendentemente dal proprietario; una pedina espulsa torna
nel Covo del *proprio* proprietario, non di chi ha inserito il nuovo Link.
Questo corregge un'implementazione errata della Milestone 3
(`rules/links.py` scopava erroneamente i 3 slot per singolo giocatore) —
`rules/officers.py::_lowest_level_link_at_contact` (arresto Fed, già
Milestone 3) era invece già scritta correttamente senza filtro per
proprietario, il che ha fatto emergere l'incoerenza.

- Un Criminale che ha venduto Merci o vinto una Rissa in un Quartiere, può
  evolversi in un Link del relativo Cliente.
- Un giocatore che ha vinto un Poker evolve un suo Gambler in un Link presso
  i Preti.
- Il Criminale che entra per sesto in prigione, causando l'evasione, evolve
  in un Link dai Politici. **Decisione (2026-07-30):** evolve direttamente,
  senza passare dal Covo (vedi §A1 Jail).
- Quando si manda un Criminale su un Link lo si mette sulla Grinta 1, se il
  Link a Grinta 1 è occupato le pedine presenti scorrono a destra. Se una
  pedina esce dal tracciato, torna nel Covo.
- I Link contano come se fossero Criminali presenti in tutti i Quartieri del
  Cliente al fine di Acquistare, Vendere e Corrompere, e per le Risse.
- Un Link può essere speso per giocare una azione extra della relativa
  grinta, fra quelle del Cliente.
- Le azioni extra possono essere giocate al massimo una volta per turno, e
  possono essere potenziate dalle carte.
- Dopo aver usato l'azione extra il Link torna nel Covo.

**Decisione (2026-08-01):** l'azione extra da Link può essere giocata prima
o dopo l'azione principale del round (vedi anche §B2), al massimo una volta
per turno intero — a meno di Skill o carte che modifichino questo limite
(non ancora implementate). Quando viene usata, il Link speso torna sempre
al Covo, indipendentemente da quando nel turno è stata giocata. Implementato
in Milestone 3 con due punti di offerta per round (prima della scelta della
Grinta, e subito dopo la risoluzione dell'azione principale del round),
entrambi declinabili: vedi `rules/turn_flow.py`.

**Decisione (2026-08-01):** il Link speso torna al Covo *immediatamente* nel
momento in cui viene scelto per l'azione extra, prima ancora che l'azione
extra stessa venga scelta o eseguita — non a fine azione. Per costruzione,
l'azione extra non può quindi mai arrestare, confiscare o comunque
influenzare il Link che la sta alimentando: al momento in cui una qualunque
sotto-azione gira, quella pedina è già una normale pedina in Covo.

### A6) Cops e Feds (Poliziotti e Detective)

Ci sono 2 tipi di poliziotti: Cops, che pattugliano i Quartieri, e Feds, che
indagano nei Punti di Vendita.

- Cops entrano in gioco in un Quartiere quando avviene una Rissa e quando si
  svuota/ricarica di Merci.
- Feds entrano in gioco in un Punto di Vendita quando questo si
  riempie/svuota di Merci.
- Cops e Feds hanno l'effetto di bloccare acquisti/vendite delle Merci.
- Cops in un Quartiere senza Merci o senza Criminali vengono rimandati al
  Commissariato. **Decisione (2026-07-30):** vanno in una riserva separata
  dai 6 slot dei Rats/Merci confiscate (non competono per lo spazio); il
  controllo che li rimanda in riserva viene rieseguito subito dopo ogni
  evento che ne cambia le condizioni, non solo a fine azione.
- Feds da un Cliente senza Merci e senza Ganci vengono rimandati al
  Commissariato (stessa decisione: riserva separata, controllo immediato).
  **Implementato (2026-08-02):** `rules/links.py::
  check_spot_fed_removal_for_contact` — "senza Ganci" significa che il
  Contact di quello Spot non ha più **nessun** Link, a nessun livello, di
  nessun giocatore. Chiamata solo dai punti dove un Link *scompare*
  (Fed che arresta il Link di livello minore, Link speso per l'azione
  extra che torna al Covo) — mai dal punto che svuota lo Spot vendendo,
  che altrimenti annullerebbe il Fed appena creato nello stesso istante
  in cui entra.
- Più Cops o Feds possono stare nello stesso Quartiere/Punti di Vendita.

### A7) Base (Covo)

Il Covo è la plancia di ciascun giocatore.

- Nel Covo possono stare al massimo 3 Chip per tipo: Cops, Poker, Merci dei
  4 tipi. **Decisione (2026-07-30):** i Feds non hanno una categoria propria,
  condividono il conteggio con i Cops (limite 3 totale tra Cops+Feds nel
  Covo).
- Nel Covo si selezionano le azioni con le pedine Grinta.

### A8) Criminali

Le pedine giocate nei quartieri si chiamano Criminali. Possono diventare
Links, Gambler o Rats.

### A9) Carte

Nel gioco ci sono 3 tipi di carte:

**Carte Clienti**

Ciascun Cliente offre 20 carte che contengono:
- in basso, il potenziamento dell'azione base (ciascun Cliente potenzia un
  certo tipo di Azione);
- in alto a sinistra, due simboli da giocare per il Poker;
- in alto a destra, quattro simboli tra "stonk" e "pistole" da giocare per
  influenzare il mercato o per fare Rissa.

**Decisione (2026-07-31) — schema dettagliato della carta (fonte: esempio
carta "TRY AGAIN"):**

- **Icona azione base** (in alto a sinistra, cerchio con simbolo):
  stella = Acquistare, cuore = Vendere, freccia in basso = Piazzare,
  freccia a destra = Spostare, distintivo di polizia = Corrompere,
  distintivo con un dollaro = Comprare Cops/Feds. La stessa icona è
  ripetuta accanto al riquadro di testo del potenziamento, in basso.
- **Simboli Poker** (2, sotto l'icona azione): fiori a 5 petali, uno dei 5
  colori: rosa scuro, arancione, verde, grigio, azzurro.
- **Simboli Stonk/Pistola** (4, colonna a destra): ciascuno è o uno Stonk
  (freccia rosa, per la free-action Marketing) o una Pistola (per la
  Rissa); combinazione variabile tra i due tipi sui 4 simboli (es. 3
  Stonk + 1 Pistola).
- **Potenziamento azione base** (riquadro di testo in basso): l'effetto è
  descritto testualmente, non da una formula fissa — varia carta per
  carta.
- Le carte hanno anche un **titolo flavor** (es. "TRY AGAIN"), senza
  effetto meccanico.

**Decisione (2026-07-31) — identificazione del Contact:** il Contact di
appartenenza di una carta si riconosce dal **colore di sfondo**
dell'illustrazione, con la stessa palette dei semi Poker (§A9) e del
tie-break Poker (§D2):

| Contact | Colore di sfondo |
|---|---|
| Artisti | Rosa |
| Studenti | Verde |
| Manager | Azzurro |
| Preti | Grigio |
| Politici | Arancione |

Il titolo flavor stampato in alto (es. "TRY AGAIN") non ha effetto
meccanico.

**Decisione (2026-07-31) — schema delle carte Preti (fonte: esempio carta
"GAMBLE"):** le carte Preti seguono uno schema diverso dalle altre 4:

- **Nessun simbolo Poker** in alto a sinistra (le carte Preti non ne hanno
  mai, a differenza delle altre 20 carte per Contact).
- L'**icona azione base** in alto a sinistra c'è comunque (stessa codifica
  a 6 icone) — nell'esempio, freccia in basso = Piazzare — ed è ripetuta in
  basso a sinistra, come nelle altre carte.
- I **4 simboli Stonk/Pistola** a destra restano, in combinazione libera
  (nell'esempio: 4 Pistole).
- Al posto del riquadro di testo con il potenziamento, in basso c'è un
  riquadro nero con **3 simboli Poker** (stessa palette a 5 colori): sono
  i simboli che, quando la carta viene giocata come Gamble, formano il
  banco comune del Poker (coerente con la decisione già registrata in
  §D2 — banco di 3 simboli dalle carte Preti).

*(vedi RULES_PENDING — "GAMBLE" è il titolo fisso di tutte le carte Preti,
o varia carta per carta come il flavor delle altre?)*

Le carte si giocano per ottenere solo uno degli effetti, e quando giocate
vengono scartate. Possono essere giocate più carte nello stesso turno.
**Decisione (2026-08-15, ribalta quella del 2026-08-01 — RULES_PENDING.md
#12/#17):** il limite di 5 carte in mano si verifica alla fine di **ogni
round** del giocatore (§B2 — fino a 9 round a partita per giocatore, non 3
turni), non solo alla fine del suo turno di 3 round.

**Carte Job**

Indicano i 9 diversi "Job" con cui le Gang guadagnano Reputazione. Ogni
giocatore ha tre pile di carte JOB suddivise per livello di difficoltà. Si
inizia il gioco rivelando JOB per livello. Quando un JOB viene portato a
termine, un altro JOB dello stesso livello viene scoperto. Ciascun Job è
associato ad 1 o 2 Clienti.

**Carte Retata**

7 carte che indicano un obiettivo generale, ossia come "non macchiare la
propria reputazione". In ogni partita ne entrano in gioco 3.

### A10) Jobs

Quando un giocatore completa un Job incassa una REP, posizionando un Token
sul tabellone sulla riga del Job. Può scegliere la colonna libera che
preferisce per incassare il relativo bonus tra: prendere una carta Skill,
prendere un Link o prendere 2 carte. Il colore della carta Job indica presso
quale Cliente raccogliere il bonus.

**Decisione (2026-07-31) — struttura dettagliata:**

- Ci sono **9 Job** in totale, divisi in **3 tier** (livelli di difficoltà)
  da 3 Job ciascuno.
- **Ogni giocatore possiede tutti e 9** i Job (non è un pool condiviso sul
  tabellone): li tiene impilati in **3 mazzetti personali**, uno per tier.
- A inizio partita ogni giocatore scopre le prime 3 carte, una per
  mazzetto (una per tier).
- Quando un giocatore completa un Job, lo scarta e scopre la prossima
  carta dello stesso tier dal proprio mazzetto.
- Il tabellone ha una **riga per Job** con **4 colonne**. Alla conclusione
  di un Job, il giocatore piazza un segnalino R (Respect/REP) nella colonna
  libera che preferisce su quella riga — le colonne sono condivise tra
  tutti i giocatori: chi completa per primo un dato Job ha tutte e 4 le
  colonne disponibili, chi lo completa dopo (essendo un Job che ogni
  giocatore possiede) sceglie tra quelle rimaste libere.
- Le colonne danno bonus diversi (non necessariamente le stesse 4 su ogni
  riga): pescare 1 carta Skill (abilità permanente + 1 punto vittoria a
  fine partita), prendere un Link spostando una pedina dal Covo
  direttamente sul Link (senza passare dai normali requisiti di
  vendita/Rissa), pescare 2 carte, oppure nessun bonus.
- Ciascun Job è associato a 1 o 2 Contact: il colore del Job determina
  presso quale Contact si pesca la Skill, si prende il Link, o si pescano
  le carte.

**Decisione (2026-07-31) — elenco dei 9 Job:**

| Job | Requisito | Contact | Tier |
|---|---|---|---|
| 1 | Vinci 1 Rissa | Studenti | 1 |
| 2 | Compra 1 Cop/Fed | Politici | 1 |
| 3 | Vinci 2 Poker | Preti | 3 |
| 4 | Abbi 3 Rats | Politici / Preti | 2 |
| 5 | Abbi 4 Dope nel Covo (almeno una per tipo) | Artisti | 2 |
| 6 | Abbi 4 Link (in totale) | Politici / Artisti | 2 |
| 7 | Abbi Criminali in 6 Hoods diversi | Manager | 1 |
| 8 | Abbi tutti i 10 Criminali in gioco (fuori dal Covo) | Manager / Studenti | 3 |
| 9 | Abbi 30 dollari o più | Manager / Artisti | 3 |

**Decisioni (2026-08-01), Milestone 5 — Jobs:**

- **Colonne del tabellone:** le 4 colonne bonus (Skill / Link / 2 carte /
  Niente) sono **le stesse su ogni riga di Job**, non una tabella diversa
  per ciascuno dei 9 Job. Il primo giocatore che completa un dato Job
  sceglie liberamente tra le 4; i completamenti successivi dello stesso
  Job (ogni giocatore possiede una propria copia) scelgono tra le colonne
  ancora libere su quella riga. Configurato in
  `game_config.json::job_board_column_bonuses`.
- **Job con 2 Contact:** il giocatore che completa sceglie liberamente
  presso quale dei due Contact incassare il bonus (Job 4, 6, 8, 9).
- **Job 8 ("Abbi tutti i 10 Criminali fuori dal Covo"):** conta qualsiasi
  pedina non `IN_BASE`, quindi anche Link/Gambler/Rat, non solo le
  pedine ancora col ruolo Criminal.
- **Job 4 ("Abbi 3 Rats"):** è un requisito di stato attuale (quanti Rat
  propri sono in prigione *in questo momento*), non un contatore
  cumulativo di quanti ne sono mai stati mandati — un Rat evaso nel
  frattempo non conta più.
- **Retata "comprato più Cops" (raid_05):** conta sia Cops sia Fed,
  stesso significato del Job 2 ("Compra 1 Cop/Fed") — un solo contatore
  cumulativo (`officers_bought_count`), non due separati.
- **Rilevamento del completamento:** automatico dopo ogni comando
  accettato (`application/command_bus.py`'s `post_success_hooks`,
  CLAUDE.md §11.12), non richiede alcuna azione esplicita del giocatore.
  Più Job possono completarsi nello stesso comando (anche per giocatori
  diversi): vengono accodati in ordine deterministico
  (`player_order`, poi tier) e risolti uno alla volta tramite
  `ChooseJobReward`, mettendo in pausa qualunque flusso interrotto
  (Corruzione, Rissa, Poker) fino alla fine della coda.

**Decisione (2026-08-01) — correzione ai Link (§A5):** i 3 slot di Link
per Contact sono condivisi fra tutti i giocatori, non un tracciato per
giocatore — vedi §A5 sopra per il dettaglio completo.

**Decisione (2026-07-31) — effetti delle Skill, per Contact:**

| Contact | Skill 1 | Skill 2 | Skill 3 |
|---|---|---|---|
| Artisti | Compri e vendi sempre con 1 Grinta in più | Compri sempre a -1 e vendi a +1 | Quando vendi mandi dal Covo sul Link |
| Studenti | Muovi sempre con una Grinta in più | Quando fai Rissa hai una Pistola in più | Quando vinci una Rissa mandi dal Covo sul Link |
| Manager | Piazzi sempre con una Grinta in più | Piazzare un Criminale ti costa 1 | Applichi Stonk 2 volte, prima e dopo l'azione |
| Preti | Puoi giocare 2 carte per ogni Poker (scegli 2 simboli) | Quando lanci un Poker incassi 6 dollari | Giochi carte Gamble associate a qualunque azione |
| Politici | Corrompi e compri Cops/Feds sempre con una Grinta in più | Corrompi e compri Cops/Feds con 1 dollaro in meno | Puoi attivare 2 Ganci (Link) a turno |

Ogni Skill dà un'abilità permanente (vedi §A10) e vale 1 punto vittoria a
fine partita. **Decisione (2026-07-31):** le Skill in gioco sono
effettivamente 15 (3 per Contact); non tutte vengono prese in una singola
partita, dato che i Job che assegnano una Skill come bonus sono un
sottoinsieme dei 9 Job totali.

**Decisioni implementative (2026-08-02), Milestone 5 Stage 4 — effetti
meccanici delle Skill:**

- **Schema dati:** `data/skills.json` porta ora anche un campo `effect`
  per ciascuna Skill (es. `{"type": "extra_grit", "action_types": [...],
  "amount": 1}`), analogo a `requirement` nei Job — l'effetto è dato
  guidato, non hardcodato nel motore (CLAUDE.md §3.5). Copiato una sola
  volta su `state.configuration["skill_effect_by_id"]` a setup, stesso
  meccanismo già usato per i criteri delle Retate e i price track.
- **"+1 Grinta sempre" (Artisti-1, Studenti-1, Manager-1, Politici-1):**
  si applica sempre, senza eccezioni, al **massimo** di pedine
  utilizzabili in quell'azione (corretto 2026-08-02: la Grinta, con o
  senza Skill, è sempre un massimo, non un numero esatto obbligatorio —
  vedi §B2). `rules/skills.py::effective_action_count` è l'unico punto
  di calcolo, usato sia dal generatore di opzioni
  (`application/legal_actions.py`) sia dalla validazione del comando
  (`rules/economy.py::_validate_action_targets`), così le due parti
  restano sempre d'accordo sullo stesso numero.
- **Cumulo di più Skill sullo stesso tipo di azione:** non esplicitamente
  regolato (nessuna coppia di Skill reali si sovrappone sullo stesso
  `action_type` nel set attuale di 15), ma l'unica lettura coerente con
  ogni Skill come abilità permanente indipendente è che si sommino.

**Decisioni implementative (2026-08-02), Milestone 5 Stage 4c — le 7
Skill "meccaniche singole":**

- **Studenti-2 "hai una Pistola in più":** **corretto (2026-08-02):** si
  applica **sempre**, incondizionatamente, a ogni partecipante con la
  Skill — anche a chi non ha giocato nessuna carta in quella Rissa
  ("tutti i presenti nel quartiere partecipano sempre in ogni caso,
  anche se non giocano carte"). `rules/brawl.py::_force_by_player`
  somma il bonus direttamente alla Forza base (Criminali + Link) di ogni
  partecipante, invece di agganciarlo al meccanismo di assegnazione
  Pistole di una carta giocata.
- **Manager-3 "Applichi Stonk 2 volte":** implementato insieme al
  meccanismo di base Marketing/Stonk (§D3, Milestone 5 Stage 4c-bis) —
  ogni Stonk allocato si applica automaticamente a entrambi i checkpoint
  (prima E dopo lo step di prezzo automatico del pacchetto),
  `rules/skills.py::marketing_applies_both_timings`.
- **Preti-2 "incassi 6 dollari":** `rules/skills.py::
  poker_launch_cashout` sostituisce (non somma a) l'incasso base al
  lancio di un Poker (`rules/poker.py::_handle_launch_poker`).
- **Preti-3 "carte Gamble associate a qualunque azione":** rimuove, sia
  lato offerta (`rules/economy.py::_player_can_launch_poker_for_action`)
  sia lato validazione del comando (`rules/poker.py::
  _handle_launch_poker`), il vincolo §D2 che il Contact/`action_type`
  della carta debba coincidere con l'azione del round.
- **Politici-3 "2 Ganci a turno":** `PlayerState.extra_action_used_this_turn`
  (bool) è diventato `extra_actions_used_this_turn` (int); il limite,
  normalmente 1, arriva a `rules/skills.py::
  max_link_extra_actions_per_turn` (2 con questa Skill) in tutti e 3 i
  punti di `rules/turn_flow.py` che lo confrontano/incrementano.
- **Artisti-3/Studenti-3 "mandi dal Covo sul Link":** sostituiscono
  (confermato dal game designer, non aggiuntive) l'evoluzione automatica
  esistente rispettivamente della pedina che vende
  (`rules/economy.py::_evolve_sale_link`) e di quella scelta dal
  vincitore di Rissa (`rules/brawl.py`) — una pedina fresca dal Covo
  diventa il Link, la pedina originale resta un Criminal sul campo. Per
  Studenti-3 questo rende l'evoluzione automatica, non più una scelta
  del vincitore. **Fallback corretto (2026-08-02):** se il Covo non ha
  una pedina libera, si manda dal Quartiere come di consueto (come se il
  giocatore non avesse la Skill) invece di saltare l'evoluzione — per
  Studenti-3 questo significa lasciare `link_evolution_done` `False`, che
  fa scattare naturalmente la normale scelta del vincitore
  (`ChooseBrawlLinkEvolution`).

## B) Fasi

I 3 turni si compongono di 4 fasi. **Decisione (2026-07-30):** la partita ha
3 turni completi; i "4 giorni" dell'introduzione sono narrativi, non un
valore di regola.

### B1) Soffiata

Si scopre una carta Retata e il giocatore con il Link più alto con i Preti
sceglie il primo giocatore.

### B2) Azione

Per tre round ciascun giocatore:
- sposta un segnalino Grinta sopra una azione;
- se vuole, gioca una o più carte per potenziare l'azione scelta o per fare
  marketing;
- fa svolgere, a diversi Criminali, 1 azione per ogni Grinta;
- può fare un'azione extra, prima o dopo l'azione principale, spendendo un
  Link;
- scarta fino ad avere al massimo 5 carte in mano.

**Decisione (2026-07-30) — meccanica della Grinta:** ogni giocatore ha 3
segnalini Grinta, di valore fisso 1, 2 e 3 (non una singola pedina che si
sposta su un tracciato). In ciascuno dei suoi 3 round per turno, il
giocatore sceglie **uno** dei 3 segnalini e lo assegna a una delle 6 azioni
(§C1–C6). Il valore del segnalino indica **quante pedine Criminale/Link**
eseguono quell'azione nello stesso round, una ciascuna, ognuna nella
propria posizione: es. "compro con Grinta 3" → si scelgono 3 pedine in
gioco, e ciascuna acquista 1 Dope nel proprio Quartiere. **Decisione
(2026-07-31):** ogni segnalino si usa una sola volta per turno — nei 3
round di un turno si usano i 3 segnalini (valore 1, 2 e 3), uno per round,
in qualunque ordine il giocatore scelga.

**Correzione (2026-08-02):** il valore della Grinta (eventualmente
potenziato da una Skill, vedi §A10) è un **massimo**, non un numero
esatto obbligatorio: il giocatore può far agire da 1 fino a quel valore
di pedine, mai zero (rifiutare l'azione per intero, prima di scegliere
il tipo, resta un'azione a parte). Questo vale per tutte e 6 le azioni
(§C1–C6) e per l'azione extra da Link. Corregge un comportamento
implementato erroneamente come "esattamente il valore della Grinta" fin
dalla Milestone 2.

**Correzione (2026-08-03):** l'azione base scelta con un segnalino Grinta
non può ripetersi nello stesso turno — nei 3 round di un turno il
giocatore sceglie 3 azioni base **diverse** tra le 6 disponibili (§C1–C6),
mai la stessa due volte (es. non è possibile "piazza" al round 1 e di
nuovo "piazza" al round 3). Il vincolo riguarda solo i segnalini Grinta
base: l'azione extra da Link (sopra) è un meccanismo separato e può
liberamente ripetere un'azione già usata nello stesso turno. Non era
implementato affatto prima di questa correzione — un bug, non
un'ambiguità, dato che il motore permetteva la ripetizione senza
segnalarla. Implementato come `PlayerState.action_types_used_this_turn`
(`rules/economy.py::_handle_choose_action_type`, azzerato a inizio turno
in `rules/turn_flow.py::_start_action_phase`).

**Decisione (2026-07-30) — associazione Contact↔Azione:** le carte Cliente
potenziano l'azione base secondo questa mappa, che vale anche per il tipo di
azione extra ottenibile spendendo un Link di quel Contact (il livello del
Link determina la Grinta, cioè quante pedine, dell'azione extra):

| Contact | Azione base potenziata / azione extra da Link |
|---|---|
| Artisti | Comprare Dope, Vendere Dope |
| Studenti | Spostare Criminali |
| Manager | Piazzare Criminali |
| Politici | Corrompere Cops/Feds, Comprare Cops/Feds |
| Preti | Diverso dagli altri — vedi sotto |

I **Preti** sono un caso speciale:
- l'azione extra ottenuta spendendo un Link dei Preti può essere di
  **qualunque tipo tranne Comprare Cops/Feds**;
- le carte Preti non potenziano una singola azione fissa: ciascuna carta è
  associata a una singola azione specifica (diversa carta per carta, a
  copertura di tutte le 6 azioni);
- quando una carta Preti viene giocata, invece di potenziare un'azione
  lancia un Poker per fine round: chi la gioca incassa 3 dollari e mette la
  carta sul banco del Poker (banco che può contenere al massimo 2 carte per
  turno — coerente con `RULES_CANONICAL.md` §D2). Le carte Preti sono quindi
  le "carte Gamble" citate in §A9/§D2.

### B3) Poker

Alla fine di ogni turno si risolvono le carte Poker, se giocate, e si
assegna il primo giocatore del turno seguente.

### B4) Resa Dei Conti

Si verifica quali giocatori sono caduti nella Retata e macchiano la loro
reputazione.

## C) Azioni

**Decisione (2026-08-16) — Quartieri nascosti:** 5 dei 10 Quartieri
iniziano coperti/nascosti (`data/board.json`'s `revealed: false`, uno per
Contact). Un Quartiere nascosto **non può mai essere scelto** per Piazzare
o Spostare (§C1/§C2 sotto) — l'unico modo di finirci è essere il
Criminale sconfitto in Rissa mandato lì dal vincitore (§D1,
`ChooseBrawlRelocationDestination`), che lo scopre (`hood.revealed =
True`) e da quel momento diventa un Quartiere normale, piazzabile e
raggiungibile come tutti gli altri.

### C1) Piazzare Criminali

- Si piazza un Criminale dal Covo in un Quartiere **già scoperto**.
- Si pagano 2 dollari.
- Si pesca una carta relativa al Quartiere.

### C2) Spostare Criminali

- Un Criminale si sposta in un Quartiere adiacente **già scoperto** o nel Den.
- Si pesca una carta del Quartiere o a scelta, nel Den.
- Non si può spostare lo stesso Criminale più volte nello stesso turno.

### C3) Acquistare Merce

- Si sceglie un Criminale **o un Link** (decisione 2026-08-15, vedi sotto)
  in un Quartiere dove c'è almeno una Merce e non ci sono Cops.
- Si decide se giocare una carta per fare Marketing. Per ogni Stonk si può
  modificare di 1 il prezzo della merce prima o dopo l'acquisto. (Gli Stonk
  vengono distribuiti a piacere tra le merci acquistate nel turno)
- Si paga il Prezzo della Merce e il Prezzo della Merce sale di 1.
- Si sposta la Merce dal Quartiere nel Covo.
- Se non restano Merci nel Quartiere, questo viene ricaricato di 3 merci ed
  entra in gioco un Cops.

**Acquisto a pacchetto:** Se si comprano più merci nello stesso Quartiere
(con più Criminali) l'aumento dei prezzi si applica alla fine.

**Decisione (2026-08-15) — presenza abilitante di un Link:** un Link conta
come presenza in **entrambi** i Quartieri del proprio Contact (§11.6),
esattamente come già per la corruzione di Cops/Feds. A differenza di
Vendere Merce (§C4), qui serve una scelta esplicita di **quale** dei due
Quartieri, perché ciascuno ha scorta e prezzo indipendenti — se il Link ha
scorta legale in entrambi, il giocatore sceglie da quale comprare
(`BuyDope.purchases: tuple[(pawn_id, hood_id), ...]`).

### C4) Vendere Merce

- Si sceglie un Criminale **o un Link** (decisione 2026-08-15, vedi sotto)
  in un Quartiere e il relativo Punto di Vendita non occupato da Feds.
- Si decide se giocare una carta per fare Marketing. Per ogni Stonk si può
  modificare di 1 il prezzo della merce prima o dopo la vendita. (Gli Stonk
  vengono distribuiti a piacere tra le merci vendute nel turno)
- Si incassa il Prezzo della Merce e il Prezzo della Merce scende di 1.
- Si sposta la Merce dal Covo nel Punto di Vendita.
- Il Criminale che ha venduto può evolvere in un Link. **Decisione
  (2026-08-02):** su una vendita **singola** (1 unità) è una vera scelta
  SI/NO del giocatore, offerta dopo la vendita
  (`EvolveSaleLink(evolve: bool)`, `ActiveStep.
  WAITING_FOR_LINK_EVOLUTION_CHOICE`) — non automatica come
  implementato erroneamente in Milestone 3.
- Se il Punto di Vendita si riempie (3 Merci) viene svuotato ed entra in
  gioco un Feds.

**Vendita a pacchetto:** Se si vendono più merci dallo stesso Quartiere allo
stesso Punto di Vendita la riduzione dei prezzi si applica alla fine. Si
prende un solo Link del livello pari al numero di merci vendute — questo
caso **resta automatico**, come dice esplicitamente il testo ("si
prende"), a differenza della vendita singola sopra.

**Decisione (2026-08-15) — presenza abilitante di un Link:** un Link conta
come presenza in entrambi i Quartieri del proprio Contact (§11.6), **senza
bisogno di scegliere quale**: i Punti di Vendita sono per Contact, non per
Quartiere (§22.6, due Merci accettate per Contact), quindi i due
Quartieri di uno stesso Contact danno sempre accesso agli stessi 2 Spot —
a differenza di Comprare Merce (§C3), che invece resta per Quartiere.
**PROVVISORIO** (`RULES_PENDING.md` #22): una vendita fatta interamente da
pedine Link (nessun Criminale tra i venditori a quello Spot) non innesca
mai l'offerta/evoluzione a Link — il regolamento descrive solo "il
Criminale che ha venduto", mai un Link che evolve ulteriormente.

### C5) Corrompere Cops e Feds

- Un Criminale/Link/Rat può corrompere un Cops o un Feds pagando 1 dollaro
  per ciascuna azione che gli fa compiere, scegliendo liberamente quante
  (da 1 a 3, mai la stessa due volte) e fermandosi quando vuole — stesso
  costo per Cops e Feds. **Decisione (2026-08-15)**, sostituisce il costo
  fisso $2/$3 per esattamente 2 azioni: vedi `RULE_CHANGELOG.md`.
- Un Rat può corrompere Cops ovunque.
- Un Cops corrotto può compiere, tra le seguenti:
  - spostarsi in un Quartiere adiacente;
  - arrestare un Criminale a scelta nel Quartiere;
  - requisire una Merce nel Quartiere (Prezzo della Merce sale di 1).
- Un Feds corrotto può compiere, tra le seguenti:
  - spostarsi in un Punto di Vendita adiacente;
  - arrestare il Link di livello minore;
  - requisire una Merce nel Punto di Vendita (Prezzo della Merce sale di 1).
- Criminali e Link arrestati entrano in Commissariato nella prima posizione
  disponibile e diventano Rats.
- Le merci requisite entrano in Commissariato nella prima posizione
  disponibile.

**Decisioni (2026-07-30):**
- le azioni diverse della corruzione possono avere lo stesso bersaglio e
  sono risolte in sequenza: un'azione successiva agisce sullo stato
  prodotto dalla precedente (es. sposta poi arresta nel nuovo Quartiere);
- la parità di livello minimo tra Link per l'arresto del Feds non può
  verificarsi (vedi §A5: un solo Link per livello per Contact), quindi non
  serve una regola di scelta.

### C6) Comprare Cops e Feds

- I Criminali possono comprare Cops e Feds.
- Un Cops/Feds può essere comprato da Criminali/Link:
  - in un Quartiere/Punto di Vendita e piazzato nel proprio Covo;
  - nel Covo di un giocatore presente nel Quartiere e piazzato nel
    Quartiere (anche se stessi).
- Per comprare bisogna pagare 7 dollari.
- Il giocatore che perde un Cops/Feds dal Covo guadagna 7 dollari.
- Un Cops/Feds comprato, può essere scartato per sbirciare una delle retate
  future.

**Decisione (2026-07-30):** il proprietario non può opporsi alla vendita del
proprio Cops/Feds; se il compratore soddisfa i requisiti (presenza, 7
dollari), l'operazione va sempre a buon fine.

## D) Altre Regole

### D1) Fare Rissa

- La Rissa scatta quando si sposta il quinto Criminale in un Quartiere.
- Partecipano alla Rissa tutti i giocatori che hanno almeno un Criminale nel
  Quartiere.
- A partire dal giocatore alla sinistra di chi ha iniziato la Rissa, i
  partecipanti possono giocare una carta coperta (Pistole).
- Si rifà il giro scoprendo la carta e assegnando le Pistole a sé stessi
  (aggiunge Pistole) o a un altro partecipante (toglie Pistole).
- Si sommano Criminali + Links + Pistole.
- Si determinano vincitore e sconfitto.
- In caso di pareggio per determinare il vincitore, vince chi ha giocato
  meno Pistole, il giocatore che ha provocato la Rissa, il primo giocatore,
  o seguenti.
- In caso di pareggio per determinare lo sconfitto, perdono tutti.
- Il vincitore:
  - ruba 2 dollari o 1 carta ad ogni sconfitto;
  - può mandare un suo Criminale dal Quartiere sul primo Link del Cliente;
  - manda il Criminale sconfitto in un Quartiere inesplorato (si prende la
    relativa carta), se c'è, o nel Covo.
- Dopo una rissa un Cops entra in gioco nel Quartiere.

**Decisione (2026-07-30):** la forza (Criminali + Links + Pistole) può
scendere sotto zero; è una somma algebrica senza troncamento a zero.

**Decisione (2026-07-31):** un Quartiere non è mai realmente pieno perché
è lo spostamento (non il piazzamento) del quinto Criminale a far scattare
subito la Rissa, che sposta via almeno un Criminale sconfitto (il
vincitore può diventare Link). Piazzare un Criminale non fa mai scattare
la Rissa e quindi **non può mai** portare un Quartiere al conteggio che la
scatenerebbe: un piazzamento che porterebbe un Quartiere a quel conteggio
è illegale.

**Decisioni (2026-08-01), Milestone 4:**
- **Assegnazione Pistole:** tutte le Pistole della carta coperta rivelata
  da un partecipante vanno a un solo bersaglio (sé stesso o un altro
  singolo partecipante), non possono essere distribuite su più bersagli
  dalla stessa carta.
- **Ricompensa del vincitore:** la scelta fra 2 dollari o 1 carta è presa
  indipendentemente per ciascuno sconfitto (non un'unica scelta valida
  per tutti gli sconfitti).
- **Quartiere inesplorato di destinazione:** se disponibile più di un
  Quartiere inesplorato adiacente/raggiungibile, sceglie il vincitore.
- **Tie-break finale (vincitore):** "il primo giocatore, o seguenti"
  significa l'ordine di rotazione dei turni a partire da
  `first_player_id` (la stessa logica di `rules/turn_flow.py`
  `_rotation_order`), applicato fra i soli partecipanti in parità dopo i
  criteri precedenti (meno Pistole giocate, poi chi ha innescato la
  Rissa).
- **Criminali spostati via da uno sconfitto:** una sola pedina fra quelle
  fisicamente presenti nel Quartiere viene mandata via, anche se lo
  sconfitto ne ha più di una lì (contribuiscono comunque alla Forza); le
  altre restano nel Quartiere.
- **Partecipanti alla Rissa:** partecipa solo chi ha almeno 1 pedina
  Criminale fisicamente nel Quartiere che raggiunge la soglia. I Link
  presso il Contact del Quartiere si sommano alla Forza di un
  partecipante già presente fisicamente — tutti e 3 i livelli, se il
  giocatore li possiede lì — ma un giocatore che ha solo un Link lì
  (nessun Criminale fisico) non partecipa alla Rissa.
- **Pistole:** ogni carta coperta può valere da 0 a 4 Pistole a seconda
  della carta giocata; non esiste un tetto fisso di Pistole per Rissa.

### D2) Scommettere

- Le carte Gamble permettono di associare ad una azione base il lancio di
  una partita a Poker per fine turno. (Max 2 per turno)
- Il giocatore che lancia una partita posiziona la carta sul tabellone,
  incassa 3 dollari e manda un Criminale dal Covo nel Den, se c'è posto,
  pescando una carta.
- Alla fine del turno, a partire dal primo giocatore, ogni giocatore può
  puntare su 2, 1 o zero Poker in base a quanti Gamblers ha nel Den. Per
  puntare, posiziona una Chip sulle carte Poker su cui intende giocare.
- Finito il giro di puntate si risolvono le partite: a partire dalla prima
  carta Poker giocata, i giocatori che hanno puntato rivelano assieme una
  carta.
- Si vince nell'ordine con 5 colori uguali/diversi > Poker > Full > Tris >
  Doppia coppia > Coppia.
- In caso di pareggio i colori vincenti sono nell'ordine: arancione > grigio
  > blu > verde > rosa.
- In caso di ulteriore pareggio le Chip restano in gioco e si sommano alla
  posta del Poker successivo.
- In caso di vittoria, il vincitore:
  - incassa 2 dollari per ogni Chip;
  - mette una sua Chip nel Covo;
  - evolve un Gambler in un Link dei Preti.
- Gli sconfitti mandano il proprio Gambler in prigione.
- Un giocatore che ha già 3 Chip nel Covo, può giocare a poker rimuovendole
  dal Covo.
- Un giocatore può giocare una sola carta Gamble per Round.

**Decisione (2026-07-30) — costruzione della mano da 5 simboli:** esiste un
banco comune di 3 simboli, creato con carte Gamble, tutte e sole quelle dei
Preti. Ciascun giocatore che ha puntato aggiunge i propri 2 simboli
(rivelando la propria carta) al banco comune, per un totale di 5 simboli da
valutare secondo il ranking sopra descritto.

**Decisioni (2026-08-01), Milestone 4 — Poker:**

- **Chip:** ogni giocatore ha 3 Chip proprie fuori dal Covo. Ne usa una per
  ogni puntata; se vince la mette nel Covo (bancata, conta per il punteggio
  di fine partita); se perde torna alla riserva fuori dal Covo. Quando tutte
  e 3 le Chip di un giocatore sono nel Covo, può continuare a puntare
  prendendole dal Covo (nessun limite di "Chip disponibili" blocca mai una
  puntata: il vincolo reale è solo il numero di Gambler nel Den, come da
  regolamento). Implementazione: `base_inventory.poker_chip_count` sale di 1
  a ogni vittoria (fino al tetto di 3) e non scende mai per una sconfitta.
- **Carta rivelata per puntare:** indipendente dal limite "1 carta Gamble
  per Round" (che regola solo il lancio di una nuova partita). Rivelare una
  carta per aggiungere i propri 2 simboli al banco è un'azione distinta, non
  conta come carta Gamble giocata.
- **Auto-puntata:** chi lancia una partita può anche puntare sulla propria
  partita, con un proprio Gambler nel Den.
- **Den pieno al lancio:** il lancio avviene comunque (incasso di 3 dollari,
  carta scartata), semplicemente nessun nuovo Gambler entra nel Den in quel
  momento se non c'è posto — coerente con "se c'è posto" già presente nel
  testo.
- **Innesco del lancio (corretto 2026-08-01):** una carta Gamble (Preti) può
  lanciare una partita solo in un round in cui il giocatore esegue l'azione
  indicata dall'`action_type` di quella stessa carta — "si associa ad
  un'azione base". La scelta (lanciare o no) è offerta subito dopo aver
  scelto il tipo di azione del round (`ChooseActionType`), prima della
  selezione dei bersagli, e vale sia per l'azione principale sia per
  un'azione extra da Link con lo stesso `action_type` (confermato: "anche
  con l'azione extra da Link"). Non è più un'offerta indipendente prima
  della Grinta. Rimangono validi gli altri vincoli: al massimo 1 carta
  Gamble giocata per Round e al massimo 2 partite lanciate per turno.
- **Fase di puntata:** avviene una sola volta a fine turno (`POKER_PHASE`),
  per tutte le partite lanciate quel turno insieme, a partire dal primo
  giocatore. Ogni giocatore con almeno 1 Gambler nel Den fa un'unica scelta:
  su quali partite aperte punta (al massimo tante quante i propri Gambler
  nel Den, fino al massimo di 2 partite esistenti).
- **Risoluzione:** le partite si risolvono in ordine di lancio. Una partita
  senza alcuna puntata si estingue senza effetti. Per ogni partita con
  puntate, ciascun puntatore rivela una carta dalla mano *non Preti/Gamble*
  (una carta Gamble non ha simboli Poker propri, solo il banco della carta
  di lancio li ha) — indipendente dal limite di 1 carta Gamble giocata per
  Round; la mano di ciascuno è banco (3 simboli) + i propri 2 simboli.
- **Classifica e tie-break (algoritmo):** confermato dal game designer che
  il tie-break fra mani della stessa combinazione guarda prima il colore
  "dominante" (quello del gruppo ripetuto: il 4 nel Poker, la Tripla nel
  Full/Tris, la Coppia più alta nella Doppia Coppia, la Coppia nella
  Coppia); se anche questo pareggia, si confrontano i simboli restanti (non
  dominanti), in ordine di posizione nella classifica colori
  (arancione > grigio > azzurro > verde > rosa). **Decisione (2026-08-02):**
  "5 uguali" non può mai verificarsi — il banco non ha mai 3 simboli
  identici, quindi nessuna mano di 5 simboli (banco + carta rivelata) può
  mai essere monocolore. La categoria di vertice della classifica è quindi
  sempre "5 diversi" (tutti e 5 i colori compaiono, sempre lo stesso
  multiset), sempre in parità totale fra le mani che la raggiungono —
  nessun confronto ulteriore possibile a quella categoria.
- **Ulteriore pareggio (jackpot):** se anche dopo aver confrontato tutti i
  simboli la parità resta (mani identiche), le Chip dei pareggiati restano
  in gioco: si sommano al piatto (`PokerMatchState.jackpot_chips`) della
  prossima partita lanciata da chiunque, a beneficio di chi la vincerà,
  indipendentemente da chi erano i pareggiati originali (il campo è un
  contatore, non per-giocatore) — PROVVISORIO su questo dettaglio, il
  regolamento dice solo "le Chip restano in gioco". I giocatori pareggiati
  in testa non sono né vincitori né sconfitti: il proprio Gambler resta nel
  Den, la propria Chip non si sposta (né al Covo né alla riserva).
- **Sconfitti:** ogni puntatore il cui punteggio non è tra i massimi (dopo
  ogni criterio di tie-break) perde: il proprio Gambler viene arrestato
  (stessa meccanica di `jail.arrest_pawn`, incluso il possibile innesco
  dell'Evasione se riempie il sesto slot). **Confermato (2026-08-02):** la
  Jail non è mai realmente piena al momento dell'arresto — il 6° Rat
  innesca l'Evasione immediatamente, svuotando tutti gli slot prima che
  quello stesso arresto ritorni; con più sconfitti nello stesso
  turno/partita, ciascuno viene processato in sequenza (mai un controllo
  di capienza unico fatto prima di tutti), quindi il caso "Jail piena
  blocca un arresto" non si presenta mai nella pratica.

### D3) Marketing

Quando si compra o vende si può scartare una carta per usare gli Stonk. Per
ogni Stonk si può modificare di 1 il prezzo di una delle merci in acquisto o
vendita, prima o dopo lo svolgimento dell'azione. Gli Stonk vengono
distribuiti a piacere tra le merci trattate nel turno.

**Decisioni implementative, Milestone 5 Stage 4c-bis (2026-08-02, corrette
lo stesso giorno dopo un chiarimento del game designer):**

- **"Prima o dopo" = prima o dopo l'intera azione** (non il solo step di
  prezzo automatico, come implementato in un primo momento): Marketing
  "prima" è offerto subito dopo `ChooseActionType`, prima della selezione
  bersagli — qualunque tipo di Merce, dato che il pacchetto non esiste
  ancora (`player.marketing_offer_is_pre`, stesso schema di stash-e-
  ripristino di `poker_launch_return_step` per il lancio Poker). Marketing
  "dopo" resta offerto in coda a `BuyDope`/`SellDope`, dopo che il
  pacchetto e il suo step di prezzo automatico si sono già risolti
  interamente, ristretto alle Merci effettivamente trattate nel pacchetto
  (`player.marketing_eligible_dope_types`). Un giocatore normale ottiene
  **l'uno o l'altro, mai entrambi** nella stessa azione — se rifiuta o non
  usa "prima", gli viene offerto "dopo"; se usa "prima", "dopo" non viene
  più offerto (salvo Manager-3, sotto). Il pagamento/incasso di ogni
  singola unità nel pacchetto riflette quindi un eventuale Stonk "prima"
  (il prezzo era già cambiato quando il pacchetto si risolve), mai uno
  "dopo" (già completato).
- **Quale carta se il giocatore ne ha più di una idonea — RISOLTO
  (2026-08-15, `RULES_PENDING.md` #21):** scelta reale del giocatore, non
  un auto-pick della carta con più Stonk. Con 2+ carte idonee viene
  offerto un sotto-passo dedicato "scegli la carta" (decision_type
  `choose_marketing_card`) prima dell'allocazione degli Stonk; con
  esattamente una carta idonea non c'è nulla da scegliere, si procede
  come prima (`application/legal_actions.py::_marketing_decision`).
- **Direzione dello Stonk:** libera per il giocatore, come le Pistole
  già liberamente assegnabili in Rissa.
- Manager-3 "Applichi Stonk 2 volte" (§A10): se il giocatore ha usato
  Marketing "prima" dell'azione, le stesse allocazioni si ripetono
  automaticamente "dopo" — senza scartare una nuova carta, senza una nuova
  decisione (`rules/skills.py::marketing_applies_both_timings`,
  `rules/economy.py::_finish_buy_or_sell_package`). Se non ha usato
  "prima", non c'è nulla da replicare: ottiene la normale offerta "dopo"
  come chiunque altro.

### D4) Retate

- A inizio del turno viene scoperta una carta Retata.
- Il giocatore che ha il Link di più alto livello con i Preti (ne c'è
  almeno uno) decide il primo giocatore e quindi le squadre che
  affronteranno la Retata: il primo e il quarto giocatore vs il secondo e
  il terzo. **Decisione (2026-07-31):** se in quel turno nessun giocatore
  ha un Link ai Preti, resta primo giocatore chi lo era nel turno
  precedente (nessun cambio).
- Alla fine del turno i giocatori che cadono nella Retata macchiano la loro
  reputazione.
- La prima Retata macchia 1 Reputazione, la seconda 2, la terza 3.
  **Decisione (2026-07-31):** questi valori sono **a testa**: ogni
  giocatore che cade nella Retata macchia quel numero di propri segnalini
  R (1 per la prima Retata persa in partita, 2 per la seconda, 3 per la
  terza) — vedi §D5 per il collegamento tra REP e segnalini R dei Job.
  **Decisione (2026-07-31):** se un giocatore non ha abbastanza segnalini R
  non macchiati da girare (es. dovrebbe macchiarne 3 ma ne ha solo 1
  piazzato, o zero), semplicemente non macchia quelli che non può — nessun
  effetto sostitutivo o penalità aggiuntiva.

**Decisione (2026-07-31) — le 7 carte Retata (fonte: `RET_V8.pdf`):**
ciascuna carta dice "Sfugge dalla Retata chi ha: ...":

| # | Criterio di fuga |
|---|---|
| 1 | Più Ganci (Link) coi Clienti |
| 2 | Più Criminali in prigione (Rats) |
| 3 | Meno valore di Merci |
| 4 | Vinto più Poker |
| 5 | Comprato più Cops |
| 6 | Più dollari |
| 7 | Più Criminali nei Quartieri |

**Decisione (2026-07-31) — applicazione alla struttura a squadre:** per
ogni carta si sommano i valori del criterio dei due compagni di squadra, e
si confrontano le due squadre (1°+4° vs 2°+3°). La squadra con la somma
più alta (o più bassa, per la carta "meno valore di Merci") sfugge alla
Retata; l'altra squadra cade e ciascun componente macchia la propria
reputazione. **In caso di parità tra le due squadre, cadono nella Retata
tutti e 4 i giocatori** (nessuno sfugge).

**Decisioni (2026-08-02), Milestone 5 — Retate:**

- **"Decide il primo giocatore e quindi le squadre" è un'unica scelta:**
  scegliere il primo giocatore della Retata **è** scegliere il
  `first_player_id` del turno (già usato per l'ordine dell'Action Phase),
  non un concetto separato — implementato come `ChooseRaidFirstPlayer`,
  offerto a Tip-off subito dopo la rivelazione della carta Retata.
- **Nessun pareggio possibile per "Link più alto ai Preti":** poiché i 3
  slot Link per Contact sono condivisi fra tutti i giocatori (§A5,
  corretto 2026-08-01), può esistere al più una pedina al livello
  massimo per un dato Contact in un dato momento — non serve alcun
  tie-break per questa scelta.
- **Retata "comprato più Cops" conta anche i Fed:** vedi §A10, stesso
  contatore cumulativo del Job "Compra 1 Cop/Fed".
- **Valutazione automatica:** `rules/raids.py::resolve_raid` viene
  chiamata automaticamente a fine turno (Showdown Phase), nessun comando
  del giocatore la innesca.
- **Quale segnalino R macchiare quando un giocatore ne ha più di uno
  pulito:** indifferente (valgono tutti 2 punti allo stesso modo prima di
  essere macchiati) — scelto deterministicamente il primo in ordine sul
  tabellone, stesso precedente di altre scelte provatamente ininfluenti
  nel motore (es. quale pedina evolve in Link su una vendita a pacchetto).

### D5) Macchiare REP

- Una REP macchiata viene indicata girando il token sul tabellone. Quella
  REP varrà 1 solo punto a fine partita.
- Una REP può venire macchiata a seguito di una retata persa.

**Decisione (2026-07-31):** i token REP sono gli stessi segnalini R
piazzati sul tracciato dei Job al momento del completamento (§A10): non
esiste un pool di REP separato. Macchiare una REP significa girare sul
retro uno dei propri segnalini R già piazzati (quindi un giocatore può
macchiare una REP solo se ne ha già almeno una non macchiata, cioè solo se
ha completato almeno un Job). Un segnalino R sul dritto vale 2 punti a
fine partita, girato sul retro (macchiato) vale 1 punto.
- I giocatori con 2 dollari o meno possono macchiarsi una REP per incassare
  5 dollari.
- Le REP macchiate non possono essere ripristinate.

**Decisione (2026-08-02):** questa scelta volontaria (`StainReputationForMoney`)
è offerta agli stessi due punti per round già usati dall'azione extra da
Link (`WAITING_FOR_STAIN_FOR_CASH_OFFER`, prima e dopo l'azione
principale), sempre declinabile — scelta implementativa autonoma, il
regolamento non specifica un momento preciso nel round.

### D6) Condizione di Vittoria

A fine partita il tracciato dei soldi si trasforma nel tracciato punti:

- i birilli vengono spostati a inizio track nell'ordine in cui sono, nelle
  posizioni 1, 2, 3, 4. Nei pareggi si prende la posizione più in basso;
- si assegnano 2 punti per ogni REP o 1 per ogni REP macchiata;
- si assegna un punto per ogni maggioranza presso i clienti (Criminali
  valgono 1, Link 2), i pareggi si annullano;
- si assegna un punto per ogni 3 fiches, anche miste, nel Covo;
- si assegna un punto per ogni Skill.

Vince chi ha più punti. In caso di pareggio vince chi ha più REP non
macchiate. In caso di ulteriore pareggio la vittoria è condivisa.

**Decisione (2026-07-30/31):** la posizione sul tracciato denaro assegna
punti propri, da sommare a REP/maggioranze/chips/skill, secondo questa
tabella:

| Posizione (per denaro, dalla più alta) | Punti |
|---|---|
| 1ª | 4 |
| 2ª | 3 |
| 3ª | 2 |
| 4ª | 1 |

In caso di parità di denaro tra due o più giocatori, tutti i pareggiati
prendono il valore più basso tra le posizioni che occuperebbero. Esempio: un
giocatore da solo in 1ª posizione prende 4 punti; se gli altri due
giocatori sono a pari merito per la 2ª/3ª posizione, prendono entrambi 2
punti (il valore della 3ª, non della 2ª); il quarto giocatore prende 1
punto.

**Decisioni implementative (2026-08-02), Milestone 5 — punteggio finale:**

- **Calcolo automatico:** `rules/scoring.py::compute_final_score` viene
  chiamata automaticamente da `rules/turn_flow.py::_end_turn` quando si
  raggiunge l'ultimo turno configurato, attraversando la fase
  `END_GAME_SCORING` (che calcola ed emette `FinalScoreCalculated`) prima
  di passare a `FINISHED` (`GameFinished`, ora con `winner_ids`) — nessun
  comando del giocatore la innesca.
- **Maggioranza per Contact:** presenza pesata per Criminali (peso 1) più
  Link (peso 2) del giocatore presso quel Contact; se un solo giocatore
  ha la presenza massima (>0) ottiene il punto, altrimenti (pareggio o
  nessuna presenza) nessuno lo ottiene. L'elenco completo dei Contact è
  letto direttamente dalla board (ogni Contact ha almeno un Hood
  ordinario), non richiede dati esterni.
- **`tie_break_clean_reputation`:** campo separato dal punteggio REP
  pulite (che è già ×2 e sommato al totale) — memorizza il conteggio
  grezzo dei segnalini R non macchiati, usato solo per il tie-break finale.

## E) Setup

Sezione non presente nel documento `how_to_play_v056` originale; dati
forniti direttamente dal game designer in chat il 2026-07-30.

### E1) Denaro e pedine

- Ogni giocatore parte con **15 dollari**.
- Ogni giocatore ha **10 pedine Criminale** in totale (nel Covo a inizio
  partita).

### E2) Carte iniziali

Si forma un mazzetto con 3 carte di ciascun Contact (mescolate insieme): 5
Contact × 3 carte = **15 carte** (vedi §F1 per l'elenco dei 5 Contact).
Ogni giocatore pesca **3 carte** da questo mazzetto: con 4 giocatori, 12
carte vengono distribuite e le **3 carte avanzate** tornano nei rispettivi
mazzi dei Contact di provenienza.

### E3) Dope iniziali nel Covo

Ogni giocatore parte con **2 Dope** nel Covo, assegnate per ordine di seggio
(seat 1–4):

| Seggio | Dope iniziali |
|---|---|
| 1 | Rana + Polpo |
| 2 | Camaleonte + Polpo |
| 3 | Rana + Gufo |
| 4 | Camaleonte + Gufo |

**Decisione (2026-07-31):** Chips Cops e Poker nel Covo iniziano a 0 (nessun
Cops/Feds sulla mappa, nessuna partita a Poker in corso all'inizio).

### E4) Hoods e mercato iniziale

- Ci sono **5 Quartieri scoperti** a inizio partita, uno per Cliente,
  ciascuno con **3 Dope** nel proprio mercato (i tipi esatti dipendono dal
  Cliente — vedi sezione Mappa, ancora da fornire).
- Ci sono **5 Quartieri coperti**, inizialmente vuoti/non rivelati.
- Un Quartiere coperto si attiva quando un Criminale sconfitto in una Rissa
  viene mandato lì (vedi `RULES_CANONICAL.md` §D1, "Quartiere inesplorato"):
  si rivela flippando una **tile rotonda** posta sul Quartiere, che indica
  quante Dope caricare nel mercato (1–3) ed eventualmente se entra un Cops.

### E5) Cops e Feds iniziali

Nessun Cops o Feds è presente sulla mappa a inizio partita; entrano solo
durante il gioco secondo le regole di §A6.

### E6) Primo giocatore

Il primo giocatore del turno 1 è scelto **casualmente**. Dal turno 2 in poi
si applica la regola di §B1/§D4 (Link più alto con i Preti; se nessuno ha
un Link ai Preti, resta primo giocatore chi lo era nel turno precedente).

### E7) Piazzamento iniziale dei Criminali

Ogni giocatore piazza **3 dei suoi 10 Criminali** durante il setup (gli
altri 7 restano nel Covo). Per ciascuna delle 3 carte pescate in E2, si
piazza un Criminale nel Quartiere scoperto del Contact corrispondente a
quella carta. Esempio: 2 carte "Manager" + 1 carta "Preti" → 2 Criminali nel
Quartiere scoperto del Manager, 1 Criminale nel Quartiere scoperto dei
Preti. *(Conferma che Preti, e presumibilmente Politici, hanno anch'essi un
Quartiere scoperto con mercato proprio tra i 5 iniziali — da confermare con
la sezione Mappa.)*

## F) Mappa

Dati forniti dal game designer in chat il 2026-07-31.

### F1) Quartieri e Contact

Ogni Contact ha esattamente 2 Hoods: uno **scoperto** (mercato attivo fin
dall'inizio) e uno **coperto** (si rivela con una tile rotonda quando un
Criminale sconfitto in Rissa vi viene mandato, vedi §E4).

| Hood | Contact | Stato iniziale | Dope iniziali |
|---|---|---|---|
| Q1 | Artisti | Scoperto | 3× Rana |
| Q2 | Artisti | Coperto | — (tile da rivelare) |
| Q3 | Studenti | Scoperto | 3× Gufo |
| Q4 | Studenti | Coperto | — (tile da rivelare) |
| Q5 | Manager | Scoperto | 3× Rana |
| Q6 | Manager | Coperto | — (tile da rivelare) |
| Q7 | Preti | Scoperto | 3× Camaleonte |
| Q8 | Preti | Coperto | — (tile da rivelare) |
| Q9 | Politici | Scoperto | 3× Polpo |
| Q10 | Politici | Coperto | — (tile da rivelare) |

### F2) Adiacenze

Confermato dal game designer il 2026-07-31: Q2↔Q6 e Q5↔Q9 sono adiacenti in
entrambi i versi (le liste originali erano incomplete su questi due punti,
ora corrette qui sotto).

**Decisione (2026-08-02):** Q3 e Q6 **non sono adiacenti** — l'asimmetria
originaria (Q6 elencava Q3, Q3 non elencava Q6) rilevata da
`tools/validate_data.py` non era un'omissione da correggere per simmetria,
ma un errore nella lista di Q6: `data/board.json` ora rimuove Q3 dagli
adiacenti di Q6 invece di aggiungere Q6 agli adiacenti di Q3.

| Hood | Adiacenti |
|---|---|
| Q1 | Q2, Q3 |
| Q2 | Q1, Q3, Q4, Q6 |
| Q3 | Q1, Q2, Q4, Q5 |
| Q4 | Q2, Q3, Q5, Q6, Q7 |
| Q5 | Q3, Q4, Q7, Q9, Q10 |
| Q6 | Q2, Q4, Q7, Q8 |
| Q7 | Q4, Q5, Q6, Q8, Q9 |
| Q8 | Q6, Q7, Q9 |
| Q9 | Q5, Q7, Q8, Q10 |
| Q10 | Q5, Q9 |

### F3) Tile dei Quartieri coperti

Dati forniti dal game designer in chat il 2026-07-31.

Ci sono **5 tile rotonde**: `1`, `2`, `2c`, `3`, `3c`. Il numero indica
quante Dope caricare nel mercato del Quartiere all'attivazione; il
suffisso `c` indica che entra anche un Cops.

Setup (fase E, da eseguire con l'RNG deterministico della partita):
1. Si prendono 5 pezzi di Dope: **2 Camaleonte + 1 Rana + 1 Polpo + 1
   Gufo**.
2. Le 5 tile vengono associate casualmente a questi 5 pezzi di Dope,
   formando 5 coppie (tipo di Dope, tile).
3. Le 5 coppie vengono assegnate casualmente, una ciascuno, ai 5 Quartieri
   coperti (Q2, Q4, Q6, Q8, Q10).

Attivazione: quando un Criminale sconfitto in una Rissa viene mandato in un
Quartiere coperto non ancora rivelato (§D1, §E4), si gira la sua tile e si
aggiungono Dope del tipo assegnato fino al numero indicato dalla tile (1,
2 o 3); se la tile ha il suffisso `c`, entra anche un Cops nel Quartiere.

### F4) Spots dei Contact

Dati forniti dal game designer in chat il 2026-07-31. I 10 Spot (2 per
Contact) sono disposti **in fila**, nell'ordine Artisti → Studenti →
Manager → Preti → Politici, ciascuno adiacente solo al proprio vicino
immediato nella fila (es. Artisti-2° confina con Studenti-1°, che confina
con Studenti-2°, ecc.). **Decisione (2026-07-31):** la fila è aperta, non un
anello — Artisti-1° e Politici-2° sono i due estremi e non sono adiacenti
tra loro.

| # | Spot | Contact | Dope accettata | Adiacenti nella fila |
|---|---|---|---|---|
| 1 | Artisti-1 | Artisti | Camaleonte | Artisti-2 |
| 2 | Artisti-2 | Artisti | Polpo | Artisti-1, Studenti-1 |
| 3 | Studenti-1 | Studenti | Camaleonte | Artisti-2, Studenti-2 |
| 4 | Studenti-2 | Studenti | Rana | Studenti-1, Manager-1 |
| 5 | Manager-1 | Manager | Gufo | Studenti-2, Manager-2 |
| 6 | Manager-2 | Manager | Camaleonte | Manager-1, Preti-1 |
| 7 | Preti-1 | Preti | Rana | Manager-2, Preti-2 |
| 8 | Preti-2 | Preti | Polpo | Preti-1, Politici-1 |
| 9 | Politici-1 | Politici | Rana | Preti-2, Politici-2 |
| 10 | Politici-2 | Politici | Gufo | Politici-1 |

Ogni Contact ha quindi due Spot con Dope accettata diversa tra loro (es.
Artisti: Camaleonte e Polpo).

## Stato

Sezioni A–D trascritte integralmente dal documento fornito il 2026-07-30.
Le ambiguità di risoluzione (interazioni tra regole) sono state chiuse lo
stesso giorno con decisioni del game designer, annotate inline come
"Decisione (2026-07-30)" nelle sezioni sopra; dettagli completi in
`RULE_CHANGELOG.md`.

Nessuna sezione di Setup dettagliato, mappa, Contacts/Spots, dataset carte,
Jobs/Skills, carte Retata o valori di punteggio del tracciato denaro era
presente nel documento ricevuto: questi contenuti restano da acquisire e
sono tracciati in `RULES_PENDING.md`.
