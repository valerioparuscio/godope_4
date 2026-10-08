import type { CSSProperties } from 'react';
import { OFFICER_ACTION_ICON, type OfficerActionKind } from '../assets';

/** Sposta / Arresta / Requisisci: the icon file's black tile, cut out of its white
 *  margin, as a square that takes its size from the CSS (width = height). */
export function OfficerActionIcon({ action, className }: { action: OfficerActionKind; className?: string }) {
  const { src, crop } = OFFICER_ACTION_ICON[action];
  const width = crop.right - crop.left;
  const height = crop.bottom - crop.top;
  const style = {
    '--oai-w': `${(100 * 100) / width}%`,
    '--oai-h': `${(100 * 100) / height}%`,
    '--oai-l': `${-(crop.left * 100) / width}%`,
    '--oai-t': `${-(crop.top * 100) / height}%`,
  } as CSSProperties;
  return (
    <span className={'officer-action-icon' + (className ? ` ${className}` : '')} style={style}>
      <img src={src} alt="" />
    </span>
  );
}
