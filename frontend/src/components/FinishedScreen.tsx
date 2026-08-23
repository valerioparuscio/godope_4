import { playerTeamNameForId } from '../assets';
import type { GameViewResponse } from '../types';

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
export function FinishedScreen({ view, onNewGame, onClose }: FinishedScreenProps) {
  const score = view.final_score;

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
