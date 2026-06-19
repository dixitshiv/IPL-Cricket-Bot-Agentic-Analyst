import { Filters, FilterState } from "../api";
import { useFilters, FLABEL, DEFAULTS } from "../state/FiltersContext";

export default function FilterDeck({ filters }: { filters: Filters | null }) {
  const { state, setFilter, reset, clearFilter } = useFilters();
  const seasons = filters?.seasons ?? [];
  const teams = filters?.teams ?? ["All"];
  const venues = filters?.venues ?? ["All"];

  const sel = (key: keyof FilterState) => ({
    value: String(state[key]),
    onChange: (e: React.ChangeEvent<HTMLSelectElement>) => setFilter(key, e.target.value),
  });

  // active chips
  const chips: { k: keyof FilterState; label: string; disp: string }[] = [];
  for (const [k, label] of Object.entries(FLABEL)) {
    const v = state[k as keyof FilterState];
    if (v !== "All")
      chips.push({ k: k as keyof FilterState, label, disp: k === "innings" ? (v === "1" ? "1st" : "2nd") : String(v) });
  }

  return (
    <section className="deck">
      <div className="deck-h">
        <span className="lbl">Filters</span>
        <button className="reset" type="button" onClick={reset}>⟲ Reset all</button>
      </div>
      <div className="deck-grid">
        <label className="field"><span>Season</span>
          <select {...sel("season")}>
            <option value="All">All seasons</option>
            {seasons.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </label>
        <label className="field"><span>Team</span>
          <select {...sel("team")}>
            {teams.map((t) => <option key={t} value={t}>{t === "All" ? "All Teams" : t}</option>)}
          </select>
        </label>
        <label className="field"><span>Opponent</span>
          <select {...sel("opponent")}>
            {teams.map((t) => <option key={t} value={t}>{t === "All" ? "Any Opponent" : t}</option>)}
          </select>
        </label>
        <label className="field"><span>Venue</span>
          <select {...sel("venue")}>
            {venues.map((v) => <option key={v} value={v}>{v === "All" ? "All Venues" : v}</option>)}
          </select>
        </label>
        <label className="field"><span>Innings</span>
          <select {...sel("innings")}>
            <option value="All">All</option><option value="1">1st innings</option><option value="2">2nd innings</option>
          </select>
        </label>
        <label className="field"><span>Phase</span>
          <select {...sel("phase")}>
            <option value="All">All</option><option value="powerplay">Powerplay</option>
            <option value="middle">Middle</option><option value="death">Death</option>
          </select>
        </label>
        <label className="field"><span>Vs Bowling</span>
          <select {...sel("bowltype")}>
            <option value="All">All</option><option value="pace">Pace</option><option value="spin">Spin</option>
          </select>
        </label>
        <label className="field"><span>Batter Hand</span>
          <select {...sel("bathand")}>
            <option value="All">All</option><option value="RHB">Right (RHB)</option><option value="LHB">Left (LHB)</option>
          </select>
        </label>
        <label className="field field-range">
          <span>Qualifier · <b>{state.min_balls}</b> balls</span>
          <input type="range" min={6} max={120} step={6} value={state.min_balls}
            onChange={(e) => setFilter("min_balls", +e.target.value)} />
        </label>
      </div>
      <div className="chips-active">
        {chips.map((c) => (
          <span className="fchip" key={c.k}>{c.label} <b>{c.disp}</b>
            <button onClick={() => clearFilter(c.k)}>×</button></span>
        ))}
        {state.min_balls !== DEFAULTS.min_balls && (
          <span className="fchip">Min <b>{state.min_balls} balls</b>
            <button onClick={() => clearFilter("min_balls")}>×</button></span>
        )}
      </div>
    </section>
  );
}
