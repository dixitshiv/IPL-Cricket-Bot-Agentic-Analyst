import { useRef } from "react";
import Card from "../charts/Card";
import HBars from "../charts/HBars";
import Scatter from "../charts/Scatter";
import { useReveal } from "../hooks/useReveal";
import { useInsights } from "../../hooks/useInsights";
import { useFilters } from "../../state/FiltersContext";

export default function InsightsView({ active }: { active: boolean }) {
  const ref = useRef<HTMLDivElement>(null);
  const { state } = useFilters();
  const data = useInsights(state.season, active);
  useReveal(ref, active ? data : null);
  if (!active) return null;
  return (
    <section className="view is-active">
      <div className="bento" ref={ref}>
        <Card title="Bowler Quadrant" meta="economy → · wickets ↑" spanClass="span-6" tall>
          {data ? <Scatter points={data.bowlers} xlabel="economy" ylabel="wickets" color="#34E7FF" /> : null}
        </Card>
        <Card title="Batter Quadrant" meta="average → · strike rate ↑" spanClass="span-6" tall>
          {data ? <Scatter points={data.batters} xlabel="average" ylabel="strike rate" color="#C6FF3A" /> : null}
        </Card>
        <Card title="Highest-Scoring Venues" meta="avg 1st-innings score" spanClass="span-12">
          {data ? <HBars data={data.venues} color="amber" /> : null}
        </Card>
      </div>
    </section>
  );
}
