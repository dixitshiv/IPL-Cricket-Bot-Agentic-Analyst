import { Series } from "../../api";

export default function Duel({ data }: { data: Series[] }) {
  const total = data.reduce((s, d) => s + d.value, 0) || 1;
  const bf = data.find((d) => d.label === "Bat First") || { value: 0 };
  const ch = data.find((d) => d.label === "Chasing") || { value: 0 };
  return (
    <div className="duel">
      <div className="side bat">
        <div className="big">{bf.value}</div>
        <div className="pct">{((bf.value / total) * 100).toFixed(0)}% of decided</div>
        <div className="cap">Bat First wins</div>
      </div>
      <div className="side chase">
        <div className="big">{ch.value}</div>
        <div className="pct">{((ch.value / total) * 100).toFixed(0)}% of decided</div>
        <div className="cap">Chasing wins</div>
      </div>
    </div>
  );
}
