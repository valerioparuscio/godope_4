# Revisione delle 100 carte (Excel v11 ITA-EN) — 2026-10-15

Confronto tra `docs/cards/carte_azioni_v11_ITA-EN.xlsx` e `data/customer_cards.json` (le carte attuali). **Nessun codice è stato cambiato**: questo è l'elenco di ciò che va deciso e fatto.

Riepilogo: **43 invariate**, **8 modificate**, **41 nuove**, **8 doppioni** (stesso effetto di un'altra carta, titolo diverso).

| # | Mazzo | Titolo | Azione | Testo nuovo | Stato | Vecchia (effetto) | Nota |
|---|---|---|---|---|---|---|---|
| 01 | Artisti | TRY AGAIN | Acquistare | Manda in Jail 1 Criminale che ha acquistato | Invariata | #001 self_arrest_after_action |  |
| 02 | Artisti | SCAM | Vendere | Vendi al prezzo della merce più cara | Invariata | #002 price_at_extreme |  |
| 03 | Artisti | DIRTY BADGE | Acquistare | Acquista anche dove ci sono Cops | NUOVA |  | acquisti anche dove ci sono Cops (ignora il blocco del Cop) |
| 04 | Artisti | FAST TRACK | Acquistare | Puoi acquistare da  Quartieri adiacenti | Modificata | #017 adjacent_hood_presence | come l'ex EXPRESS (Quartieri adiacenti); l'ex FAST TRACK 'stesso Cliente' non c'è più |
| 05 | Artisti | HIGH HIGH | Vendere | Manda in Jail 1 Criminale che ha venduto | Invariata | #005 self_arrest_after_action |  |
| 06 | Artisti | SCAM | Acquistare | Acquista al prezzo della merce meno cara | Invariata | #006 price_at_extreme |  |
| 07 | Artisti | HARD ACQUIRE | Acquistare | 1 Criminale può acquistare fino a 3 merci | Invariata | #007 repeat_pawn_target |  |
| 08 | Artisti | DOUBLE PUSH | Acquistare | Fai 2 marketing | NUOVA |  | 'Fai 2 marketing': da definire (2 Stonk? 2 carte Marketing?) |
| 09 | Artisti | BARGAIN | Acquistare | Acquista a -2$ | Invariata | #009 trade_price_delta |  |
| 10 | Artisti | DIRTY DEAL | Vendere | Vendi anche dove ci sono Feds | NUOVA |  | vendi anche dove ci sono Feds |
| 11 | Artisti | BACKUP | Acquistare | Piazza 1 Criminale dove hai acquistato | NUOVA |  | dopo l'acquisto piazzi 1 Criminale nello stesso Quartiere |
| 12 | Artisti | CONNECTION | Vendere | Prendi un link di un cliente a scelta | NUOVA |  | prendi un Link (livello?) di un Cliente a scelta |
| 13 | Artisti | SPREADING | Vendere | Prendi un Link 3 | Modificata | #013 spot_fill_bonus_links | prima 'se riempi il PdV prendi 2 Ganci'; ora 'prendi un Link 3' |
| 14 | Artisti | AFTER HOURS | Acquistare | Manda nel Den 1 Criminale che ha acquistato | NUOVA |  | il Criminale che ha acquistato va nel Den |
| 15 | Artisti | HARD VEND | Vendere | 1 Criminale può vendere fino a 3 merci | Invariata | #015 repeat_pawn_target |  |
| 16 | Artisti | BACK ROOM | Vendere | Manda nel Den 1 Criminale che ha venduto | NUOVA |  | il Criminale che ha venduto va nel Den |
| 17 | Artisti | RUSH | Acquistare | Sposta 1 criminale che ha acquistato | NUOVA |  | sposti il Criminale che ha acquistato |
| 18 | Artisti | CLOSER | Vendere | Vendi a +2$ | Invariata | #018 trade_price_delta |  |
| 19 | Artisti | STREET CREW | Vendere | Piazza 1 Criminale dove hai venduto | NUOVA |  | dopo la vendita piazzi 1 Criminale nel Quartiere |
| 20 | Artisti | DOUBLE PUSH | Vendere | Fai 2 marketing | Doppione |  | come la 08, ma su Vendere |
| 21 | Studenti | PUSH | Muovere | Fai 1 marketing | NUOVA |  | 'Fai 1 marketing' |
| 22 | Studenti | RIOT SQUAD | Muovere | Se provochi una Rissa, i Cops presenti ti danno +2 Pistole. | NUOVA |  | se provochi una Rissa, ogni Cop presente ti dà +2 Pistole |
| 23 | Studenti | PUSH | Muovere | Fai 1 marketing | Doppione |  | come la 21 |
| 24 | Studenti | STREET TAX | Muovere | Se provochi una Rissa, prendi 1$ da ogni criminale nemico | Invariata | #024 brawl_trigger_toll | stesso effetto (1$ da ogni Criminale nemico nel Quartiere) |
| 25 | Studenti | FIGHT!! | Muovere | Se provochi una Rissa, hai +2 Pistole. | Invariata | #025 provoker_gun_bonus |  |
| 26 | Studenti | BADGE HUNT | Muovere | Se entri in Quartieri con Cops, puoi spostarli | NUOVA |  | entrando in un Quartiere con Cops puoi spostarli |
| 27 | Studenti | BUSTED | Muovere | 1 Criminale puoi muoverlo in Jail | Invariata | #033 move_to_jail | Criminale in Jail con una mossa |
| 28 | Studenti | PLAY!! | Muovere | Se muovi nel Den, pesca 2 carte | Invariata | #032 double_den_draw | controllare: ora 'pesca 2 carte' (prima 2 carte a scelta di mazzo) |
| 29 | Studenti | LONG WAY | Muovere | Muovi a distanza 2 | NUOVA |  | muovi a distanza 2 |
| 30 | Studenti | SHAKE DOWN | Muovere | Se vinci una Rissa, rubi allo sconfitto 4$ invece di 2$. | Invariata | #037 brawl_reward_money_bonus | +2$ sulla base di 2$ = 4$ (già così nel motore) |
| 31 | Studenti | SPLIT | Muovere | Puoi muovere Link nei quartieri | Modificata | #034 link_reposition | 'muovere Link nei quartieri': da chiarire rispetto all'ex REPOSITION |
| 32 | Studenti | SEAT SWAP | Muovere | Se entri nel Den, scambia posto con 1 Gambler avversario. | NUOVA |  | entrando nel Den scambi il posto con un Gambler avversario |
| 33 | Studenti | FALL GUY | Muovere | Se vinci una Rissa, manda gli sconfitti in Jail | NUOVA |  | se vinci una Rissa gli sconfitti vanno in Jail |
| 34 | Studenti | FALL GUY | Muovere | Se vinci una Rissa, manda gli sconfitti in Jail | Doppione |  | come la 33 |
| 35 | Studenti | STREET CRED | Muovere | Se vinci una Rissa, prendi un Link 3. | NUOVA |  | se vinci una Rissa prendi un Link 3 |
| 36 | Studenti | AFTERSHOCK | Muovere | Se vinci una Rissa, puoi corrompere il Cops che entra. | NUOVA |  | se vinci una Rissa puoi corrompere il Cop che entra |
| 37 | Studenti | FOLLOW ME | Muovere | Se vinci una Rissa, piazzi li un Criminale gratis | NUOVA |  | se vinci una Rissa piazzi lì 1 Criminale gratis |
| 38 | Studenti | TAKE THE POT | Muovere | Se vinci una Rissa, ruba 1 Chip Poker allo sconfitto. | Invariata | #028 brawl_reward_chip_theft | furto di 1 Chip Poker |
| 39 | Studenti | SPOILS | Muovere | Se vinci una Rissa, ruba 1 Dope a tua scelta allo sconfitto. | Invariata | #021 brawl_reward_dope_theft | furto di 1 Merce, ora a scelta (già fatto) |
| 40 | Studenti | MAKE FRIENDS | Muovere | Se entri in Quartiere dove non sei presente, pesca 2 carte | Modificata | #031 bonus_card_draw_per_unit | prima 'pesca 2 carte per ogni piazza'; ora solo entrando in un Quartiere dove non sei presente |
| 41 | Manager | REINFORCE | Piazzare | Piazza 2 Criminali per Grinta, ma non peschi carte | Invariata | #041 place_double_no_draw |  |
| 42 | Manager | NO GAMBLE | Piazzare | Piazza 1 Criminale nel Den e manda 1 Gambler nel Covo | Modificata | #042 place_in_den_evict_enemy | prima rimuovi 1 pedina nemica; ora manda 1 Gambler nel Covo (di chi?) |
| 43 | Manager | RAT | Piazzare | Piazza 1 Criminale in Jail | Invariata | #043 place_to_jail |  |
| 44 | Manager | HOME TURF | Piazzare | Piazza gratis dove hai già Criminali. | NUOVA |  | piazzi gratis dove hai già Criminali |
| 45 | Manager | BIG RAT | Piazzare | Piazza 1 Criminale in Jail | Modificata | #054 place_to_jail_evasion_immune | l'ex BIG RAT impediva di evadere; ora è identica a RAT |
| 46 | Manager | SCOUT | Piazzare | Piazza 1 Criminale in un Quartiere non rivelato | NUOVA |  | piazzi in un Quartiere non rivelato |
| 47 | Manager | RECRUITER | Piazzare | Piazza a 1$. | Invariata | #047 cost_delta |  |
| 48 | Manager | GO GAMBLE | Piazzare | Piazza 2 Criminali nel Den | Invariata | #048 place_in_den | 'Piazza 2 nel Den' |
| 49 | Manager | RESERVES | Piazzare | Piazza tutti i tuoi  Criminali a 3$ ciascuno | NUOVA |  | piazzi tutti i tuoi Criminali a 3$ ciascuno |
| 50 | Manager | BADGE HIRE | Piazzare | Un criminale piazzato in un Quartiere con un Cops, puo corromperlo | NUOVA |  | un Criminale piazzato in un Quartiere con un Cop può corromperlo |
| 51 | Manager | EXPANSION | Piazzare | Puoi spostare 1 Criminale piazzato | NUOVA |  | puoi spostare 1 Criminale appena piazzato |
| 52 | Manager | STASH | Piazzare | Non peschi carte, ma 1 Criminale piazzato può acquistare. | NUOVA |  | non peschi, ma 1 Criminale piazzato può acquistare |
| 53 | Manager | SHORTCUT | Piazzare | Piazzi 1 Criminale come Link 1 | Invariata | #053 shortcut_place_as_link |  |
| 54 | Manager | DECOY | Piazzare | Fai entrare 1 Cop in un Quartiere dove piazzi | NUOVA |  | fai entrare 1 Cop in un Quartiere dove piazzi |
| 55 | Manager | SUPPLY DROP | Piazzare | Non peschi carte, ma 1 Criminale piazzato può acquistare. | Doppione |  | come la 52 |
| 56 | Manager | NETWORK | Piazzare | Piazzi 1 Criminale come Link 1 | Doppione |  | come la 53 |
| 57 | Manager | FLASH MOB | Piazzare | Puoi spostare 1 Criminale piazzato | Doppione |  | come la 51 |
| 58 | Manager | SCOUT | Piazzare | Piazza 1 Criminale in un Quartiere non rivelato | Doppione |  | come la 46 |
| 59 | Manager | INVASION | Piazzare | Piazza 2 Criminali per Grinta, ma non peschi carte | Doppione | #041 place_double_no_draw | come la 41 (REINFORCE) |
| 60 | Manager | CHAIN REACTION | Piazzare | Pesca 2 carte per ogni Criminale piazzato | Invariata | #046 bonus_card_draw_per_unit | pesca 2 carte per ogni Criminale piazzato |
| 61 | Preti | GAMBLE | Acquistare | Banco RVB | Invariata | #081 | Gamble, invariata (prima 81-100) |
| 62 | Preti | GAMBLE | Acquistare | Banco RVG | Invariata | #082 | Gamble, invariata (prima 81-100) |
| 63 | Preti | GAMBLE | Acquistare | Banco RVA | Invariata | #083 | Gamble, invariata (prima 81-100) |
| 64 | Preti | GAMBLE | Acquistare | Banco RBG | Invariata | #084 | Gamble, invariata (prima 81-100) |
| 65 | Preti | GAMBLE | Acquistare | Banco RBA | Invariata | #085 | Gamble, invariata (prima 81-100) |
| 66 | Preti | GAMBLE | Acquistare | Banco RGA | Invariata | #086 | Gamble, invariata (prima 81-100) |
| 67 | Preti | GAMBLE | Acquistare | Banco VBG | Invariata | #087 | Gamble, invariata (prima 81-100) |
| 68 | Preti | GAMBLE | Vendere | Banco VBA | Invariata | #088 | Gamble, invariata (prima 81-100) |
| 69 | Preti | GAMBLE | Vendere | Banco VGA | Invariata | #089 | Gamble, invariata (prima 81-100) |
| 70 | Preti | GAMBLE | Vendere | Banco BGA | Invariata | #090 | Gamble, invariata (prima 81-100) |
| 71 | Preti | GAMBLE | Vendere | Banco RRB | Invariata | #091 | Gamble, invariata (prima 81-100) |
| 72 | Preti | GAMBLE | Vendere | Banco VVA | Invariata | #092 | Gamble, invariata (prima 81-100) |
| 73 | Preti | GAMBLE | Vendere | Banco BBG | Invariata | #093 | Gamble, invariata (prima 81-100) |
| 74 | Preti | GAMBLE | Vendere | Banco VGG | Invariata | #094 | Gamble, invariata (prima 81-100) |
| 75 | Preti | GAMBLE | Piazzare | Banco RAA | Invariata | #095 | Gamble, invariata (prima 81-100) |
| 76 | Preti | GAMBLE | Piazzare | Banco BAA | Invariata | #096 | Gamble, invariata (prima 81-100) |
| 77 | Preti | GAMBLE | Piazzare | Banco GGA | Invariata | #097 | Gamble, invariata (prima 81-100) |
| 78 | Preti | GAMBLE | Piazzare | Banco VBB | Invariata | #098 | Gamble, invariata (prima 81-100) |
| 79 | Preti | GAMBLE | Piazzare | Banco RVV | Invariata | #099 | Gamble, invariata (prima 81-100) |
| 80 | Preti | GAMBLE | Piazzare | Banco RRG | Invariata | #100 | Gamble, invariata (prima 81-100) |
| 81 | Politici | FULL CONTROL | Manovrare | Puoi corrompere Cops/Feds che manovri 3 volte | NUOVA |  | puoi corrompere Cops/Feds che hai manovrato 3 volte |
| 82 | Politici | PAYOFF | Corrompere | Per corrompere puoi pagare 1 Dope invece di 7$. | Modificata | #061 fake_police_dope_payment | paghi 1 Merce invece di 7$ per corrompere (prima: mazzetta in Merce per manovrare) |
| 83 | Politici | INSIDER | Manovrare | Se requisici, metti la Dope dove vuoi in Jail | Invariata | #066 insider_choose_jail_slot | scegli dove mettere la Merce in Jail |
| 84 | Politici | EVIDENCE | Corrompere | Cops/Feds corrotti si portano dietro una Dope | NUOVA |  | Cops/Feds corrotti si portano dietro una Merce |
| 85 | Politici | ESCORT | Manovrare | Se sposti Cops, puoi spostare assieme 1 tuo Criminale. | NUOVA |  | se sposti Cops puoi spostare insieme 1 tuo Criminale |
| 86 | Politici | VACANCY | Corrompere | Muovi 1 tuo Criminale dove hai corrotto Cops da un Quartiere adiacente. | NUOVA |  | muovi 1 tuo Criminale dove hai corrotto Cops da un Quartiere adiacente |
| 87 | Politici | FREE RIDE | Manovrare | Sposta gratis | NUOVA |  | 'Sposta gratis' (solo il sotto-passo Sposta) |
| 88 | Politici | DISCOUNT | Manovrare | Requisisci gratis | NUOVA |  | 'Requisisci gratis' |
| 89 | Politici | FIXER | Corrompere | I Link che corrompono Feds salgono di livello | NUOVA |  | i Link che corrompono Feds salgono di livello |
| 90 | Politici | CONNECTION | Corrompere | I Criminali che corrompono Cops diventano Links | NUOVA |  | i Criminali che corrompono Cops diventano Link |
| 91 | Politici | BACKROOM DEAL | Manovrare | I Criminali che manovrano Cops, possono andare nel Den | NUOVA |  | i Criminali che manovrano Cops possono andare nel Den |
| 92 | Politici | SAFE PASSAGE | Corrompere | I Criminali che corrompono Cops, possono andare nel Den. | NUOVA |  | i Criminali che corrompono Cops possono andare nel Den |
| 93 | Politici | PROVOCATEUR | Manovrare | Arresta gratis | NUOVA |  | 'Arresta gratis' |
| 94 | Politici | RIOT | Corrompere | Sposta 1 tuo Criminale dove corrompi Cops | NUOVA |  | sposti 1 tuo Criminale dove corrompi Cops |
| 95 | Politici | BASHER | Manovrare | Se arresti, arresta 2 Criminali invece di 1. | Invariata | #076 arrest_extra_target | se arresti, arresti 2 Criminali |
| 96 | Politici | LAST JOB | Corrompere | Se corrompi Cops, arresta anche 1 Criminale | NUOVA |  | se corrompi Cops arresti anche 1 Criminale |
| 97 | Politici | REDEEM | Manovrare | Invece di arrestare, manda un Rat nel Quartiere del Cop | Modificata | #073 redeem_release_rats | prima: invece di arrestare fai evadere 2 Rat; ora: invece di arrestare mandi un Rat nel Quartiere del Cop |
| 98 | Politici | COVER | Corrompere | Se corrompi Cops, piazza 1 Criminale nel Quartiere | NUOVA |  | se corrompi Cops piazzi 1 Criminale nel Quartiere |
| 99 | Politici | NEW ORDERS | Corrompere | Se hai 3 Cops nel Covo puoi sostituire la Retata | NUOVA |  | con 3 Cops nel Covo puoi sostituire la Retata |
| 100 | Politici | SWEEP | Manovrare | I Criminali arrestati scambiano posto con Rats | NUOVA |  | i Criminali arrestati scambiano posto con i Rat |

## Effetti delle carte attuali che non ci sono più nel nuovo set

Da togliere dal motore (o lasciare inutilizzati) quando le carte nuove li sostituiscono:

| Effetto attuale | Carte attuali | Nota |
|---|---|---|
| `extra_price_step` (RARE STUFF) | 003 | il prezzo non sale più di uno in più |
| `pre_action_restock` (REFILL) | 008 | |
| `pre_action_clear_spot` (CRAVING) | 010, 019 | |
| `same_contact_hood_presence` (FAST TRACK vecchia) | 004 | resta solo "Quartieri adiacenti" |
| `adjacent_hood_presence` (DELIVERY, vendere in un Quartiere adiacente) | 012 | la nuova 12 è un'altra cosa |
| `spot_fill_bonus_links` (SPREADING vecchia) | 013 | la nuova 13 è "prendi un Link 3" |
| `bonus_card_draw_per_unit` su Muovere (SWEET) | 029 | |
| `link_reposition` (REPOSITION) | 034, 035 | forse sostituita da SPLIT (31) |
| `invade_own_hoods` (INVADE) | 044, 051 | |
| `reinforce_dope_discard` (REINFORCE con Merce) | 052, 056 | |
| `place_to_jail_evasion_immune` (BIG RAT) | 054, 059 | la nuova BIG RAT (45) è identica a RAT |
| `extra_grit` su Manovrare (COOPS) | 067, 072 | |
| `officer_move_anywhere` (TRANSFER) | 065 | |
| `officer_move_cross_type` (REASSIGN) | 069, 070, 071 | |
| `keep_confiscated_dope` (Prendi la Merce requisita) | 063, 064 | |
| `confiscate_extra_unit` (STRIKE) | 078 | |
| `cost_delta` "Manovra gratis" | 068, 079 | ora solo per un sotto-passo: Sposta (87), Requisisci (88), Arresta (93) |

## Cosa è cambiato a livello di mazzi

- **Stonk e Pistole: identici** alle carte attuali (nessuna differenza).
- **Simboli Poker:** identici per le carte che si corrispondono; i colori sono gli stessi (blu = azzurro).
- **Mazzo Preti** (le carte Gamble con Banco di 3 simboli): invariato, ma ora occupa le carte 61–80 (prima 81–100). **Politici** passa a 81–100 (prima 61–80). Gli id interni delle carte e le immagini vanno rimappati di conseguenza.
- **Nuova colonna "Job"** (Rats, Dollars, Cops, Hoods, Dope, Crimes, Links, Poker, Brawl): non esiste oggi nei dati. Da capire a cosa serve.

## Domande aperte per il game designer

1. **Colonna "Job":** è solo un'indicazione grafica (l'icona sulla carta) o ha un effetto di gioco?
2. **"Fai 1 / Fai 2 marketing" (08, 20, 21, 23):** che cosa si fa? Giocare un'azione Marketing in più? Muovere i prezzi con gli Stonk senza scartare una carta?
3. **"Prendi un Link 3" (13, 35) e "prendi un Link di un Cliente a scelta" (12):** il Link va sempre nel livello 3 anche se occupato (e il Link che c'è scorre/viene espulso come per un livello 1)? Da dove si prende la pedina: dal Covo?
4. **NO GAMBLE (42):** "manda 1 Gambler nel Covo": un Gambler tuo o di un avversario?
5. **SPLIT (31) "Puoi muovere Link nei quartieri":** i Link possono essere mossi in un Quartiere come se fossero Criminali? (Oggi un Link non sta in un Quartiere.)
6. **VACANCY (86), FULL CONTROL (81), NEW ORDERS (99)** e altre carte nuove con il verbo "corrompere": confermi che usano la nuova azione Corrompere (compri il Cops, 7$)? NEW ORDERS: "sostituire la Retata" = scarti la Retata del turno e ne scopri un'altra?
7. **Small:** togliamo le 20 carte Studenti (21–40) come ora?
8. **Raddoppi (8 carte):** i titoli sono diversi ma l'effetto è lo stesso di un'altra carta (20=08, 23=21, 34=33, 55=52, 56=53, 57=51, 58=46, 59=41): è voluto (più copie di un effetto) o è un refuso?

## Risposte del game designer (2026-10-15)

1. **Colonna "Job":** da ignorare.
2. **"Fai 1 / Fai 2 marketing":** puoi giocare 1 carta Marketing, oppure 2. Con "1" la giochi senza fare un acquisto/una vendita; con "2" ne giochi due *invece di una* durante la vendita o l'acquisto.
3. **"Prendi un Link 3" (13, 35) e "un Link di un Cliente a scelta" (12):** il Link prende il livello 3 e **sposta fuori quello che c'è già** (torna Criminale/Covo, come per un Link espulso). Lo si prende quando si evolve un Criminale: che ha venduto (13), che ha vinto una Rissa (35), ecc.
4. **NO GAMBLE (42):** il Gambler mandato nel Covo è **di un avversario** (torna nel *suo* Covo).
5. **SPLIT (31):** un Link torna a essere un Criminale normale e passa dal tracciato dei Link al relativo Quartiere.
6. **NEW ORDERS (99):** si scarta la Retata del turno e se ne scopre un'altra.
7. **Doppioni:** voluti (poche copie di ciascun effetto).
8. **Small:** si tolgono le 20 carte Studenti (21–40), come ora.
