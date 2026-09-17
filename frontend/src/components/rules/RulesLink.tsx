import type { ReactNode } from 'react';
import { RULE_PAGE_BY_SLUG } from '../../rules/content';

// A clickable reference to another rule page — never a real <a href>
// (game designer's spec §16: avoid real browser navigation), just an
// in-memory navigate(slug) call. Used by related-links, quick-links, and
// non-final breadcrumb crumbs.
export function RulesLink({
  slug,
  onNavigate,
  children,
}: {
  slug: string;
  onNavigate: (slug: string) => void;
  children?: ReactNode;
}) {
  const page = RULE_PAGE_BY_SLUG[slug];
  // A slug not backfilled yet renders nothing instead of a dead link —
  // content/index.ts's own dev-time warning already flags this case for
  // `related`; quick-links.ts is kept in sync by hand instead.
  if (!page) return null;
  return (
    <button type="button" className="rules-link" onClick={() => onNavigate(slug)}>
      {children ?? page.title}
    </button>
  );
}
