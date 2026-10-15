import { DOPE_ASSET, actionTypeAssetUrl, hoodContactAssetUrl } from '../assets';

// Words a tutorial table can show with their own icon — only the ones that
// have one (a Rissa or a Poker has no icon of its own). Keyed by the word a
// cell part *starts* with, so "Muovere (fare Rissa)" still finds "Muovere".
// The action icons that are dark line art are drawn white on the sheet's dark
// background (`mono`). The coloured ones (Merci, Clienti) and the white
// place/move/buy/sell icons stay as they are.
// All six action icons are white now, so none needs the `mono` treatment.
const ACTION_WORDS = new Set<string>();

const ICON_BY_WORD: Record<string, string> = {
  Camaleonte: DOPE_ASSET.camaleonte,
  Polpo: DOPE_ASSET.polpo,
  Rana: DOPE_ASSET.rana,
  Gufo: DOPE_ASSET.gufo,
  Acquistare: actionTypeAssetUrl('buy_dope'),
  Vendere: actionTypeAssetUrl('sell_dope'),
  Muovere: actionTypeAssetUrl('move_criminal'),
  Piazzare: actionTypeAssetUrl('place_criminal'),
  Manovrare: actionTypeAssetUrl('maneuver_officer'),
  Corrompere: actionTypeAssetUrl('corrupt_officer'),
  Acquista: actionTypeAssetUrl('buy_dope'),
  Vendi: actionTypeAssetUrl('sell_dope'),
  Sposta: actionTypeAssetUrl('move_criminal'),
  Piazza: actionTypeAssetUrl('place_criminal'),
  Manovra: actionTypeAssetUrl('maneuver_officer'),
  Corrompi: actionTypeAssetUrl('corrupt_officer'),
  Artisti: hoodContactAssetUrl('artisti'),
  Studenti: hoodContactAssetUrl('studenti'),
  Manager: hoodContactAssetUrl('manager'),
  Preti: hoodContactAssetUrl('preti'),
  Politici: hoodContactAssetUrl('politici'),
};

export function iconForPart(part: string): { url: string; mono: boolean } | null {
  const word = part.trim().split(/[\s(]/)[0];
  const url = ICON_BY_WORD[word];
  return url ? { url, mono: ACTION_WORDS.has(word) } : null;
}
