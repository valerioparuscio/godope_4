# PWA: DOPE installabile a schermo intero

Dal 2026-11-11 il gioco (`<sito>/game/`) si può installare come app: icona sulla home, apertura a schermo intero senza
barra del browser, e l'app si apre anche senza rete (il **guscio**: la schermata iniziale; per giocare serve comunque il
backend). Le istruzioni di partenza sono in `pwa-istruzioni.md`; qui sta ciò che è stato fatto e dove si discosta.

## Cosa c'è

| Cosa | Dove |
|---|---|
| Plugin (service worker + manifest) | `frontend/vite.config.ts` (`vite-plugin-pwa`, dipendenza di sviluppo) |
| Manifest | generato in `dist/manifest.webmanifest`: `display: fullscreen` (ripiego `standalone`), `orientation: landscape`, scope e start `/game/` |
| Icone | `frontend/public/icons/` (192, 512, 512 maskable, apple-touch 180), ricavate da `public/favicon.svg` su fondo `#141414` |
| Tag per iOS e notch | `frontend/index.html` (`viewport-fit=cover`, `apple-mobile-web-app-*`, `theme-color`) |
| Aree sicure | `.app` e `.setup-screen` in `App.css` (padding `max(8px, env(safe-area-inset-*))`), `overscroll-behavior: none` in `index.css` |

`manifest`, service worker e icone stanno in `frontend/public/` o vengono generati dal build, perché il deploy
(`.github/workflows/deploy-pages.yml`) cancella e riscrive la cartella `game/` del sito con `dist/`.

## Cosa mette in cache il service worker

- **Guscio** (precache, circa 1 MB): `index.html`, JS, CSS, font Terror Babble, icone.
- **Immagini** dello stesso sito (carte, tabelloni...): salvate man mano che si usano (`CacheFirst`, al massimo 500, 30
  giorni). Hanno nomi con hash, quindi non diventano mai vecchie.
- **Mai in cache:** il backend (Render, altro dominio: nessuna regola lo intercetta, quindi lo stato di gioco si legge
  sempre dalla rete) e la **musica** (circa 50 MB, in streaming).

Differenze dall'esempio di `pwa-istruzioni.md`: niente `sw.js` scritto a mano, che avrebbe messo in cache **ogni** GET,
comprese le `GET /api/v1/games/…/view` (stato vecchio); elenco dei file generato dal build (i nomi hanno l'hash); niente
`user-scalable=no` (blocca lo zoom con le dita).

## Aggiornamenti

`registerType: 'autoUpdate'`: all'apertura l'app controlla se c'è una versione nuova; se c'è la installa e **ricarica la
pagina una volta**. Succede all'avvio; in teoria anche in una sessione rimasta aperta da oltre 24 ore (il browser
ricontrolla da solo), caso in cui la pagina si ricaricherebbe a metà partita.

## Telefoni: schermo piccolo

Il layout del gioco è fatto per almeno circa **780 px di altezza**. Un telefono in orizzontale ne ha 360-430: il
layout si sfasciava (plancia al 29% della larghezza, finita sotto la piega, elementi accavallati).

- **In orizzontale:** uno script in `frontend/index.html` allarga il viewport (`width=<larghezza × 780 ÷ altezza>`, per
  esempio 1732 su uno schermo 915×412), così il browser mostra la pagina intera rimpicciolita, **in proporzione**
  (circa 0,53 su un telefono). Il resto del codice vede un viewport grande, quindi misure e media query non cambiano.
  Vale solo per schermi touch (`pointer: coarse`) più bassi di 780 px: PC e tablet grandi non cambiano. Si ripete a ogni
  rotazione.
- **In verticale:** sopra la partita compare l'avviso «Gira il telefono in orizzontale» (`RotateHint.tsx`, mostrato dal
  CSS in `responsive.css` solo su schermi stretti, touch e in verticale). Il manifest blocca già l'orientamento su Android.
- Sul telefono il gioco resta quello da PC, rimpicciolito: testi e pulsanti sono circa la metà. Un layout pensato
  davvero per il telefono sarebbe un lavoro a parte.

Provato con l'emulazione di telefoni di Chrome (915×412, 844×390, 740×360, 412×915): plancia al 66% della larghezza in
orizzontale, avviso in verticale, ritorno al layout normale ruotando; a 1920×1080 e 1280×720 nulla è cambiato.
**Non provato** su telefoni veri né su iPhone (lì il comportamento del viewport dinamico può essere diverso).

## Come provarla in locale

```bash
cd frontend
npm run build
npx vite preview --port 4173      # http://localhost:4173/game/
```

In Chrome: F12, Application: *Manifest* senza errori, *Service Workers* «activated», e nella barra degli indirizzi
l'icona «Installa». Il service worker è spento con `npm run dev`.

Controllato il 2026-11-11 con Chrome (profilo normale): installabile senza errori, scope `/game/`, ricarica offline
con la schermata iniziale, nessuna richiesta all'API né mp3 nelle cache.
**Non provato** su telefoni veri (Android, iPhone), né l'aggiornamento con una versione nuova pubblicata.

## Da sapere

- `vite-plugin-pwa` porta con sé `workbox-build`: `npm audit` passa da 3 a 9 avvisi, tutti negli strumenti di build
  (nessuno nel codice pubblicato: `npm audit --omit=dev` dà 0).
- Se la landing apre `/game/` dentro un iframe, l'installazione va fatta aprendo direttamente `/game/`.
- iPhone: ignora `display: fullscreen` e apre l'app in modalità normale (senza barra di Safari); il blocco
  dell'orientamento funziona solo su Android.
- Per cambiare le icone basta sostituire i PNG in `public/icons/` (stessi nomi): il build li rimette in cache da solo.
