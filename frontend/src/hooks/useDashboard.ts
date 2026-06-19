import { useEffect, useState } from "react";
import { Dashboard, FilterState, getDashboard } from "../api";

export function useDashboard(state: FilterState) {
  const [data, setData] = useState<Dashboard | null>(null);
  useEffect(() => {
    let cancelled = false;
    getDashboard(state)
      .then((d) => { if (!cancelled) setData(d); })
      .catch((e) => console.error("dashboard fetch failed", e));
    return () => { cancelled = true; };
    // re-fetch whenever any filter changes
  }, [state.season, state.team, state.opponent, state.venue, state.innings,
      state.phase, state.bowltype, state.bathand, state.min_balls]);
  return data;
}
