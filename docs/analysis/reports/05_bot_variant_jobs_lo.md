# Sequenza dei Job e punti finali — Easy Price, bot euristici

700 partite (2800 giocatori-partita), file `jobs_lo_v1_seeds30000-30699.jsonl`.

## 1. Quadro generale
- Punti finali per giocatore: media 6.51, deviazione standard 3.42; nella stessa partita la deviazione standard tra i 4 giocatori è 2.76.
- Job completati per giocatore: media 1.59; nessun Job: 27% dei giocatori.
- Punti medi per numero di Job completati: 0 Job → 3.53 pt (vince 4%, n=761); 1 Job → 5.27 pt (vince 13%, n=820); 2 Job → 7.30 pt (vince 30%, n=543); 3 Job → 9.02 pt (vince 47%, n=358); 4 Job → 11.09 pt (vince 64%, n=179); 5 Job → 13.38 pt (vince 86%, n=92); 6 Job → 16.11 pt (vince 89%, n=35); 7 Job → 20.12 pt (vince 100%, n=8); 8 Job → 20.25 pt (vince 100%, n=4)
- Posizione al tavolo (punti rispetto alla media del tavolo): posto 0: +0.00 ±0.22 pt, vince 24.3%; posto 1: -0.01 ±0.22 pt, vince 25.4%; posto 2: +0.03 ±0.24 pt, vince 26.2%; posto 3: -0.02 ±0.23 pt, vince 24.2%
- In media ogni Job completato in più vale circa +1.48 punti (a parità di partita).

## 2. Il primo Job di ogni livello (quello rivelato a inizio partita)
Punti rispetto alla media del proprio tavolo, e quota di vittorie (25% = pari). ± = intervallo di confidenza al 95%.

**Livello 1**

| Job rivelato per primo | n | punti vs tavolo | vittorie | Job completati | lo completa |
|---|---:|---:|---:|---:|---:|
| Vinci 1 Rissa (01) | 923 | +0.05 ±0.18 | 26.7% ±2.3 | 1.62 | 49% |
| Abbi 1 Cop/Fed (02) | 965 | +0.16 ±0.16 | 26.1% ±2.2 | 1.82 | 82% |
| Criminali in 6 Hoods (07) | 912 | -0.22 ±0.16 | 22.1% ±2.3 | 1.33 | 32% |

- Vinci 1 Rissa − Abbi 1 Cop/Fed: -0.11 ±0.29 punti
- Vinci 1 Rissa − Criminali in 6 Hoods: +0.28 ±0.30 punti
- Abbi 1 Cop/Fed − Criminali in 6 Hoods: +0.38 ±0.27 punti  ← **significativo**

**Livello 2**

| Job rivelato per primo | n | punti vs tavolo | vittorie | Job completati | lo completa |
|---|---:|---:|---:|---:|---:|
| 2 Rats (04) | 928 | -0.17 ±0.16 | 24.1% ±2.2 | 1.58 | 29% |
| 4 Dope nel Covo (05) | 922 | +0.07 ±0.16 | 24.4% ±2.2 | 1.65 | 39% |
| 4 Link (06) | 950 | +0.11 ±0.16 | 26.4% ±2.2 | 1.54 | 33% |

- 2 Rats − 4 Dope nel Covo: -0.24 ±0.28 punti
- 2 Rats − 4 Link: -0.28 ±0.27 punti  ← **significativo**
- 4 Dope nel Covo − 4 Link: -0.04 ±0.27 punti

**Livello 3**

| Job rivelato per primo | n | punti vs tavolo | vittorie | Job completati | lo completa |
|---|---:|---:|---:|---:|---:|
| 2 Chip Poker (03) | 910 | -0.18 ±0.17 | 23.3% ±2.2 | 1.55 | 24% |
| 10 Criminali fuori (08) | 913 | +0.74 ±0.17 | 33.3% ±2.3 | 2.06 | 50% |
| 30 dollari (09) | 977 | -0.53 ±0.15 | 18.9% ±2.0 | 1.20 | 12% |

- 2 Chip Poker − 10 Criminali fuori: -0.91 ±0.29 punti  ← **significativo**
- 2 Chip Poker − 30 dollari: +0.35 ±0.27 punti  ← **significativo**
- 10 Criminali fuori − 30 dollari: +1.26 ±0.27 punti  ← **significativo**

## 3. Quanto pesa la sequenza nel suo insieme (modello con effetto-partita)
- Solo la posizione al tavolo: R² nella partita 0.00%.
- Posizione + Job iniziali dei 3 livelli: R² 4.72% (corretto 4.41%); effetto congiunto dei Job iniziali: χ²(6) = 100.7, p = 1.76e-19.
  - solo livello 1: χ²(2) = 9.9, p = 0.00696
  - solo livello 2: χ²(2) = 6.3, p = 0.0427
  - solo livello 3: χ²(2) = 91.1, p = 1.69e-20
- Posizione + primo e secondo Job di ogni livello: R² 4.90% (corretto 4.39%).
  - il secondo Job del livello 1 (dato il primo): χ²(2) = 0.7, p = 0.719
  - il secondo Job del livello 2 (dato il primo): χ²(2) = 2.6, p = 0.267
  - il secondo Job del livello 3 (dato il primo): χ²(2) = 1.0, p = 0.619
- Posizione + ordine completo (6 ordini per livello): R² 5.00% (corretto 4.39%).

## 4. Le 27 combinazioni di Job iniziali (livello 1 · livello 2 · livello 3)
Differenza tra la migliore e la peggiore: 3.05 punti (con rumore di campionamento ±0.90).
| combinazione | n | punti vs tavolo | vittorie |
|---|---:|---:|---:|
| 01·05·08 | 97 | +1.53 ±0.71 | 42.6% |
| 01·06·08 | 98 | +1.51 ±0.60 | 43.9% |
| 02·06·08 | 98 | +1.20 ±0.69 | 35.0% |
| 01·04·08 | 106 | +1.16 ±0.56 | 39.6% |
| 02·06·03 | 104 | +0.57 ±0.53 | 31.1% |
| 07·06·09 | 101 | -0.69 ±0.47 | 15.3% |
| 02·04·09 | 104 | -0.75 ±0.55 | 18.3% |
| 01·06·09 | 127 | -0.83 ±0.42 | 16.4% |
| 07·04·09 | 92 | -0.87 ±0.47 | 13.6% |
| 01·04·09 | 100 | -1.52 ±0.54 | 10.8% |
Test «le 27 combinazioni sono tutte uguali»: χ²(26) = 159.8, p = 3.26e-21. R² del modello a 27 combinazioni: 7.26% (corretto 6.29%).
Interazioni tra i tre livelli (oltre agli effetti singoli): χ²(20) ≈ 61.8, p ≈ 3.72e-06.

## 5. Perché: completamento dei Job in base alla posizione nella pila
| Job | lo completa se è il 1° | se è il 2° | se è il 3° | turno medio di completamento |
|---|---:|---:|---:|---:|
| Vinci 1 Rissa (liv. 1) | 49% | 18% | 6% | 2.08 |
| Abbi 1 Cop/Fed (liv. 1) | 82% | 26% | 7% | 2.01 |
| Criminali in 6 Hoods (liv. 1) | 32% | 14% | 4% | 2.48 |
| 2 Rats (liv. 2) | 29% | 9% | 1% | 2.49 |
| 4 Dope nel Covo (liv. 2) | 39% | 1% | 0% | 1.36 |
| 4 Link (liv. 2) | 33% | 10% | 1% | 2.52 |
| 2 Chip Poker (liv. 3) | 24% | 11% | 2% | 2.36 |
| 10 Criminali fuori (liv. 3) | 50% | 8% | 3% | 2.50 |
| 30 dollari (liv. 3) | 12% | 4% | 2% | 2.07 |

## 6. Da dove viene la differenza di punti (primo Job del livello 3)
| primo Job liv. 3 | money | clean | stained | maj | chip | skill | totale |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2 Chip Poker | -0.16 ±0.06 | +0.03 ±0.09 | -0.07 ±0.05 | -0.03 ±0.04 | +0.10 ±0.03 | -0.05 ±0.03 | -0.18 ±0.17 |
| 10 Criminali fuori | -0.13 ±0.06 | +0.17 ±0.08 | +0.27 ±0.06 | +0.23 ±0.04 | +0.08 ±0.03 | +0.12 ±0.03 | +0.74 ±0.17 |
| 30 dollari | +0.27 ±0.05 | -0.18 ±0.07 | -0.19 ±0.05 | -0.19 ±0.04 | -0.17 ±0.03 | -0.07 ±0.03 | -0.53 ±0.15 |

