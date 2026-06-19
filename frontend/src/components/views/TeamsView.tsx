import { useRef } from "react";
import { Dashboard } from "../../api";
import Card from "../charts/Card";
import HBars from "../charts/HBars";
import { useReveal } from "../hooks/useReveal";

export default function TeamsView({ active, data }: { active: boolean; data: Dashboard }) {
  const ref = useRef<HTMLDivElement>(null);
  useReveal(ref, active ? data : null);
  if (!active) return null;
  return (
    <section className="view is-active">
      <div className="bento" ref={ref}>
        <Card title="Matches Won" meta="wins" spanClass="span-12" csvKey="team_wins" csvData={data.team_wins}>
          <HBars data={data.team_wins} color="lime" />
        </Card>
        <Card title="Runs Scored" meta="runs" spanClass="span-6" csvKey="team_runs" csvData={data.team_runs}>
          <HBars data={data.team_runs} color="cyan" />
        </Card>
        <Card title="Run Rate" meta="runs / over" spanClass="span-6" csvKey="team_rr" csvData={data.team_rr}>
          <HBars data={data.team_rr} color="pink" />
        </Card>
      </div>
    </section>
  );
}
