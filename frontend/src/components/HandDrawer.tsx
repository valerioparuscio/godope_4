import { useEffect, useState } from 'react';
import { cardAssetUrl } from '../assets';
import type { GameViewResponse, PendingDecisionResponse } from '../types';

interface HandDrawerProps {
  view: GameViewResponse;
  decision?: PendingDecisionResponse | null;
  selected?: string[];
  onToggle?: (optionId: string) => void;
  onSubmit?: (selectedOptionIds: string[]) => void;
}

// Decisions whose options are literally "pick one of your own hand
// cards" — clicking a card thumbnail here answers the decision directly
// instead of picking it from the text list (designer's request,
// 2026-08-16). hand_discard is multi-select (build up to the exact
// overflow count, then Confirm in the sidebar); the other three submit
// the instant a card is clicked.
const CARD_DECISION_TYPES = new Set([
  'hand_discard',
  'play_brawl_card',
  'launch_poker',
  'play_poker_card',
  'choose_marketing_card',
  'play_customer_card_boost',
]);

// The hand is hidden by default (screen real estate is tight in the
// locked single-screen layout) and opened via a "Carte" button in the
// sidebar, under the action selection (designer's request, 2026-08-16 —
// was a floating bottom-right button before) — click to toggle, then
// scroll sideways through the cards in a panel that still floats over
// the board (a card needs real width to read, more than the sidebar's
// own column has). It also auto-opens whenever one of the card decisions
// above becomes pending, so there's no need to remember to open it first
// — and auto-*closes* again once that decision resolves, since the
// floating panel would otherwise sit open over the board indefinitely,
// covering any board-highlight targets a later decision (e.g. a Brawl's
// relocation step, right after its card-play step) happens to place
// underneath it.
export function HandDrawer({ view, decision, selected = [], onToggle, onSubmit }: HandDrawerProps) {
  const [open, setOpen] = useState(false);
  const cardIds = view.own_hand_card_ids;

  const isCardDecision = !!decision && CARD_DECISION_TYPES.has(decision.decision_type);
  useEffect(() => {
    setOpen(isCardDecision);
  }, [decision?.decision_id, isCardDecision]);

  const optionIdByCardId = new Map<string, string>();
  if (isCardDecision && decision) {
    for (const option of decision.options) {
      const cardId = option.payload.card_id as string | undefined;
      if (cardId) optionIdByCardId.set(cardId, option.option_id);
    }
  }
  // Normally one card submits immediately; hand_discard always builds up
  // to an exact count first, and play_poker_card does too whenever its
  // own max_selections is boosted past 1 (§A10 Preti-1, "Puoi giocare 2
  // carte per ogni Poker") — checked by count, not decision_type, so
  // this generalizes without needing a second hardcoded type list.
  const isMultiSelect =
    decision?.decision_type === 'hand_discard' ||
    (decision?.decision_type === 'play_poker_card' && (decision?.max_selections ?? 1) > 1);

  function handleCardClick(cardId: string) {
    const optionId = optionIdByCardId.get(cardId);
    if (!optionId) return;
    if (isMultiSelect) {
      onToggle?.(optionId);
    } else {
      onSubmit?.([optionId]);
    }
  }

  return (
    <div className="hand-drawer">
      {open && (
        <div className="hand-drawer__panel">
          {cardIds.length === 0 ? (
            <p>Nessuna carta.</p>
          ) : (
            <div className="hand-drawer__cards">
              {cardIds.map((cardId) => {
                const optionId = optionIdByCardId.get(cardId);
                const clickable = !!optionId;
                const isSelected = !!optionId && selected.includes(optionId);
                return (
                  <img
                    key={cardId}
                    src={cardAssetUrl(cardId)}
                    alt={cardId}
                    title={cardId}
                    className={
                      'hand-drawer__card' +
                      (clickable ? ' hand-drawer__card--clickable' : '') +
                      (isSelected ? ' hand-drawer__card--selected' : '')
                    }
                    onClick={clickable ? () => handleCardClick(cardId) : undefined}
                  />
                );
              })}
            </div>
          )}
        </div>
      )}
      <button className="hand-drawer__toggle" onClick={() => setOpen((v) => !v)}>
        Carte ({cardIds.length}) {open ? '▾' : '▴'}
      </button>
    </div>
  );
}
