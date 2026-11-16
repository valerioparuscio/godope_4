import { useEffect } from 'react';
import type { Notice } from '../notices';

const NOTICE_DURATION_MS = 4500;

// Why a step of a played card was skipped (`noticesFromEvents`, notices.ts): one message at a
// time, top centre, readable for a few seconds; a click closes it earlier.
export function NoticePopup({
  queue,
  onShown,
}: {
  queue: Notice[];
  onShown: (key: string) => void;
}) {
  const current = queue[0];

  useEffect(() => {
    if (!current) return;
    const timer = setTimeout(() => onShown(current.key), NOTICE_DURATION_MS);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [current?.key]);

  if (!current) return null;
  return (
    <div
      className="notice-popup"
      key={current.key}
      role="status"
      onClick={() => onShown(current.key)}
    >
      {current.text}
    </div>
  );
}
