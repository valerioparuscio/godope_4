import { useLayoutEffect, useRef } from 'react';
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

const FIT_REFERENCE_PX = 100;
const FIT_MAX_PX = 80;

// Sizes the text so it fills the whole width of its box: each Raid's word has a different
// length, and the point is that it reads big. Re-fits when the box is resized or the font loads.
function FitText({ text }: { text: string }) {
  const boxRef = useRef<HTMLDivElement>(null);
  const textRef = useRef<HTMLSpanElement>(null);
  useLayoutEffect(() => {
    const box = boxRef.current;
    const label = textRef.current;
    if (!box || !label) return undefined;
    const fit = () => {
      const width = box.clientWidth;
      if (width <= 0) return;
      label.style.fontSize = `${FIT_REFERENCE_PX}px`;
      const natural = label.offsetWidth;
      if (natural <= 0) return;
      const size = Math.floor(((FIT_REFERENCE_PX * width) / natural) * 0.99 * 10) / 10;
      // A layout that is short on height (a phone) can lower the cap with --fit-max-px.
      const cssMax = parseFloat(getComputedStyle(box).getPropertyValue('--fit-max-px'));
      label.style.fontSize = `${Math.min(cssMax > 0 ? cssMax : FIT_MAX_PX, size)}px`;
    };
    fit();
    const observer = new ResizeObserver(fit);
    observer.observe(box);
    void document.fonts?.ready.then(fit);
    return () => observer.disconnect();
  }, [text]);
  return (
    <div ref={boxRef} className="raid-banner__requirement">
      <span ref={textRef} className="raid-banner__requirement-text">{highlightKeywords(text)}</span>
    </div>
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
      {requirement && <FitText text={requirement} />}
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
