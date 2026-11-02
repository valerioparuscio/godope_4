import { Fragment, type ReactNode } from 'react';
import { getLang } from './lang';
import { TEXTS, type TextKey } from './texts';

/** Like `t`, for texts whose `{name}` placeholders hold React elements (e.g. a coloured player name). */
export function tNodes(key: TextKey, nodes: Record<string, ReactNode>): ReactNode {
  return TEXTS[key][getLang()]
    .split(/\{(\w+)\}/)
    .map((part, index) => (index % 2 === 1 ? <Fragment key={index}>{nodes[part]}</Fragment> : part));
}
