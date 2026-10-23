# Job e Retate in Easy Price: cosa dicono le simulazioni

Studio del 2026-10-20 / 2026-10-22. Domande del game designer: quanto conta la sequenza dei Job sui punti finali, se
conviene spostare qualche Job tra i livelli, come entrano in gioco le Retate. Dati, script e tabelle complete:
[`README.md`](README.md).

## Metodo e limiti

- Modalità Easy Price, quattro bot euristici (`HeuristicBot`, che insegue il Job che sente più vicino) per partita. Migliaia
  di partite per ogni configurazione (vedi la tabella dei dati nel README).
- Tutti i confronti sono **dentro la partita**: punti meno la media del proprio tavolo. Le incertezze (intervalli al 95%)
  sono raggruppate per partita perché i quattro giocatori non sono indipendenti. Le quote di varianza sono calcolate
  **fuori campione** (5 gruppi di partite), così i molti parametri non le gonfiano.
- L'assegnazione dei Job a ogni giocatore è casuale, quindi l'effetto del «primo Job» è causale **per questi bot**.
- **Limite principale: sono bot.** Il bot euristico non pianifica, sfrutta poco le azioni extra dei Link, non ha nessun
  meccanismo per le Retate «+Poker» e «−Rats» e reagisce poco alle Retate che chiedono di avere di più. Le conclusioni
  sul valore relativo dei Job vanno lette con questo filtro; un giocatore umano potrebbe ottenere molto di più da alcuni
  Job (30 dollari, 2 Chip Poker) e anche pianificare le Retate.

## 1. Quanto pesa la sequenza dei Job (layout attuale)

Fonti: report 01-05 (3.000 partite, v1; bot più e meno interessati ai Job, 700 partite ciascuno).

- Punti medi 7,8 (dev. std. 4,1; 3,4 dentro il tavolo). Job completati a testa 2,36; il 16% non ne completa nessuno.
- Nessun vantaggio di posizione al tavolo (R² 0,06%).
- I tre Job rivelati a inizio partita spiegano il **12,3%** della varianza dei punti nel tavolo (14% con le 27
  combinazioni). Distanza tra la combinazione migliore (01·06·08: +2,5 punti, vince il 47%) e la peggiore (01·04·09: −2,3,
  vince l'8%): **4,8 punti**.
- Quasi tutto viene dal primo Job del livello 3:

| Primo Job del livello 3 | Punti vs tavolo | Vittorie | Lo completa |
|---|---:|---:|---:|
| 10 Criminali fuori (08) | **+1,47** | 38,5% | 71% |
| 2 Chip Poker (03) | −0,48 | 21,8% | 24% |
| 30 dollari (09) | −1,00 | 14,7% | 14% |

  Chi parte con 2 Chip Poker **non** è svantaggiato rispetto a chi parte con 30 dollari: è meglio di +0,52 ±0,15 punti
  (+7 punti percentuali di vittorie), in tutti i sottogruppi. Il Job anomalo è «10 Criminali fuori».
- Livello 2: 2 Rats −0,51 (21% vittorie), 4 Dope +0,15, 4 Link +0,36 (28%). Livello 1: Vinci 1 Rissa −0,23, 1 Cop/Fed +0,04,
  6 Hoods +0,19.
- **Il meccanismo è il numero di Job completati.** A parità di Job completati l'effetto del primo Job sparisce (R² 12% →
  79% aggiungendo il conteggio). Ogni Job completato vale circa 2,1 punti a parità di tutto il resto.
- Robustezza: con bot molto interessati ai Job la quota spiegata è 12,6%, con bot poco interessati 4,7% (ne completano
  meno). L'ordine nel livello 3 non cambia (08 > 03 > 09; 03 − 09 = +0,65 e +0,35). Il livello 1 e 2 sono sensibili allo stile
  del bot.

### Cosa lascia in dote «10 Criminali fuori» (report 07)

La tua obiezione (costo economico, perdita di flessibilità, niente Link) è vera nella direzione, ma piccola. Con 10 Criminali
come primo Job, rispetto agli altri due del livello 3:

| | |
|---|---|
| Denaro medio | −2,05$ (media 10$); round con ≤ 2$ +3,5 punti percentuali, con 0$ +1,6 |
| Pedine in base | −1,2 in media; round con 0 pedine in base +5,6 punti percentuali |
| Poker | +0,20 lanci a testa, solo +0,05 senza Gambler gratis |
| Cosa guadagna | +1,2 Criminali sul tabellone, +0,47 carte (ogni piazzamento pesca), più maggioranze e Skill |
| Al completamento | denaro −0,02$ ±0,37 rispetto agli altri giocatori: il costo è diluito nei round precedenti |
| Netto | **+1,35 punti** |

Tempi: lo completa il 41% entro il turno 2 e il 70% entro il 3; round medio 5,6 su 9 (come 2 Chip Poker, prima di 4 Link e 2 Rats).

### Valore dei premi dei Job (report 06)

Esperimento: ogni bot, nella stessa partita, ha una preferenza fissa sulla colonna (1.199 partite).

| Preferenza | Punti vs tavolo | Vittorie |
|---|---:|---:|
| Skill | +0,96 ±0,21 | 33,8% |
| Link | +0,22 ±0,22 | 28,4% |
| 3$ | −0,39 ±0,20 | 20,3% |
| 2 carte | −0,79 ±0,19 | 17,4% |

Con questi bot la Skill vale più del Link (che vale +0,16 in maggioranze). Per «10 Criminali fuori», che non dà il Link,
chi lo completa per primo prende comunque la Skill; perde il Link solo chi arriva dopo (circa −0,6 punti). Resta il
limite sulle azioni extra dei Link, poco usate dal bot.

## 2. Raggruppare i Job nei livelli: layout attuale, A e C

Layout (definiti in `tools/analysis/job_layouts.py`): **A** scambia «10 Criminali fuori» con «2 Rats» (08 al livello 2, 04 al
livello 3); **C** ordina i livelli per difficoltà (08 al livello 1, Vinci 1 Rissa al livello 2, 2 Rats al livello 3).

Fonti: report 10 e 27.

| | Attuale | A | C |
|---|---:|---:|---:|
| Varianza dei punti spiegata dai Job iniziali | 11,3% | **4,5%** | 5,8% |
| Migliore − peggiore combinazione | 4,5 | **3,2** | 3,2 |
| Scarto tra i primi Job: livello 1 / 2 / 3 | 0,59 / 0,76 / 2,38 | 0,90 / **0,36** / 1,25 | 0,59 / 0,90 / 1,24 |
| Job completati a testa | 2,31 | 2,28 | 2,20 |
| Punti medi | 7,71 | 7,70 | 7,62 |

- A dimezza il peso dei Job iniziali con due soli spostamenti. C non fa meglio sul punteggio e completa meno Job.
- Con A i livelli restano ordinati per difficoltà: dopo il turno 2 il livello 1 è completato al 53%, il livello 2 al 31%, il
  livello 3 al 13%.
- Nel confronto appaiato su 2.000 seed (stessa sequenza di Retate e setup): A − C sui Job completati +0,062 [+0,012; +0,115]
  (significativo), sui punti +0,09 [−0,00; +0,19], sulla distanza migliore−peggiore −0,21 [−0,81; +0,58] (non significativa).
  A resta preferibile; i due sono pari sull'equilibrio.
- Resta fuori linea «30 dollari»: nel livello 3 è sempre il più basso (circa −0,7 punti, completato nell'11% dei casi), in
  qualunque raggruppamento. Per correggerlo servirebbe cambiare la soglia, non la posizione. **Non testato**: la soglia
  da 25 dollari è solo un'ipotesi.

## 3. «Bankability»: Job che si possono preparare prima di essere rivelati

Fonti: report 11-13 (layout A e C: 3.000 partite ciascuno).

- Pochi Job risultano già soddisfatti nel momento in cui vengono rivelati: **2 Chip Poker 20%** (quando è 2° o 3°),
  **1 Cop/Fed 8%**, **10 Criminali fuori 8%** (10% in C); tutti gli altri 4% o meno; Vinci 1 Rissa 0%, come da regola.
  In totale il 3,0% dei completamenti in A e il 4,6% in C è immediato. Catene di tre Job nello stesso istante: 5 in A,
  47 in C (1 Cop/Fed, 6 Hoods e 10 Criminali stanno insieme nel livello 1).
- Completati entro 3 round dalla rivelazione, se il Job è il primo e se è secondo/terzo (A):

| Job | 1° | 2°/3° | Round dalla rivelazione al completamento |
|---|---:|---:|---|
| 1 Cop/Fed | 31% | 71% | 4,5 → 1,2 |
| 10 Criminali fuori | 2% | 37% | 5,7 → 1,9 |
| 6 Hoods | 9% | 47% | 5,4 → 2,5 |
| 4 Link | 2% | 27% | 6,5 → 3,0 |
| 2 Chip Poker | 5% | 24% | 5,8 → **0,9** |
| 2 Rats | 3% | 17% | 6,5 → 2,6 |
| 30 dollari | 3% | 15% | 4,8 → 2,0 |
| Vinci 1 Rissa | 27% | 37% | 4,4 → 2,1 |
| **4 Dope** | 31% | **12%** | 3,0 → 2,0 |

  A parità di round di calendario (4-9) un Job rivelato dopo si completa più in fretta per round: 30 dollari ×3,2, 4 Link ×1,5,
  Vinci 1 Rissa ×1,5, 1 Cop/Fed ×1,2; 4 Dope ×0,47 (diventa più difficile). Una parte è semplicemente che a metà partita la
  posizione è più ricca: Vinci 1 Rissa, che non si può preparare, è più veloce da secondo.

## 4. Retate

### Quanto costano e quanto contano

Fonti: report 14, 28.

- Macchie inflitte dalle Retate: 1,18 per giocatore in A (dev. std. 1,26), cioè 1,18 punti a testa (il 15% dei punti medi).
  Il 62% dei giocatori ne subisce almeno una.
- La loro varianza è circa il **10% della varianza dei punti**, il triplo di quella dei Job iniziali (3-4%). Tra il più e il
  meno macchiato dello stesso tavolo ci sono in media 2,4 macchie. Non dipende dall'abbinamento Job/Retata, ma da chi viene preso.
- Esito di ogni Retata: pareggio (tutti e quattro presi) il 51% delle volte con +Cops, 40% con −Rats, 23% +Poker, 16% +Links,
  12% −Dope, 9% −Crimes, 4% −$. Nei turni 1, 2, 3 i giocatori hanno in media 0,42, 1,41, 2,34 REP e a chi è preso vengono
  applicate 0,28, 0,76, 1,01 macchie (di 1, 2, 3).
- Venire presi 0, 1, 2, 3 volte: +1,44, +0,52, −0,16, −0,69 punti rispetto al tavolo.

### La sequenza delle Retate cambia il valore dei Job iniziali? No

Fonti: report 15-17, 21-22, 25-27.

- Quota di varianza spiegata (fuori campione, confronto appaiato A − C su 2.000 seed): Job iniziali A 4,1% / C 3,6%;
  sequenza di Retate 0,0% / 0,3%; **interazione Job × Retata −0,69 / −0,76 punti** (valore negativo: aggiungere
  l'interazione peggiora la previsione, cioè è rumore). Differenza A − C dell'interazione +0,07 [−0,36; +0,50].
- Test congiunto sulle 63 coppie Job × Retata: p = 0,78 (attuale), 0,31 (A), 0,21 (C); 4-5 celle «significative» contro ~3
  attese per caso.
- Quanto le Retate spostano il vantaggio di un trio di Job iniziali: mediana 0,13-0,19 punti, 95° percentile 0,37-0,49,
  massimo 0,60-0,72. Per una data sequenza di tre Retate **non** ci sono pescate di Job nettamente favorevoli.
- Per ogni Retata la distanza tra i tre Job iniziali di un livello è sempre vicina a quella su tutte le partite (A, livello 3:
  1,12 in generale, 1,00-1,26 con una Retata specifica); le differenze sono nel rumore. Esempio: con +Links, chi parte con
  Cop/Fed è avanti a chi parte con Rissa di 0,38 punti (−0,03 contro −0,41), contro 0,29 in media.

### La matrice teorica Job × Retata (−5..+5) contro la simulazione

Fonti: report 18-20, 23.

- Sulla probabilità di **sfuggire** alla Retata la correlazione è +0,52 (attuale), +0,54 (A), +0,32 (C), +0,35 (Job attivo a
  inizio turno × Retata del turno). Il segno concorda nel 74%, 68% e 58% delle celle forti.
- Le coppie dirette sono confermate: 4 Link × +Links +11 punti percentuali, 30$ × −$ −14, 4 Dope × −Dope −15, 6 Hoods ×
  −Crimes −9, 10 Criminali × −Crimes −13.
- Discordanze: 2 Chip Poker × +Poker (teoria +5, osservato ~0: pochi giocatori accumulano le chip), 1 Cop/Fed × +Cops (teoria +5,
  osservato ~0: la Retata finisce spesso in pareggio) e 2 Chip Poker × −$ (teoria −3, osservato **+7,5**, opposto: in Easy
  Price il lancio non dà soldi).
- Sui **punti** nessuna combinazione Job attivo × Retata supera ±0,19 punti, sul completamento del Job nel turno ±5,6 punti
  percentuali. La matrice non ha potere predittivo su completamento (+0,05) e punti (−0,15): le Retate cambiano soprattutto
  il rischio, e poco i punti, perché una macchia costa 1 punto.

### Le Retate preparano i Job futuri?

Fonte: report 24.

- Con questi bot quasi no. Durante il turno della Retata corrispondente i bot accumulano solo +0,02 chip (+Poker), +0,09 Link
  (+Links), +0,02 Cop/Fed (+Cops). Reagiscono molto di più alle Retate che chiedono di avere *meno*: −$ → −2,6$,
  −Dope → −0,8 Dope, −Crimes → −0,5 Criminali.
- L'unico effetto di preparazione consistente: 1 Cop/Fed rivelato dopo risulta già soddisfatto il **15,6%** delle volte se
  la Retata +Cops è uscita nel turno precedente, contro l'8,2% (A + C, n = 673 e 3.921). Per 2 Chip Poker (22,2% contro 20,3%) e
  4 Link (1,2% contro 1,7%) non c'è nessun effetto.

## 5. Test «Retata ×4»: bot che pesano il criterio della Retata quattro volte di più

Fonti: report 30-43. Layout A e C, 2.000 partite ciascuno sugli **stessi seed** del confronto con i bot normali
(`raid_criterion_bonus=4` invece di 1), quindi ogni differenza è appaiata. Domanda: se i bot tengono davvero conto della
Retata, compare l'interazione Job × Retata e la preparazione dei Job futuri che i bot normali non mostrano?

**1. Rispondono, ma solo ai criteri «meno».** Variazione nel turno della Retata, rispetto alle altre Retate (A; in C è simile):

| Retata → risorsa | ×1 | ×4 | differenza |
|---|---:|---:|---:|
| −$ → denaro | −2,61 | −4,27 | **−1,67** [−1,96; −1,36] |
| −Crimes → Criminali nei Quartieri | −0,51 | −1,32 | **−0,81** [−0,88; −0,73] |
| −Dope → Dope nel Covo | −0,83 | −1,22 | **−0,40** [−0,45; −0,35] |
| +Links → Link | +0,093 | +0,091 | −0,003 [−0,038; +0,036] |
| +Cops → Cop/Fed nel Covo | +0,017 | +0,023 | +0,006 [−0,013; +0,027] |
| +Poker → chip Poker | +0,024 | +0,017 | −0,007 [−0,023; +0,008] |
| −Rats → Rats | +0,012 | +0,032 | +0,020 [−0,006; +0,048] |

In C è uguale (−$ −1,82, −Crimes −0,79, −Dope −0,31; le altre dentro l'incertezza, +Cops −0,022 [−0,042; −0,001]). Per +Poker e
−Rats il bot non ha un meccanismo, ma anche per +Links e +Cops la risposta non cresce: il peso non basta, mancano azioni che
li preparino. Quindi ×4 **non produce** il comportamento che volevamo osservare, produce solo più «scarico» sulle Retate «meno».

**2. Giocare così costa.** Rispetto ai bot normali sugli stessi seed (A / C):

| | ×1 | ×4 | differenza |
|---|---:|---:|---:|
| Job completati a testa | 2,29 / 2,23 | 2,00 / 1,93 | **−0,30** [−0,34; −0,26] / **−0,30** |
| punti medi | 7,71 / 7,62 | 7,15 / 7,03 | **−0,56** [−0,64; −0,48] / **−0,60** [−0,68; −0,52] |
| macchie inflitte per giocatore | 1,18 / 1,17 | 1,07 / 1,05 | −0,12 / −0,12 |
| Retate finite in pareggio (su 3) | 0,63 / 0,67 | 0,71 / 0,72 | +0,09 / +0,05 |

Le macchie calano di 0,12 ma si perdono 0,3 Job, circa 0,6 punti. Essere preso non cala (1,81 → 1,86 volte su 3): la Retata si
decide sulle squadre, e se tutti si comportano allo stesso modo i pareggi aumentano.

**3. Nessuna preparazione dei Job futuri.** Con la Retata corrispondente uscita nel turno precedente alla rivelazione, il Job
risulta già soddisfatto: 1 Cop/Fed 12,7% contro 7,4% (×1: 15,6% contro 8,2%), 4 Link 0,7% contro 1,0%, 2 Chip Poker 27,8% contro
18,7% (n=144, nello stesso turno 16,3% contro 18,1%; ×1: 22,2% contro 20,3%). Il valore dei Poker è nel rumore (circa 2,4 errori
standard, e lo stesso effetto nel turno della Retata va in direzione opposta). Entro 3 round dalla rivelazione nessuna differenza.

**4. L'interazione Job × Retata compare, ma resta piccola.** Test congiunto sulle 63 celle: p = 0,0007 in A e 7·10⁻⁵ in C
(bot normali: 0,31 e 0,21 su 3.000 partite); celle significative 8 e 11 su 63 (≈ 3 attese per caso). Celle che si ripetono
in A e C:

| Job × Retata | A | C |
|---|---:|---:|
| 4 Dope × −Dope | −0,38 | −0,40 |
| 30 dollari × +Cops | −0,46 | −0,29 |
| 10 Criminali × −Crimes | −0,38 | −0,16 |
| 30 dollari × −$ | +0,08 | +0,30 |

Le celle 4 Dope × −Dope e 30 dollari × −$ erano già visibili con i bot normali in A (−0,37 e +0,24). Però la previsione fuori campione **non migliora**
(A: R² 1,99% → 1,48%; C: 2,77% → 1,91%, allenando su 1.000 partite e verificando su altre 1.000), e la quota di varianza
aggiunta dall'interazione è −0,25 punti in A e +0,23 in C (nulla). In punti: lo scostamento che le Retate danno al vantaggio di un
trio iniziale ha mediana 0,24 e massimo 1,32 (A), contro 0,19 e 0,72 con ×1; sempre piccolo rispetto ai 2,4-2,5 punti tra il
trio migliore e il peggiore.

**5. Quote di varianza.** Job iniziali 2,3% (A) e 2,1% (C), contro 4,1% e 3,6%, perché con ×4 si completano meno Job. La sequenza
delle Retate sale da 0,0-0,3% a 1,5% della varianza rispetto alla media generale (dentro il tavolo resta 0,0% per costruzione:
la Retata è la stessa per tutti): sposta il punteggio medio del tavolo, non il vantaggio relativo. L'esito delle Retate (quante
volte preso, macchie) spiega ancora il 24,5-26% della varianza dentro il tavolo, come con ×1.

**6. Matrice del designer e confronto A − C.** Correlazione tra teoria e probabilità di sfuggire: A +0,48 (×1 +0,54), C +0,30
(×1 +0,32); segno concorde nel 68% e 58% delle celle forti, come con ×1. Il confronto A − C dà la stessa conclusione: Job
completati +0,068 [+0,019; +0,119], punti +0,124 [+0,037; +0,219] (ora significativo), distanza migliore − peggiore −0,15
[−0,73; +0,54] (non significativa).

**Cosa si può dire.** I risultati sui Job (sezioni 1-3) non dipendono dal fatto che i bot normali guardano poco le
Retate: i bot più attenti non cambiano né la classifica dei Job né il confronto A − C. La domanda «chi si prepara alle Retate
trova pescate di Job favorevoli?» invece **non è stata testata davvero**: ×4 pesa di più il criterio ma non dà al bot le azioni
per prepararsi (comprare Cop/Fed in anticipo, accumulare chip, tenere Link liberi). Per rispondere servirebbe un bot con una
pianificazione esplicita; è un lavoro a parte, non una questione di pesi.

## 6. Cose scoperte per strada

- **Bug dei bot** (corretto, `26ec5d7`): una scelta opzionale rimasta senza opzioni (FOLLOW ME dopo che un bonus Link
  aveva preso l'ultima pedina in base) faceva campionare 1 elemento su 0 e il bot andava in errore, bloccando la partita.
  Ora il numero di scelte è limitato alle opzioni disponibili.
- **Riproducibilità**: la non riproducibilità nota dei bot (stesso seed, comportamento diverso) dipende dall'ordine di
  iterazione di insiemi di stringhe nel codice dei bot, sensibile al seme di hash di Python. Con `PYTHONHASHSEED` fisso le
  partite sono identiche a ogni esecuzione. `simulate.py` lo imposta; i run precedenti al 2026-10-22 non sono
  riproducibili bit a bit (le statistiche non ne risentono).
- Il bot ha un meccanismo per le Retate solo per cinque criteri (−Dope, −$, +Links, +Cops, −Crimes); non ne ha per +Poker e −Rats.

## 7. Ipotesi sul design (da verificare, non applicate)

- Adottare il layout **A** (scambio di «10 Criminali fuori» con «2 Rats») dimezza il peso dei Job iniziali.
- Per «30 dollari» servirebbe una soglia più bassa (ipotesi: 25), da simulare. In Easy Price 2 Chip Poker non dà soldi al lancio.
- Le Retate «+Cops» e «−Rats» finiscono in pareggio spesso (51% e 40%) e il pareggio prende tutti: sono le più punitive.
