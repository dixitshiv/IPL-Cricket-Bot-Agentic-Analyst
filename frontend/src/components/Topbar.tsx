import { useFilters } from "../state/FiltersContext";

export default function Topbar({ matches }: { matches: number | "" }) {
  const { state } = useFilters();
  const label = state.season === "All" ? "ALL-TIME" : state.season;
  return (
    <header className="topbar">
      <div className="brand">
        <span className="brand-dot" />
        <span className="brand-name">CRICKET<span>//</span>COMMAND</span>
      </div>
      <div className="top-meta">
        IPL {label} · {matches} MATCHES · <span>LIVE</span>
      </div>
    </header>
  );
}
