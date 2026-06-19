import { ScatterPoint } from "../../api";

type Props = { points: ScatterPoint[]; xlabel: string; ylabel: string; color?: string };

export default function Scatter({ points, xlabel, ylabel, color = "#C6FF3A" }: Props) {
  if (!points.length) return <div className="rowsmini">not enough data for this scope</div>;
  const W = 540, H = 340, pad = 46;
  const xs = points.map((p) => p.x), ys = points.map((p) => p.y);
  const xmin = Math.min(...xs), xmax = Math.max(...xs), ymin = Math.min(...ys), ymax = Math.max(...ys);
  const px = (v: number) => pad + ((v - xmin) / ((xmax - xmin) || 1)) * (W - pad - 14);
  const py = (v: number) => H - pad - ((v - ymin) / ((ymax - ymin) || 1)) * (H - pad - 16);
  const top = [...points].sort((a, b) => b.y - a.y).slice(0, 6);
  return (
    <svg className="scatter" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="xMidYMid meet">
      <line x1={pad} y1={H - pad} x2={W - 6} y2={H - pad} stroke="rgba(255,255,255,.13)" />
      <line x1={pad} y1="6" x2={pad} y2={H - pad} stroke="rgba(255,255,255,.13)" />
      <text x={W - 6} y={H - pad + 22} fill="#86927C" fontSize="9" fontFamily="IBM Plex Mono" textAnchor="end">{xlabel} →</text>
      <text x={pad - 8} y="14" fill="#86927C" fontSize="9" fontFamily="IBM Plex Mono">↑ {ylabel}</text>
      {points.map((p, i) => (
        <circle key={i} cx={px(p.x).toFixed(1)} cy={py(p.y).toFixed(1)} r="5" fill={color} opacity=".82">
          <title>{p.player} — {xlabel}: {p.x}, {ylabel}: {p.y}</title>
        </circle>
      ))}
      {top.map((p, i) => (
        <text key={`l${i}`} x={(px(p.x) + 7).toFixed(1)} y={(py(p.y) + 3).toFixed(1)}
          fill="#AEB8A2" fontSize="9" fontFamily="IBM Plex Mono">{p.player}</text>
      ))}
    </svg>
  );
}
