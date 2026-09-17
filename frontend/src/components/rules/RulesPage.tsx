import type { RulePage } from '../../rules/types';
import { RulesLink } from './RulesLink';

// Renders one RulePage's fixed template (game designer's spec §8) — only
// the sections a page actually fills in are shown; "Sintesi" is the only
// one guaranteed to exist.
export function RulesPage({ page, onNavigate }: { page: RulePage; onNavigate: (slug: string) => void }) {
  return (
    <div className="rules-page">
      <h2 className="rules-page__title">{page.title}</h2>
      <p className="rules-page__summary">{page.summary}</p>

      {page.images && page.images.length > 0 && (
        <div className="rules-page__images">
          {page.images.map((image, i) => (
            <figure key={i} className="rules-page__image">
              <img src={image.src} alt={image.alt} />
              {image.caption && <figcaption>{image.caption}</figcaption>}
            </figure>
          ))}
        </div>
      )}

      {page.cosaServe && page.cosaServe.length > 0 && (
        <section className="rules-page__section">
          <h3>Cosa serve</h3>
          <ul>
            {page.cosaServe.map((text, i) => (
              <li key={i}>{text}</li>
            ))}
          </ul>
        </section>
      )}

      {page.cosaFai && page.cosaFai.length > 0 && (
        <section className="rules-page__section">
          <h3>Cosa fai</h3>
          <ol>
            {page.cosaFai.map((text, i) => (
              <li key={i}>{text}</li>
            ))}
          </ol>
        </section>
      )}

      {page.cosaSuccede && page.cosaSuccede.length > 0 && (
        <section className="rules-page__section">
          <h3>Cosa succede</h3>
          <ul>
            {page.cosaSuccede.map((text, i) => (
              <li key={i}>{text}</li>
            ))}
          </ul>
        </section>
      )}

      {page.attenzione && page.attenzione.length > 0 && (
        <section className="rules-page__section rules-page__section--warning">
          <h3>Attenzione</h3>
          <ul>
            {page.attenzione.map((text, i) => (
              <li key={i}>{text}</li>
            ))}
          </ul>
        </section>
      )}

      {page.esempio && (
        <section className="rules-page__section rules-page__section--example">
          <h3>Esempio</h3>
          <p>{page.esempio}</p>
        </section>
      )}

      {page.related && page.related.length > 0 && (
        <section className="rules-page__related">
          <h3>Vedi anche</h3>
          <div className="rules-page__related-links">
            {page.related.map((slug) => (
              <RulesLink key={slug} slug={slug} onNavigate={onNavigate} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
