import { useFilters } from "../state/FiltersContext";

export default function Hero() {
  const { state } = useFilters();
  const s = state.season;
  const year = s === "All" ? "ALL‑TIME" : s;
  const mark = s === "All" ? "∞" : s;
  const kicker = `${s === "All" ? "ALL SEASONS" : "SEASON " + s} · LIVE INTELLIGENCE`;
  return (
    <section className="hero">
      <div className="hero-mark">{mark}</div>
      <div className="kicker"><span className="live" /><span>{kicker}</span></div>
      <h1>IPL <em>{year}</em><br />COMMAND&nbsp;CENTER</h1>
      <p className="lede">Ball-by-ball intelligence over seventy matches — every number computed
        live on the rule-encoding views, plus an AI analyst that investigates any question on demand.</p>
    </section>
  );
}
