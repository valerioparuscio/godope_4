import { useLayoutEffect, useRef } from 'react';
import { splitSentences } from '../tutorial/text';

/** Fill the space left by the heading and controls without shrinking the buttons. */
export function TutorialMessage({ text, interactive }: { text: string; interactive: boolean }) {
  const container = useRef<HTMLParagraphElement>(null);
  const content = useRef<HTMLSpanElement>(null);
  const lines = splitSentences(text);

  useLayoutEffect(() => {
    const box = container.current;
    const message = content.current;
    if (!box || !message) return;
    const fits = (size: number) => {
      message.style.fontSize = `${size}px`;
      return message.getBoundingClientRect().height <= box.clientHeight && message.scrollWidth <= box.clientWidth;
    };
    const largest = (whiteSpace: 'normal' | 'pre-line') => {
      message.style.whiteSpace = whiteSpace;
      let lower = 24;
      let upper = interactive ? 42 : 56;
      let best = lower;
      while (upper - lower >= 0.5) {
        const size = (lower + upper) / 2;
        if (fits(size)) {
          best = size;
          lower = size;
        } else {
          upper = size;
        }
      }
      return best;
    };
    const fit = () => {
      if (!box.clientWidth || !box.clientHeight) return;
      const flat = largest('normal');
      // One sentence per line only when there is room: it may cost at most
      // ~8% of the text size, never a visibly smaller font.
      const broken = largest('pre-line');
      const useBreaks = lines.includes('\n') && broken >= flat * 0.92;
      const best = useBreaks ? broken : flat;
      message.style.whiteSpace = useBreaks ? 'pre-line' : 'normal';
      message.style.fontSize = `${Math.floor(best * 2) / 2}px`;
    };
    fit();
    const observer = new ResizeObserver(fit);
    observer.observe(box);
    return () => observer.disconnect();
  }, [text, interactive, lines]);

  return <p className="tutorial-game__instruction" ref={container} aria-live="polite">
    <span ref={content}>{lines}</span>
  </p>;
}
