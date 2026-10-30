import { useLayoutEffect, useRef, useState } from 'react';
import type { TutorialSheet as TutorialSheetData } from '../tutorial/scenarios';
import { actionTypeAssetUrl } from '../assets';
import { largestFreeRect, type Box } from '../tutorial/free-rect';
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

/** Where the card sits inside the board wrapper: a free rectangle between the labels, or
 *  'full' (the whole board) when no gap is big enough; null until it has been measured. */
type Placement = Box | 'full' | null;

const sameBox = (a: Placement, b: Placement) =>
  a === b || (a !== null && b !== null && a !== 'full' && b !== 'full'
    && a.left === b.left && a.top === b.top && a.right === b.right && a.bottom === b.bottom);

/** The biggest rectangle of the board wrapper (in its own pixels) that no marker label covers. */
function measureFreeRect(wrapper: HTMLElement, onLabel: (label: Element) => void): Box | null | undefined {
  const area = wrapper.getBoundingClientRect();
  if (!area.width || !wrapper.offsetWidth) return undefined; // not laid out yet
  const scale = area.width / wrapper.offsetWidth; // 1 unless an ancestor is scaled
  const toLocal = (r: DOMRect): Box => ({
    left: (r.left - area.left) / scale,
    top: (r.top - area.top) / scale,
    right: (r.right - area.left) / scale,
    bottom: (r.bottom - area.top) / scale,
  });
  const labels = Array.from(document.querySelectorAll('.tutorial-game .tutorial-marker__box'));
  labels.forEach(onLabel);
  const obstacles = labels.map((label) => toLocal(label.getBoundingClientRect()));
  const bounds: Box = { left: 0, top: 0, right: wrapper.offsetWidth, bottom: wrapper.offsetHeight };
  return largestFreeRect(bounds, obstacles) ?? largestFreeRect(bounds, obstacles, { minWidth: 240, minHeight: 140 });
}

/** A temporary info card laid over the board (a list, a table of rewards…) —
 *  the lesson text stays in the top bar, this carries the detail. It is kept compact and
 *  placed in the largest gap between the marker labels, so it never hides them. */
export function TutorialSheet({ sheet, onClose }: TutorialSheetProps) {
  const rootRef = useRef<HTMLDivElement>(null);
  const [placement, setPlacement] = useState<Placement>(null);

  useLayoutEffect(() => {
    const wrapper = rootRef.current?.parentElement;
    if (!wrapper) return;
    let disposed = false;
    const resizeObserver = new ResizeObserver(() => update());
    function update() {
      if (disposed || !wrapper) return;
      // observe() is a no-op for labels already watched: new labels (and a late font) get picked up
      const free = measureFreeRect(wrapper, (label) => resizeObserver.observe(label));
      if (free === undefined) return;
      const next: Placement = free ?? 'full';
      setPlacement((previous) => (sameBox(previous, next) ? previous : next));
    }
    update();
    resizeObserver.observe(wrapper);
    // labels follow their targets, which settle a few frames after the scene is laid out
    const mutationObserver = new MutationObserver(update);
    document.querySelectorAll('.tutorial-game .tutorial-markers').forEach((markers) =>
      mutationObserver.observe(markers, { subtree: true, childList: true, attributes: true }));
    window.addEventListener('resize', update);
    void document.fonts?.ready.then(update);
    let frames = 0;
    let frame = requestAnimationFrame(function settle() {
      update();
      if (++frames < 4) frame = requestAnimationFrame(settle);
    });
    return () => {
      disposed = true;
      cancelAnimationFrame(frame);
      resizeObserver.disconnect();
      mutationObserver.disconnect();
      window.removeEventListener('resize', update);
    };
  }, [sheet]);

  const full = placement === 'full';
  const slotStyle = placement && !full
    ? { left: placement.left, top: placement.top, width: placement.right - placement.left, height: placement.bottom - placement.top }
    : undefined;

  return (
    <div ref={rootRef} style={slotStyle}
      className={'tutorial-sheet-slot' + (placement === null ? ' tutorial-sheet-slot--pending' : '') + (full ? ' tutorial-sheet-slot--full' : '')}>
      <section className={'tutorial-sheet' + (full ? ' tutorial-sheet--full' : '')} aria-label={sheet.title}>
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
    </div>
  );
}
