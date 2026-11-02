export type Lang = 'it' | 'en';

export const LANGS: readonly Lang[] = ['it', 'en'];

/** One piece of interface text in every language. A language missing from an entry is a compile error,
 *  so adding a text without its English (or Italian) cannot be forgotten. */
export interface Text {
  it: string;
  en: string;
}

/** Identity helper that keeps each table's keys as literal types (for `t('key')` autocompletion and checks). */
export function defineTexts<const T extends Record<string, Text>>(texts: T): T {
  return texts;
}
