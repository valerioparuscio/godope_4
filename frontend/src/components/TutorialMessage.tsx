import { useLayoutEffect, useRef } from 'react';

/** Fill the space left by the heading and controls without shrinking the buttons. */
export function TutorialMessage({ text, interactive }: { text: string; interactive: boolean }) {
  const container = useRef<HTMLParagraphElement>(null);
  const content = useRef<HTMLSpanElement>(null);

  useLayoutEffect(() => {
    const box = container.current;
    const message = content.current;
    if (!box || !message) return;
    const fit = () => {
      if (!box.clientWidth || !box.clientHeight) return;
      let lower = 24;
      let upper = interactive ? 42 : 56;
      let best = lower;
      while (upper - lower >= 0.5) {
        const size = (lower + upper) / 2;
        message.style.fontSize = `${size}px`;
        if (message.getBoundingClientRect().height <= box.clientHeight && message.scrollWidth <= box.clientWidth) {
          best = size;
          lower = size;
        } else {
          upper = size;
        }
      }
      message.style.fontSize = `${Math.floor(best * 2) / 2}px`;
    };
    fit();
    const observer = new ResizeObserver(fit);
    observer.observe(box);
    return () => observer.disconnect();
  }, [text, interactive]);

  return <p className="tutorial-game__instruction" ref={container} aria-live="polite">
    <span ref={content}>{text}</span>
  </p>;
}
