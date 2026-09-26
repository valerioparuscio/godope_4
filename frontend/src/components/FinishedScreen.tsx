import { useState } from 'react';
import {
  criminalAssetsForPlayer,
  pawnAssetForPlayer,
  playerColorForId,
  playerTeamNameForId,
} from '../assets';
import type { GameViewResponse } from '../types';

// criminalAssetsForPlayer has no Red variant at all (assets/index.ts:
// "no Red variant exists, since TurnPlayback.tsx only ever narrates bot
// segments" — Red/seat 0 is always the human) — the winner announcement,
// unlike that bot-only banner, can perfectly well be Red, so this falls
// back to 3 copies of the plain pawn icon for that one color specifically
// until real Red portrait art exists.
function winnerPortraitsForPlayer(playerId: string): string[] {
  const portraits = criminalAssetsForPlayer(playerId);
  return portraits.length > 0 ? portraits : [0, 1, 2].map(() => pawnAssetForPlayer(playerId));
}

interface FinishedScreenProps {
  view: GameViewResponse;
  onNewGame: () => void;
  onClose: () => void;
}

// Closable with its own "×" (designer's request, 2026-08-23: "vorrei che
// il popup di fine partita fosse chiudibile con una x per riguardare lo
// stato del tabellone finale") — App.tsx keeps the board/player panels
// rendered underneath this overlay the whole time, already inert (no
// pending_decision once the game is finished), so closing just reveals
// them; onNewGame (unlike onClose) still actually resets the game.
//
// A dramatic "And the winner is.." reveal (game designer, 2026-09-26)
// comes first — one gang box (team name + 3 pawns, in that gang's own
// colour) per winner_id, covering a shared-victory tie as well as a
// single winner — then a button moves on to the actual score table.
// Local state, not something App.tsx needs to know about: reset to
// `false` any time this component is freshly mounted for a newly
// finished game (App.tsx already unmounts/remounts it via handleNewGame
// clearing `view`/`activeGame` entirely), and skipped outright if there's
// no score or no winner to announce.
export function FinishedScreen({ view, onNewGame, onClose }: FinishedScreenProps) {
  const score = view.final_score;
  const [announced, setAnnounced] = useState(!score || score.winner_ids.length === 0);

  if (!announced && score) {
    return (
      <div className="finished-screen finished-screen--winner">
        <button className="finished-screen__close" onClick={onClose} aria-label="Chiudi">
          ×
        </button>
        <h2 className="finished-screen__winner-title">And the winner is..</h2>
        <div className="finished-screen__winner-gangs">
          {score.winner_ids.map((id) => (
            <div key={id} className="finished-screen__winner-gang">
              <div className="finished-screen__winner-name">{playerTeamNameForId(id)}</div>
              <div className={`finished-screen__winner-box player-card--${playerColorForId(id)}`}>
                {winnerPortraitsForPlayer(id).map((src, i) => (
                  <img key={i} src={src} alt="" className="finished-screen__winner-pawn" />
                ))}
              </div>
            </div>
          ))}
        </div>
        <button className="finished-screen__winner-continue" onClick={() => setAnnounced(true)}>
          Vedi i punteggi
        </button>
      </div>
    );
  }

  return (
    <div className="finished-screen">
      <button className="finished-screen__close" onClick={onClose} aria-label="Chiudi">
        ×
      </button>
      <h2>Partita finita</h2>
      {score ? (
        <>
          <p>
            Vincitore/i:{' '}
            {score.winner_ids.length > 0
              ? score.winner_ids.map(playerTeamNameForId).join(', ')
              : 'nessuno'}
          </p>
          <table>
            <thead>
              <tr>
                <th>Giocatore</th>
                <th>Denaro</th>
                <th>REP pulite</th>
                <th>REP macchiate</th>
                <th>Maggioranze</th>
                <th>Chips</th>
                <th>Skill</th>
                <th>Totale</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(score.breakdown_by_player).map(([playerId, b]) => (
                <tr key={playerId}>
                  <td>{playerTeamNameForId(playerId)}</td>
                  <td>{b.money_track_position_points}</td>
                  <td>{b.clean_reputation_points}</td>
                  <td>{b.stained_reputation_points}</td>
                  <td>{b.contact_majority_points}</td>
                  <td>{b.base_chip_points}</td>
                  <td>{b.skill_points}</td>
                  <td>
                    <strong>{b.total_points}</strong>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      ) : (
        <p>Punteggio non disponibile.</p>
      )}
      <button onClick={onNewGame}>Nuova partita</button>
    </div>
  );
}
