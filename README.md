# DOPE — versione digitale 2D

Porting digitale del gioco da tavolo **DOPE**: backend Python autoritativo,
frontend Godot 4 in 2D, partita locale 1 umano + 3 bot.

Le specifiche architetturali complete sono in [CLAUDE.md](CLAUDE.md).

## Struttura del repository

- `docs/` — architettura, decisioni, regolamento canonico e pendente, API.
- `data/` — file dati versionati (mappa, mazzi, config, asset manifest).
- `backend/` — motore di gioco Python (`dope_engine`) e adapter HTTP.
- `godot/` — progetto Godot 4 (frontend 2D).
- `tools/` — script di validazione dati, avvio backend, simulazioni.

## Stato del progetto

Milestone 0 (fondazioni) in corso. Vedi `CLAUDE.md`, sezione 21, per l'ordine
di implementazione previsto e `docs/rules/RULES_PENDING.md` per le regole
ancora da chiarire.

## Sviluppo backend

```bash
cd backend
pip install -e ".[dev]"
pytest
ruff check .
mypy src
```
