import { pawnAssetForPlayer, playerColorLabelForId, raidScoreUnit } from '../assets';
import { t, tDyn } from '../i18n';
import { playerNameForId } from '../player-names';
import type { GameViewResponse } from '../types';

interface RaidBannerProps {
  view: GameViewResponse;
}

// The words that name what is counted (LINK, RAT, POKER, COPS/FEDS, CASH,
// CRIMINALI) and the "+"/"-" are the point of the requirement: shown in accent.
function highlightKeywords(text: string) {
  return text.split(/([A-Z][A-Z/]+|\+|-)/).map((part, i) =>
    i % 2 === 1 ? <span key={i} className="raid-banner__key">{part}</span> : part,
  );
}

export function RaidBanner({ view }: RaidBannerProps) {
  const standings = view.raid_standings;
  const criterion = standings?.escape_criterion ?? '';
  const title = tDyn(`raid.title.${criterion}`);
  const requirement = tDyn(`raid.need.${criterion}`);
  const choosingTeams = view.phase === 'tip_off';
  const unit = standings?.escape_criterion === 'least_dope_value'
    ? t('raidBanner.dopeUnit')
    : raidScoreUnit(criterion) ?? '';
  return (
    <section className="raid-banner" aria-label={t('raidBanner.label')}>
      <div className="raid-banner__intro">
      <div className="raid-banner__heading">{title ?? t('raidBanner.heading')}</div>
      {requirement && (
        <p className="raid-banner__requirement">
          <span className="raid-banner__requirement-label">{t('raidBanner.toEscape')}</span>
          <span className="raid-banner__requirement-text">{highlightKeywords(requirement)}</span>
        </p>
      )}
      {!view.raid_card_id && (
        <span className="raid-banner__text">{t('raidBanner.none')}</span>
      )}
      </div>
      {standings && (
        <div className="raid-banner__standings">
          {choosingTeams && <div className="raid-banner__caption">{t('raidBanner.provisionalTeams')}</div>}
          {(['a', 'b'] as const).map((team) => {
            const players = team === 'a' ? standings.team_a : standings.team_b;
            const total = team === 'a' ? standings.total_a : standings.total_b;
            const leading = standings.leading_team === team;
            return (
              <div key={team} className={'raid-banner__team' + (leading ? ' raid-banner__team--leading' : '')}>
                <div className="raid-banner__team-players">
                  {players.map((id) => <img key={id} src={pawnAssetForPlayer(id)} alt={playerColorLabelForId(id)} title={playerNameForId(view, id)} />)}
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
