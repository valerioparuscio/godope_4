# 0001 — Frontend: React + Vite + TypeScript invece di Godot

- Stato: accettata
- Data: 2026-08-02

## Contesto

CLAUDE.md (sezione 4) indicava inizialmente Godot 4 + GDScript come stack
frontend. Al momento della decisione, `godot/` era ancora uno scaffold
vuoto (solo cartelle con `.gitkeep`, nessun asset o script reale importato)
— nessun lavoro frontend era stato svolto, quindi il cambio non comporta
alcuna perdita.

Il game designer ha chiesto esplicitamente di sostituire Godot con uno
stack web (React + Vite), con l'obiettivo di arrivare il prima possibile a
una partita completa e giocabile (1 umano + 3 bot dall'inizio alla
schermata finale), rimandando i dettagli (mazzo di carte definitivo, asset
grafici finali) a un secondo momento.

## Decisione

Il frontend è **React 18+ con TypeScript, build tool Vite**. Nessun
framework UI aggiuntivo, nessun router, nessun tooling di lint/test
frontend nel primo giro — solo `tsc` come rete di sicurezza dei tipi, per
privilegiare la velocità di consegna di una partita giocabile.

Per rendere questo praticabile senza dover reimplementare una logica di
dispatch per ciascuno dei ~15 `command_type` lato client, è stato aggiunto
un endpoint HTTP generico,
`POST /api/v1/games/{game_id}/decisions/answer`, che avvolge la funzione di
dominio già esistente `application/legal_actions.py::
build_command_from_selection` (già usata da `tools/play_cli.py`): il
frontend seleziona solo tra `PendingDecision.options` e non costruisce mai
un comando a mano (CLAUDE.md sezione 10).

## Conseguenze

- I vincoli architetturali di CLAUDE.md sezione 3 (backend autoritativo,
  dominio isolato da FastAPI/trasporto/grafica, nessuna regola duplicata
  nel frontend) restano invariati — non dipendono dalla tecnologia del
  frontend.
- `godot/` (scaffold vuoto) è stato rimosso; `frontend/` lo sostituisce
  nella struttura del repository (CLAUDE.md sezione 5).
- Il primo giro del nuovo frontend è deliberatamente non rifinito
  visivamente: board/mercato/mano sono tabelle HTML testuali, senza asset
  grafici. Gli asset reali (tabellone, carte, pedine Dope/Cop/Fed, token
  REP) sono pronti lato game designer e verranno integrati in un giro
  successivo, sostituendo le tabelle con una board grafica vera e propria.
- `docs/rules/RULE_CHANGELOG.md` non viene toccato da questa decisione: è
  riservato alle decisioni di regolamento, non di stack tecnico.
