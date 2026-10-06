import type { TutorialSheet as TutorialSheetData } from '../tutorial/scenarios';
import { actionTypeAssetUrl } from '../assets';
import { iconForPart } from '../tutorial/icons';
import { splitSentences } from '../tutorial/text';

// Their icons are already white; the others (dark line art) get the white filter.
const WHITE_ACTIONS = new Set(['place_criminal', 'move_criminal', 'buy_dope', 'sell_dope']);

/** A table cell: comma-separated parts, each led by its icon when it has one. */
function CellParts({ text }: { text: string }) {
  // Split on commas and " o ", keeping the separators so the text reads as written.
  const tokens = text.split(/(,\s*|\s+o\s+)/);
  return <>{tokens.map((token, i) => {
    if (i % 2 === 1) return <span key={i}>{token.trim() === 'o' ? ' o ' : token}</span>;
    const icon = iconForPart(token);
    return <span key={i} className="tutorial-sheet__part">
      {icon && <img src={icon.url} alt=""
        className={'tutorial-sheet__icon' + (icon.mono ? ' tutorial-sheet__icon--white' : '')} />}
      {token}
    </span>;
  })}</>;
}

interface TutorialSheetProps {
  sheet: TutorialSheetData;
  onClose: () => void;
}

/** A temporary info card laid over the board (a list, a table of rewards…) —
 *  the lesson text stays in the top bar, this carries the detail. */
export function TutorialSheet({ sheet, onClose }: TutorialSheetProps) {
  return (
    <section className="tutorial-sheet" aria-label={sheet.title}>
      <header className="tutorial-sheet__header">
        <h2>{sheet.title}</h2>
        <button className="tutorial-sheet__close" onClick={onClose}>Vedi il tabellone</button>
      </header>
      {sheet.table && (
        <table className="tutorial-sheet__table">
          {sheet.table.columns && <thead>
            <tr>{sheet.table.columns.map((column, i) => <th key={i}>{column}</th>)}</tr>
          </thead>}
          <tbody>
            {sheet.table.rows.map((row) => (
              <tr key={row[0]}>
                {row.map((cell, i) => i === 0
                  ? <th key={i} scope="row"><CellParts text={cell} /></th>
                  : <td key={i}><CellParts text={cell} /></td>)}
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {sheet.items && <ul className={'tutorial-sheet__list' + (sheet.items.length > 6 ? ' tutorial-sheet__list--columns' : '')}>
        {sheet.items.map((item) => (
          <li key={item.label + item.text} className="tutorial-sheet__item">
            <strong className="tutorial-sheet__label">
              {item.action && <img src={actionTypeAssetUrl(item.action)} alt=""
                className={'tutorial-sheet__icon' + (WHITE_ACTIONS.has(item.action) ? '' : ' tutorial-sheet__icon--white')} />}
              {item.label}
            </strong>
            <span>{splitSentences(item.text)}</span>
          </li>
        ))}
      </ul>}
      {sheet.footer && (
        <ul className="tutorial-sheet__list tutorial-sheet__footer">
          {sheet.footer.map((item) => (
            <li key={item.label} className="tutorial-sheet__item">
              <strong>{item.label}</strong>
              <span>{splitSentences(item.text)}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
