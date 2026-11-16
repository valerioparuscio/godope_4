import { useLayoutEffect, useRef } from 'react';

// The words that name what is counted (LINK, RAT, POKER, COPS/FEDS, CASH,
// CRIMINALI) and the "+"/"-" are the point of a Raid requirement: shown in accent.
function highlightKeywords(text: string, keyClassName: string) {
  return text.split(/([A-Z][A-Z/]+|\+|-)/).map((part, i) =>
    i % 2 === 1 ? <span key={i} className={keyClassName}>{part}</span> : part,
  );
}

const FIT_REFERENCE_PX = 100;
const FIT_MAX_PX = 80;

// Sizes the text so it fills the whole width of its box: each Raid's word has a different
// length, and the point is that it reads big. Re-fits when the box is resized or the font loads.
// Shared by the Raid box (RaidBanner) and the Raid announcement popup (OutcomeModal); each
// passes its own class names, and a layout that is short on height (a phone) or wants a
// different ceiling can set `--fit-max-px` on the box.
export function FitText({
  text,
  boxClassName,
  textClassName,
  keyClassName,
}: {
  text: string;
  boxClassName: string;
  textClassName: string;
  keyClassName: string;
}) {
  const boxRef = useRef<HTMLDivElement>(null);
  const textRef = useRef<HTMLSpanElement>(null);
  useLayoutEffect(() => {
    const box = boxRef.current;
    const label = textRef.current;
    if (!box || !label) return undefined;
    const fit = () => {
      const width = box.clientWidth;
      if (width <= 0) return;
      label.style.fontSize = `${FIT_REFERENCE_PX}px`;
      const natural = label.offsetWidth;
      if (natural <= 0) return;
      const size = Math.floor(((FIT_REFERENCE_PX * width) / natural) * 0.99 * 10) / 10;
      const cssMax = parseFloat(getComputedStyle(box).getPropertyValue('--fit-max-px'));
      label.style.fontSize = `${Math.min(cssMax > 0 ? cssMax : FIT_MAX_PX, size)}px`;
    };
    fit();
    const observer = new ResizeObserver(fit);
    observer.observe(box);
    // The word's width depends on the font: fit again once Terror Babble is there.
    if (document.fonts) {
      void document.fonts.load("100px 'Terror Babble'").then(fit);
      void document.fonts.ready.then(fit);
    }
    return () => observer.disconnect();
  }, [text]);
  return (
    <div ref={boxRef} className={boxClassName}>
      <span ref={textRef} className={textClassName}>{highlightKeywords(text, keyClassName)}</span>
    </div>
  );
}
