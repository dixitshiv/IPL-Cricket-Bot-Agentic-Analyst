import { useRef } from "react";
import { Dashboard } from "../../api";
import Card from "../charts/Card";
import HBars from "../charts/HBars";
import { useReveal } from "../hooks/useReveal";
import { useFilters } from "../../state/FiltersContext";

type Props = { active: boolean; data: Dashboard; onPlayer: (name: string) => void };

export default function BowlingView({ active, data, onPlayer }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const { state } = useFilters();
  useReveal(ref, active ? data : null);
  if (!active) return null;
  const qual = `min ${state.min_balls} balls`;
  return (
    <section className="view is-active">
      <div className="bento" ref={ref}>
        <Card title="Best Economy" meta={<>lower is better · {qual}</>} spanClass="span-6" tall csvKey="economy" csvData={data.economy}>
          <HBars data={data.economy} color="lime" clickable onPlayer={onPlayer} />
        </Card>
        <Card title="Dot-Ball %" meta={qual} spanClass="span-6" tall csvKey="dot_pct" csvData={data.dot_pct}>
          <HBars data={data.dot_pct} color="cyan" clickable onPlayer={onPlayer} />
        </Card>
      </div>
    </section>
  );
}
