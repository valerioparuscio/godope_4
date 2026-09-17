import { categoryOfSlug, RULE_CATEGORY_LABEL } from '../../rules/types';
import { RULE_PAGE_BY_SLUG } from '../../rules/content';

// A pure function of currentSlug (category + page title), not of the
// back-navigation history — those are different concepts: this shows
// *where a page lives*, not *how you got here* (game designer's own
// example: "Regolamento > Polizia > Jail > Evasione").
export function RulesBreadcrumb({
  currentSlug,
  onNavigateHome,
}: {
  currentSlug: string | null;
  onNavigateHome: () => void;
}) {
  const page = currentSlug ? RULE_PAGE_BY_SLUG[currentSlug] : null;

  return (
    <nav className="rules-breadcrumb" aria-label="Percorso">
      <button type="button" className="rules-breadcrumb__crumb" onClick={onNavigateHome}>
        Regolamento
      </button>
      {page && (
        <>
          <span className="rules-breadcrumb__separator">›</span>
          <span className="rules-breadcrumb__crumb rules-breadcrumb__crumb--muted">
            {RULE_CATEGORY_LABEL[categoryOfSlug(page.slug)]}
          </span>
          <span className="rules-breadcrumb__separator">›</span>
          <span className="rules-breadcrumb__crumb rules-breadcrumb__crumb--current">{page.title}</span>
        </>
      )}
    </nav>
  );
}
