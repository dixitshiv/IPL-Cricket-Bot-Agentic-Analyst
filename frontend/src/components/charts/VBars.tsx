import { Series } from "../../api";

const PHASE_ORDER: Record<string, number> = { powerplay: 0, middle: 1, death: 2 };

export default function VBars({ data, color = "lime" }: { data: Series[]; color?: string }) {
  let rows = data;
  if (rows.some((d) => d.phase))
    rows = [...rows].sort((a, b) => (PHASE_ORDER[a.phase ?? ""] ?? 9) - (PHASE_ORDER[b.phase ?? ""] ?? 9));
  const max = Math.max(...rows.map((d) => d.value)) || 1;
  return (
    <div className={`vbars c-${color}`}>
      {rows.map((d, i) => (
        <div className={`vbar c-${color}`} key={i}>
          <div className="col" style={{ height: `${(d.value / max) * 100}%` }}>
            <span className="vv">{d.value}</span>
          </div>
          <span className="vl">{d.label ?? d.phase}</span>
        </div>
      ))}
    </div>
  );
}
