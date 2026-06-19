import { useEffect, useRef } from "react";
import { Kpis } from "../api";

const fmt = (n: number) => (n >= 1000 ? n.toLocaleString("en-US") : `${n}`);

function CountUp({ target, decimals }: { target: number; decimals: number }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = ref.current; if (!el) return;
    const dur = 950, t0 = performance.now();
    const ease = (t: number) => 1 - Math.pow(1 - t, 3);
    let raf = 0;
    const step = (now: number) => {
      const p = Math.min(1, (now - t0) / dur), v = target * ease(p);
      el.textContent = decimals ? v.toFixed(decimals) : fmt(Math.round(v));
      if (p < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [target, decimals]);
  return <div className="v" ref={ref}>0</div>;
}

type Cell = { value: number; label: string; decimals: number };

export default function KpiTicker({ kpis, onExplain }: { kpis: Kpis; onExplain: (label: string, value: number) => void }) {
  const cells: Cell[] = [
    { value: kpis.matches, label: "Matches", decimals: 0 },
    { value: kpis.runs, label: "Runs", decimals: 0 },
    { value: kpis.wickets, label: "Wickets", decimals: 0 },
    { value: kpis.sixes, label: "Sixes", decimals: 0 },
    { value: kpis.run_rate, label: "Run Rate", decimals: 2 },
  ];
  return (
    <section className="ticker">
      {cells.map((c, i) => (
        <div className="kpi" key={i} style={{ cursor: "pointer" }} title="Explain this number"
          onClick={() => onExplain(c.label, c.value)}>
          <CountUp target={c.value} decimals={c.decimals} />
          <div className="l">{c.label}</div>
          <div className="tick" />
        </div>
      ))}
    </section>
  );
}
