import { ALL_RULE_PAGES } from '../../rules/content';
import { HOW_DO_I_LINKS, WHAT_IF_LINKS } from '../../rules/quick-links';
import { categoryOfSlug, RULE_CATEGORY_LABEL, type RuleCategorySlug } from '../../rules/types';
import type { RulePage } from '../../rules/types';
import { RulesLink } from './RulesLink';
import { RulesSearch } from './RulesSearch';

function groupByCategory(pages: RulePage[]): Map<RuleCategorySlug, RulePage[]> {
  const groups = new Map<RuleCategorySlug, RulePage[]>();
  for (const page of pages) {
    const category = categoryOfSlug(page.slug);
    const bucket = groups.get(category);
    if (bucket) bucket.push(page);
    else groups.set(category, [page]);
  }
  return groups;
}

// The modal's index: search, then the designer's spec §6 "Come faccio
// a...?"/"Cosa succede se...?" shortcut lists, then the full index
// grouped by category.
export function RulesHome({ onNavigate }: { onNavigate: (slug: string) => void }) {
  const groups = groupByCategory(ALL_RULE_PAGES);

  return (
    <div className="rules-home">
      <RulesSearch onNavigate={onNavigate} />

      <section className="rules-home__quick-links">
        <div>
          <h3>Come faccio a...</h3>
          <ul>
            {HOW_DO_I_LINKS.map((link, i) => (
              <li key={i}>
                <RulesLink slug={link.slug} onNavigate={onNavigate}>
                  {link.question}
                </RulesLink>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <h3>Cosa succede se...</h3>
          <ul>
            {WHAT_IF_LINKS.map((link, i) => (
              <li key={i}>
                <RulesLink slug={link.slug} onNavigate={onNavigate}>
                  {link.question}
                </RulesLink>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <section className="rules-home__index">
        {Array.from(groups.entries()).map(([category, pages]) => (
          <div key={category} className="rules-home__category">
            <h3>{RULE_CATEGORY_LABEL[category]}</h3>
            <ul>
              {pages.map((page) => (
                <li key={page.slug}>
                  <RulesLink slug={page.slug} onNavigate={onNavigate} />
                </li>
              ))}
            </ul>
          </div>
        ))}
      </section>
    </div>
  );
}
