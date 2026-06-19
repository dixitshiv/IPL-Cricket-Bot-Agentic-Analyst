import { useState } from "react";
import { Matchup, getMatchup } from "../../api";
import { useFilters } from "../../state/FiltersContext";

export default function MatchupsView({ active }: { active: boolean }) {
  const { state } = useFilters();
  const [batter, setBatter] = useState("");
  const [bowler, setBowler] = useState("");
  const [result, setResult] = useState<Matchup | null>(null);
  const [loading, setLoading] = useState(false);

  if (!active) return null;

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!batter.trim() || !bowler.trim()) return;
    setLoading(true); setResult(null);
    try {
      const d = await getMatchup(batter.trim(), bowler.trim(), state.season);
      setResult(d);
    } finally { setLoading(false); }
  };

  const kpis: [string, string | number][] = result?.found
    ? [["Balls", result.stats.balls ?? "—"], ["Runs", result.stats.runs ?? "—"],
       ["Strike Rate", result.stats.sr ?? "—"], ["Dismissals", result.stats.dismissals ?? "—"],
       ["Sixes", result.stats.sixes ?? "—"], ["Fours", result.stats.fours ?? "—"],
       ["Dot %", (result.stats.dot ?? "—") + "%"]]
    : [];

  return (
    <section className="view is-active">
      <div className="bento">
        <div className="card span-12">
          <div className="card-h">
            <span className="lbl">Batter vs Bowler</span>
            <span className="meta">head-to-head · all-time unless a season is set</span>
          </div>
          <form className="mu-form" onSubmit={submit}>
            <input placeholder="Batter — e.g. Kohli" autoComplete="off"
              value={batter} onChange={(e) => setBatter(e.target.value)} />
            <span className="mu-vs">VS</span>
            <input placeholder="Bowler — e.g. Bumrah" autoComplete="off"
              value={bowler} onChange={(e) => setBowler(e.target.value)} />
            <button type="submit">▸ Compare</button>
          </form>
          <div className="mu-result">
            {loading && <div className="rowsmini">crunching…</div>}
            {!loading && result && !result.found && (
              <div className="mu-note">No balls found between <b>{result.batter}</b> and <b>{result.bowler}</b>
                {state.season !== "All" ? " in " + state.season : ""}. Try other spellings, or set Season to <b>All seasons</b>.</div>
            )}
            {!loading && result && result.found && (
              <>
                <div className="mu-head"><b>{result.batter}</b><span className="vs">vs</span>{result.bowler}</div>
                <div className="mu-note">{result.season === "All" ? "All-time head-to-head" : "Season " + result.season}</div>
                <div className="mu-kpis">
                  {kpis.map(([l, v]) => (
                    <div className="pm-kpi" key={l}><div className="v">{v}</div><div className="l">{l}</div></div>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
