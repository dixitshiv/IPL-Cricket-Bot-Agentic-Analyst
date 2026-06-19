import { useRef } from "react";
import { Dashboard } from "../../api";
import Card from "../charts/Card";
import HBars from "../charts/HBars";
import { useReveal } from "../hooks/useReveal";
import { useFilters } from "../../state/FiltersContext";

type Props = { active: boolean; data: Dashboard; onPlayer: (name: string) => void };

export default function BattingView({ active, data, onPlayer }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const { state } = useFilters();
  useReveal(ref, active ? data : null);
  if (!active) return null;
  const qual = `min ${state.min_balls} balls`;
  return (
    <section className="view is-active">
      <div className="bento" ref={ref}>
        <Card title="Strike Rate Leaders" meta={qual} spanClass="span-6" tall csvKey="strike_rate" csvData={data.strike_rate}>
          <HBars data={data.strike_rate} color="lime" clickable onPlayer={onPlayer} />
        </Card>
        <Card title="Most Sixes" meta="sixes" spanClass="span-6" tall csvKey="sixes" csvData={data.sixes}>
          <HBars data={data.sixes} color="pink" clickable onPlayer={onPlayer} />
        </Card>
        <Card title="Batting Average Leaders" meta={qual} spanClass="span-12" csvKey="average" csvData={data.average}>
          <HBars data={data.average} color="cyan" clickable onPlayer={onPlayer} />
        </Card>
      </div>
    </section>
  );
}
