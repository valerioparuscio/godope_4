# DOPE — versione digitale 2D

Porting digitale del gioco da tavolo **DOPE**: backend Python autoritativo,
frontend web React + Vite + TypeScript, partita locale 1 umano + 3 bot.

Le specifiche architetturali complete sono in [CLAUDE.md](CLAUDE.md).

## Struttura del repository

- `docs/` — architettura, decisioni, regolamento canonico e pendente, API.
- `data/` — file dati versionati (mappa, mazzi, config, asset manifest).
- `backend/` — motore di gioco Python (`dope_engine`) e adapter HTTP.
- `frontend/` — app React + Vite + TypeScript (frontend web).
- `tools/` — script di validazione dati, avvio backend, simulazioni,
  replay da riga di comando.

## Stato del progetto

Motore e regolamento sono implementati end-to-end: setup, azioni economiche,
Links/officers/Jail, Rissa, Poker, Jobs/REP, Retate e punteggio finale, con
salvataggio/caricamento e replay. Il frontend React è giocabile contro 3 bot
(`RandomLegalBot`/`HeuristicBot`), con tabellone, carte e asset reali. Lo
sviluppo prosegue su affinamento dei bot euristici e rifinitura UI — vedi
`docs/rules/RULES_PENDING.md` per le regole ancora da chiarire e
`docs/rules/RULE_CHANGELOG.md` per lo storico delle decisioni.

## Sviluppo backend

```bash
cd backend
pip install -e ".[dev]"
pytest
ruff check .
mypy src
```

Avvio del backend in locale (usato dal frontend in sviluppo):

```bash
python tools/run_backend.py
```

## Sviluppo frontend

```bash
cd frontend
npm install
npm run dev     # dev server Vite, si collega al backend su 127.0.0.1
npm run build   # tsc -b && vite build
npm run lint    # oxlint
```

## Simulazioni e replay

```bash
python tools/run_full_test_game.py   # partite complete con bot, per trovare deadlock/regressioni
python tools/replay_game.py          # ricostruisce/verifica una partita salvata da seed + comandi
```
