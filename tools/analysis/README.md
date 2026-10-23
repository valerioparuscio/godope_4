# Strumenti per gli studi su Job e Retate

Simulazioni bot contro bot e analisi dei risultati (Easy Price, ma `simulate.py` accetta anche `standard` e `simple`).
I risultati degli studi sono in [`docs/analysis/`](../../docs/analysis/README.md); i dati grezzi in `analysis_data/`
(non versionata: grande e rigenerabile).

## Come si lavora

```text
python tools/analysis/simulate.py --layout A --policy heuristic --seeds 500000-501999 \
       --out analysis_data/layout_A/heuristic_v3_seeds500000-501999.jsonl
python tools/analysis/make_reports.py            # rigenera i report in docs/analysis/reports/
python tools/analysis/make_reports.py 27 41      # solo quelli il cui nome inizia per 27 o 41
python tools/analysis/<script>.py <dati.jsonl>   # una analisi singola, stampa su schermo
```

`simulate.py` esegue una partita per seed con 4 bot e scrive una riga JSON per partita. Un run si può riprendere o
estendere: i seed già presenti nel file di uscita vengono saltati.

| Opzione | Valori |
|---|---|
| `--ruleset` | `easy_price` (default), `standard`, `simple` |
| `--layout` | `current` (default), `A`, `C`: assegnazione dei 9 Job ai 3 livelli, vedi `job_layouts.py` |
| `--policy` | `heuristic`; `heuristic:chiave=valore,...` per cambiare i pesi del bot (es. `heuristic:raid_criterion_bonus=4`); `mix:link,skill,two_cards,money` per l'esperimento sul valore dei premi |
| `--seeds` | `primo-ultimo`, estremi inclusi |
| `--workers` | processi paralleli (24 di default; circa 0,6 partite al secondo sulla macchina di sviluppo) |

Lo stesso seed dà lo stesso setup e la stessa sequenza di Retate qualunque siano layout e policy, quindi due run sugli
stessi seed sono confrontabili. Con `PYTHONHASHSEED` fisso (lo imposta `simulate.py` per i suoi processi) anche le scelte dei bot sono
riproducibili: senza, il codice dei bot itera su insiemi di stringhe e la stessa partita può andare diversamente a ogni
esecuzione.

## Formato dei dati

Una riga per partita. Le versioni successive aggiungono campi: gli script che usano solo i campi comuni leggono tutte.

| Versione | Prodotta da | Contenuto |
|---|---|---|
| v1 | primi run (`sim_jobs.py`, non più presente) | pile dei Job di ogni giocatore, completamenti (turno, round, passo), premi scelti, Retate e macchie, punteggio finale |
| v2 | secondo run | in più: istantanea di ogni giocatore a inizio di ogni round (denaro, pedine per ruolo, carte, chip, azioni disponibili, passato), stato subito dopo ogni completamento, lanci di Poker |
| v3 | `simulate.py` | in più: Retata corrente e Job attivo di ogni livello a ogni round, Cop/Fed nel Covo; campi `version`, `layout`, `policy` |

Gli script che hanno bisogno delle istantanee (`aftermath.py`, `activejob_raid.py`, `prepare.py`, `paired_policies.py`)
richiedono almeno v2, quelli che parlano di Retata corrente richiedono v3.

## Script

| Script | Cosa fa |
|---|---|
| `simulate.py`, `job_layouts.py` | le simulazioni; i layout alternativi dei Job |
| `make_reports.py` | rigenera tutti i report |
| `analyze_jobs.py` | peso del primo Job di ogni livello sui punti, confronti a coppie, quota di varianza spiegata, perché (completamento, componenti del punteggio); contiene le funzioni statistiche usate dagli altri |
| `extra_jobs.py`, `job_value.py` | quanto dell'effetto passa dal numero di Job completati; cosa porta con sé aver completato ciascun Job |
| `aftermath.py` | in che stato lascia un Job: denaro, pedine in base, azioni, Poker; intorno al completamento |
| `compare_tiers.py` | confronto tra layout senza Retate (equilibrio dei livelli, varianza spiegata) |
| `reward_analysis.py` | quale colonna di premio vale di più (bot con preferenza fissa) |
| `bankability.py`, `hazard.py`, `delay.py` | Job soddisfatti già alla rivelazione, completamento per round e per posizione nella pila, round tra rivelazione e completamento |
| `raidlib.py`, `lib3.py` | caricamento: giocatore-partita con Retate e giocatore-turno con Job attivo |
| `raid_desc.py` | quanto costano le Retate (macchie, pareggi, quante volte si viene presi) |
| `raid_tables.py` | per ogni Retata (e posizione 1ª/2ª/3ª) l'effetto del Job iniziale sui punti, per livello |
| `raid_job_interaction.py` | interazione Job × Retata, con verifica fuori campione (con `-` al posto del secondo file divide un solo dataset: seed pari per allenare, dispari per verificare) |
| `variance_shares.py`, `paired_AC.py`, `outcome_share.py` | quota di varianza dei punti spiegata da Job iniziali, sequenza di Retate, interazione; confronto appaiato di due layout; effetto dell'esito delle Retate |
| `theory_matrix.py`, `theory_check.py` | la matrice teorica Job × Retata (−5..+5) e il confronto con la simulazione |
| `activejob_raid.py` | Job attivo a inizio turno × Retata del turno |
| `prepare.py` | le Retate preparano i Job futuri? Risorse accumulate e Job già soddisfatti alla rivelazione |
| `paired_policies.py` | stesso layout e stessi seed, due policy dei bot: cosa cambia |

## Statistica

Tutti i confronti sono dentro la partita (punti meno la media del tavolo), con incertezze raggruppate per partita (i
quattro giocatori di una partita non sono indipendenti). Le quote di varianza sono fuori campione (5 gruppi di partite).
I confronti appaiati usano un bootstrap sui seed.
