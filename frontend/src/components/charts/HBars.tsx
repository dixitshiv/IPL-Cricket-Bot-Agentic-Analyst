import { Series } from "../../api";

type Props = { data: Series[]; color?: string; clickable?: boolean; onPlayer?: (name: string) => void };

export default function HBars({ data, color = "lime", clickable = false, onPlayer }: Props) {
  if (!data.length) return <div className="rowsmini">no data for this filter</div>;
  const max = Math.max(...data.map((d) => d.value)) || 1;
  return (
    <div className="hbars">
      {data.map((d, i) => {
        const nm = d.player ?? d.label ?? d.phase ?? "—";
        return (
          <div className={`hbar c-${color}`} key={i}>
            <span className="rk">{String(i + 1).padStart(2, "0")}</span>
            <span
              className={`nm${clickable ? " pl" : ""}`}
              title={String(nm)}
              onClick={clickable && onPlayer ? () => onPlayer(String(nm)) : undefined}
            >{nm}</span>
            <div className="track">
              <div className="fill" style={{ width: `${Math.max(2, (d.value / max) * 100)}%` }} />
            </div>
            <span className="val">{d.value ?? "—"}</span>
          </div>
        );
      })}
    </div>
  );
}
