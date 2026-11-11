import { t } from '../i18n';

/** Covers the game on a phone held upright (the CSS decides when, see `.rotate-hint` in responsive.css):
 *  the board is wide, so it asks for the other orientation instead of squeezing it. */
export function RotateHint() {
  return (
    <div className="rotate-hint" role="alert">
      <div className="rotate-hint__phone" aria-hidden="true" />
      <p className="rotate-hint__text">{t('app.rotateHint')}</p>
    </div>
  );
}
