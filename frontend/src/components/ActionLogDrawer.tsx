import { useEffect, useRef, useState } from 'react';

export interface LogEntry {
  id: string;
  text: string;
}

interface ActionLogDrawerProps {
  entries: LogEntry[];
}

// Same toggle-button + floating-panel drawer pattern as HandDrawer.tsx/
// SkillsDrawer.tsx, stacked above both (designer's request: an action log
// covering every player's moves, not just the ephemeral one-beat-at-a-time
// TurnPlayback popups). Newest entry at the bottom with auto-scroll, like
// a chat log — App.tsx appends to `entries` as moves resolve, this
// component never mutates it.
export function ActionLogDrawer({ entries }: ActionLogDrawerProps) {
  const [open, setOpen] = useState(false);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight });
  }, [open, entries.length]);

  return (
    <div className="action-log-drawer">
      {open && (
        <div className="action-log-drawer__panel">
          {entries.length === 0 ? (
            <p>Nessuna azione ancora.</p>
          ) : (
            <div className="action-log-drawer__list" ref={listRef}>
              {entries.map((entry) => (
                <p key={entry.id} className="action-log-drawer__entry">
                  {entry.text}
                </p>
              ))}
            </div>
          )}
        </div>
      )}
      <button className="hand-drawer__toggle" onClick={() => setOpen((v) => !v)}>
        Log ({entries.length}) {open ? '▾' : '▴'}
      </button>
    </div>
  );
}
