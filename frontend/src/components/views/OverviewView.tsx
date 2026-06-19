import { useRef } from "react";
import { Dashboard } from "../../api";
import Card from "../charts/Card";
import HBars from "../charts/HBars";
import VBars from "../charts/VBars";
import Donut from "../charts/Donut";
import Duel from "../charts/Duel";
import { useReveal } from "../hooks/useReveal";

type Props = { active: boolean; data: Dashboard; onPlayer: (name: string) => void };

export default function OverviewView({ active, data, onPlayer }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  useReveal(ref, active ? data : null);
  if (!active) return null;
  return (
    <section className="view is-active">
      <div className="bento" ref={ref}>
        <Card title="Top Run Scorers" meta="runs" spanClass="span-5" tall csvKey="run_scorers" csvData={data.run_scorers}>
          <HBars data={data.run_scorers} color="lime" clickable onPlayer={onPlayer} />
        </Card>
        <Card title="Top Wicket-Takers" meta="wickets" spanClass="span-5" tall csvKey="wicket_takers" csvData={data.wicket_takers}>
          <HBars data={data.wicket_takers} color="lime" clickable onPlayer={onPlayer} />
        </Card>
        <Card title="Runs / Phase" spanClass="span-2" tall csvKey="runs_by_phase" csvData={data.runs_by_phase}>
          <Donut data={data.runs_by_phase} />
        </Card>
        <Card title="Bat First vs Chasing" meta="matches won" spanClass="span-7" csvKey="bat_vs_chase" csvData={data.bat_vs_chase}>
          <Duel data={data.bat_vs_chase} />
        </Card>
        <Card title="Economy by Phase" meta="runs / over" spanClass="span-5" csvKey="econ_by_phase" csvData={data.econ_by_phase}>
          <VBars data={data.econ_by_phase} color="amber" />
        </Card>
      </div>
    </section>
  );
}
