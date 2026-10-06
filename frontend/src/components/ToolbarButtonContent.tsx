import marketIcon from '../assets/actions/MARKET W.png';

type ToolbarIcon = 'cards' | 'skills' | 'log' | 'rules' | 'music' | 'muted' | 'stonk' | 'poker' | 'gear';

// The five Poker symbols are 5-petal flowers; the Poker button shows all five
// in the button's text colour (white; 3 above, 2 below) on a wider 64x48 box, each flower solid (petals
// overlap at the centre, no hole) with a small gap to its neighbours.
const POKER_VIEW_BOX = '2 3 60 42'; // cropped tight around the flowers
const POKER_FLOWERS: { x: number; y: number }[] = [
  { x: 12, y: 14 },
  { x: 32, y: 14 },
  { x: 52, y: 14 },
  { x: 22, y: 35 },
  { x: 42, y: 35 },
];

function Flower({ x, y }: { x: number; y: number }) {
  return (
    <g stroke="none">
      {[0, 1, 2, 3, 4].map((i) => {
        const angle = ((-90 + i * 72) * Math.PI) / 180;
        return <circle key={i} cx={x + Math.cos(angle) * 4.6} cy={y + Math.sin(angle) * 4.6} r="4.6" fill="currentColor" />;
      })}
    </g>
  );
}

export function ToolbarButtonContent({ icon, label, count }: {
  icon: ToolbarIcon;
  label: string;
  count?: number;
}) {
  return (
    <>
      {icon === 'stonk' ? (
        <img src={marketIcon} alt="" className="toolbar-icon" aria-hidden="true" />
      ) : (
      <svg className="toolbar-icon" viewBox={icon === 'poker' ? POKER_VIEW_BOX : '0 0 48 48'} fill="none" stroke="currentColor" strokeWidth="2.3" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        {icon === 'cards' && <><rect x="8" y="7" width="25" height="33" rx="4" transform="rotate(-12 20 24)" /><rect x="17" y="9" width="24" height="33" rx="4" fill="var(--toolbar-face, #f0f0f4)" /><path d="m29 18 6 8-6 8-6-8Z" fill="currentColor" stroke="none" /><path d="M22 14h2m10 23h2" /></>}
        {icon === 'skills' && <><path d="m24 4 6 7 9 1 1 10 4 7-8 6-4 9-9-3-9 2-3-9-7-6 5-8 1-9 10-1Z" /><path d="m27 12-12 15h9l-3 10 13-16h-9Z" fill="currentColor" stroke="none" /></>}
        {icon === 'gear' && <><path d="M24 4v6m0 28v6M4 24h6m28 0h6M9.9 9.9l4.2 4.2m19.8 19.8 4.2 4.2m0-28.2-4.2 4.2M14.1 33.9l-4.2 4.2" /><circle cx="24" cy="24" r="11" /><circle cx="24" cy="24" r="4.5" /></>}
        {icon === 'poker' && POKER_FLOWERS.map((f) => <Flower key={`${f.x}-${f.y}`} {...f} />)}
        {icon === 'log' && <><rect x="10" y="9" width="28" height="34" rx="4" /><rect x="18" y="5" width="12" height="8" rx="2" fill="var(--toolbar-face, #f0f0f4)" /><path d="M18 21h13m-13 7h13m-13 7h8" /></>}
        {icon === 'rules' && <><path d="M24 12c-6-5-13-5-19-3v30c7-2 13-2 19 3 6-5 12-5 19-3V9c-6-2-13-2-19 3Zm0 0v30M11 17l7 1m-7 6 7 1m12-7 7-1m-7 8 7-1" /></>}
        {(icon === 'music' || icon === 'muted') && <><path d="M7 18h9L28 8v32L16 30H7Z" />{icon === 'music' ? <><path d="M34 16c4 4 4 12 0 16m5-22c7 7 7 21 0 28" /></> : <path d="m35 19 9 10m0-10-9 10" />}</>}
      </svg>
      )}
      <span className="toolbar-label">{label}</span>
      {count !== undefined && <span className="toolbar-count">{count}</span>}
    </>
  );
}
