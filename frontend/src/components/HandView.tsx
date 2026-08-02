import { cardAssetUrl } from '../assets';
import type { GameViewResponse } from '../types';

interface HandViewProps {
  view: GameViewResponse;
}

export function HandView({ view }: HandViewProps) {
  return (
    <div className="hand-view">
      <h3>La tua mano</h3>
      {view.own_hand_card_ids.length === 0 ? (
        <p>Nessuna carta.</p>
      ) : (
        <div className="hand-view__cards">
          {view.own_hand_card_ids.map((cardId) => (
            <img
              key={cardId}
              src={cardAssetUrl(cardId)}
              alt={cardId}
              title={cardId}
              className="hand-view__card"
            />
          ))}
        </div>
      )}
    </div>
  );
}
