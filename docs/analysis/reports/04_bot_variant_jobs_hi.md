# Sequenza dei Job e punti finali — Easy Price, bot euristici

700 partite (2800 giocatori-partita), file `jobs_hi_v1_seeds20000-20699.jsonl`.

## 1. Quadro generale
- Punti finali per giocatore: media 8.11, deviazione standard 4.25; nella stessa partita la deviazione standard tra i 4 giocatori è 3.57.
- Job completati per giocatore: media 2.54; nessun Job: 14% dei giocatori.
- Punti medi per numero di Job completati: 0 Job → 3.50 pt (vince 1%, n=387); 1 Job → 5.03 pt (vince 3%, n=622); 2 Job → 6.95 pt (vince 12%, n=512); 3 Job → 8.69 pt (vince 23%, n=439); 4 Job → 10.59 pt (vince 44%, n=378); 5 Job → 13.13 pt (vince 66%, n=247); 6 Job → 15.12 pt (vince 83%, n=127); 7 Job → 18.15 pt (vince 87%, n=62); 8 Job → 20.72 pt (vince 94%, n=18); 9 Job → 22.12 pt (vince 88%, n=8)
- Posizione al tavolo (punti rispetto alla media del tavolo): posto 0: +0.13 ±0.29 pt, vince 25.0%; posto 1: -0.04 ±0.28 pt, vince 24.3%; posto 2: -0.17 ±0.29 pt, vince 23.6%; posto 3: +0.07 ±0.29 pt, vince 27.1%
- In media ogni Job completato in più vale circa +1.60 punti (a parità di partita).

## 2. Il primo Job di ogni livello (quello rivelato a inizio partita)
Punti rispetto alla media del proprio tavolo, e quota di vittorie (25% = pari). ± = intervallo di confidenza al 95%.

**Livello 1**

| Job rivelato per primo | n | punti vs tavolo | vittorie | Job completati | lo completa |
|---|---:|---:|---:|---:|---:|
| Vinci 1 Rissa (01) | 952 | -0.25 ±0.22 | 23.8% ±2.2 | 2.44 | 59% |
| Abbi 1 Cop/Fed (02) | 930 | -0.24 ±0.20 | 22.8% ±2.2 | 2.42 | 85% |
| Criminali in 6 Hoods (07) | 918 | +0.51 ±0.22 | 28.5% ±2.3 | 2.78 | 77% |

- Vinci 1 Rissa − Abbi 1 Cop/Fed: -0.01 ±0.35 punti
- Vinci 1 Rissa − Criminali in 6 Hoods: -0.76 ±0.39 punti  ← **significativo**
- Abbi 1 Cop/Fed − Criminali in 6 Hoods: -0.75 ±0.35 punti  ← **significativo**

**Livello 2**

| Job rivelato per primo | n | punti vs tavolo | vittorie | Job completati | lo completa |
|---|---:|---:|---:|---:|---:|
| 2 Rats (04) | 914 | -0.72 ±0.20 | 20.4% ±2.1 | 2.29 | 33% |
| 4 Dope nel Covo (05) | 961 | +0.53 ±0.21 | 27.8% ±2.2 | 2.85 | 64% |
| 4 Link (06) | 925 | +0.16 ±0.19 | 26.6% ±2.2 | 2.47 | 46% |

- 2 Rats − 4 Dope nel Covo: -1.25 ±0.36 punti  ← **significativo**
- 2 Rats − 4 Link: -0.88 ±0.33 punti  ← **significativo**
- 4 Dope nel Covo − 4 Link: +0.38 ±0.35 punti  ← **significativo**

**Livello 3**

| Job rivelato per primo | n | punti vs tavolo | vittorie | Job completati | lo completa |
|---|---:|---:|---:|---:|---:|
| 2 Chip Poker (03) | 921 | -0.36 ±0.21 | 22.6% ±2.3 | 2.28 | 28% |
| 10 Criminali fuori (08) | 948 | +1.35 ±0.20 | 36.7% ±2.3 | 3.48 | 72% |
| 30 dollari (09) | 931 | -1.01 ±0.19 | 15.5% ±2.0 | 1.85 | 13% |

- 2 Chip Poker − 10 Criminali fuori: -1.71 ±0.36 punti  ← **significativo**
- 2 Chip Poker − 30 dollari: +0.65 ±0.34 punti  ← **significativo**
- 10 Criminali fuori − 30 dollari: +2.36 ±0.32 punti  ← **significativo**

## 3. Quanto pesa la sequenza nel suo insieme (modello con effetto-partita)
- Solo la posizione al tavolo: R² nella partita 0.08%.
- Posizione + Job iniziali dei 3 livelli: R² 12.59% (corretto 12.31%); effetto congiunto dei Job iniziali: χ²(6) = 314.7, p = 5.71e-65.
  - solo livello 1: χ²(2) = 22.7, p = 1.15e-05
  - solo livello 2: χ²(2) = 63.5, p = 1.66e-14
  - solo livello 3: χ²(2) = 240.3, p = 6.59e-53
- Posizione + primo e secondo Job di ogni livello: R² 12.97% (corretto 12.50%).
  - il secondo Job del livello 1 (dato il primo): χ²(2) = 4.2, p = 0.121
  - il secondo Job del livello 2 (dato il primo): χ²(2) = 3.3, p = 0.188
  - il secondo Job del livello 3 (dato il primo): χ²(2) = 0.6, p = 0.752
- Posizione + ordine completo (6 ordini per livello): R² 13.14% (corretto 12.58%).

## 4. Le 27 combinazioni di Job iniziali (livello 1 · livello 2 · livello 3)
Differenza tra la migliore e la peggiore: 5.41 punti (con rumore di campionamento ±1.02).
| combinazione | n | punti vs tavolo | vittorie |
|---|---:|---:|---:|
| 07·05·08 | 99 | +2.49 ±0.85 | 41.4% |
| 01·06·08 | 109 | +2.10 ±0.59 | 44.0% |
| 02·06·08 | 108 | +1.83 ±0.61 | 44.4% |
| 07·06·08 | 92 | +1.61 ±0.68 | 34.2% |
| 01·04·08 | 109 | +1.44 ±0.71 | 36.7% |
| 01·04·03 | 84 | -1.36 ±0.71 | 16.1% |
| 07·04·09 | 91 | -1.55 ±0.55 | 11.0% |
| 02·04·03 | 98 | -1.61 ±0.65 | 10.2% |
| 02·04·09 | 115 | -1.78 ±0.54 | 10.4% |
| 01·04·09 | 99 | -2.91 ±0.57 | 6.6% |
Test «le 27 combinazioni sono tutte uguali»: χ²(26) = 453.0, p = 1.74e-79. R² del modello a 27 combinazioni: 14.97% (corretto 14.08%).
Interazioni tra i tre livelli (oltre agli effetti singoli): χ²(20) ≈ 60.3, p ≈ 6.3e-06.

## 5. Perché: completamento dei Job in base alla posizione nella pila
| Job | lo completa se è il 1° | se è il 2° | se è il 3° | turno medio di completamento |
|---|---:|---:|---:|---:|
| Vinci 1 Rissa (liv. 1) | 59% | 36% | 16% | 2.05 |
| Abbi 1 Cop/Fed (liv. 1) | 85% | 51% | 27% | 2.10 |
| Criminali in 6 Hoods (liv. 1) | 77% | 39% | 21% | 2.37 |
| 2 Rats (liv. 2) | 33% | 15% | 5% | 2.53 |
| 4 Dope nel Covo (liv. 2) | 64% | 4% | 0% | 1.62 |
| 4 Link (liv. 2) | 46% | 21% | 4% | 2.50 |
| 2 Chip Poker (liv. 3) | 28% | 16% | 4% | 2.30 |
| 10 Criminali fuori (liv. 3) | 72% | 12% | 3% | 2.41 |
| 30 dollari (liv. 3) | 13% | 6% | 5% | 2.25 |

## 6. Da dove viene la differenza di punti (primo Job del livello 3)
| primo Job liv. 3 | money | clean | stained | maj | chip | skill | totale |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2 Chip Poker | -0.18 ±0.06 | -0.03 ±0.12 | -0.21 ±0.07 | -0.02 ±0.04 | +0.14 ±0.03 | -0.06 ±0.04 | -0.36 ±0.21 |
| 10 Criminali fuori | -0.09 ±0.06 | +0.35 ±0.12 | +0.57 ±0.07 | +0.23 ±0.04 | +0.08 ±0.03 | +0.21 ±0.04 | +1.35 ±0.20 |
| 30 dollari | +0.27 ±0.06 | -0.32 ±0.11 | -0.37 ±0.07 | -0.21 ±0.04 | -0.22 ±0.03 | -0.15 ±0.04 | -1.01 ±0.19 |

