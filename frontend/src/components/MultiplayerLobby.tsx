import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import {
  criminalAssetsForPlayer,
  playerColorForId,
  playerTeamNameForId,
  startBackgroundUrl,
} from '../assets';
import {
  MultiplayerApiError,
  createRoom,
  getRoom,
  isTransientFailure,
  joinRoom,
  leaveRoom,
  startRoom,
} from '../multiplayer/api';
import {
  ROOM_CODE_LENGTH,
  cleanRoomCode,
  dropRoomParamFromUrl,
  shareLink,
} from '../multiplayer/link';
import { multiplayerErrorMessage } from '../multiplayer/messages';
import {
  clearSeat,
  loadNickname,
  loadSeat,
  saveNickname,
  saveSeat,
} from '../multiplayer/storage';
import type { CredentialsResponse, RoomResponse, SeatResponse, StoredSeat } from '../multiplayer/types';
import { useRoom } from '../multiplayer/useRoom';
import './MultiplayerLobby.css';

interface MultiplayerLobbyProps {
  /** The nickname typed on the start screen, if any. */
  initialNickname: string;
  /** A room code that came in a shared link (`?stanza=F7KQ`). */
  initialRoomCode: string | null;
  /** Opened by the app on its own (a reload) rather than by the player: if there is no seat to
   *  get back to after all, go straight back to the start screen instead of showing the menu. */
  resumeOnly: boolean;
  onBack: () => void;
  /** The room's game has started: hand the seat over to the game screen. `fresh` says whether this
   *  browser was here for the run-up (so the game's opening is news), not coming back to a game
   *  already under way after a reload. */
  onGameStart: (seat: StoredSeat, fresh: boolean) => void;
}

type Step = 'checking' | 'menu' | 'create' | 'join' | 'room';

const HUMAN_SEAT_CHOICES = [2, 3, 4];

function storedSeatFrom(credentials: CredentialsResponse, nickname: string): StoredSeat {
  return {
    room_code: credentials.room_code,
    game_id: credentials.game_id,
    seat_token: credentials.seat_token,
    seat_index: credentials.seat_index,
    player_id: credentials.player_id,
    nickname,
  };
}

export function MultiplayerLobby({
  initialNickname,
  initialRoomCode,
  resumeOnly,
  onBack,
  onGameStart,
}: MultiplayerLobbyProps) {
  const background = startBackgroundUrl();
  const [step, setStep] = useState<Step>('checking');
  const [nickname, setNickname] = useState(() => initialNickname || loadNickname());
  const [humanSeats, setHumanSeats] = useState(2);
  const [codeInput, setCodeInput] = useState(() => cleanRoomCode(initialRoomCode ?? ''));
  const [seat, setSeat] = useState<StoredSeat | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [copied, setCopied] = useState<'code' | 'link' | null>(null);
  const copiedTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const sawLobby = useRef(false);
  const handedOver = useRef(false);

  const watch = useRoom(step === 'room' ? seat : null);
  const room = watch.room;

  // First thing: does this browser still hold a seat? Then go straight back to it.
  useEffect(() => {
    let cancelled = false;
    const entryStep: Step = initialRoomCode ? 'join' : 'menu';
    const stored = loadSeat();
    const giveUp = () => {
      clearSeat();
      if (resumeOnly) onBack();
      else setStep(entryStep);
    };
    if (!stored) {
      giveUp();
      return () => undefined;
    }
    getRoom(stored.room_code, stored.seat_token)
      .then((current) => {
        if (cancelled) return;
        if (current.me !== null && (current.status === 'lobby' || current.status === 'running')) {
          setSeat(stored);
          setStep('room');
          if (initialRoomCode && cleanRoomCode(initialRoomCode) !== stored.room_code) {
            setNotice(
              `Hai già un posto nella stanza ${stored.room_code}: esci da quella prima di entrare in un'altra.`,
            );
          }
        } else {
          giveUp();
        }
      })
      .catch((failure: unknown) => {
        if (cancelled) return;
        if (failure instanceof MultiplayerApiError && !isTransientFailure(failure)) {
          giveUp(); // the room is gone, or the token isn't valid any more
        } else {
          // The server can't be reached (or is restarting): keep the seat and let the room screen
          // keep trying.
          setSeat(stored);
          setStep('room');
        }
      });
    return () => {
      cancelled = true;
    };
    // Only on first show.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // The seat disappeared under us (the host closed the room, the server restarted...).
  useEffect(() => {
    if (!watch.seatLost) return;
    clearSeat();
    setSeat(null);
    setStep('menu');
    setNotice('La stanza non esiste più o hai perso il tuo posto.');
  }, [watch.seatLost]);

  // Once the game starts, keep its id (the game screen needs it to come back to the seat after a
  // reload) and hand the seat over to the game screen.
  useEffect(() => {
    if (!room) return;
    if (room.status === 'lobby') sawLobby.current = true;
    if (!seat || !room.game_id || room.status !== 'running' || handedOver.current) return;
    handedOver.current = true;
    const started = { ...seat, game_id: room.game_id };
    saveSeat(started);
    onGameStart(started, sawLobby.current);
  }, [room, seat, onGameStart]);

  useEffect(
    () => () => {
      if (copiedTimer.current) clearTimeout(copiedTimer.current);
    },
    [],
  );

  const portraits = useMemo(
    () =>
      [0, 1, 2, 3].map((seatIndex) => {
        const faces = criminalAssetsForPlayer(`player_${seatIndex}`);
        return faces.length ? faces[Math.floor(Math.random() * faces.length)] : null;
      }),
    [],
  );

  function enterRoom(credentials: CredentialsResponse, name: string) {
    const stored = storedSeatFrom(credentials, name);
    saveNickname(name);
    saveSeat(stored);
    dropRoomParamFromUrl();
    sawLobby.current = true;
    setSeat(stored);
    setNotice(null);
    setStep('room');
  }

  async function handleCreate() {
    const name = nickname.trim();
    if (!name || busy) return;
    setBusy(true);
    setError(null);
    try {
      enterRoom(await createRoom(name, humanSeats), name);
    } catch (failure) {
      setError(multiplayerErrorMessage(failure));
    } finally {
      setBusy(false);
    }
  }

  async function handleJoin() {
    const name = nickname.trim();
    const code = cleanRoomCode(codeInput);
    if (!name || code.length !== ROOM_CODE_LENGTH || busy) return;
    setBusy(true);
    setError(null);
    try {
      enterRoom(await joinRoom(code, name), name);
    } catch (failure) {
      setError(multiplayerErrorMessage(failure));
    } finally {
      setBusy(false);
    }
  }

  async function handleStart() {
    if (!seat || busy) return;
    setBusy(true);
    setError(null);
    try {
      const started = await startRoom(seat.room_code, seat.seat_token);
      watch.setRoom({ ...started, me: started.seats[seat.seat_index] ?? null });
    } catch (failure) {
      setError(multiplayerErrorMessage(failure));
    } finally {
      setBusy(false);
    }
  }

  async function handleLeave() {
    if (!seat || busy) return;
    if (
      room?.status === 'running' &&
      !window.confirm('Uscire dalla partita? Il tuo posto passerà a un bot.')
    ) {
      return;
    }
    setBusy(true);
    try {
      await leaveRoom(seat.room_code, seat.seat_token);
    } catch {
      // The seat may already be gone: leaving is the goal anyway.
    }
    clearSeat();
    setSeat(null);
    setError(null);
    setNotice(null);
    setStep('menu');
    setBusy(false);
  }

  async function copy(what: 'code' | 'link') {
    if (!seat) return;
    const text = what === 'code' ? seat.room_code : shareLink(seat.room_code);
    try {
      await navigator.clipboard.writeText(text);
      setCopied(what);
      if (copiedTimer.current) clearTimeout(copiedTimer.current);
      copiedTimer.current = setTimeout(() => setCopied(null), 1800);
    } catch {
      // No clipboard access: the code and the link are on screen to read out loud.
    }
  }

  function goBackToStart() {
    dropRoomParamFromUrl();
    onBack();
  }

  const nicknameField = (
    <input
      className="mp-input"
      type="text"
      aria-label="Il tuo nickname"
      placeholder="Il tuo nickname"
      value={nickname}
      maxLength={24}
      disabled={busy}
      onChange={(event) => setNickname(event.target.value)}
    />
  );
  const hasNickname = nickname.trim().length > 0;

  let body: ReactNode;

  if (step === 'checking') {
    body = <p className="mp-note">Controllo la tua stanza…</p>;
  } else if (step === 'menu') {
    body = (
      <>
        <h2 className="mp-title">Multiplayer</h2>
        {nicknameField}
        <button
          className="mp-button mp-button--primary"
          type="button"
          disabled={!hasNickname}
          onClick={() => {
            setError(null);
            setStep('create');
          }}
        >
          Crea stanza
        </button>
        <button
          className="mp-button mp-button--primary"
          type="button"
          disabled={!hasNickname}
          onClick={() => {
            setError(null);
            setStep('join');
          }}
        >
          Entra in una stanza
        </button>
        <button className="mp-button" type="button" onClick={goBackToStart}>
          Indietro
        </button>
      </>
    );
  } else if (step === 'create') {
    body = (
      <>
        <h2 className="mp-title">Crea stanza</h2>
        <p className="mp-note">Modalità Easy Price.</p>
        <div className="mp-choices" role="radiogroup" aria-label="Giocatori umani">
          {HUMAN_SEAT_CHOICES.map((count) => (
            <button
              key={count}
              type="button"
              role="radio"
              aria-checked={humanSeats === count}
              className={'mp-choice' + (humanSeats === count ? ' mp-choice--selected' : '')}
              disabled={busy}
              onClick={() => setHumanSeats(count)}
            >
              <span className="mp-choice__count">{count}</span>
              <span className="mp-choice__label">giocatori</span>
            </button>
          ))}
        </div>
        <p className="mp-note">
          {humanSeats === 4
            ? 'Quattro umani, nessun bot.'
            : humanSeats === 3
              ? 'Il posto rimasto lo gioca un bot.'
              : 'I 2 posti rimasti li giocano i bot.'}
        </p>
        <button
          className="mp-button mp-button--primary"
          type="button"
          disabled={!hasNickname || busy}
          onClick={handleCreate}
        >
          {busy ? 'Creazione…' : 'Crea stanza'}
        </button>
        <button className="mp-button" type="button" disabled={busy} onClick={() => setStep('menu')}>
          Indietro
        </button>
      </>
    );
  } else if (step === 'join') {
    body = (
      <>
        <h2 className="mp-title">Entra in una stanza</h2>
        {nicknameField}
        <input
          className="mp-input mp-input--code"
          type="text"
          aria-label="Codice stanza"
          placeholder="CODICE"
          value={codeInput}
          maxLength={ROOM_CODE_LENGTH}
          autoCapitalize="characters"
          autoCorrect="off"
          spellCheck={false}
          disabled={busy}
          onChange={(event) => setCodeInput(cleanRoomCode(event.target.value))}
          onKeyDown={(event) => {
            if (event.key === 'Enter') void handleJoin();
          }}
        />
        <button
          className="mp-button mp-button--primary"
          type="button"
          disabled={!hasNickname || codeInput.length !== ROOM_CODE_LENGTH || busy}
          onClick={handleJoin}
        >
          {busy ? 'Ingresso…' : 'Entra'}
        </button>
        <button className="mp-button" type="button" disabled={busy} onClick={() => setStep('menu')}>
          Indietro
        </button>
      </>
    );
  } else if (seat) {
    body = (
      <RoomPanel
        seat={seat}
        room={room}
        portraits={portraits}
        busy={busy}
        connectionLost={watch.connectionLost}
        copied={copied}
        onCopy={copy}
        onStart={handleStart}
        onLeave={handleLeave}
      />
    );
  }

  return (
    <div
      className="setup-screen"
      style={background ? { backgroundImage: `url(${background})` } : undefined}
    >
      <div className="mp-panel">
        {body}
        {notice && (
          <p className="mp-notice" role="status">
            {notice}
          </p>
        )}
        {error && (
          <p className="mp-error" role="alert">
            {error}
          </p>
        )}
      </div>
    </div>
  );
}

interface RoomPanelProps {
  seat: StoredSeat;
  room: RoomResponse | null;
  portraits: (string | null)[];
  busy: boolean;
  connectionLost: boolean;
  copied: 'code' | 'link' | null;
  onCopy: (what: 'code' | 'link') => void;
  onStart: () => void;
  onLeave: () => void;
}

function seatLabel(seat: SeatResponse): { name: string; waiting: boolean } {
  if (seat.controller_type === 'bot') return { name: seat.nickname ?? 'Bot', waiting: false };
  if (!seat.occupied) return { name: 'In attesa…', waiting: true };
  return { name: seat.nickname ?? '—', waiting: false };
}

function RoomPanel({
  seat,
  room,
  portraits,
  busy,
  connectionLost,
  copied,
  onCopy,
  onStart,
  onLeave,
}: RoomPanelProps) {
  const seats = room?.seats ?? [];
  const missing = seats.filter((s) => s.controller_type === 'human' && !s.occupied).length;
  const me = seats[seat.seat_index] ?? null;
  const isHost = me?.is_host ?? seat.seat_index === 0;
  const hostName = seats.find((s) => s.is_host)?.nickname ?? "l'host";
  const started = room?.status === 'running';

  return (
    <>
      <h2 className="mp-title">Stanza {seat.room_code}</h2>
      {!started && (
        <>
          <p className="mp-note">Dì agli altri di entrare con questo codice o con il link.</p>
          <div className="mp-share">
            <button className="mp-button mp-button--small" type="button" onClick={() => onCopy('code')}>
              {copied === 'code' ? 'Copiato!' : 'Copia codice'}
            </button>
            <button className="mp-button mp-button--small" type="button" onClick={() => onCopy('link')}>
              {copied === 'link' ? 'Copiato!' : 'Copia link'}
            </button>
          </div>
        </>
      )}
      <ul className="mp-seats" aria-label="Posti">
        {[0, 1, 2, 3].map((index) => {
          const info = seats[index];
          const playerId = `player_${index}`;
          const label = info ? seatLabel(info) : { name: '…', waiting: true };
          const isMe = index === seat.seat_index;
          return (
            <li
              key={index}
              className={
                `mp-seat player-card--${playerColorForId(playerId)}` +
                (label.waiting ? ' mp-seat--waiting' : '') +
                (isMe ? ' mp-seat--me' : '')
              }
            >
              {portraits[index] && <img className="mp-seat__face" src={portraits[index]} alt="" />}
              <span className="mp-seat__gang">{playerTeamNameForId(playerId)}</span>
              <span className="mp-seat__name">{label.name}</span>
              <span className="mp-seat__tags">
                {info?.controller_type === 'bot' && <span className="mp-tag">BOT</span>}
                {info?.is_host && <span className="mp-tag">HOST</span>}
                {isMe && <span className="mp-tag">TU</span>}
              </span>
            </li>
          );
        })}
      </ul>
      {connectionLost && (
        <p className="mp-notice" role="status">
          Connessione persa: riprovo…
        </p>
      )}
      {started ? (
        <>
          <p className="mp-note mp-note--big">La partita sta partendo…</p>
        </>
      ) : isHost ? (
        <button
          className="mp-button mp-button--primary"
          type="button"
          disabled={!room || missing > 0 || busy}
          onClick={onStart}
        >
          {busy
            ? 'Avvio…'
            : missing > 0
              ? `In attesa di ${missing} ${missing === 1 ? 'giocatore' : 'giocatori'}…`
              : 'Avvia partita'}
        </button>
      ) : (
        <p className="mp-note mp-note--big" aria-live="polite">
          {room ? `Aspetta che ${hostName} avvii la partita…` : 'Mi collego alla stanza…'}
        </p>
      )}
      <button className="mp-button" type="button" disabled={busy} onClick={onLeave}>
        Esci dalla stanza
      </button>
    </>
  );
}
