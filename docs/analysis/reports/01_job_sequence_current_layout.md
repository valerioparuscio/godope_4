# Sequenza dei Job e punti finali — Easy Price, bot euristici

3000 partite (12000 giocatori-partita), file `heuristic_v1_seeds1000-3999.jsonl`.

## 1. Quadro generale
- Punti finali per giocatore: media 7.80, deviazione standard 4.09; nella stessa partita la deviazione standard tra i 4 giocatori è 3.41.
- Job completati per giocatore: media 2.36; nessun Job: 16% dei giocatori.
- Punti medi per numero di Job completati: 0 Job → 3.44 pt (vince 1%, n=1962); 1 Job → 5.09 pt (vince 5%, n=2669); 2 Job → 6.94 pt (vince 14%, n=2296); 3 Job → 8.77 pt (vince 27%, n=1933); 4 Job → 10.85 pt (vince 48%, n=1499); 5 Job → 13.13 pt (vince 68%, n=958); 6 Job → 15.60 pt (vince 86%, n=444); 7 Job → 18.36 pt (vince 93%, n=169); 8 Job → 20.59 pt (vince 93%, n=58); 9 Job → 22.25 pt (vince 100%, n=12)
- Posizione al tavolo (punti rispetto alla media del tavolo): posto 0: +0.00 ±0.13 pt, vince 25.1%; posto 1: +0.01 ±0.13 pt, vince 25.4%; posto 2: -0.13 ±0.13 pt, vince 23.4%; posto 3: +0.12 ±0.13 pt, vince 26.1%
- In media ogni Job completato in più vale circa +1.59 punti (a parità di partita).

## 2. Il primo Job di ogni livello (quello rivelato a inizio partita)
Punti rispetto alla media del proprio tavolo, e quota di vittorie (25% = pari). ± = intervallo di confidenza al 95%.

**Livello 1**

| Job rivelato per primo | n | punti vs tavolo | vittorie | Job completati | lo completa |
|---|---:|---:|---:|---:|---:|
| Vinci 1 Rissa (01) | 4074 | -0.23 ±0.10 | 24.1% ±1.1 | 2.26 | 56% |
| Abbi 1 Cop/Fed (02) | 3911 | +0.04 ±0.10 | 25.4% ±1.1 | 2.37 | 84% |
| Criminali in 6 Hoods (07) | 4015 | +0.19 ±0.09 | 25.5% ±1.1 | 2.44 | 72% |

- Vinci 1 Rissa − Abbi 1 Cop/Fed: -0.26 ±0.17 punti  ← **significativo**
- Vinci 1 Rissa − Criminali in 6 Hoods: -0.42 ±0.16 punti  ← **significativo**
- Abbi 1 Cop/Fed − Criminali in 6 Hoods: -0.16 ±0.16 punti

**Livello 2**

| Job rivelato per primo | n | punti vs tavolo | vittorie | Job completati | lo completa |
|---|---:|---:|---:|---:|---:|
| 2 Rats (04) | 4048 | -0.51 ±0.09 | 21.2% ±1.0 | 2.20 | 36% |
| 4 Dope nel Covo (05) | 3976 | +0.15 ±0.10 | 25.9% ±1.1 | 2.46 | 53% |
| 4 Link (06) | 3976 | +0.36 ±0.09 | 28.0% ±1.1 | 2.41 | 43% |

- 2 Rats − 4 Dope nel Covo: -0.66 ±0.16 punti  ← **significativo**
- 2 Rats − 4 Link: -0.87 ±0.16 punti  ← **significativo**
- 4 Dope nel Covo − 4 Link: -0.21 ±0.16 punti  ← **significativo**

**Livello 3**

| Job rivelato per primo | n | punti vs tavolo | vittorie | Job completati | lo completa |
|---|---:|---:|---:|---:|---:|
| 2 Chip Poker (03) | 3969 | -0.48 ±0.09 | 21.8% ±1.1 | 2.08 | 24% |
| 10 Criminali fuori (08) | 4006 | +1.47 ±0.09 | 38.5% ±1.1 | 3.29 | 71% |
| 30 dollari (09) | 4025 | -1.00 ±0.09 | 14.7% ±0.9 | 1.70 | 14% |

- 2 Chip Poker − 10 Criminali fuori: -1.95 ±0.16 punti  ← **significativo**
- 2 Chip Poker − 30 dollari: +0.52 ±0.15 punti  ← **significativo**
- 10 Criminali fuori − 30 dollari: +2.47 ±0.15 punti  ← **significativo**

## 3. Quanto pesa la sequenza nel suo insieme (modello con effetto-partita)
- Solo la posizione al tavolo: R² nella partita 0.06%.
- Posizione + Job iniziali dei 3 livelli: R² 12.31% (corretto 12.25%); effetto congiunto dei Job iniziali: χ²(6) = 1320.1, p = 4.9e-282.
  - solo livello 1: χ²(2) = 32.7, p = 7.91e-08
  - solo livello 2: χ²(2) = 127.0, p = 2.64e-28
  - solo livello 3: χ²(2) = 1131.3, p = 2.21e-246
- Posizione + primo e secondo Job di ogni livello: R² 12.85% (corretto 12.74%).
  - il secondo Job del livello 1 (dato il primo): χ²(2) = 17.1, p = 0.000189
  - il secondo Job del livello 2 (dato il primo): χ²(2) = 34.6, p = 3.05e-08
  - il secondo Job del livello 3 (dato il primo): χ²(2) = 6.5, p = 0.038
- Posizione + ordine completo (6 ordini per livello): R² 12.89% (corretto 12.76%).

## 4. Le 27 combinazioni di Job iniziali (livello 1 · livello 2 · livello 3)
Differenza tra la migliore e la peggiore: 4.77 punti (con rumore di campionamento ±0.41).
| combinazione | n | punti vs tavolo | vittorie |
|---|---:|---:|---:|
| 01·06·08 | 464 | +2.47 ±0.31 | 47.1% |
| 02·06·08 | 437 | +2.27 ±0.32 | 48.2% |
| 07·05·08 | 432 | +1.49 ±0.37 | 38.2% |
| 01·04·08 | 460 | +1.47 ±0.34 | 37.8% |
| 07·06·08 | 452 | +1.44 ±0.32 | 38.1% |
| 02·04·03 | 414 | -1.14 ±0.33 | 16.1% |
| 01·06·09 | 411 | -1.29 ±0.34 | 13.8% |
| 01·04·03 | 481 | -1.59 ±0.33 | 15.0% |
| 02·04·09 | 412 | -1.72 ±0.27 | 8.5% |
| 01·04·09 | 475 | -2.30 ±0.26 | 7.8% |
Test «le 27 combinazioni sono tutte uguali»: χ²(26) = 1679.5, p = 0. R² del modello a 27 combinazioni: 13.98% (corretto 13.78%).
Interazioni tra i tre livelli (oltre agli effetti singoli): χ²(20) ≈ 169.3, p ≈ 1.18e-25.

## 5. Perché: completamento dei Job in base alla posizione nella pila
| Job | lo completa se è il 1° | se è il 2° | se è il 3° | turno medio di completamento |
|---|---:|---:|---:|---:|
| Vinci 1 Rissa (liv. 1) | 56% | 32% | 17% | 2.06 |
| Abbi 1 Cop/Fed (liv. 1) | 84% | 47% | 22% | 2.06 |
| Criminali in 6 Hoods (liv. 1) | 72% | 38% | 19% | 2.38 |
| 2 Rats (liv. 2) | 36% | 13% | 3% | 2.49 |
| 4 Dope nel Covo (liv. 2) | 53% | 3% | 1% | 1.61 |
| 4 Link (liv. 2) | 43% | 16% | 2% | 2.49 |
| 2 Chip Poker (liv. 3) | 24% | 16% | 4% | 2.33 |
| 10 Criminali fuori (liv. 3) | 71% | 11% | 3% | 2.40 |
| 30 dollari (liv. 3) | 14% | 6% | 3% | 2.25 |

## 6. Da dove viene la differenza di punti (primo Job del livello 3)
| primo Job liv. 3 | money | clean | stained | maj | chip | skill | totale |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2 Chip Poker | -0.17 ±0.03 | -0.14 ±0.05 | -0.14 ±0.03 | -0.06 ±0.02 | +0.11 ±0.02 | -0.07 ±0.02 | -0.48 ±0.09 |
| 10 Criminali fuori | -0.04 ±0.03 | +0.39 ±0.06 | +0.53 ±0.03 | +0.26 ±0.02 | +0.11 ±0.02 | +0.22 ±0.02 | +1.47 ±0.09 |
| 30 dollari | +0.21 ±0.03 | -0.25 ±0.05 | -0.39 ±0.03 | -0.20 ±0.02 | -0.22 ±0.02 | -0.15 ±0.02 | -1.00 ±0.09 |

