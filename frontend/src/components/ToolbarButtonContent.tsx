type ToolbarIcon = 'cards' | 'skills' | 'log' | 'rules' | 'music' | 'muted';

export function ToolbarButtonContent({ icon, label, count }: {
  icon: ToolbarIcon;
  label: string;
  count?: number;
}) {
  return (
    <>
      <svg className="toolbar-icon" viewBox="0 0 48 48" fill="none" stroke="currentColor" strokeWidth="2.3" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        {icon === 'cards' && <><rect x="8" y="7" width="25" height="33" rx="4" transform="rotate(-12 20 24)" /><rect x="17" y="9" width="24" height="33" rx="4" fill="var(--toolbar-face, #f0f0f4)" /><path d="m29 18 6 8-6 8-6-8Z" fill="currentColor" stroke="none" /><path d="M22 14h2m10 23h2" /></>}
        {icon === 'skills' && <><path d="m24 4 6 7 9 1 1 10 4 7-8 6-4 9-9-3-9 2-3-9-7-6 5-8 1-9 10-1Z" /><path d="m27 12-12 15h9l-3 10 13-16h-9Z" fill="currentColor" stroke="none" /></>}
        {icon === 'log' && <><rect x="10" y="9" width="28" height="34" rx="4" /><rect x="18" y="5" width="12" height="8" rx="2" fill="var(--toolbar-face, #f0f0f4)" /><path d="M18 21h13m-13 7h13m-13 7h8" /></>}
        {icon === 'rules' && <><path d="M24 12c-6-5-13-5-19-3v30c7-2 13-2 19 3 6-5 12-5 19-3V9c-6-2-13-2-19 3Zm0 0v30M11 17l7 1m-7 6 7 1m12-7 7-1m-7 8 7-1" /></>}
        {(icon === 'music' || icon === 'muted') && <><path d="M7 18h9L28 8v32L16 30H7Z" />{icon === 'music' ? <><path d="M34 16c4 4 4 12 0 16m5-22c7 7 7 21 0 28" /></> : <path d="m35 19 9 10m0-10-9 10" />}</>}
      </svg>
      <span className="toolbar-label">{label}</span>
      {count !== undefined && <span className="toolbar-count">{count}</span>}
    </>
  );
}
