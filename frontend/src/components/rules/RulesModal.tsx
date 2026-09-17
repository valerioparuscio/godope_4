import { useEffect, useRef, useState, type KeyboardEvent, type MouseEvent } from 'react';
import { RULE_PAGE_BY_SLUG } from '../../rules/content';
import { RulesBreadcrumb } from './RulesBreadcrumb';
import { RulesHome } from './RulesHome';
import { RulesPage } from './RulesPage';

const FOCUSABLE_SELECTOR =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

// The Regolamento modal shell (game designer's spec, 2026-09-18):
// index/search + per-page navigation over frontend/src/rules/content,
// replacing the old 6-step UI-orientation Tutorial.tsx. Reuses
// .outcome-modal-overlay/.outcome-modal verbatim for the scrim+card
// (same shell Tutorial.tsx used), with its own size/layout on top.
//
// State split: App.tsx owns only {open, initialSlug} — the one thing a
// future "?" button outside this modal would need to set. Navigating
// around once open (currentSlug/historyStack) is local here, same as
// Tutorial.tsx's own stepIndex today.
export function RulesModal({
  open,
  initialSlug,
  onClose,
}: {
  open: boolean;
  initialSlug: string | null;
  onClose: () => void;
}) {
  const [currentSlug, setCurrentSlug] = useState<string | null>(initialSlug);
  const [historyStack, setHistoryStack] = useState<string[]>([]);
  const containerRef = useRef<HTMLDivElement>(null);
  const previouslyFocusedRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (open) {
      setCurrentSlug(initialSlug);
      setHistoryStack([]);
    }
    // Deliberately reacts only to `open` flipping, same as Tutorial.tsx's
    // own stepIndex-reset effect — initialSlug only matters at the exact
    // moment the modal opens, not on every re-render while it's open.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  // Accessibility (spec §23): focus the dialog on open, return focus to
  // whatever opened it on close. Neither OutcomeModal nor Tutorial.tsx
  // implement this today — written fresh here.
  useEffect(() => {
    if (!open) return;
    previouslyFocusedRef.current = document.activeElement as HTMLElement | null;
    containerRef.current?.focus();
    return () => {
      previouslyFocusedRef.current?.focus?.();
    };
  }, [open]);

  // Every navigation reclaims focus onto the dialog container. Without
  // this, a click that also unmounts its own button (e.g. "Indietro"
  // disappearing once historyStack empties) drops browser focus to
  // <body> — outside the dialog's own subtree — which silently breaks
  // both the Tab trap and Escape-to-close from then on, since keydown
  // only bubbles up a focused element's own ancestor chain.
  function refocusContainer() {
    requestAnimationFrame(() => containerRef.current?.focus());
  }

  function navigate(slug: string) {
    setHistoryStack((stack) => (currentSlug ? [...stack, currentSlug] : stack));
    setCurrentSlug(slug);
    refocusContainer();
  }

  function goHome() {
    setHistoryStack([]);
    setCurrentSlug(null);
    refocusContainer();
  }

  function goBack() {
    if (historyStack.length === 0) {
      setCurrentSlug(null);
    } else {
      const previousSlug = historyStack[historyStack.length - 1];
      setHistoryStack((stack) => stack.slice(0, -1));
      setCurrentSlug(previousSlug);
    }
    refocusContainer();
  }

  function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === 'Escape') {
      event.stopPropagation();
      onClose();
      return;
    }
    if (event.key !== 'Tab') return;
    const container = containerRef.current;
    if (!container) return;
    const focusable = Array.from(container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR));
    if (focusable.length === 0) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  function handleOverlayClick(event: MouseEvent<HTMLDivElement>) {
    if (event.target === event.currentTarget) onClose();
  }

  if (!open) return null;

  // Falls back to the home index if `currentSlug` doesn't resolve to a
  // real page (a not-yet-backfilled slug reached some other way) instead
  // of rendering a blank body.
  const page = currentSlug ? (RULE_PAGE_BY_SLUG[currentSlug] ?? null) : null;

  return (
    <div className="outcome-modal-overlay rules-modal-overlay" onClick={handleOverlayClick}>
      <div
        className="outcome-modal rules-modal"
        role="dialog"
        aria-modal="true"
        aria-label="Regolamento"
        tabIndex={-1}
        ref={containerRef}
        onKeyDown={handleKeyDown}
      >
        <div className="rules-modal__header">
          <RulesBreadcrumb currentSlug={page?.slug ?? null} onNavigateHome={goHome} />
          <button type="button" className="rules-modal__close" onClick={onClose} aria-label="Chiudi">
            ×
          </button>
        </div>
        <div className="rules-modal__body">
          {page ? <RulesPage page={page} onNavigate={navigate} /> : <RulesHome onNavigate={navigate} />}
        </div>
        {historyStack.length > 0 && (
          <div className="rules-modal__footer">
            <button type="button" className="rules-modal__back" onClick={goBack}>
              ← Indietro
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
