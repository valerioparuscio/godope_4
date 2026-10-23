# Studi con simulazioni: Job e Retate (Easy Price)

Dal 2026-10-20 al 2026-10-22 sono state fatte simulazioni bot contro bot per capire quanto conta la sequenza dei Job,
come conviene raggrupparli nei livelli e come interagiscono con le Retate. Questa cartella raccoglie tutto in ordine.

| Cosa | Dove |
|---|---|
| Risultati e conclusioni, scritti | [`JOBS_RETATE_EASY_PRICE.md`](JOBS_RETATE_EASY_PRICE.md) |
| Tabelle complete di ogni analisi (generate dagli script) | [`reports/`](reports/) |
| Script di simulazione e analisi, con le istruzioni | [`tools/analysis/`](../../tools/analysis/README.md) |
| Dati grezzi delle simulazioni (non versionati) | `analysis_data/` |

I dati grezzi pesano circa 250 MB e si rigenerano con `tools/analysis/simulate.py`; per questo `analysis_data/` è nel
`.gitignore`. La tabella sotto dice quale file è quale run, così si può rifare.

## Dati grezzi (`analysis_data/`)

Una riga JSON per partita. Formato v1 / v2 / v3: vedi [`tools/analysis/README.md`](../../tools/analysis/README.md).

| File | Layout dei Job | Bot | Partite | Seed | Fmt | Per cosa |
|---|---|---|---:|---|---|---|
| `current_layout/heuristic_v1_seeds1000-3999.jsonl` | attuale | euristico | 3.000 | 1000-3999 | v1 | peso dei Job iniziali (report 01-03), bankability, Retate |
| `current_layout/heuristic_v2_seeds100000-101499.jsonl` | attuale | euristico | 1.500 | 100000-101499 | v2 | stato lasciato dai Job (07), confronto tra layout (10) |
| `layout_A/heuristic_v2_seeds300000-300999.jsonl` | A | euristico | 1.000 | 300000-300999 | v2 | stato dopo i Job (08), confronto (10) |
| `layout_A/heuristic_v3_seeds500000-501999.jsonl` | A | euristico | 2.000 | 500000-501999 | v3 | Retate, Job attivo, preparazione, confronto appaiato con C |
| `layout_C/heuristic_v2_seeds400000-400999.jsonl` | C | euristico | 1.000 | 400000-400999 | v2 | come A |
| `layout_C/heuristic_v3_seeds500000-501999.jsonl` | C | euristico | 2.000 | 500000-501999 | v3 | come A (stessi seed di A) |
| `reward_preference/mix_v2_seeds200000-201199.jsonl` | attuale | euristico con preferenza fissa sul premio (`mix:`) | 1.200 | 200000-201199 | v2 | valore delle colonne di premio (06); una partita con errore del bot è esclusa |
| `bot_variants/jobs_hi_v1_seeds20000-20699.jsonl` | attuale | euristico, Job inseguiti con più forza (`job_progress_bonus=6, committed_job_bonus=10`) | 700 | 20000-20699 | v1 | robustezza (04) |
| `bot_variants/jobs_lo_v1_seeds30000-30699.jsonl` | attuale | euristico, Job inseguiti con meno forza (`0,75` e `1,25`) | 700 | 30000-30699 | v1 | robustezza (05) |
| `raid_x4/layout_A_raidx4_seeds500000-501999.jsonl` | A | euristico con `raid_criterion_bonus=4` | 2.000 | 500000-501999 | v3 | test «Retata ×4» (30-43) |
| `raid_x4/layout_C_raidx4_seeds500000-501999.jsonl` | C | euristico con `raid_criterion_bonus=4` | 2.000 | 500000-501999 | v3 | come sopra |

Definizione dei layout (`tools/analysis/job_layouts.py`):

| Layout | Livello 1 | Livello 2 | Livello 3 |
|---|---|---|---|
| attuale (`data/jobs.json`) | Vinci 1 Rissa (01), 1 Cop/Fed (02), Criminali in 6 Hoods (07) | 2 Rats (04), 4 Dope nel Covo (05), 4 Link (06) | 2 Chip Poker (03), 10 Criminali fuori (08), 30 dollari (09) |
| A | 01, 02, 07 | 05, 06, **08** | 03, **04**, 09 |
| C | 02, 07, **08** | **01**, 05, 06 | 03, **04**, 09 |

## Report (`reports/`)

Ogni file è il testo stampato da uno script; `python tools/analysis/make_reports.py` li rigenera tutti.

| Report | Contenuto |
|---|---|
| 01-03 | Layout attuale: peso del primo Job di ogni livello sui punti; quanto passa dal numero di Job completati; valore di ogni Job completato |
| 04-05 | Gli stessi risultati con bot più e meno interessati ai Job (robustezza) |
| 06 | Valore dei premi dei Job (Link, Skill, 2 carte, 3$) |
| 07-09 | Stato lasciato dai Job: denaro, pedine in base, azioni, Poker; intorno al completamento (attuale, A, C) |
| 10 | Confronto tra layout senza Retate: equilibrio dei livelli e varianza spiegata |
| 11-13 | «Bankability»: Job già soddisfatti alla rivelazione, completamento per posizione nella pila e per round, round tra rivelazione e completamento |
| 14 | Costo delle Retate: macchie, pareggi, quante volte si viene presi |
| 15-17 | Interazione Job × Retata sui punti, con verifica fuori campione (attuale, A, C) |
| 18-20 | La matrice teorica Job × Retata contro la simulazione (attuale, A, C) |
| 21-22 | Per ogni Retata e posizione, l'effetto del Job iniziale sui punti, per livello (A, C) |
| 23 | Job attivo a inizio turno × Retata del turno: probabilità di sfuggire, di completare il Job, punti |
| 24 | Le Retate preparano i Job futuri? Risorse accumulate e Job già soddisfatti alla rivelazione |
| 25-27 | Quota di varianza dei punti spiegata da Job iniziali, sequenza di Retate e interazione; confronto appaiato A contro C |
| 28 | Quota spiegata dall'esito delle Retate (quante volte preso, macchie) |
| 30-43 | Gli stessi test con bot che pesano la Retata quattro volte di più (30-40, 43), e confronto appaiato con i bot normali sugli stessi seed (41-42) |

## Come si rifà

```text
python tools/analysis/simulate.py --layout A --policy heuristic --seeds 500000-501999 --out analysis_data/layout_A/heuristic_v3_seeds500000-501999.jsonl
python tools/analysis/make_reports.py
```

I bot sono deterministici dato il seed (`simulate.py` fissa `PYTHONHASHSEED`), quindi lo stesso comando dà gli stessi dati.
