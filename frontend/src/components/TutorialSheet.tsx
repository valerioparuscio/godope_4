import type { TutorialSheet as TutorialSheetData } from '../tutorial/scenarios';

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
      <ul className={'tutorial-sheet__list' + (sheet.items.length > 6 ? ' tutorial-sheet__list--columns' : '')}>
        {sheet.items.map((item) => (
          <li key={item.label + item.text} className="tutorial-sheet__item">
            <strong>{item.label}</strong>
            <span>{item.text}</span>
          </li>
        ))}
      </ul>
      {sheet.footer && (
        <ul className="tutorial-sheet__list tutorial-sheet__footer">
          {sheet.footer.map((item) => (
            <li key={item.label} className="tutorial-sheet__item">
              <strong>{item.label}</strong>
              <span>{item.text}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
