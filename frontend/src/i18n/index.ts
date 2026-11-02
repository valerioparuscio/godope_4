import type { Lang } from './define';
import { getLang } from './lang';
import { TEXTS, type TextKey } from './texts';

export { getLang, setLang, useLang } from './lang';
export type { Lang } from './define';
export type { TextKey } from './texts';

export type TextParams = Record<string, string | number>;

function fill(template: string, params?: TextParams): string {
  if (!params) return template;
  return template.replace(/\{(\w+)\}/g, (placeholder, name: string) =>
    name in params ? String(params[name]) : placeholder,
  );
}

/** The text for `key` in the current language; `{name}` placeholders are filled from `params`. */
export function t(key: TextKey, params?: TextParams): string {
  return fill(TEXTS[key][getLang()], params);
}

/** The text for a key built at run time (e.g. `raid.title.${criterion}`), or undefined when there is none. */
export function tDyn(key: string, params?: TextParams): string | undefined {
  return key in TEXTS ? t(key as TextKey, params) : undefined;
}

/** The name of a Dope type (frog, chameleon, octopus, owl) in the current language. */
export function dopeName(type: string): string {
  return tDyn(`dope.${type}`) ?? type;
}

/** `t` for a count: uses `<key>.one` when `count` is 1 and `<key>.other` otherwise, with `{count}` filled in. */
export function tn(key: string, count: number, params?: TextParams): string {
  const entry = TEXTS[`${key}.${count === 1 ? 'one' : 'other'}` as TextKey];
  return fill(entry[getLang()], { count, ...params });
}

/** The text of `lang` regardless of the current one (e.g. a label that must not follow the language). */
export function textIn(lang: Lang, key: TextKey, params?: TextParams): string {
  return fill(TEXTS[key][lang], params);
}
