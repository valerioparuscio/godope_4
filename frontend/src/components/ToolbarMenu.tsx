import { useEffect, useRef, useState, type ReactNode } from 'react';
import { ToolbarButtonContent } from './ToolbarButtonContent';

/** The secondary toolbar buttons (Log, Regolamento, Musica, Home) folded behind a
 *  single gear button: clicking it shows them in a panel below. The children
 *  stay mounted while the panel is closed (only hidden), so an open Log drawer
 *  or a toggle's own state isn't lost; clicking outside or pressing Escape
 *  closes the panel. */
export function ToolbarMenu({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (event: MouseEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false);
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', onPointerDown);
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('mousedown', onPointerDown);
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [open]);

  return (
    <div className="top-strip__buttons top-strip__buttons--menu" ref={root}>
      <button
        className="hand-drawer__toggle top-strip__button--secondary"
        aria-expanded={open}
        aria-haspopup="true"
        aria-label="Menu: log, regolamento, musica e home"
        onClick={() => setOpen((value) => !value)}
      >
        <ToolbarButtonContent icon="gear" label="Menu" />
      </button>
      <div className={'top-strip__menu' + (open ? '' : ' top-strip__menu--closed')}>{children}</div>
    </div>
  );
}
