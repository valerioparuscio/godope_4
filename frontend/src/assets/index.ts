// Single source of truth mapping the game's own IDs (card_id, DopeType,
// PlayerId) to the actual asset filenames on disk — component code should
// import from here, never reference a raw filename directly, so a future
// re-export/rename only touches this file.

import board from './board/BOARD_v14_b.png';

import cop from './officers/cop.png';
import fed from './officers/fed.png';

import chipCamaleonte from './dope/CHIP_RET.png';
import chipGufo from './dope/CHIP_GUF.png';
import chipPolpo from './dope/CHIP_POL.png';
import chipRana from './dope/CHIP_RAN.png';

import pawnRed from './pawns/red.png';
import pawnBlu from './pawns/blu.png';
import pawnGreen from './pawns/green.png';
import pawnYellow from './pawns/yellow.png';

import repBlu from './tokens/REP_BLU.png';
import repGialla from './tokens/REP_GIALLA.png';
import repRossa from './tokens/REP_ROSSA.png';
import repVerde from './tokens/REP_VERDE.png';

import chipBlu from './poker_chips/2$ blu.png';
import chipGiallo from './poker_chips/2$ giallo.png';
import chipRosso from './poker_chips/2$ rosso.png';
import chipVerde from './poker_chips/2$ verde.png';

import priceCamaleonte from './price/price_CAMA.png';
import priceGufo from './price/price_GUFO.png';
import pricePolpo from './price/price_POLPO.png';
import priceRana from './price/price_RANA.png';

import cashR from './cash/R.png';
import cashB from './cash/B.png';
import cashG from './cash/G.png';
import cashY from './cash/Y.png';
import cashR30 from './cash/R30.png';
import cashB30 from './cash/B30.png';
import cashG30 from './cash/G30.png';
import cashY30 from './cash/Y30.png';

export const BOARD_BACKGROUND = board;

export const OFFICER_ASSET: Record<'cop' | 'fed', string> = {
  cop,
  fed,
};

// Matches DopeType values in data/dope_types.json exactly.
export const DOPE_ASSET: Record<string, string> = {
  camaleonte: chipCamaleonte,
  gufo: chipGufo,
  polpo: chipPolpo,
  rana: chipRana,
};

// The market-price track's own physical token, one per Dope type — moved
// along PRICE_TOKEN_POSITION (board-layout.ts) instead of a price table.
export const PRICE_TOKEN_ASSET: Record<string, string> = {
  camaleonte: priceCamaleonte,
  gufo: priceGufo,
  polpo: pricePolpo,
  rana: priceRana,
};

// player_0..3 -> color, per the game designer's confirmed mapping
// (2026-08-02): 0=red, 1=blu, 2=green, 3=yellow. No "color" concept exists
// in the engine itself — this is a frontend-only display convention.
const PLAYER_COLOR_BY_SEAT = ['red', 'blu', 'green', 'yellow'] as const;
export type PlayerColor = (typeof PLAYER_COLOR_BY_SEAT)[number];

const PAWN_ASSET_BY_COLOR: Record<(typeof PLAYER_COLOR_BY_SEAT)[number], string> = {
  red: pawnRed,
  blu: pawnBlu,
  green: pawnGreen,
  yellow: pawnYellow,
};

const REP_ASSET_BY_COLOR: Record<(typeof PLAYER_COLOR_BY_SEAT)[number], string> = {
  red: repRossa,
  blu: repBlu,
  green: repVerde,
  yellow: repGialla,
};

const POKER_CHIP_ASSET_BY_COLOR: Record<(typeof PLAYER_COLOR_BY_SEAT)[number], string> = {
  red: chipRosso,
  blu: chipBlu,
  green: chipVerde,
  yellow: chipGiallo,
};

function seatFromPlayerId(playerId: string): number {
  const match = playerId.match(/(\d+)$/);
  return match ? Number(match[1]) : 0;
}

// Exposed so the board can order/size the money-track markers by seat
// without re-deriving the seat index itself.
export function seatIndexForPlayer(playerId: string): number {
  return seatFromPlayerId(playerId);
}

export function pawnAssetForPlayer(playerId: string): string {
  const color = PLAYER_COLOR_BY_SEAT[seatFromPlayerId(playerId)];
  return PAWN_ASSET_BY_COLOR[color];
}

// No dedicated "stained" REP asset exists yet (2026-08-02): rendered as the
// clean token with a CSS filter (see App.css's .rep-token--stained) rather
// than a second image, until a real stained asset is provided.
export function repAssetForPlayer(playerId: string): string {
  const color = PLAYER_COLOR_BY_SEAT[seatFromPlayerId(playerId)];
  return REP_ASSET_BY_COLOR[color];
}

export function pokerChipAssetForPlayer(playerId: string): string {
  const color = PLAYER_COLOR_BY_SEAT[seatFromPlayerId(playerId)];
  return POKER_CHIP_ASSET_BY_COLOR[color];
}

// Same red/blu/green/yellow convention as the pawn/REP/chip assets above,
// exposed as a plain string so the sidebar player cards can tint
// themselves (designer's request, 2026-08-16 — "un po' più colorati")
// without duplicating the seat->color mapping.
export function playerColorForId(playerId: string): (typeof PLAYER_COLOR_BY_SEAT)[number] {
  return PLAYER_COLOR_BY_SEAT[seatFromPlayerId(playerId)];
}

const PLAYER_COLOR_LABEL_IT: Record<(typeof PLAYER_COLOR_BY_SEAT)[number], string> = {
  red: 'Rosso',
  blu: 'Blu',
  green: 'Verde',
  yellow: 'Giallo',
};

// The user-facing Italian color name (designer's request, 2026-08-16 —
// bot-turn narration: "Turno giocatore Rosso"), same seat->color mapping
// as playerColorForId above.
export function playerColorLabelForId(playerId: string): string {
  return PLAYER_COLOR_LABEL_IT[playerColorForId(playerId)];
}

const CASH_ASSET_BY_COLOR: Record<(typeof PLAYER_COLOR_BY_SEAT)[number], string> = {
  red: cashR,
  blu: cashB,
  green: cashG,
  yellow: cashY,
};

// The board's money track only prints $0-30; once a player passes $30
// their marker restarts at 0 and switches to this "+30" variant (designer's
// request, 2026-08-16) so the real amount is track-position + 30.
const CASH_ASSET_LAP_BY_COLOR: Record<(typeof PLAYER_COLOR_BY_SEAT)[number], string> = {
  red: cashR30,
  blu: cashB30,
  green: cashG30,
  yellow: cashY30,
};

export function moneyMarkerAssetForPlayer(playerId: string, hasLooped: boolean): string {
  const color = PLAYER_COLOR_BY_SEAT[seatFromPlayerId(playerId)];
  return hasLooped ? CASH_ASSET_LAP_BY_COLOR[color] : CASH_ASSET_BY_COLOR[color];
}

const CARD_MODULES = import.meta.glob('./cards/*.png', {
  eager: true,
  import: 'default',
}) as Record<string, string>;

export function cardAssetUrl(cardId: string): string {
  // card_001 .. card_100 -> 01.png .. 100.png
  const num = cardId.replace('card_', '').replace(/^0+/, '') || '0';
  const padded = num.padStart(2, '0');
  const key = Object.keys(CARD_MODULES).find((path) => path.endsWith(`/${padded}.png`));
  return key ? CARD_MODULES[key] : '';
}

// data/skills.json's skill_id is exactly `skill_{contact_id}_{tier}` — the
// art files use the same contact prefix (art/stu/man/pre/pol) + tier, so
// the mapping is a straight lookup, no ordering assumptions needed.
const SKILL_MODULES = import.meta.glob('./skill/*.png', {
  eager: true,
  import: 'default',
}) as Record<string, string>;

const SKILL_FILE_PREFIX_BY_CONTACT: Record<string, string> = {
  artisti: 'art',
  studenti: 'stu',
  manager: 'man',
  preti: 'pre',
  politici: 'pol',
};

export function skillAssetUrl(skillId: string): string {
  // skill_artisti_1 -> ["artisti", "1"]
  const match = skillId.match(/^skill_([a-z]+)_(\d+)$/);
  if (!match) return '';
  const [, contactId, tier] = match;
  const prefix = SKILL_FILE_PREFIX_BY_CONTACT[contactId];
  const key = Object.keys(SKILL_MODULES).find((path) => path.endsWith(`/${prefix}${tier}.png`));
  return key ? SKILL_MODULES[key] : '';
}

// data/raids.json's 7 raid cards, in file order, matched to their
// escape_criterion by content (verified against each image, 2026-08-02;
// re-verified 2026-08-16 against the designer's wide-banner replacement
// set, same Job-icon naming convention — links/rats/dope/poker/cops/
// cash/crimes): raid_01 most_links_with_contacts, raid_02
// most_criminals_in_jail, raid_03 least_dope_value, raid_04
// most_poker_wins, raid_05 most_cops_bought, raid_06 most_money, raid_07
// most_criminals_in_hoods.
import raidLinks from './raid/links.png';
import raidRats from './raid/rats.png';
import raidDope from './raid/dope.png';
import raidPoker from './raid/poker.png';
import raidCops from './raid/cops.png';
import raidCash from './raid/cash.png';
import raidCrimes from './raid/crimes.png';

export const RAID_ASSET: Record<string, string> = {
  raid_01: raidLinks,
  raid_02: raidRats,
  raid_03: raidDope,
  raid_04: raidPoker,
  raid_05: raidCops,
  raid_06: raidCash,
  raid_07: raidCrimes,
};

// data/jobs.json's job_01..job_09 in tier/definition order; the uploaded
// files are numbered 01,03,05..17 (the designer's own sheet numbering, not
// job_id) but sort into the same 9-item sequence — verified 01->job_01
// ("1 BRAWL") and 03->job_02 ("1 COPS") against jobs.json, 2026-08-02.
const JOB_MODULES = import.meta.glob('./job/*.png', {
  eager: true,
  import: 'default',
}) as Record<string, string>;

const JOB_IDS_IN_FILE_ORDER = Array.from({ length: 9 }, (_, i) => `job_0${i + 1}`);

export const JOB_ASSET: Record<string, string> = Object.fromEntries(
  Object.keys(JOB_MODULES)
    .sort()
    .map((path, i) => [JOB_IDS_IN_FILE_ORDER[i], JOB_MODULES[path]]),
);
