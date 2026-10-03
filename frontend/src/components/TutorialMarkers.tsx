import { useLayoutEffect, useRef, useState } from 'react';
import type { TutorialMarker } from '../tutorial/scenarios';

/** Coordinates match the board image; the overlay never intercepts a move. */
export function TutorialMarkers({ markers }: { markers: TutorialMarker[] }) {
  const root = useRef<HTMLDivElement>(null);
  const [targets, setTargets] = useState<Record<string, { xPct: number; yPct: number }>>({});
  const spec = JSON.stringify(markers);
  useLayoutEffect(() => {
    const container = root.current?.parentElement;
    if (!container) return;
    const markers: TutorialMarker[] = JSON.parse(spec);
    const update = () => {
      const bounds = container.getBoundingClientRect();
      if (!bounds.width || !bounds.height) return;
      const next: typeof targets = {};
      for (const marker of markers) {
        if (!marker.target) continue;
        const element = container.querySelector(marker.target);
        if (!element) continue;
        const box = element.getBoundingClientRect();
        next[marker.target] = {
          xPct: (box.left + box.width / 2 - bounds.left) / bounds.width * 100,
          yPct: (box.top + box.height / 2 - bounds.top) / bounds.height * 100,
        };
      }
      setTargets(next);
    };
    update();
    const observer = new ResizeObserver(update);
    observer.observe(container);
    for (const marker of markers) {
      const element = marker.target && container.querySelector(marker.target);
      if (element) observer.observe(element);
    }
    return () => observer.disconnect();
  }, [spec]);
  if (!markers.length) return null;
  const positioned = markers.map((a) => {
    const { xPct, yPct } = a.target && targets[a.target] ? targets[a.target] : a;
    return { ...a, xPct, yPct };
  });
  return (
    <div className="tutorial-markers" ref={root} aria-hidden="true">
      {positioned.map(({ xPct, yPct, label, labelSide }, index) =>
        <span key={`${label}-${index}`}
          className={'tutorial-marker' + ((labelSide ?? (xPct > 65 ? 'left' : 'right')) === 'left' ? ' tutorial-marker--label-left' : '')}
          style={{ left: `${xPct}%`, top: `${yPct}%` }}>
          <span className="tutorial-marker__box">
            <span className="tutorial-marker__asterisk">✱</span>
            <span className="tutorial-marker__label">{label}</span>
          </span>
        </span>
      )}
    </div>
  );
}
