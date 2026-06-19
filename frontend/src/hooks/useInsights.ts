import { useEffect, useState } from "react";
import { Insights, getInsights } from "../api";

export function useInsights(season: string, enabled: boolean) {
  const [data, setData] = useState<Insights | null>(null);
  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    getInsights(season)
      .then((d) => { if (!cancelled) setData(d); })
      .catch((e) => console.error("insights fetch failed", e));
    return () => { cancelled = true; };
  }, [season, enabled]);
  return data;
}
