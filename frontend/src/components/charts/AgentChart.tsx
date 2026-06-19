import HBars from "./HBars";
import VBars from "./VBars";

export type ChartSpec = {
  kind?: string; x?: string; y?: string; title?: string;
  data?: Record<string, any>[];
};

export default function AgentChart({ spec }: { spec: ChartSpec }) {
  const data = (spec.data || [])
    .map((r) => ({ player: r[spec.x ?? ""], value: r[spec.y ?? ""] as number }))
    .filter((d) => d.value != null);
  return (
    <div className="agentchart">
      <div className="ac-t">{spec.title || ""}</div>
      <div className="chart">
        {spec.kind === "line"
          ? <VBars data={data.map((d) => ({ label: d.player, value: d.value }))} color="cyan" />
          : <HBars data={data.slice(0, 12)} color="lime" />}
      </div>
    </div>
  );
}
