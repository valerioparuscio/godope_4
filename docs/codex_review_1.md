# Codex review 1 — riepilogo della sessione

Date: 27–28 settembre 2026.

Aggiornamento del 28 settembre 2026: inventario verificato rispetto a `HEAD`
`7efffa293840f8ca35ec4174aa6728fd6ccd2256`, branch `main`. Non risultano commit
datati 28 settembre nella storia raggiungibile consultata: le differenze sono
nel working tree, compresi i nuovi file non ancora tracciati. Git non consente
di attribuire con precisione a un giorno o autore ogni modifica non committata;
questo documento descrive lo stato locale riscontrato oggi. Le sezioni 11–16
completano il resoconto precedente e forniscono istruzioni per un altro agente.

Questo documento riporta le modifiche realizzate da Codex durante la sessione,
le verifiche effettuate e le attività soltanto discusse. Al momento della
stesura tutte le modifiche sono locali: Codex non ha eseguito commit né push.

## 1. Lettura iniziale del progetto

Esaminate struttura, README, istruzioni in `CLAUDE.md`, regolamento canonico,
regole pendenti, changelog e principali flussi di frontend, motore, API e
persistenza. Questa fase non ha modificato file.

## 2. Revisione grafica dei popup

Richiesta: mantenere le dimensioni dei popup, adottando uno stile più da gioco
a tema criminalità leggera.

- Creato `frontend/src/popup-theme.css`, importato da `frontend/src/App.tsx`.
- Applicati fondi antracite, testi crema, accenti senape, texture puntinata,
  bordi marcati, ombre nette e pulsanti in rilievo.
- Aggiunta una striscia segnaletica decorativa ai popup degli eventi.
- Differenziati gli accenti di Poker, Rissa e Retata tramite l'attributo
  `data-outcome` in `frontend/src/components/OutcomeModal.tsx`.
- Rivisti anche regolamento, tutorial, fine partita, classifica e popup Skill.
  La classifica conserva font arcade e scanline.
- Aggiunti stili di focus visibile, hover e pressione per i controlli interessati.
- Conservati misure, spaziature e metriche dei testi dei popup; nessuna modifica
  alle regole o ai tempi di conferma degli eventi.

Verifica: confronto automatico delle dimensioni prima/dopo nel browser a
larghezze di 1280 e 390 pixel per annuncio turno, inizio Poker, Rissa, Retata,
risultato Poker, regolamento, annuncio vincitore, punteggi e classifica.
Le dimensioni dei casi verificati coincidono. Ispezionati anche screenshot
di Retata e regolamento. Il controllo dimensionale non equivale a una revisione
completa dell'usabilità mobile.

## 3. Centratura dei segnalini prezzo

Modificato esclusivamente `frontend/src/board-layout.ts` per tre posizioni.
Coordinate espresse in percentuale della larghezza e dell'altezza della board:

| Segnalino | X prima | Y prima | X dopo | Y dopo |
|---|---:|---:|---:|---:|
| Polpo, prezzo 3 | 94.365 | 62.763 | 94.365 | 63.9 |
| Rana, prezzo 3 | 92.79 | 39.02 | 92.45 | 39.02 |
| Polpo, prezzo 5 | 92.646 | 68.508 | 92.35 | 69.05 |

Il Polpo sul 3 è stato abbassato, la Rana sul 3 spostata a sinistra e il Polpo
sul 5 spostato a sinistra e in basso. Controllati i centri sulla board ingrandita
con croci di riferimento prima e dopo. Le altre coordinate non sono cambiate.
Codex non ha modificato i file immagine dei segnalini.

## 4. Allineamento dei player board

In `frontend/src/App.css` aggiunto `margin-top: auto` a
`.app__sidebar > .player-strip`, per ancorare i quattro player board al fondo
della colonna quando c'è spazio disponibile, senza modificarne dimensioni e
distanze. Verificato nel browser che il fondo del gruppo coincida con il fondo
della colonna.

La successiva introduzione del box Retata esteso ha aggiunto lo scorrimento
della colonna: quando l'altezza complessiva supera lo schermo, i pannelli sono
raggiungibili scorrendo e il margine automatico non aggiunge spazio superiore.

## 5. Pulsanti in alto a destra

Richiesta: icona sopra e testo in basso, Carte e Skill rettangolari più larghi,
Log, Regolamento e Musica quadrati arrotondati, sfruttando l'altezza disponibile.

- Creato `frontend/src/components/ToolbarButtonContent.tsx` con icone SVG per
  carte, Skill, registro, regolamento e musica attiva/disattivata.
- Aggiornati `HandDrawer.tsx`, `SkillsDrawer.tsx`, `ActionLogDrawer.tsx` e
  `App.tsx` per usare icone, etichette e contatori separati.
- Carte ha una superficie color sabbia, Skill verde salvia e gli altri tre
  pulsanti una superficie scura, coerenti con la revisione grafica.
- I contatori sono nell'angolo superiore destro; le etichette restano in basso.
- In `App.css` introdotta una misura adattabile fra 76 e 118 pixel. Carte e
  Skill sono larghi 1,3 volte tale misura; gli altri tre sono quadrati.
- Aggiunti stati visivi di apertura/pressione, focus da tastiera e rispetto
  della preferenza per movimento ridotto nelle transizioni.
- I drawer espongono `aria-expanded`; Musica espone stato e nome accessibile.

Verifica: layout a larghezze di 1440, 1280 e 1024 pixel, senza fuoriuscite
orizzontali dei cinque pulsanti nei casi provati. Apertura e chiusura di Carte,
Skill e Log verificate nel browser. Ispezionato uno screenshot della barra.

## 6. Box Retata con punteggi parziali

### Interfaccia

`frontend/src/components/RaidBanner.tsx`, nello stato finale verificato, mostra:

- titolo testuale della Retata e requisito per sfuggire, senza immagine della
  carta e senza numero del turno;
- due squadre identificate da segnalini e nomi dei colori;
- totale corrente di ogni squadra e unità del criterio;
- squadra in vantaggio evidenziata in verde; in parità nessuna evidenziata
  (non è presente una dicitura esplicita di pareggio);
- promemoria del criterio: totale maggiore, oppure minore per il valore Merci;
- dicitura di squadre provvisorie durante la fase di Soffiata (`tip_off`).

Il titolo, il requisito e i punteggi sono raccolti in un box verticale in alto a sinistra.
`App.tsx` dispone ora la colonna sinistra con Retata e player board accanto
all'area principale, che contiene barra dei comandi e tabellone.
`App.css` definisce il nuovo layout e lo scorrimento della colonna per schermi
più bassi. Il box non estende in altezza la barra sopra il tabellone.

### Backend e API

- In `backend/src/dope_engine/rules/raids.py` introdotti `RaidStandings` e
  `current_raid_standings(state)`, un calcolo in sola lettura.
- La risoluzione finale della Retata riutilizza lo stesso calcolo dei parziali:
  non esiste una copia delle regole nel frontend.
- Conservati i sette criteri esistenti, la composizione delle squadre secondo
  l'ordine corrente (primo + quarto contro secondo + terzo), il criterio inverso
  per il valore Merci e la regola che in parità nessuno sfugge.
- Aggiunto `raid_standings` alla vista applicativa in `application/views.py`.
- Aggiunto `RaidStandingsResponse` negli schemi HTTP e relativa conversione
  in `adapters/http/app.py`.
- Aggiornati i tipi corrispondenti in `frontend/src/types.ts`.
- Il nuovo campo contiene criterio, membri delle squadre, totali,
  `leading_team` (`a`, `b` o `null`) e `lower_wins`; è nullo senza Retata rivelata.
- I parziali vengono ricostruiti nella vista aggiornata della partita, quindi
  seguono anche le viste mostrate durante la riproduzione dei turni dei bot.
- Aggiornato `README.md` per documentare il box e il nuovo campo della vista.

Non sono state introdotte nuove regole di gioco o modifiche al formato dei
salvataggi. L'API aggiunge un campo alla vista; non modifica gli endpoint.

### Test aggiunti

In `backend/tests/unit/test_raids.py`:

- confronto fra parziali e risoluzione finale per tutti i sette criteri e le
  quattro possibili rotazioni del primo giocatore;
- verifica che il calcolo dei parziali non muti lo stato;
- aggiornamento del vantaggio al variare del denaro e gestione della parità;
- vittoria del totale minore per le Merci e aggiornamento al variare dei prezzi;
- assenza dei parziali quando nessuna Retata è stata rivelata.

In `backend/tests/integration/test_http_app.py` aggiunta una verifica della
presenza e della struttura dei parziali nella risposta HTTP.

## 7. Verifiche riportate nella stesura precedente

I risultati seguenti sono conservati come storico della prima stesura, non
come certificazione di tutte le modifiche aggiunte successivamente. Per i
controlli rieseguiti durante questo aggiornamento vedere la sezione 15.

- Test mirati Retate, viste e HTTP: **83 superati**.
- Suite backend completa: **492 superati**, con un errore di preparazione
  dell'ambiente nel test di salvataggio su file, dovuto ai permessi Windows
  sulla directory temporanea `.pytest_tmp`.
- Quel singolo test è stato rieseguito con una directory temporanea dedicata:
  **superato**. La directory creata per la verifica è stata poi rimossa.
- Ruff: nessun errore nei controlli finali eseguiti.
- mypy: nessun problema nei 53 file sorgente verificati.
- Build frontend TypeScript/Vite: riuscita.
- Lint frontend: nessun errore, sei avvisi preesistenti relativi a Fast Refresh
  e dipendenze degli hook.
- Verificati nel browser box Retata, squadre in pareggio e layout completo;
  controllata l'altezza della colonna a 1080, 900 e 768 pixel.
- Verificata nell'OpenAPI del backend locale riavviato la presenza di
  `raid_standings`.

## 8. Operazioni sull'ambiente locale

- Avviato/riavviato il frontend Vite su `http://127.0.0.1:5173/game/` quando
  il collegamento locale non rispondeva.
- Verificata la risposta HTTP di frontend e backend locale sulla porta 8000.
- Per controllare il box Retata è stato avviato temporaneamente un backend
  separato sulla porta 8001, con persistenza esterna disabilitata. Arrestato
  al termine delle verifiche.
- Il backend principale è stato riavviato per caricare il nuovo campo della
  vista, dopo l'autorizzazione esplicita dell'utente alla perdita delle partite
  mantenute in memoria. Per arrestare il precedente processo sono serviti
  permessi di esecuzione aggiuntivi.
- Screenshot e log di verifica sono stati prodotti nella directory temporanea
  del sistema; non sono nuovi asset del gioco.

## 9. Responsive: discusso, non implementato integralmente

È stata valutata la possibilità di migliorare mobile, tablet e zoom del browser.
Proposta una prima fase su desktop/zoom e una seconda fase dedicata al mobile,
con pannelli richiudibili e tabellone ingrandibile/trascinabile.

Questa revisione completa non è stata richiesta in esecuzione né realizzata
nella sessione. Le dimensioni adattabili della barra e lo scorrimento della
colonna sinistra sono interventi locali e non costituiscono una soluzione
responsive completa. Restano da verificare sistematicamente zoom desktop,
orientamento mobile, interazioni touch e accessibilità dei pannelli su schermi
piccoli.

## 10. Modifiche presenti nel workspace non attribuite a Codex

Durante la sessione sono state rilevate modifiche ai quattro PNG in
`frontend/src/assets/price/` e, al momento di questa stesura, la presenza del
nuovo file `frontend/src/assets/music_dope/Arcade Hustle.mp3`.
Queste modifiche non sono state eseguite da Codex e non vengono incluse fra
gli interventi documentati sopra. Sono state lasciate intatte.

Questo riepilogo è salvato in `docs/codex_review_1.md`.

## 11. Pianificazione reversibile delle azioni umane

### Obiettivo e comportamento

Il giocatore può esplorare Grinta e tipo di azione prima di consumare risorse.
Le anteprime vengono calcolate dal backend usando le decisioni legali e il
command bus esistenti. La vista autoritativa resta separata dall'anteprima:
scegliere Grinta o azione nell'interfaccia non registra subito un comando nella
partita. La conferma successiva invia insieme le scelte preparatorie e la
selezione finale. Giocare davvero una carta o spendere un Gancio è invece una
conferma che modifica lo stato, non una semplice anteprima.

### Backend

- Nuovo `backend/src/dope_engine/application/human_planning.py`:
  `is_preparatory_selection` ammette selezioni non vuote di
  `choose_grit_action` e `choose_action_type`, oppure il passaggio vuoto, se
  consentito, di Marketing, lancio Poker e potenziamento con carta Cliente.
  Il passaggio di `spend_link_for_extra_action` è preparatorio solo prima
  dell'azione principale: dopo l'azione terminerebbe realmente il round.
- `GameService.answer_sequence` in `application/game_service.py` valida
  proprietario, cardinalità e assenza di duplicati; i passaggi intermedi
  devono essere preparatori. Usa `_bus.dispatch` e aggiorna la decisione a
  ogni passo, accumulando eventi e comandi. La cronologia viene aggiornata
  solo a sequenza completata e mai con `preview=True`.
- L'endpoint di risposta continua a utilizzare il meccanismo esistente di
  salvataggio dello stato e undo, ma ora riceve l'intera sequenza: l'undo
  della richiesta torna allo stato precedente alla sequenza.
- La simulazione non deve attraversare azioni sul tabellone né decisioni di
  un altro giocatore; non deve consumare carte, Ganci o cronologia di replay.
  Questi vincoli sono essenziali anche in una futura reimplementazione.

### Contratto HTTP e procedura per un client

In `adapters/http/schemas.py` aggiunti `PlanDecisionRequest` e il campo
opzionale `AnswerDecisionRequest.preparatory_selections` (default `[]`). Entrambe
le liste di scelte preparatorie hanno al massimo 8 elementi.

1. Leggere la vista autoritativa con `GET /api/v1/games/{game_id}/view` e
   parametro `player_id`. Conservare il suo `pending_decision.decision_id`.
2. Chiamare `POST /api/v1/games/{game_id}/decisions/plan` con:

   ```json
   {"player_id":"player_0","decision_id":"<id autoritativo>","selections":[]}
   ```

3. La risposta contiene `view` (anteprima), `prefix` (sequenza preparatoria
   effettiva, inclusi passaggi automatici), `optional` (Ganci/Marketing/Poker,
   ciascuno con propria vista e prefisso), `grit` (decisione, prefisso e
   `action_options` per valore), `selected_grit` e `selected_action`.
4. Per cambiare anteprima, inviare a `/decisions/plan` il prefisso opportuno
   seguito dagli `option_id` ricevuti. Non costruire gli ID né dedurre azioni
   legali nel client. Il backend salta le opportunità facoltative passando
   solo quando ciò è preparatorio; il percorso interno è limitato a 12 passi.
5. Per confermare, chiamare `POST /api/v1/games/{game_id}/decisions/answer`:

   ```json
   {
     "player_id":"player_0",
     "decision_id":"<id autoritativo originale>",
     "preparatory_selections":[["<opzione preparatoria>"]],
     "selected_option_ids":["<opzione finale>"]
   }
   ```

   Usare il prefisso della scelta opzionale quando si conferma da quella
   vista. Non inviare il `decision_id` simulato al posto di quello originale.
6. Applicare la vista confermata e proseguire con l'avanzamento dei bot come
   nel flusso esistente. Una decisione iniziale scaduta produce HTTP 409;
   giocatore errato o percorso/selezione non validi producono HTTP 400 nei
   controlli descritti. I fallimenti di dominio nella risposta definitiva
   mantengono il formato `ok: false` con errore.

Il nuovo endpoint è implementato in `adapters/http/app.py`; restituisce un
dizionario senza uno schema Pydantic di risposta dedicato. Il tipo frontend
è `HumanActionPlan` in `frontend/src/types.ts`. `frontend/src/api.ts` aggiunge
`planDecision` ed estende `answerDecision` mantenendo il prefisso vuoto come
default. I client che inviano una sola scelta restano supportati. Il formato
dei salvataggi non cambia; il replay conserva i singoli comandi confermati,
non le richieste di anteprima.

### Stato e interfaccia frontend

- Nuovo `frontend/src/useHumanActionPlan.ts`: conserva il piano con chiave
  `game_id:revision:decision_id`, gestisce caricamento/errori e invalida le
  risposte asincrone superate tramite contatore. Si attiva sulle decisioni
  supportate durante il turno umano, fuori dalla riproduzione dei bot.
- `App.tsx` distingue `rawView` autoritativa da `planner.view`, usata per la
  visualizzazione. Le selezioni vengono azzerate al cambio di piano/decisione;
  invii durante caricamento o richiesta già in corso vengono bloccati.
  L'animazione Evasione usa la vista autoritativa precedente alla conferma.
- Nuovo `components/ActionChooser.tsx`: box Grinta e sei azioni (Piazza,
  Sposta, Acquista, Vendi, Corrompi, Compra), con icona ed etichetta. Permette
  di preselezionare l'azione prima della Grinta; compatibilità e disponibilità
  derivano da `grit.action_options` restituito dal backend.
- Pulsanti Ganci, Marketing e Poker sempre visibili, abilitati solo quando
  l'opportunità è disponibile; aprono la relativa vista del piano. Fine turno
  è abilitato quando il piano resta sulla decisione di Gancio e può passare,
  non durante una scelta opzionale Marketing/Poker.
- La freccia «Torna indietro» chiude prima la scelta opzionale, poi cancella
  selezioni sul tabellone/corruzione, quindi rimuove l'ultima scelta non vuota
  del prefisso; può infine azzerare l'azione preselezionata o richiamare l'undo
  autoritativo se disponibile. Sostituisce il pulsante undo separato.
- `App.css`: contenitore comandi scuro con istruzioni in alto a destra,
  Grinta/azioni in box rossi, pulsanti opzionali da 114 × 114 px, scorrimento
  orizzontale del contenuto quando necessario. Azioni più compatte sotto
  1300 px; ulteriore misura della toolbar sotto 1700 px. Non equivale a una
  revisione responsive completa.
- Il banner del turno bot è ora posizionato rispetto al contenitore comandi
  (`position: absolute`), con `TurnPlayback` spostato al suo interno.

## 12. Carte, evoluzione dei Criminali e risultati

### Carte nei popup

`DecisionPanel.tsx` mostra carte cliccabili in popup dedicati per Marketing e
potenziamento dell'azione, con pulsante «No, grazie». Nel Marketing con scelta
diretta degli effetti, il primo click apre il passaggio successivo della UI;
con `choose_marketing_card` invia la scelta della carta. Le carte Marketing
sono deduplicate per `card_id`. Il popup Poker ha ora attributi di dialogo
accessibile, come quelli nuovi. La larghezza delle immagini condivisa è
`clamp(130px, 13vw, 180px)` al posto di 90 px.

`HandDrawer.tsx` conserva l'apertura automatica per scarto, carta Rissa e
carta durante il Poker; lancio Poker, scelta Marketing e boost sono tolti
dall'elenco automatico perché hanno popup dedicati. La prop `autoOpen` consente
ad `App.tsx` di impedire l'apertura automatica quando il piano offre Marketing.

### Evoluzione dopo una vendita

In `application/legal_actions.py`, entrambe le opzioni di `evolve_sale_link`
includono ora `pawn_id`, `contact_id` e `spot_id` della prima evoluzione in
coda, oltre a `evolve`. `BoardView.tsx` usa quel `pawn_id` per evidenziare solo
il Criminale interessato. La classe `board-token--pawn-evolution` aggiunge
contorno e lampeggio dorati; con movimento ridotto resta l'evidenza statica.
Il pannello propone «Evolvi in Link» e «No, grazie», senza il vecchio titolo.
Quando ci sono più evoluzioni, il bersaglio segue la coda backend.

### Riepiloghi Poker e Rissa

`OutcomeModal.tsx` estende `PawnRow` con badge circolari W/L, verdi/rossi e con
nomi accessibili Vittoria/Sconfitta. Le righe dei vincitori/sconfitti di Poker
e Rissa usano i badge; i pareggi Poker conservano il messaggio del jackpot
riportato. Premi, Link Preti e arresti restano visibili.

Il Poker ordina le righe per combinazione e poi per colori raggruppati per
frequenza e priorità: arancione, grigio, azzurro, verde, rosa. La combinazione
`five_different` usa solo il rango della combinazione. Il vincitore e i
pareggi continuano a provenire dal backend. Attenzione per chi prosegue:
questa priorità di presentazione è duplicata in `POKER_COLOR_ORDER`; se cambia
`poker_color_tiebreak_order` in `data/game_config.json`, occorre riallinearla.

## 13. Stato finale della Retata e asset esterni

La prima versione del box Retata descritta nella sessione è stata ulteriormente
semplificata: `RaidBanner.tsx` usa `RAID_COPY` per titolo e requisito dei sette
criteri e non renderizza più l'immagine della carta, il numero turno o una
scritta di vantaggio/pareggio. Le squadre mantengono pedine, nomi dei colori,
unità e totali; il vantaggio è verde e durante `tip_off` appare «Squadre
provvisorie». Titolo e requisito sono a 1,15 rem. Il paragrafo aggiunto al
README conserva ancora la parola «carta»: è una descrizione precedente alla
semplificazione grafica, non prova che l'immagine sia tuttora mostrata.

Gli asset non attribuiti a Codex nella sezione 10 fanno parte dell'inventario
da preservare per riprodurre esattamente il workspace:

| File sotto `frontend/src/assets/` | Dimensione attuale in byte |
|---|---:|
| `price/price_CAMA.png` | 7387 |
| `price/price_GUFO.png` | 5467 |
| `price/price_POLPO.png` | 8002 |
| `price/price_RANA.png` | 7136 |
| `music_dope/Arcade Hustle.mp3` | 3701196 |

I quattro PNG sostituiscono binari già tracciati; l'MP3 è nuovo. La revisione
dei binari non permette di ricostruire gli interventi grafici dalla sola
documentazione: usare questi file esatti. Il glob già presente in
`frontend/src/assets/index.ts` include automaticamente tutti gli MP3 della
cartella nella playlist; non serve modificare `useBackgroundMusic.ts`.

## 14. Inventario e ordine per riprodurre le modifiche

Partire dal commit base indicato all'inizio. Per riprodurre le funzionalità
senza il futuro commit, seguire quest'ordine, conservando separazione tra
regole backend e presentazione frontend:

| Gruppo | File modificati o nuovi |
|---|---|
| Calcolo Retata | `backend/src/dope_engine/rules/raids.py`, `application/views.py` sotto lo stesso package |
| Pianificazione e metadati evoluzione | `backend/src/dope_engine/application/human_planning.py` (nuovo), `game_service.py`, `legal_actions.py` nella stessa directory |
| Trasporto HTTP | `backend/src/dope_engine/adapters/http/schemas.py`, `app.py` |
| Test backend | `backend/tests/unit/test_raids.py`, `backend/tests/integration/test_http_app.py`, `test_human_planning.py` (nuovo) nella stessa directory integration |
| Client e coordinamento UI | `frontend/src/types.ts`, `api.ts`, `App.tsx`, `useHumanActionPlan.ts` (nuovo) |
| Scelta azioni, carte e pedine | `frontend/src/components/ActionChooser.tsx` (nuovo), `DecisionPanel.tsx`, `BoardView.tsx`, `HandDrawer.tsx` |
| Toolbar, Retata e riepiloghi | `frontend/src/components/ToolbarButtonContent.tsx` (nuovo), `ActionLogDrawer.tsx`, `SkillsDrawer.tsx`, `RaidBanner.tsx`, `OutcomeModal.tsx` |
| Grafica e coordinate | `frontend/src/App.css`, `popup-theme.css` (nuovo), `board-layout.ts` |
| Asset | I cinque file elencati nella sezione 13 |
| Documentazione | `README.md`, `docs/codex_review_1.md` (nuovo e ancora non tracciato) |

Tutti i nomi di componenti nella tabella appartengono a
`frontend/src/components/`. Nessuna dipendenza aggiunta, nessun lockfile,
migrazione salvataggi o configurazione di deploy modificati nel diff esaminato.
Per un trasferimento fedele servono anche i file nuovi: `git diff` da solo
non contiene gli untracked e non è un pacchetto completo delle modifiche.

## 15. Verifiche attuali e comandi ripetibili

Durante questo aggiornamento documentale del 28 settembre è stato eseguito,
dalla directory `backend`, il seguente comando:

```powershell
python -m pytest tests/integration/test_human_planning.py tests/unit/test_raids.py tests/integration/test_http_app.py -q --basetemp=.pytest_tmp_review_20260928
```

Risultato: **86 test superati in 2,45 secondi**. I nuovi test di pianificazione
verificano corrispondenza delle azioni per Grinta, assenza di mutazioni della
vista e del replay nelle anteprime, selezione finale invalida, conferma e undo
della sequenza, Ganci prima/dopo l'azione principale, Marketing con una/due
carte, rifiuto di passaggi non preparatori e giocatore errato, ordine dei
Criminali da evolvere e avvio effettivo del Poker solo alla conferma.

In questo aggiornamento non sono stati rieseguiti suite completa, build,
lint, mypy o test browser. I risultati della sezione 7 appartengono alla
stesura precedente. Per una verifica completa successiva, usare Python 3.12+
con dipendenze del progetto e quelle di test già installate nell'ambiente;
il test client HTTP richiede anche `httpx` (disponibile nell'ambiente usato).

Comandi dalla root, con dipendenze già installate:

```powershell
Push-Location backend
python -m pytest --basetemp=.pytest_tmp_review_full_20260928
python -m ruff check .
python -m mypy src
Pop-Location
Push-Location frontend
npm run build
npm run lint
Pop-Location
```

Le directory temporanee dedicate evitano di riusare la `.pytest_tmp` che
aveva dato problemi di permessi; non costituiscono dati di gioco da pubblicare.

## 16. Scenari manuali per l'agente successivo

Avviare da root `python tools/run_backend.py` e, in un secondo terminale,
da `frontend` eseguire `npm run dev`. Aprire `http://127.0.0.1:5173/game/`.
Non riavviare un server in uso senza considerare le partite mantenute in memoria.

1. In una nuova partita, al turno umano provare Grinta prima dell'azione e
   azione prima della Grinta; controllare opzioni disabilitate e bersagli
   evidenziati. Tornare indietro prima di confermare e confrontare vista
   autoritativa/replay: le sole anteprime non devono cambiarli.
2. Con opportunità disponibili, aprire/chiudere Ganci, Marketing e Poker;
   verificare le carte ingrandite, «No, grazie» e la mancata apertura
   automatica della mano per i popup dedicati. La conferma di carta/Gancio
   deve invece aggiornare davvero lo stato. I fixture del test di planning
   forniscono stati riproducibili con seed 2 per questi casi.
3. Dopo l'azione principale controllare che il piano non passi automaticamente
   la decisione Gancio e che «Fine turno» consenta di concludere esplicitamente.
   Provare la freccia sia sulle scelte locali sia quando è disponibile l'undo.
4. Provocare una vendita con evoluzione e verificare contorno/lampeggio solo
   sulla pedina indicata; con più evoluzioni il bersaglio deve cambiare in
   ordine. Verificare anche la preferenza di movimento ridotto.
5. Controllare Poker con combinazioni pari ma colori diversi, pareggio vero,
   premio e arresto; controllare badge W/L anche nella Rissa. Confrontare
   sempre gli esiti con i dati ricevuti dal backend.
6. Verificare i sette criteri Retata, parità e criterio Merci inverso, cambio
   squadre durante Soffiata e aggiornamenti durante i bot. Controllare la
   sidebar e i comandi a 1440, 1280 e 1024 px, oltre a schermi bassi e zoom:
   le precedenti verifiche grafiche non coprono automaticamente il nuovo box
   azioni. Verificare toolbar, tre coordinate prezzo e nuovo brano musicale.

Questo aggiornamento ha modificato esclusivamente il presente Markdown e
ha eseguito i test mirati indicati. Commit, push GitHub e deploy Render non
sono stati eseguiti.

## 17. Verifiche prima della pubblicazione su GitHub

Successivamente all'aggiornamento documentale, l'utente ha richiesto commit e
push su `https://github.com/valerioparuscio/godope_4`. Verificati `origin` e
`main` remoto: entrambi corrispondono al repository e al commit base indicati
all'inizio del documento.

Controlli eseguiti il 28 settembre 2026 prima del commit:

- Suite backend completa: `python -m pytest -q --basetemp=.pytest_tmp_publish_20260928`
  dalla directory `backend`: **503 superati in 7,37 secondi**.
- `python -m ruff check .` da `backend`: superato.
- `python -m mypy src` da `backend`: nessun problema in 54 file sorgente.
- `npm run build` da `frontend`: TypeScript e build Vite superati.
- `npm run lint` da `frontend`: nessun errore; sei avvisi su Fast Refresh e
  dipendenze degli hook in `SkillUsePopup.tsx`, `TurnPlayback.tsx` e `App.tsx`.
- `git diff --check`: nessun errore di whitespace.

Il workflow esistente `.github/workflows/deploy-pages.yml` si attiva con
modifiche al frontend pubblicate su `main`: esegue il deploy GitHub Pages e
un job che aggiorna `game/` nel repository `valerioparuscio/dope`. Il successo
di questi job va verificato separatamente dal successo del push. Nessuna
configurazione Render è stata modificata; questi controlli non certificano
un deploy del backend su Render.
