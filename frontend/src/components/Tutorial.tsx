import { useEffect, useState } from 'react';

interface TutorialStep {
  title: string;
  body: string;
}

const TUTORIAL_STEPS: TutorialStep[] = [
  {
    title: 'Benvenuto in DOPE',
    body: 'Gestisci Criminali, Merce e Contatti per accumulare Reputazione e vincere. Ogni round hai fino a 3 azioni Grinta da spendere.',
  },
  {
    title: 'Il tabellone',
    body: 'I Quartieri (i fiori colorati) mostrano Merce, Cops e le tue pedine. Den, Jail e il tuo Covo hanno le loro icone dedicate; in alto a destra trovi il tracciato dei turni.',
  },
  {
    title: 'Le tue carte',
    body: 'Il bottone "Carte" in basso a sinistra mostra la tua mano — per alcune decisioni basta cliccare direttamente una carta per rispondere.',
  },
  {
    title: 'Il pannello decisioni',
    body: 'Quando tocca a te, qui a sinistra vedi cosa puoi fare. Le opzioni evidenziate sul tabellone si scelgono cliccandole direttamente.',
  },
  {
    title: 'Il registro azioni',
    body: 'Il bottone "Log" mostra lo storico di tutte le mosse della partita, tue e degli avversari.',
  },
  {
    title: 'Le tue Skill',
    body: 'Se hai Skill attive, il bottone "Skills" te le mostra — si attivano da sole quando le condizioni sono soddisfatte, nessun click necessario.',
  },
];

interface TutorialProps {
  open: boolean;
  onClose: () => void;
}

// Reuses OutcomeModal's exact visual convention (scrim + purple-bordered
// card, same entrance animation) but with its own Avanti/Salta navigation
// instead of OutcomeModal's queue-and-dismiss. Shown once automatically
// (App.tsx gates `open` on a localStorage flag) and reopenable anytime via
// a sidebar button.
export function Tutorial({ open, onClose }: TutorialProps) {
  const [stepIndex, setStepIndex] = useState(0);

  useEffect(() => {
    if (open) setStepIndex(0);
  }, [open]);

  if (!open) return null;

  const step = TUTORIAL_STEPS[stepIndex];
  const isLast = stepIndex === TUTORIAL_STEPS.length - 1;

  function handleNext() {
    if (isLast) {
      onClose();
      return;
    }
    setStepIndex((i) => i + 1);
  }

  return (
    <div className="outcome-modal-overlay">
      <div className="outcome-modal tutorial-modal">
        <h3>{step.title}</h3>
        <p className="tutorial-modal__body">{step.body}</p>
        <div className="tutorial-modal__footer">
          <span className="tutorial-modal__progress">
            {stepIndex + 1} / {TUTORIAL_STEPS.length}
          </span>
          <div className="tutorial-modal__buttons">
            <button className="tutorial-modal__skip" onClick={onClose}>
              Salta
            </button>
            <button className="outcome-modal__ok tutorial-modal__next" onClick={handleNext}>
              {isLast ? 'Fine' : 'Avanti'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
