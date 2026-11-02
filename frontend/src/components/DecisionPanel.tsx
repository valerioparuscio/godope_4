import { useState } from 'react';
import {
  actionTypeAssetUrl,
  cardAssetUrl,
  GRIT_ICON,
  playerColorForId,
  POKER_SYMBOL_COLOR,
  pokerSymbolLabel,
  skillAssetUrl,
} from '../assets';
import { isBoardFollowup } from '../move-followups';
import { t, tDyn } from '../i18n';
import { tNodes } from '../i18n/nodes';
import { playerNameForId } from '../player-names';
import type { DecisionOptionResponse, GameViewResponse, PendingDecisionResponse } from '../types';
import { OfficerActionIcon } from './OfficerActionIcon';

interface DecisionPanelProps {
  decision: PendingDecisionResponse;
  view: GameViewResponse;
  selected: string[];
  onToggle: (optionId: string) => void;
  onSubmit: (selectedOptionIds: string[]) => void;
  submitting: boolean;
  compactOptional?: boolean;
  guidanceInCorner?: boolean;
  stagedManeuverAction?: string | null;
  onStageManeuverAction?: (action: string | null) => void;
}

// What each Rissa reward button says: money or a card, plus the two theft rewards a
// "FIGHT!!" card unlocks (a Dope / a Poker Chip taken from the loser's Covo).
const brawlRewardLabel = (type: string) => tDyn(`decision.brawlReward.${type}`) ?? t('common.card');

const dopeName = (type: string) => tDyn(`dope.${type}`) ?? t('decision.brawlReward.dope');

// Rissa reward picker. Every option targets the same loser (with several losers the
// decision is asked once per loser, so the title names whose reward this is). The
// Dope reward has one option per type the loser holds: "Merce" opens a second
// message to pick which one (or takes it straight away when there is only one).
function BrawlRewardPanel({
  view,
  decision,
  onSubmit,
  submitting,
}: {
  view: GameViewResponse;
  decision: PendingDecisionResponse;
  onSubmit: (selectedOptionIds: string[]) => void;
  submitting: boolean;
}) {
  const [choosingDope, setChoosingDope] = useState(false);
  const loserId = decision.options[0].payload.loser_player_id as string | undefined;
  const loserName = loserId ? (
    <span className={`decision-panel__loser decision-panel__loser--${playerColorForId(loserId)}`}>
      {playerNameForId(view, loserId)}
    </span>
  ) : t('decision.brawl.aLoser');
  const dopeOptions = decision.options.filter((o) => o.payload.reward_type === 'dope');
  const otherOptions = decision.options.filter((o) => o.payload.reward_type !== 'dope');

  // "Easy Price": the card is always taken (automatically); the only choice left is which Dope
  // the winner's SPOILS card takes, asked straight away.
  if (decision.context?.steal_card === true) {
    return (
      <div className="decision-panel decision-panel--quick">
        <h3>{tNodes('decision.brawl.alsoDope', { loser: loserName })}</h3>
        <div className="decision-panel__quick-buttons">
          {dopeOptions.map((option) => (
            <button key={option.option_id} disabled={submitting} onClick={() => onSubmit([option.option_id])}>
              {dopeName(option.payload.dope_type as string)}
            </button>
          ))}
        </div>
      </div>
    );
  }

  if (choosingDope && dopeOptions.length > 1) {
    return (
      <div className="decision-panel decision-panel--quick">
        <h3>{tNodes('decision.brawl.whichDope', { loser: loserName })}</h3>
        <div className="decision-panel__quick-buttons">
          {dopeOptions.map((option) => (
            <button key={option.option_id} disabled={submitting} onClick={() => onSubmit([option.option_id])}>
              {dopeName(option.payload.dope_type as string)}
            </button>
          ))}
          <button disabled={submitting} onClick={() => setChoosingDope(false)}>
            {t('common.back')}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="decision-panel decision-panel--quick">
      <h3>{tNodes('decision.brawl.whichReward', { loser: loserName })}</h3>
      <div className="decision-panel__quick-buttons">
        {otherOptions.map((option) => (
          <button key={option.option_id} disabled={submitting} onClick={() => onSubmit([option.option_id])}>
            {brawlRewardLabel(option.payload.reward_type as string)}
          </button>
        ))}
        {dopeOptions.length > 0 && (
          <button
            disabled={submitting}
            onClick={() => (dopeOptions.length === 1 ? onSubmit([dopeOptions[0].option_id]) : setChoosingDope(true))}
          >
            {brawlRewardLabel('dope')}
          </button>
        )}
      </div>
    </div>
  );
}

const maneuverActionLabel = (action: 'move' | 'arrest' | 'confiscate') => t(`decision.maneuver.${action}`);

// Same fixed order every round (designer's request, 2026-08-16: "così ci
// stanno tutti in posizione fissa") — all 6 action types always render,
// so the row never reflows as choices become unavailable; only the
// legal_actions.py-qualifying ones (in decision.options) are clickable.
const ACTION_TYPE_ORDER = [
  'place_criminal',
  'move_criminal',
  'buy_dope',
  'sell_dope',
  'maneuver_officer',
  'corrupt_officer',
] as const;

// Package-select decisions answered entirely by clicking targets on the
// board (BoardView's own dedicated components or its generic
// BoardHighlights) — this panel only ever needs a heading, a one-line
// hint, and the Confirm/Passa button that already existed at the bottom
// of the plain fallback, never the raw option list with its
// JSON.stringify(payload) dump.
const boardPackageLabel = (type: string) =>
  tDyn(`action.${type}`) ?? tDyn(`decision.package.${type}`) ?? type;

// The package-select decisions answered by clicking on the board (each has a hint text).
const BOARD_PACKAGE_TYPES = new Set([
  'place_criminal',
  'move_criminal',
  'buy_dope',
  'sell_dope',
  'maneuver_officer',
  'corrupt_officer',
  'play_marketing_card',
]);

// Titles of the optional steps cards ask after a move or a Rissa (`move_followup` decisions).
const moveFollowupTitle = (kind: string) => tDyn(`decision.followup.title.${kind}`) ?? t('common.card');

// What the panel says under the title when the follow-up is answered on the board (move-followups.ts
// lists those): the lit-up target to click.
const moveFollowupHint = (kind: string) => tDyn(`decision.followup.hint.${kind}`);

// The follow-ups with nothing to point at on the board: a plain yes/no button.
const moveFollowupButton = (kind: string) => tDyn(`decision.followup.button.${kind}`) ?? t('common.confirm');

// A Buy/Sell card's follow-up (cards 11/19 place, 14/16 Den, 17 move) is asked as an ordinary
// Place/Move decision whose `context.card_followup` says which one; these replace its title/hint.
function cardFollowupText(kind: string): { title: string; hint: string } | undefined {
  const title = tDyn(`decision.cardFollowup.title.${kind}`);
  const hint = tDyn(`decision.cardFollowup.hint.${kind}`);
  return title && hint ? { title, hint } : undefined;
}

// Why a Poker launch has no "send a pawn to the Den?" question (`context.no_gambler_reason`).
const NO_GAMBLER_REASON: Record<string, 'decision.launchPoker.denFull' | 'decision.launchPoker.noPawn'> = {
  den_full: 'decision.launchPoker.denFull',
  no_pawn_in_base: 'decision.launchPoker.noPawn',
};

// A Move decision's own legend for the marks on pawns it doesn't offer (`unavailable_pawns`).
function unavailablePawnsHint(context: Record<string, unknown> | undefined): string {
  const reasons = new Set(Object.values((context?.unavailable_pawns ?? {}) as Record<string, string>));
  const parts: string[] = [];
  if (reasons.has('moved_this_action')) parts.push(t('decision.unavailable.moved'));
  if (reasons.has('no_destination')) parts.push(t('decision.unavailable.noDestination'));
  return parts.length > 0 ? ` ${parts.join(' · ')}.` : '';
}

// The two decisions that fire every single action round (how much Grit,
// then which action) get a dedicated one-click button row instead of the
// generic checkbox list below — clicking submits immediately since both
// are always single-select with no "pass".
function QuickButtons({
  options,
  render,
  onSubmit,
  submitting,
}: {
  options: DecisionOptionResponse[];
  render: (option: DecisionOptionResponse) => string;
  onSubmit: (selectedOptionIds: string[]) => void;
  submitting: boolean;
}) {
  return (
    <div className="decision-panel__quick-buttons">
      {options.map((option) => (
        <button
          key={option.option_id}
          disabled={submitting}
          onClick={() => onSubmit([option.option_id])}
        >
          {render(option)}
        </button>
      ))}
    </div>
  );
}

export function DecisionPanel({
  decision,
  view,
  selected,
  onToggle,
  onSubmit,
  submitting,
  compactOptional,
  guidanceInCorner,
  stagedManeuverAction,
  onStageManeuverAction,
}: DecisionPanelProps) {
  const [marketingCardOpenedFor, setMarketingCardOpenedFor] = useState<string | null>(null);
  const isValidSelection =
    selected.length >= decision.min_selections && selected.length <= decision.max_selections;
  const isPass = selected.length === 0 && decision.can_pass;
  const canSubmit = (isValidSelection || isPass) && !submitting;
  const buttonLabel = selected.length === 0 && decision.can_pass ? t('common.pass') : t('common.confirm');

  if (decision.decision_type === 'choose_grit_action') {
    return (
      <div className="decision-pill">
        <span className="decision-pill__verb">{t('decision.verb.grit')}</span>
        <div className="decision-pill__options">
          {decision.options.length > 0 ? (
            decision.options.map((option) => (
              <button
                key={option.option_id}
                className="decision-pill__grit-button"
                disabled={submitting}
                onClick={() => onSubmit([option.option_id])}
              >
                <img
                  src={GRIT_ICON[Number(option.payload.grit_value)]}
                  alt={t('chooser.gritN', { n: Number(option.payload.grit_value) })}
                  className="grit-icon"
                />
              </button>
            ))
          ) : (
            decision.can_pass && (
              <button className="decision-pill__pass" disabled={submitting} onClick={() => onSubmit([])}>
                {t('common.pass')}
              </button>
            )
          )}
        </div>
      </div>
    );
  }

  if (decision.decision_type === 'choose_action_type') {
    const optionByActionType = new Map(
      decision.options.map((option) => [option.payload.action_type as string, option]),
    );
    return (
      <div className="decision-pill">
        <span className="decision-pill__verb">{t('decision.verb.action')}</span>
        <div className="decision-pill__options">
          {decision.options.length > 0 ? (
            ACTION_TYPE_ORDER.map((actionType) => {
              const option = optionByActionType.get(actionType);
              return (
                <button
                  key={actionType}
                  className="decision-pill__action-button"
                  disabled={!option || submitting}
                  onClick={() => option && onSubmit([option.option_id])}
                  title={t(`action.${actionType}`)}
                >
                  <img src={actionTypeAssetUrl(actionType)} alt={t(`action.${actionType}`)} data-action={actionType} />
                </button>
              );
            })
          ) : (
            decision.can_pass && (
              <button className="decision-pill__pass" disabled={submitting} onClick={() => onSubmit([])}>
                {t('common.pass')}
              </button>
            )
          )}
        </div>
      </div>
    );
  }

  if (decision.decision_type === 'maneuver_action') {
    const groups: Record<string, DecisionOptionResponse[]> = { move: [], arrest: [], confiscate: [] };
    for (const option of decision.options) {
      const action = option.payload.action as string;
      (groups[action] ??= []).push(option);
    }
    // Cards 97 "REDEEM" / 100 "SWEEP": the arrest involves a Rat (not a Criminal on the board),
    // so those choices are listed as buttons instead of board clicks.
    const pawnOwner = (pawnId: unknown) =>
      view.pawns.find((p) => p.pawn_id === pawnId)?.owner_player_id;
    const ratArrests = groups.arrest.filter((o) =>
      o.payload.second_target_id != null
      || view.pawns.find((p) => p.pawn_id === o.payload.target_id)?.role === 'RAT');
    if (ratArrests.length > 0) {
      groups.arrest = groups.arrest.filter((o) => !ratArrests.includes(o));
    }
    return (
      <div className="decision-panel decision-panel--quick">
        <h3>{t('decision.maneuver.question')}</h3>
        <div className="decision-panel__quick-buttons">
          {(['move', 'arrest', 'confiscate'] as const)
            .filter((action) => groups[action].length > 0)
            .map((action) => (
              <button
                key={action}
                disabled={submitting}
                className={'decision-panel__officer-action'
                  + (stagedManeuverAction === action ? ' decision-panel__quick-buttons--staged' : '')}
                aria-label={maneuverActionLabel(action)}
                title={maneuverActionLabel(action)}
                onClick={() => {
                  if (groups[action].length === 1) {
                    onSubmit([groups[action][0].option_id]);
                  } else {
                    onStageManeuverAction?.(stagedManeuverAction === action ? null : action);
                  }
                }}
              >
                <OfficerActionIcon action={action === 'move' ? 'move' : action === 'arrest' ? 'arrest' : 'confiscate'} />
                <span className="decision-panel__officer-action-name">{maneuverActionLabel(action)}</span>
              </button>
            ))}
          {decision.can_pass && (
            <button disabled={submitting} onClick={() => onSubmit([])}>
              {t('common.done')}
            </button>
          )}
        </div>
        {ratArrests.length > 0 && (
          <div className="decision-panel__quick-buttons">
            {ratArrests.map((option) => (
              <button key={option.option_id} disabled={submitting} onClick={() => onSubmit([option.option_id])}>
                {option.payload.second_target_id != null
                  ? t('decision.maneuver.arrestAndFree', {
                      a: playerNameForId(view, String(pawnOwner(option.payload.target_id))),
                      b: playerNameForId(view, String(pawnOwner(option.payload.second_target_id))),
                    })
                  : t('decision.maneuver.freeRat', { a: playerNameForId(view, String(pawnOwner(option.payload.target_id))) })}
              </button>
            ))}
          </div>
        )}
        {stagedManeuverAction && (
          <p>{t('decision.maneuver.pickTarget')}</p>
        )}
      </div>
    );
  }

  if (decision.decision_type === 'spend_link_for_extra_action') {
    if (compactOptional) return (
      <div className={guidanceInCorner ? 'human-controls__guidance' : 'decision-panel'}>
        <h3>{t('decision.link.pick')}</h3>
      </div>
    );
    return (
      <div className="decision-panel decision-panel--quick">
        <h3>{t('decision.link.question')}</h3>
        {decision.options.length > 0 && <p>{t('decision.link.hint')}</p>}
        <div className="decision-panel__quick-buttons">
          <button disabled={submitting} onClick={() => onSubmit([])}>
            {t('common.skip')}
          </button>
        </div>
      </div>
    );
  }

  if (decision.decision_type === 'choose_brawl_link_evolution') {
    return (
      <div className="decision-panel decision-panel--quick">
        <h3>{t('decision.brawlLink.question')}</h3>
        {decision.options.length > 0 && <p>{t('decision.brawlLink.hint')}</p>}
        <div className="decision-panel__quick-buttons">
          <button disabled={submitting} onClick={() => onSubmit([])}>
            {t('common.pass')}
          </button>
        </div>
      </div>
    );
  }

  if (decision.decision_type === 'choose_brawl_relocation_destination') {
    return (
      <div className="decision-panel decision-panel--quick">
        <h3>{t('decision.relocation.question')}</h3>
        {decision.options.length > 0 ? (
          <p>{t('decision.relocation.hint')}</p>
        ) : (
          <div className="decision-panel__quick-buttons">
            <button disabled={submitting} onClick={() => onSubmit([])}>
              {t('common.pass')}
            </button>
          </div>
        )}
      </div>
    );
  }

  if (decision.decision_type === 'choose_job_reward') {
    return (
      <div className="decision-panel decision-panel--quick">
        <h3>{t('decision.job.reward')}</h3>
        <p>{t('decision.job.rewardHint')}</p>
      </div>
    );
  }

  if (decision.decision_type === 'choose_skill_to_discard') {
    return (
      <div className="decision-panel decision-panel--quick">
        <h3>{t('decision.job.discardSkill')}</h3>
        <div className="decision-panel__skill-discard-options">
          {decision.options.map((option) => {
            const skillId = String(option.payload.skill_id ?? '');
            return (
              <img
                key={option.option_id}
                src={skillAssetUrl(skillId)}
                alt={skillId}
                title={skillId}
                className="player-card__skill-icon decision-panel__skill-discard-icon"
                onClick={() => !submitting && onSubmit([option.option_id])}
              />
            );
          })}
        </div>
      </div>
    );
  }

  if (decision.decision_type === 'choose_job_bonus_alternative') {
    return (
      <div className="decision-panel decision-panel--quick">
        <h3>{t('decision.job.bonusInstead')}</h3>
        <QuickButtons
          options={decision.options}
          render={(option) =>
            option.payload.bonus_type === 'money' ? t('decision.job.bonusMoney') : t('decision.job.bonusCards')
          }
          onSubmit={onSubmit}
          submitting={submitting}
        />
      </div>
    );
  }

  if (decision.decision_type === 'evolve_sale_link' && decision.options.length > 0) {
    return (
      <div className="decision-panel decision-panel--quick">
        <h3>{t('decision.evolve.question')}</h3>
        <QuickButtons
          options={decision.options}
          render={(option) => {
            if (!option.payload.evolve) return t('common.noThanks');
            // Card CONNECTION: one "yes" per Client, the Link may be of any of them.
            if (decision.options.filter((o) => o.payload.evolve).length > 1) {
              const contact = String(option.payload.contact_id ?? '');
              return t('decision.evolve.contact', {
                contact: tDyn(`contact.${contact}`) ?? `${contact.charAt(0).toUpperCase()}${contact.slice(1)}`,
              });
            }
            return t('decision.evolve.yes');
          }}
          onSubmit={onSubmit}
          submitting={submitting}
        />
      </div>
    );
  }

  if (decision.decision_type === 'choose_brawl_loser_reward' && decision.options.length > 0) {
    // Every option of one decision targets the same loser; with several losers the
    // decision is asked once per loser, so name whose reward this is.
    return <BrawlRewardPanel key={decision.decision_id} view={view} decision={decision} onSubmit={onSubmit} submitting={submitting} />;
  }

  if (decision.decision_type === 'move_followup') {
    // Card follow-ups after a move, a placement or a Rissa. What points at something on the board
    // (a Hood, a pawn, a Cop/Fed) is chosen there, by clicking the lit-up target (BoardView's
    // MoveFollowupHighlights); only the plain yes/no steps are buttons.
    const followupKind = String(decision.context?.followup);
    const title = moveFollowupTitle(followupKind);
    const passButton = decision.can_pass && (
      <button disabled={submitting} onClick={() => onSubmit([])}>
        {t('common.noThanks')}
      </button>
    );
    if (isBoardFollowup(followupKind)) {
      // EXPANSION asks for the pawn first when several just-placed ones can move.
      const severalPawns = new Set(decision.options.map((option) => option.payload.pawn_id)).size > 1;
      return (
        <div className="decision-panel decision-panel--quick">
          <h3>{title}</h3>
          <p>{followupKind === 'expansion' && severalPawns ? t('decision.followup.expansionPawn') : moveFollowupHint(followupKind)}</p>
          {passButton && <div className="decision-panel__quick-buttons">{passButton}</div>}
        </div>
      );
    }
    return (
      <div className="decision-panel decision-panel--quick">
        <h3>{title}</h3>
        <div className="decision-panel__quick-buttons">
          {decision.options.map((option) => (
            <button key={option.option_id} disabled={submitting} onClick={() => onSubmit([option.option_id])}>
              {moveFollowupButton(followupKind)}
            </button>
          ))}
          {passButton}
        </div>
      </div>
    );
  }

  if (decision.decision_type === 'choose_raid_first_player' && decision.options.length > 0) {
    return (
      <div className="decision-panel decision-panel--quick decision-panel--teams">
        <h3>{t('decision.raidFirst')}</h3>
        {/* One button per gang, in its own colour, two per row. It is a regular
            quick-buttons group so the message shell places it in its button column. */}
        <div className="decision-panel__quick-buttons decision-panel__quick-buttons--teams">
          {decision.options.map((option) => {
            const playerId = option.payload.chosen_first_player_id as string;
            return (
              <button
                key={option.option_id}
                className={`decision-panel__team-button decision-panel__team-button--${playerColorForId(playerId)}`}
                disabled={submitting}
                onClick={() => onSubmit([option.option_id])}
              >
                {playerNameForId(view, playerId)}
              </button>
            );
          })}
        </div>
      </div>
    );
  }

  if (decision.decision_type === 'stain_reputation_for_money') {
    return (
      <div className="decision-panel decision-panel--quick">
        <h3>{t('decision.stain.question')}</h3>
        <div className="decision-panel__quick-buttons">
          {decision.options.map((option) => (
            <button key={option.option_id} disabled={submitting} onClick={() => onSubmit([option.option_id])}>
              {t('decision.stain.yes')}
            </button>
          ))}
          <button disabled={submitting} onClick={() => onSubmit([])}>
            {t('common.no')}
          </button>
        </div>
      </div>
    );
  }

  if (decision.decision_type === 'hand_discard') {
    return (
      <div className="decision-panel decision-panel--quick">
        <h3>{t('decision.discard.title', { n: decision.min_selections })}</h3>
        <p>{t('decision.discard.hint', { selected: selected.length, n: decision.min_selections })}</p>
        <div className="decision-panel__quick-buttons">
          <button data-bar-label={t('common.confirm')} disabled={!canSubmit} onClick={() => onSubmit(selected)}>
            {t('common.confirm')}
          </button>
        </div>
      </div>
    );
  }

  // Joining a launched Poker match (designer's request, 2026-10-02): just
  // two bar buttons instead of clicking a ring on the Gamble card on the
  // board. There is always exactly one option (the current match).
  if (decision.decision_type === 'place_poker_bet') {
    const betOption = decision.options[0];
    return (
      <div className="decision-panel decision-panel--quick">
        <h3>{t('decision.pokerBet.question')}</h3>
        <div className="decision-panel__quick-buttons">
          <button
            data-bar-label={t('decision.pokerBet.join')}
            disabled={submitting || !betOption || decision.max_selections < 1}
            onClick={() => betOption && onSubmit([betOption.option_id])}
          >
            {t('decision.pokerBet.join')}
          </button>
          <button data-bar-label={t('common.pass')} disabled={submitting} onClick={() => onSubmit([])}>
            {t('common.pass')}
          </button>
        </div>
      </div>
    );
  }

  if (decision.decision_type === 'play_brawl_card') {
    return (
      <div className="decision-panel decision-panel--quick">
        <h3>{t('decision.brawlCard.question')}</h3>
        {decision.options.length > 0 && <p>{t('decision.brawlCard.hint')}</p>}
        <div className="decision-panel__quick-buttons">
          <button disabled={submitting} onClick={() => onSubmit([])}>
            {t('common.pass')}
          </button>
        </div>
      </div>
    );
  }

  if (decision.decision_type === 'launch_poker') {
    // Nothing eligible to actually launch with (no matching Gamble card
    // in hand right now) — nothing for a "Gioca!" button to do, so this
    // stays the old, easy-to-ignore inline prompt instead of interrupting
    // with a popup over a choice that isn't really there.
    if (decision.options.length === 0) {
      return (
        <div className="decision-panel decision-panel--quick">
          <h3>{t('decision.launchPoker.question')}</h3>
          <div className="decision-panel__quick-buttons">
            <button disabled={submitting} onClick={() => onSubmit([])}>
              {t('common.pass')}
            </button>
          </div>
        </div>
      );
    }
    // A real, blocking popup instead (game designer, 2026-09-26: "vorrei
    // che prima di risolvere il poker uscisse un popup che mi dicesse
    // 'Partita a poker?' e io la avvio con un tasto 'Gioca!'") — reuses
    // OutcomeModal's own overlay/card shell for visual consistency with
    // every other blocking popup already in the game. Usually exactly one
    // eligible Gamble card (one big "Gioca!"); the Preti-3 Skill can make
    // more than one match at once, so each gets its own card + button
    // rather than guessing which one "Gioca!" alone would mean.
    // Game designer, 2026-11-01: launching also asks whether to send a Criminal from the Covo to
    // the Den as a Gambler — the backend offers two options per card when it can
    // (`context.can_send_gambler`, each option's `send_gambler`) and one plain option when it can't.
    const canSendGambler = decision.context?.can_send_gambler === true;
    const noGamblerKey = NO_GAMBLER_REASON[String(decision.context?.no_gambler_reason ?? '')];
    const noGamblerReason = noGamblerKey ? t(noGamblerKey) : undefined;
    return (
      <div className="outcome-modal-overlay">
        <div className="outcome-modal launch-poker-modal" role="dialog" aria-modal="true" aria-label={t('decision.launchPoker.dialog')}>
          <h3>{t('decision.launchPoker.title')}</h3>
          <p className="launch-poker-modal__question">
            {canSendGambler
              ? t('decision.launchPoker.askGambler')
              : noGamblerReason}
          </p>
          <div className="launch-poker-modal__cards">
            {[...new Set(decision.options.map((option) => option.payload.card_id as string))].map((cardId) => (
              <div key={cardId} className="launch-poker-modal__choice">
                <img src={cardAssetUrl(cardId)} alt={cardId} className="launch-poker-modal__card-img" />
                {decision.options
                  .filter((option) => option.payload.card_id === cardId)
                  .map((option) => (
                    <button
                      key={option.option_id}
                      className="launch-poker-modal__card-button"
                      disabled={submitting}
                      onClick={() => onSubmit([option.option_id])}
                    >
                      <span>
                        {!canSendGambler
                          ? t('decision.launchPoker.play')
                          : option.payload.send_gambler === true
                            ? t('decision.launchPoker.playSend')
                            : t('decision.launchPoker.playStay')}
                      </span>
                    </button>
                  ))}
              </div>
            ))}
          </div>
          <button
            className="launch-poker-modal__decline"
            disabled={submitting}
            onClick={() => onSubmit([])}
          >
            {t('common.noThanks')}
          </button>
        </div>
      </div>
    );
  }

  if (decision.decision_type === 'play_customer_card_boost') {
    return (
      <div className="outcome-modal-overlay">
        <div className="outcome-modal launch-poker-modal" role="dialog" aria-modal="true" aria-label={t('decision.boost.dialog')}>
          <div className="launch-poker-modal__cards">
            {decision.options.map((option) => {
              const cardId = option.payload.card_id as string;
              return (
                <button
                  key={option.option_id}
                  className="launch-poker-modal__card-button"
                  disabled={submitting}
                  aria-label={t('decision.boost.useCard', { card: cardId })}
                  onClick={() => onSubmit([option.option_id])}
                >
                  <img src={cardAssetUrl(cardId)} alt={cardId} className="launch-poker-modal__card-img" />
                </button>
              );
            })}
          </div>
          <button className="launch-poker-modal__decline" disabled={submitting} onClick={() => onSubmit([])}>
            {t('common.noThanks')}
          </button>
        </div>
      </div>
    );
  }

  if (decision.decision_type === 'play_poker_card') {
    // §A10 Preti-1 lets a bettor reveal 2 cards instead of 1
    // (max_selections becomes 2) — the single-card case still submits
    // the instant a card is clicked (HandDrawer), but 2 cards need an
    // explicit Confirm, same pattern as hand_discard.
    if (decision.max_selections > 1) {
      return (
        <div className="decision-panel decision-panel--quick">
          <h3>{t('decision.pokerCards.title', { max: decision.max_selections })}</h3>
          <p>{t('decision.pokerCards.hint', { selected: selected.length, max: decision.max_selections })}</p>
          <div className="decision-panel__quick-buttons">
            <button data-bar-label={t('common.confirm')} disabled={!canSubmit} onClick={() => onSubmit(selected)}>
              {t('common.confirm')}
            </button>
          </div>
        </div>
      );
    }
    return (
      <div className="decision-panel decision-panel--quick">
        <h3>{t('decision.pokerCard.title')}</h3>
        <p>{t('decision.pokerCard.hint')}</p>
      </div>
    );
  }

  if (decision.decision_type === 'choose_poker_symbols') {
    // §A10 Preti-1's second step: no standalone art exists for the 5
    // Poker symbol colors (the flower icon only ever appears printed on
    // a customer card), so each of the 4 revealed instances is a plain
    // colored dot — click to toggle, exactly 2 must end up selected.
    return (
      <div className="decision-panel decision-panel--quick">
        <h3>{t('decision.pokerSymbols.title')}</h3>
        <p>{t('decision.pokerSymbols.hint', { selected: selected.length, max: decision.max_selections })}</p>
        <ul className="decision-panel__symbols">
          {decision.options.map((option) => {
            const symbol = String(option.payload.symbol ?? '');
            const isSelected = selected.includes(option.option_id);
            return (
              <li key={option.option_id}>
                <button
                  type="button"
                  className={
                    'decision-panel__symbol-dot' +
                    (isSelected ? ' decision-panel__symbol-dot--selected' : '')
                  }
                  style={{ backgroundColor: POKER_SYMBOL_COLOR[symbol] ?? '#495057' }}
                  title={pokerSymbolLabel(symbol) ?? symbol}
                  aria-label={pokerSymbolLabel(symbol) ?? symbol}
                  disabled={submitting}
                  onClick={() => onToggle(option.option_id)}
                />
              </li>
            );
          })}
        </ul>
        <div className="decision-panel__quick-buttons">
          <button data-bar-label={t('common.confirm')} disabled={!canSubmit} onClick={() => onSubmit(selected)}>
            {t('common.confirm')}
          </button>
        </div>
      </div>
    );
  }

  if (decision.decision_type === 'choose_marketing_card' ||
    (compactOptional && decision.decision_type === 'play_marketing_card' && marketingCardOpenedFor !== decision.decision_id)) {
    const cardOptions = [...new Map(decision.options.map((option) => [String(option.payload.card_id), option])).values()];
    return (
      <div className="outcome-modal-overlay">
        <div className="outcome-modal launch-poker-modal" role="dialog" aria-modal="true" aria-label={t('decision.marketing.dialog')}>
          <div className="launch-poker-modal__cards">
            {cardOptions.map((option) => {
              const cardId = String(option.payload.card_id);
              return <button key={cardId} className="launch-poker-modal__card-button" disabled={submitting}
                aria-label={t('decision.marketing.useCard', { card: cardId })}
                onClick={() => {
                  if (decision.decision_type === 'choose_marketing_card') onSubmit([option.option_id]);
                  else setMarketingCardOpenedFor(decision.decision_id);
                }}>
                <img src={cardAssetUrl(cardId)} alt={cardId} className="launch-poker-modal__card-img" />
              </button>;
            })}
          </div>
          <button className="launch-poker-modal__decline" disabled={submitting} onClick={() => onSubmit([])}>
            {t('common.noThanks')}
          </button>
        </div>
      </div>
    );
  }

  if (
    decision.decision_type === 'corrupt_officer'
    && decision.options.some((o) => 'payment_dope_type' in o.payload)
  ) {
    // Card 82 "PAYOFF": each officer can be paid in money or with 1 Dope of the Covo — listed
    // as buttons since several options share the same officer on the board.
    const where = (officerId: unknown) => {
      const officer = view.officers.find((o) => o.officer_id === officerId);
      const place = (officer?.hood_id ?? officer?.spot_id ?? '').replace('hood_q', t('decision.payoff.hoodShort')).toUpperCase();
      return `${officer?.officer_type === 'FED' ? t('decision.officer.fed') : t('decision.officer.cop')} ${place}`.trim();
    };
    return (
      <div className="decision-panel decision-panel--quick">
        <h3>{t('decision.payoff.question')}</h3>
        <div className="decision-panel__quick-buttons">
          {decision.options.map((option) => (
            <button key={option.option_id} disabled={submitting} onClick={() => onSubmit([option.option_id])}>
              {where(option.payload.officer_id)} — {option.payload.payment_dope_type
                ? t('decision.payoff.payDope', { dope: dopeName(String(option.payload.payment_dope_type)) })
                : t('decision.payoff.payMoney')}
            </button>
          ))}
          {decision.can_pass && (
            <button disabled={submitting} onClick={() => onSubmit([])}>{t('common.pass')}</button>
          )}
        </div>
      </div>
    );
  }

  if (BOARD_PACKAGE_TYPES.has(decision.decision_type)) {
    const followup = cardFollowupText(String(decision.context?.card_followup ?? ''));
    // The strict Marketing ("marketing_mode": "distinct_exact", off in every mode today): every
    // Stonk must move a different good by one level (min_selections > 0).
    const easyPriceMarketing = decision.decision_type === 'play_marketing_card' && decision.min_selections > 0;
    return (
      <div className="decision-panel decision-panel--quick">
        <div className={guidanceInCorner ? 'human-controls__guidance' : undefined}>
        <h3>{followup?.title ?? boardPackageLabel(decision.decision_type)}</h3>
        <p>
          {easyPriceMarketing
            ? t('decision.marketingStrict', { n: decision.min_selections })
            : (followup?.hint ?? tDyn(`decision.packageHint.${decision.decision_type}`) ?? '') +
              (decision.decision_type === 'move_criminal' ? unavailablePawnsHint(decision.context) : '')}
        </p>
        </div>
        <div className="decision-panel__quick-buttons">
          <button data-bar-label={buttonLabel} disabled={!canSubmit} onClick={() => onSubmit(selected)}>
            {buttonLabel}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="decision-panel">
      <h3>{decision.prompt_key}</h3>
      {decision.options.length === 0 ? (
        <p>{t('decision.noOptions')}</p>
      ) : (
        <ul className="decision-panel__options">
          {decision.options.map((option) => (
            <li key={option.option_id}>
              <label>
                <input
                  type={decision.max_selections === 1 ? 'radio' : 'checkbox'}
                  name="decision-option"
                  checked={selected.includes(option.option_id)}
                  onChange={() => onToggle(option.option_id)}
                />
                {option.label_key} {JSON.stringify(option.payload)}
              </label>
            </li>
          ))}
        </ul>
      )}
      <p>
        {t('decision.pickRange', { min: decision.min_selections, max: decision.max_selections })}
      </p>
      <button disabled={!canSubmit} onClick={() => onSubmit(selected)}>
        {buttonLabel}
      </button>
    </div>
  );
}
