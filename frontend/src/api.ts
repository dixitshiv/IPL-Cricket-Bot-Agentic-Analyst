// Typed wrappers over the FastAPI /api/* endpoints.

export type Series = { player?: string; label?: string; phase?: string; value: number };
export type ScatterPoint = { player: string; x: number; y: number };

export type FilterState = {
  season: string;
  team: string;
  opponent: string;
  venue: string;
  innings: string;
  phase: string;
  bowltype: string;
  bathand: string;
  min_balls: number;
};

export type Filters = { seasons: string[]; teams: string[]; venues: string[] };

export type Health = {
  status: string;
  db: boolean;
  seasons: number;
  latest_season: string | null;
  has_key: boolean;
  model: string;
};

export type Kpis = {
  matches: number;
  runs: number;
  wickets: number;
  sixes: number;
  run_rate: number;
};

export type Dashboard = {
  kpis: Kpis;
  run_scorers: Series[];
  wicket_takers: Series[];
  runs_by_phase: Series[];
  bat_vs_chase: Series[];
  strike_rate: Series[];
  sixes: Series[];
  average: Series[];
  economy: Series[];
  dot_pct: Series[];
  econ_by_phase: Series[];
  team_wins: Series[];
  team_runs: Series[];
  team_rr: Series[];
};

export type Player = {
  name: string;
  teams: string[];
  seasons: string[];
  season: string;
  batting: {
    matches?: number; runs?: number; balls?: number; sr?: number;
    bat_avg?: number; sixes?: number; fours?: number; dot?: number;
  };
  bowling: { balls?: number; wickets?: number; econ?: number; dot?: number };
  is_bowler: boolean;
  runs_by_season: Series[];
  sr_by_phase: Series[];
  sr_vs_type: Series[];
  runs_by_venue: Series[];
  econ_by_season: Series[];
  wkts_by_season: Series[];
};

export type Insights = {
  bowlers: ScatterPoint[];
  batters: ScatterPoint[];
  venues: Series[];
  minb: number;
};

export type MatchupStats = {
  balls?: number; runs?: number; sr?: number; dismissals?: number;
  sixes?: number; fours?: number; dot?: number;
};
export type Matchup = {
  batter: string; bowler: string; season: string;
  stats: MatchupStats; found: boolean;
};

async function getJSON<T>(url: string): Promise<T> {
  const r = await fetch(url);
  return r.json() as Promise<T>;
}

const q = (v: string | number) => encodeURIComponent(String(v));

export const getFilters = () => getJSON<Filters>("/api/filters");
export const getHealth = () => getJSON<Health>("/api/health");

export function getDashboard(state: FilterState): Promise<Dashboard> {
  const qs = Object.entries(state).map(([k, v]) => `${k}=${q(v)}`).join("&");
  return getJSON<Dashboard>(`/api/dashboard?${qs}`);
}

export const getPlayer = (name: string, season: string) =>
  getJSON<Player>(`/api/player?name=${q(name)}&season=${q(season)}`);

export const getInsights = (season: string) =>
  getJSON<Insights>(`/api/insights?season=${q(season)}`);

export const getMatchup = (batter: string, bowler: string, season: string) =>
  getJSON<Matchup>(`/api/matchup?batter=${q(batter)}&bowler=${q(bowler)}&season=${q(season)}`);

// Build the SSE URL for the analyst stream. `scopeParams` is already-encoded `k=v` pairs.
export function askStreamUrl(question: string, sid: string, scopeParams: string[]): string {
  let url = `/api/ask?q=${q(question)}&sid=${sid}`;
  if (scopeParams.length) url += "&scope=1&" + scopeParams.join("&");
  return url;
}
