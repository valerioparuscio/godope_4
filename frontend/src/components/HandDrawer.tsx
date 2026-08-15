import { useState } from 'react';
import { cardAssetUrl } from '../assets';
import type { GameViewResponse } from '../types';

interface HandDrawerProps {
  view: GameViewResponse;
}

// The hand is hidden by default (screen real estate is tight in the
// locked single-screen layout) and opened via a floating button at the
// bottom-left, per the designer's request (2026-08-16) — click to
// toggle, then scroll sideways through the cards.
export function HandDrawer({ view }: HandDrawerProps) {
  const [open, setOpen] = useState(false);
  const cardIds = view.own_hand_card_ids;

  return (
    <div className="hand-drawer">
      {open && (
        <div className="hand-drawer__panel">
          {cardIds.length === 0 ? (
            <p>Nessuna carta.</p>
          ) : (
            <div className="hand-drawer__cards">
              {cardIds.map((cardId) => (
                <img
                  key={cardId}
                  src={cardAssetUrl(cardId)}
                  alt={cardId}
                  title={cardId}
                  className="hand-drawer__card"
                />
              ))}
            </div>
          )}
        </div>
      )}
      <button className="hand-drawer__toggle" onClick={() => setOpen((v) => !v)}>
        Mano ({cardIds.length}) {open ? '▾' : '▴'}
      </button>
    </div>
  );
}
