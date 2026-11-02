import { getLang } from '../i18n';
import { TUTORIAL_EN } from './en';
import type { TutorialMarker, TutorialScenario, TutorialSheet } from './scenarios';

const warned = new Set<string>();

/** A tutorial sentence in the interface language: the Italian text is its own key (see ./en.ts). */
export function tt(text: string): string {
  if (getLang() !== 'en' || text === '') return text;
  const english = TUTORIAL_EN[text];
  if (english === undefined && import.meta.env.DEV && !warned.has(text)) {
    warned.add(text);
    console.warn(`[tutorial] no English for "${text}"`);
  }
  return english ?? text;
}

const localizeMarker = (marker: TutorialMarker): TutorialMarker => ({ ...marker, label: tt(marker.label) });

function localizeSheet(sheet: TutorialSheet): TutorialSheet {
  return {
    title: tt(sheet.title),
    items: sheet.items?.map((item) => ({ ...item, label: tt(item.label), text: tt(item.text) })),
    table: sheet.table && {
      columns: sheet.table.columns?.map(tt),
      rows: sheet.table.rows.map((row) => row.map(tt)),
    },
    footer: sheet.footer?.map((item) => ({ label: tt(item.label), text: tt(item.text) })),
  };
}

const cache = new Map<string, TutorialScenario>();

/** A scene with every sentence in the interface language (the scene itself when that is Italian). Cached, so the
 *  same scene is the same object from one render to the next. */
export function localizeScenario(scenario: TutorialScenario): TutorialScenario {
  if (getLang() !== 'en') return scenario;
  let localized = cache.get(scenario.id);
  if (!localized) {
    localized = {
      ...scenario,
      title: tt(scenario.title),
      instruction: tt(scenario.instruction),
      outcome: tt(scenario.outcome),
      markers: scenario.markers?.map(localizeMarker),
      outcomeMarkers: scenario.outcomeMarkers?.map(localizeMarker),
      sheet: scenario.sheet && localizeSheet(scenario.sheet),
      decisionInstructions: scenario.decisionInstructions && Object.fromEntries(
        Object.entries(scenario.decisionInstructions).map(([type, text]) => [type, tt(text)]),
      ),
    };
    cache.set(scenario.id, localized);
  }
  return localized;
}
