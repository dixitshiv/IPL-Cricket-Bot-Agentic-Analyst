import { createContext, useContext, useEffect, useRef, useState, ReactNode } from "react";
import { FilterState } from "../api";

export const DEFAULTS: FilterState = {
  season: "2026", team: "All", opponent: "All", venue: "All",
  innings: "All", phase: "All", bowltype: "All", bathand: "All", min_balls: 30,
};

// label map for the active-filter chips / scope summary (excludes season + min_balls)
export const FLABEL: Record<string, string> = {
  team: "Team", opponent: "vs", venue: "Venue", innings: "Innings",
  phase: "Phase", bowltype: "Vs", bathand: "Hand",
};

type Ctx = {
  state: FilterState;
  setFilter: (key: keyof FilterState, value: string | number) => void;
  reset: () => void;
  clearFilter: (key: keyof FilterState) => void;
  scopeOn: boolean;
  setScopeOn: (v: boolean) => void;
  activeView: string;
  setActiveView: (v: string) => void;
  activeFilters: () => string[];
  scopeParams: () => string[];
};

const FiltersCtx = createContext<Ctx | null>(null);

function readHash(): { state: Partial<FilterState>; view?: string } {
  const h = location.hash.slice(1);
  const o: Record<string, string> = {};
  if (h) h.split("&").forEach((p) => {
    const [k, v] = p.split("=");
    if (k) o[k] = decodeURIComponent(v || "");
  });
  const state: Partial<FilterState> = {};
  (Object.keys(DEFAULTS) as (keyof FilterState)[]).forEach((k) => {
    if (o[k] != null) (state as any)[k] = k === "min_balls" ? +o[k] : o[k];
  });
  return { state, view: o.view };
}

export function FiltersProvider({ children }: { children: ReactNode }) {
  const init = useRef(readHash());
  const [state, setState] = useState<FilterState>({ ...DEFAULTS, ...init.current.state });
  const [scopeOn, setScopeOn] = useState(false);
  const [activeView, setActiveView] = useState<string>(init.current.view || "overview");

  // write non-default filters + non-overview view back to the hash
  useEffect(() => {
    const parts: string[] = [];
    (Object.keys(DEFAULTS) as (keyof FilterState)[]).forEach((k) => {
      if (state[k] !== DEFAULTS[k]) parts.push(`${k}=${encodeURIComponent(String(state[k]))}`);
    });
    if (activeView && activeView !== "overview") parts.push(`view=${activeView}`);
    history.replaceState(null, "", parts.length ? "#" + parts.join("&") : location.pathname + location.search);
  }, [state, activeView]);

  const setFilter = (key: keyof FilterState, value: string | number) =>
    setState((s) => ({ ...s, [key]: value }));
  const reset = () => setState({ ...DEFAULTS });
  const clearFilter = (key: keyof FilterState) =>
    setState((s) => ({ ...s, [key]: key === "min_balls" ? DEFAULTS.min_balls : "All" }));

  const activeFilters = () => {
    const out: string[] = [];
    if (state.season !== "2026")
      out.push(`Season ${state.season === "All" ? "all-time" : state.season}`);
    for (const [k, l] of Object.entries(FLABEL)) {
      const v = state[k as keyof FilterState];
      if (v !== "All")
        out.push(`${l} ${k === "innings" ? (v === "1" ? "1st" : "2nd") : v}`);
    }
    return out;
  };

  const scopeParams = () => {
    const params: string[] = [];
    if (state.season !== "2026") params.push(`season=${encodeURIComponent(state.season)}`);
    Object.keys(FLABEL)
      .filter((k) => state[k as keyof FilterState] !== "All")
      .forEach((k) => params.push(`${k}=${encodeURIComponent(String(state[k as keyof FilterState]))}`));
    return params;
  };

  return (
    <FiltersCtx.Provider value={{
      state, setFilter, reset, clearFilter, scopeOn, setScopeOn,
      activeView, setActiveView, activeFilters, scopeParams,
    }}>
      {children}
    </FiltersCtx.Provider>
  );
}

export function useFilters(): Ctx {
  const c = useContext(FiltersCtx);
  if (!c) throw new Error("useFilters must be used within FiltersProvider");
  return c;
}
