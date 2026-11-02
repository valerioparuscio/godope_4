import { useState } from 'react';
import { t } from '../../i18n';
import { allRulePages } from '../../rules/content';
import { searchRules } from '../../rules/search';

export function RulesSearch({ onNavigate }: { onNavigate: (slug: string) => void }) {
  const [query, setQuery] = useState('');
  const trimmed = query.trim();
  const results = trimmed ? searchRules(query, allRulePages()) : [];

  return (
    <div className="rules-search">
      <input
        type="text"
        className="rules-search__input"
        placeholder={t('rules.search')}
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      {trimmed && (
        <ul className="rules-search__results">
          {results.length === 0 ? (
            <li className="rules-search__no-results">{t('rules.noResults', { query: trimmed })}</li>
          ) : (
            results.map((page) => (
              <li key={page.slug}>
                <button type="button" className="rules-search__result" onClick={() => onNavigate(page.slug)}>
                  <strong>{page.title}</strong>
                  <span>{page.summary}</span>
                </button>
              </li>
            ))
          )}
        </ul>
      )}
    </div>
  );
}
