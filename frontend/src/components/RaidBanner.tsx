import { pawnAssetForPlayer, playerColorLabelForId, raidScoreUnit } from '../assets';
import { t, tDyn } from '../i18n';
import { playerNameForId } from '../player-names';
import type { GameViewResponse } from '../types';
import { FitText } from './FitText';

interface RaidBannerProps {
  view: GameViewResponse;
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
        <FitText
          text={requirement}
          boxClassName="raid-banner__requirement"
          textClassName="raid-banner__requirement-text"
          keyClassName="raid-banner__key"
        />
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
