import type { GameViewResponse } from '../types';

interface BoardSummaryProps {
  view: GameViewResponse;
}

export function BoardSummary({ view }: BoardSummaryProps) {
  return (
    <div className="board-summary">
      <section>
        <h3>Mercato (prezzo corrente)</h3>
        <table>
          <thead>
            <tr>
              <th>Dope</th>
              <th>Prezzo</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(view.current_price_by_dope_type).map(([dopeType, price]) => (
              <tr key={dopeType}>
                <td>{dopeType}</td>
                <td>${price}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section>
        <h3>Hoods</h3>
        <table>
          <thead>
            <tr>
              <th>Hood</th>
              <th>Contact</th>
              <th>Dope</th>
              <th>Criminals</th>
              <th>Cops</th>
            </tr>
          </thead>
          <tbody>
            {view.hoods
              .filter((h) => h.revealed)
              .map((h) => (
                <tr key={h.hood_id}>
                  <td>{h.hood_id}</td>
                  <td>{h.contact_id}</td>
                  <td>{h.dope_stack.join(', ') || '-'}</td>
                  <td>{h.criminal_pawn_ids.length}</td>
                  <td>{h.cop_ids.length}</td>
                </tr>
              ))}
          </tbody>
        </table>
      </section>

      <section>
        <h3>Spots</h3>
        <table>
          <thead>
            <tr>
              <th>Spot</th>
              <th>Contact</th>
              <th>Accetta</th>
              <th>Venduto</th>
              <th>Feds</th>
            </tr>
          </thead>
          <tbody>
            {view.spots.map((s) => (
              <tr key={s.spot_id}>
                <td>{s.spot_id}</td>
                <td>{s.contact_id}</td>
                <td>{s.accepted_dope_type}</td>
                <td>
                  {s.sold_dope_tokens.length}/{s.capacity}
                </td>
                <td>{s.fed_ids.length}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section>
        <h3>Jail</h3>
        <div className="jail-slots">
          {view.jail_slots.map((slot) => (
            <div key={slot.index} className="jail-slot">
              <div>#{slot.index}</div>
              <div>{slot.rat_pawn_id ?? '-'}</div>
              <div>{slot.confiscated_dope_type ?? ''}</div>
            </div>
          ))}
        </div>
      </section>

      <section>
        <h3>Job board</h3>
        <table>
          <thead>
            <tr>
              <th>Job</th>
              <th>Colonna</th>
              <th>Giocatore</th>
              <th>Macchiato</th>
            </tr>
          </thead>
          <tbody>
            {view.job_board.map((cell) => (
              <tr key={`${cell.job_id}-${cell.column_index}`}>
                <td>{cell.job_id}</td>
                <td>{cell.column_index}</td>
                <td>{cell.player_id ?? '-'}</td>
                <td>{cell.stained ? 'sì' : 'no'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section>
        <h3>Retata</h3>
        <p>
          Carta corrente: {view.raid_card_id ?? '-'} — occorrenze perse:{' '}
          {view.raid_lost_occurrences_count}
        </p>
      </section>
    </div>
  );
}
