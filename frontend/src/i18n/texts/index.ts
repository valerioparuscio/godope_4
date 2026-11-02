import { boardTexts } from './board';
import { commonTexts } from './common';
import { decisionTexts } from './decision';
import { errorTexts } from './errors';
import { logTexts } from './log';
import { outcomeTexts } from './outcome';
import { screenTexts } from './screens';
import { rulesTexts } from './rules';
import { setupTexts } from './setup';
import { shellTexts } from './shell';

/** Every interface text, by key. One file per area under ./texts, each entry holding both languages. */
export const TEXTS = {
  ...boardTexts,
  ...commonTexts,
  ...decisionTexts,
  ...errorTexts,
  ...logTexts,
  ...outcomeTexts,
  ...screenTexts,
  ...rulesTexts,
  ...setupTexts,
  ...shellTexts,
} as const;

export type TextKey = keyof typeof TEXTS;
