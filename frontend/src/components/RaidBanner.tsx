import { pawnAssetForPlayer, playerColorLabelForId, RAID_SCORE_UNIT_BY_CRITERION } from '../assets';
import type { GameViewResponse } from '../types';

interface RaidBannerProps {
  view: GameViewResponse;
}

const RAID_COPY: Record<string, { title: string; requirement: string }> = {
  most_links_with_contacts: { title: 'Retata dei Palazzi', requirement: 'avere + LINK coi Clienti' },
  most_criminals_in_jail: { title: 'Retata dalla Prigione', requirement: 'avere + RAT in prigione' },
  least_dope_value: { title: 'Retata nei Covi', requirement: 'avere meno valore di Merci' },
  most_poker_wins: { title: "Retata dell’Azzardo", requirement: 'avere + CHIP POKER nel Covo' },
  most_cops_bought: { title: 'Retata dei Corrotti', requirement: 'avere + COPS/FEDS nel Covo' },
  most_money: { title: 'Retata Finanziaria', requirement: 'avere + CASH' },
  most_criminals_in_hoods: { title: 'Retata in Strada', requirement: 'avere + CRIMINALI nei Quartieri' },
};

// The words that name what is counted (LINK, RAT, POKER, COPS/FEDS, CASH,
// CRIMINALI) and the "+" are the point of the requirement: shown in accent.
function highlightKeywords(text: string) {
  return text.split(/([A-Z][A-Z/]+|\+)/).map((part, i) =>
    i % 2 === 1 ? <span key={i} className="raid-banner__key">{part}</span> : part,
  );
}

export function RaidBanner({ view }: RaidBannerProps) {
  const standings = view.raid_standings;
  const copy = RAID_COPY[standings?.escape_criterion ?? ''];
  const choosingTeams = view.phase === 'tip_off';
  const unit = standings?.escape_criterion === 'least_dope_value'
    ? '$ merci'
    : RAID_SCORE_UNIT_BY_CRITERION[standings?.escape_criterion ?? ''] ?? '';
  return (
    <section className="raid-banner" aria-label="Retata e punteggi parziali">
      <div className="raid-banner__intro">
      <div className="raid-banner__heading">{copy?.title ?? 'Retata'}</div>
      {copy && (
        <p className="raid-banner__requirement">
          <span className="raid-banner__requirement-label">Per sfuggire devi</span>
          <span className="raid-banner__requirement-text">{highlightKeywords(copy.requirement)}</span>
        </p>
      )}
      {!view.raid_card_id && (
        <span className="raid-banner__text">Nessuna Retata rivelata.</span>
      )}
      </div>
      {standings && (
        <div className="raid-banner__standings">
          {choosingTeams && <div className="raid-banner__caption">Squadre provvisorie</div>}
          {(['a', 'b'] as const).map((team) => {
            const players = team === 'a' ? standings.team_a : standings.team_b;
            const total = team === 'a' ? standings.total_a : standings.total_b;
            const leading = standings.leading_team === team;
            return (
              <div key={team} className={'raid-banner__team' + (leading ? ' raid-banner__team--leading' : '')}>
                <div className="raid-banner__team-players">
                  {players.map((id) => <img key={id} src={pawnAssetForPlayer(id)} alt={playerColorLabelForId(id)} title={view.players.find((p) => p.player_id === id)?.display_name} />)}
                </div>
                <div className="raid-banner__result">
                  <strong className="raid-banner__score">{total}</strong>
                  <span className="raid-banner__unit">{unit}</span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
