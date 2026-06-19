import { Series } from "../../api";

const PALETTE = ["#C6FF3A", "#34E7FF", "#FF4D9D", "#FFC14D"];
const ORDER: Record<string, number> = { powerplay: 0, middle: 1, death: 2 };
const fmt = (n: number) => (n >= 1000 ? n.toLocaleString("en-US") : `${n}`);

export default function Donut({ data }: { data: Series[] }) {
  const rows = [...data].sort((a, b) => (ORDER[a.phase ?? ""] ?? 9) - (ORDER[b.phase ?? ""] ?? 9));
  const total = rows.reduce((s, d) => s + d.value, 0) || 1;
  const R = 52, C = 2 * Math.PI * R;
  let off = 0;
  const segs = rows.map((d, i) => {
    const len = (d.value / total) * C;
    const seg = (
      <circle className="seg" r={R} cx="64" cy="64" fill="none"
        stroke={PALETTE[i]} strokeWidth="15"
        strokeDasharray={`${len} ${C - len}`} strokeDashoffset={-off}
        data-dash={`${len} ${C - len}`} key={i} />
    );
    off += len;
    return seg;
  });
  return (
    <div className="donut">
      <div className="donut-wrap">
        <svg width="128" height="128" viewBox="0 0 128 128">
          <circle r={R} cx="64" cy="64" fill="none" stroke="rgba(255,255,255,.05)" strokeWidth="15" />
          {segs}
        </svg>
        <div className="donut-ctr"><b>{fmt(total)}</b><span>runs</span></div>
      </div>
      <div className="legend">
        {rows.map((d, i) => (
          <div className="lg" key={i}>
            <span className="dot" style={{ background: PALETTE[i] }} />
            {d.phase}<b>{((d.value / total) * 100).toFixed(0)}%</b>
          </div>
        ))}
      </div>
    </div>
  );
}
