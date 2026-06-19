# React Frontend Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite the vanilla-JS frontend (`web/`) as a React + TypeScript app in a new `frontend/` folder, keeping design, layout, and functionality pixel-identical, with no backend changes.

**Architecture:** Vite + React + TypeScript, run as a standalone dev server with a `/api` proxy to the existing FastAPI server (`http://localhost:8765`). Shared filter state lives in a `FiltersContext`; data fetching lives in hooks (`useDashboard`, `useInsights`, `useAnalystStream`). The existing `web/styles.css` is reused verbatim, and every component emits the same class names and DOM structure so the design carries over unchanged.

**Tech Stack:** Vite, React 18, TypeScript, `marked` (npm), the existing `styles.css`.

> **Note on testing:** Per the approved spec, this project ships **no automated frontend test suite** (matching the existing repo, which has only Python tests). The TDD "write a failing test" step is therefore replaced by **type-check + build verification** (`npm run build`, which runs `tsc` then `vite build`) plus manual parity checks against the running vanilla app. Each task ends with a build-verify step and a commit.

---

## File Structure

```
frontend/
  package.json              # deps + scripts (Task 1)
  tsconfig.json             # TS config (Task 1)
  tsconfig.node.json        # TS config for vite.config (Task 1)
  vite.config.ts            # dev proxy /api -> :8765 (Task 1)
  index.html                # mounts #root + Google Fonts (Task 1)
  .gitignore                # node_modules, dist (Task 1)
  src/
    main.tsx                # React root; imports styles.css (Task 1)
    App.tsx                 # page composition; active view + modal state (Tasks 1, 8, 14)
    styles.css              # copied verbatim from web/styles.css (Task 1)
    api.ts                  # typed fetch wrappers + response types (Task 2)
    state/FiltersContext.tsx# filter state, setters, URL-hash sync, scope (Task 3)
    components/
      Background.tsx        # .bg atmosphere (Task 4)
      Topbar.tsx            # top control bar (Task 4)
      Hero.tsx              # season branding (Task 4)
      Footer.tsx            # footer (Task 4)
      charts/
        HBars.tsx           # horizontal bars (Task 5)
        VBars.tsx           # vertical bars (Task 5)
        Donut.tsx           # phase donut (Task 5)
        Duel.tsx            # bat-vs-chase (Task 5)
        Scatter.tsx         # insights scatter (Task 5)
        AgentChart.tsx      # inline agent chart (Task 5)
        Card.tsx            # bento card shell + CSV download (Task 5)
      hooks/
        useReveal.ts        # replay grow-in animations (Task 5)
      FilterDeck.tsx        # 9 filters + reset + active chips (Task 6)
      KpiTicker.tsx         # 5 KPIs + count-up; click -> Ask (Task 7)
      Nav.tsx               # 7 tabs + sliding nav-ink (Task 8)
      views/
        OverviewView.tsx    # (Task 9)
        BattingView.tsx     # (Task 9)
        BowlingView.tsx     # (Task 9)
        TeamsView.tsx       # (Task 9)
        InsightsView.tsx    # (Task 10)
        MatchupsView.tsx    # (Task 11)
        AskView.tsx         # analyst console (Task 13)
      PlayerModal.tsx       # player drilldown overlay (Task 12)
    hooks/
      useDashboard.ts       # fetch /api/dashboard on filter change (Task 9)
      useInsights.ts        # fetch /api/insights (Task 10)
      useAnalystStream.ts   # SSE wrapper for /api/ask (Task 13)
```

---

### Task 1: Scaffold the Vite + React + TypeScript project

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tsconfig.node.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/index.html`
- Create: `frontend/.gitignore`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/styles.css` (copied from `web/styles.css`)

- [ ] **Step 1: Create `frontend/package.json`**

```json
{
  "name": "cricket-command-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "marked": "^12.0.0",
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  },
  "devDependencies": {
    "@types/react": "^18.3.3",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.1",
    "typescript": "^5.5.3",
    "vite": "^5.4.0"
  }
}
```

- [ ] **Step 2: Create `frontend/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

- [ ] **Step 3: Create `frontend/tsconfig.node.json`**

```json
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "noEmit": true
  },
  "include": ["vite.config.ts"]
}
```

- [ ] **Step 4: Create `frontend/vite.config.ts`** — proxies `/api` to FastAPI so fetches and the SSE stream work in dev.

```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8765",
        changeOrigin: true,
      },
    },
  },
});
```

- [ ] **Step 5: Create `frontend/index.html`** — keeps the Google Fonts links from the original (marked now comes from npm, so its CDN `<script>` is dropped).

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>IPL 2026 · Command Center</title>
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Anton&family=IBM+Plex+Mono:wght@400;500;600&family=Hanken+Grotesk:wght@400;500;600;700;800&display=swap" rel="stylesheet" />
</head>
<body>
  <div id="root"></div>
  <script type="module" src="/src/main.tsx"></script>
</body>
</html>
```

- [ ] **Step 6: Create `frontend/.gitignore`**

```
node_modules
dist
```

- [ ] **Step 7: Copy the stylesheet verbatim**

Run from the repo root:
```bash
cp web/styles.css frontend/src/styles.css
```
Expected: `frontend/src/styles.css` exists and is byte-identical to `web/styles.css`.

- [ ] **Step 8: Create `frontend/src/main.tsx`**

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

- [ ] **Step 9: Create a minimal `frontend/src/App.tsx` placeholder** (fleshed out in later tasks)

```tsx
export default function App() {
  return <div className="wrap">Cricket Command — React shell</div>;
}
```

- [ ] **Step 10: Install dependencies and verify the build**

Run:
```bash
cd frontend && npm install && npm run build
```
Expected: `npm run build` exits 0 and emits `frontend/dist/`.

- [ ] **Step 11: Commit**

```bash
git add frontend/ && git commit -m "feat(frontend): scaffold Vite + React + TS shell"
```

---

### Task 2: API layer with typed responses (`api.ts`)

**Files:**
- Create: `frontend/src/api.ts`

This module centralizes every `/api/*` call and defines the TypeScript types for each
response, mirroring the shapes in `server.py`. All chart series share one `Series`
shape: the backend returns `{player|label|phase, value}` rows.

- [ ] **Step 1: Create `frontend/src/api.ts`**

```ts
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
```

- [ ] **Step 2: Verify the build**

Run: `cd frontend && npm run build`
Expected: exits 0 (types compile).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api.ts && git commit -m "feat(frontend): typed API layer for /api/* endpoints"
```

---

### Task 3: Filters context + URL-hash sync (`FiltersContext.tsx`)

**Files:**
- Create: `frontend/src/state/FiltersContext.tsx`

Mirrors the original `state`, `DEFAULTS`, `FLABEL`, `applyHash`/`updateHash`,
`activeFilters`, `clearFilter`, `resetFilters`, and the `scopeOn` toggle. The active
view is passed in via `setActiveView` so the hash can include it (original behavior:
hash carries non-default filters plus `view=` when not `overview`).

- [ ] **Step 1: Create `frontend/src/state/FiltersContext.tsx`**

```tsx
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
```

- [ ] **Step 2: Wrap the app in the provider** — update `frontend/src/main.tsx`:

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { FiltersProvider } from "./state/FiltersContext";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <FiltersProvider>
      <App />
    </FiltersProvider>
  </React.StrictMode>
);
```

- [ ] **Step 3: Verify the build**

Run: `cd frontend && npm run build`
Expected: exits 0.

- [ ] **Step 4: Commit**

```bash
git add frontend/src && git commit -m "feat(frontend): filters context with URL-hash sync"
```

---

### Task 4: Static layout components (Background, Topbar, Hero, Footer)

**Files:**
- Create: `frontend/src/components/Background.tsx`
- Create: `frontend/src/components/Topbar.tsx`
- Create: `frontend/src/components/Hero.tsx`
- Create: `frontend/src/components/Footer.tsx`

Hero + Topbar derive their season branding from `state.season` and the matches KPI
(passed as a prop), reproducing `applySeasonBranding`.

- [ ] **Step 1: Create `frontend/src/components/Background.tsx`**

```tsx
export default function Background() {
  return (
    <div className="bg">
      <div className="bg-grid" />
      <div className="bg-glow bg-glow-a" />
      <div className="bg-glow bg-glow-b" />
      <div className="bg-grain" />
      <div className="bg-vignette" />
    </div>
  );
}
```

- [ ] **Step 2: Create `frontend/src/components/Topbar.tsx`**

```tsx
import { useFilters } from "../state/FiltersContext";

export default function Topbar({ matches }: { matches: number | "" }) {
  const { state } = useFilters();
  const label = state.season === "All" ? "ALL-TIME" : state.season;
  return (
    <header className="topbar">
      <div className="brand">
        <span className="brand-dot" />
        <span className="brand-name">CRICKET<span>//</span>COMMAND</span>
      </div>
      <div className="top-meta">
        IPL {label} · {matches} MATCHES · <span>LIVE</span>
      </div>
    </header>
  );
}
```

- [ ] **Step 3: Create `frontend/src/components/Hero.tsx`**

```tsx
import { useFilters } from "../state/FiltersContext";

export default function Hero() {
  const { state } = useFilters();
  const s = state.season;
  const year = s === "All" ? "ALL‑TIME" : s;
  const mark = s === "All" ? "∞" : s;
  const kicker = `${s === "All" ? "ALL SEASONS" : "SEASON " + s} · LIVE INTELLIGENCE`;
  return (
    <section className="hero">
      <div className="hero-mark">{mark}</div>
      <div className="kicker"><span className="live" /><span>{kicker}</span></div>
      <h1>IPL <em>{year}</em><br />COMMAND&nbsp;CENTER</h1>
      <p className="lede">Ball-by-ball intelligence over seventy matches — every number computed
        live on the rule-encoding views, plus an AI analyst that investigates any question on demand.</p>
    </section>
  );
}
```

- [ ] **Step 4: Create `frontend/src/components/Footer.tsx`**

```tsx
export default function Footer() {
  return (
    <footer className="foot">
      IPL 2026 · 70 matches · numbers computed live over rule-encoding DuckDB views ·{" "}
      <span>LLM lives only at the edges</span>
    </footer>
  );
}
```

- [ ] **Step 5: Verify the build**

Run: `cd frontend && npm run build`
Expected: exits 0.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components && git commit -m "feat(frontend): static layout components"
```

---

### Task 5: Chart components + Card shell + reveal hook

**Files:**
- Create: `frontend/src/components/charts/HBars.tsx`
- Create: `frontend/src/components/charts/VBars.tsx`
- Create: `frontend/src/components/charts/Donut.tsx`
- Create: `frontend/src/components/charts/Duel.tsx`
- Create: `frontend/src/components/charts/Scatter.tsx`
- Create: `frontend/src/components/charts/AgentChart.tsx`
- Create: `frontend/src/components/charts/Card.tsx`
- Create: `frontend/src/components/hooks/useReveal.ts`

Each chart renders the **same markup** as the matching function in `web/app.js`.
Colors are CSS class suffixes (`c-lime`, `c-cyan`, …). `HBars` rows can be clickable
(player drilldown) via an `onPlayer` callback.

- [ ] **Step 1: Create `frontend/src/components/charts/HBars.tsx`**

```tsx
import { Series } from "../../api";

type Props = { data: Series[]; color?: string; clickable?: boolean; onPlayer?: (name: string) => void };

export default function HBars({ data, color = "lime", clickable = false, onPlayer }: Props) {
  if (!data.length) return <div className="rowsmini">no data for this filter</div>;
  const max = Math.max(...data.map((d) => d.value)) || 1;
  return (
    <div className="hbars">
      {data.map((d, i) => {
        const nm = d.player ?? d.label ?? d.phase ?? "—";
        return (
          <div className={`hbar c-${color}`} key={i}>
            <span className="rk">{String(i + 1).padStart(2, "0")}</span>
            <span
              className={`nm${clickable ? " pl" : ""}`}
              title={String(nm)}
              onClick={clickable && onPlayer ? () => onPlayer(String(nm)) : undefined}
            >{nm}</span>
            <div className="track">
              <div className="fill" style={{ width: `${Math.max(2, (d.value / max) * 100)}%` }} />
            </div>
            <span className="val">{d.value ?? "—"}</span>
          </div>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 2: Create `frontend/src/components/charts/VBars.tsx`**

```tsx
import { Series } from "../../api";

const PHASE_ORDER: Record<string, number> = { powerplay: 0, middle: 1, death: 2 };

export default function VBars({ data, color = "lime" }: { data: Series[]; color?: string }) {
  let rows = data;
  if (rows.some((d) => d.phase))
    rows = [...rows].sort((a, b) => (PHASE_ORDER[a.phase ?? ""] ?? 9) - (PHASE_ORDER[b.phase ?? ""] ?? 9));
  const max = Math.max(...rows.map((d) => d.value)) || 1;
  return (
    <div className={`vbars c-${color}`}>
      {rows.map((d, i) => (
        <div className={`vbar c-${color}`} key={i}>
          <div className="col" style={{ height: `${(d.value / max) * 100}%` }}>
            <span className="vv">{d.value}</span>
          </div>
          <span className="vl">{d.label ?? d.phase}</span>
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 3: Create `frontend/src/components/charts/Donut.tsx`**

```tsx
import { Series } from "../../api";

const PALETTE = ["#C6FF3A", "#34E7FF", "#FF4D9D", "#FFC14D"];
const ORDER: Record<string, number> = { powerplay: 0, middle: 1, death: 2 };
const fmt = (n: number) => (n >= 1000 ? n.toLocaleString("en-US") : `${n}`);

export default function Donut({ data }: { data: Series[] }) {
  const rows = [...data].sort((a, b) => (ORDER[a.phase ?? ""] ?? 9) - (ORDER[b.phase ?? ""] ?? 9));
  const total = rows.reduce((s, d) => s + d.value, 0) || 1;
  const R = 52, C = 2 * Math.PI * R;
  let off = 0;
  const segs = rows.map((d, i) => {
    const len = (d.value / total) * C;
    const seg = (
      <circle className="seg" r={R} cx="64" cy="64" fill="none"
        stroke={PALETTE[i]} strokeWidth="15"
        strokeDasharray={`${len} ${C - len}`} strokeDashoffset={-off}
        data-dash={`${len} ${C - len}`} key={i} />
    );
    off += len;
    return seg;
  });
  return (
    <div className="donut">
      <div className="donut-wrap">
        <svg width="128" height="128" viewBox="0 0 128 128">
          <circle r={R} cx="64" cy="64" fill="none" stroke="rgba(255,255,255,.05)" strokeWidth="15" />
          {segs}
        </svg>
        <div className="donut-ctr"><b>{fmt(total)}</b><span>runs</span></div>
      </div>
      <div className="legend">
        {rows.map((d, i) => (
          <div className="lg" key={i}>
            <span className="dot" style={{ background: PALETTE[i] }} />
            {d.phase}<b>{((d.value / total) * 100).toFixed(0)}%</b>
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Create `frontend/src/components/charts/Duel.tsx`**

```tsx
import { Series } from "../../api";

export default function Duel({ data }: { data: Series[] }) {
  const total = data.reduce((s, d) => s + d.value, 0) || 1;
  const bf = data.find((d) => d.label === "Bat First") || { value: 0 };
  const ch = data.find((d) => d.label === "Chasing") || { value: 0 };
  return (
    <div className="duel">
      <div className="side bat">
        <div className="big">{bf.value}</div>
        <div className="pct">{((bf.value / total) * 100).toFixed(0)}% of decided</div>
        <div className="cap">Bat First wins</div>
      </div>
      <div className="side chase">
        <div className="big">{ch.value}</div>
        <div className="pct">{((ch.value / total) * 100).toFixed(0)}% of decided</div>
        <div className="cap">Chasing wins</div>
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Create `frontend/src/components/charts/Scatter.tsx`**

```tsx
import { ScatterPoint } from "../../api";

type Props = { points: ScatterPoint[]; xlabel: string; ylabel: string; color?: string };

export default function Scatter({ points, xlabel, ylabel, color = "#C6FF3A" }: Props) {
  if (!points.length) return <div className="rowsmini">not enough data for this scope</div>;
  const W = 540, H = 340, pad = 46;
  const xs = points.map((p) => p.x), ys = points.map((p) => p.y);
  const xmin = Math.min(...xs), xmax = Math.max(...xs), ymin = Math.min(...ys), ymax = Math.max(...ys);
  const px = (v: number) => pad + ((v - xmin) / ((xmax - xmin) || 1)) * (W - pad - 14);
  const py = (v: number) => H - pad - ((v - ymin) / ((ymax - ymin) || 1)) * (H - pad - 16);
  const top = [...points].sort((a, b) => b.y - a.y).slice(0, 6);
  return (
    <svg className="scatter" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="xMidYMid meet">
      <line x1={pad} y1={H - pad} x2={W - 6} y2={H - pad} stroke="rgba(255,255,255,.13)" />
      <line x1={pad} y1="6" x2={pad} y2={H - pad} stroke="rgba(255,255,255,.13)" />
      <text x={W - 6} y={H - pad + 22} fill="#86927C" fontSize="9" fontFamily="IBM Plex Mono" textAnchor="end">{xlabel} →</text>
      <text x={pad - 8} y="14" fill="#86927C" fontSize="9" fontFamily="IBM Plex Mono">↑ {ylabel}</text>
      {points.map((p, i) => (
        <circle key={i} cx={px(p.x).toFixed(1)} cy={py(p.y).toFixed(1)} r="5" fill={color} opacity=".82">
          <title>{p.player} — {xlabel}: {p.x}, {ylabel}: {p.y}</title>
        </circle>
      ))}
      {top.map((p, i) => (
        <text key={`l${i}`} x={(px(p.x) + 7).toFixed(1)} y={(py(p.y) + 3).toFixed(1)}
          fill="#AEB8A2" fontSize="9" fontFamily="IBM Plex Mono">{p.player}</text>
      ))}
    </svg>
  );
}
```

- [ ] **Step 6: Create `frontend/src/components/charts/AgentChart.tsx`** — renders an inline chart from an agent chart spec (original `agentChart`: `line` → VBars cyan, else HBars lime top-12).

```tsx
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
```

- [ ] **Step 7: Create `frontend/src/components/hooks/useReveal.ts`** — replays the grow-in flourish (original `animateView`/`replay`) on a container ref whenever `dep` changes.

```ts
import { RefObject, useEffect } from "react";

function replay(el: HTMLElement, animation: string) {
  el.style.animation = "none";
  void el.offsetWidth; // force reflow so the animation restarts
  el.style.animation = animation;
}

export function useReveal(ref: RefObject<HTMLElement>, dep: unknown) {
  useEffect(() => {
    const root = ref.current;
    if (!root) return;
    root.querySelectorAll<HTMLElement>(".fill").forEach((f, i) =>
      replay(f, `growX 1.05s cubic-bezier(.2,.7,.2,1) ${(0.04 + i * 0.035).toFixed(3)}s both`));
    root.querySelectorAll<HTMLElement>(".col").forEach((c, i) =>
      replay(c, `growY 1s cubic-bezier(.2,.7,.2,1) ${(0.06 + i * 0.06).toFixed(3)}s both`));
    root.querySelectorAll<SVGElement>(".seg").forEach((s, i) => {
      const dash = s.getAttribute("data-dash") || "0 9999";
      (s as any).style.strokeDasharray = "0 9999";
      setTimeout(() => {
        (s as any).style.transition = "stroke-dasharray 1.1s cubic-bezier(.2,.7,.2,1)";
        (s as any).style.strokeDasharray = dash;
      }, 120 + i * 140);
    });
  }, [ref, dep]);
}
```

- [ ] **Step 8: Create `frontend/src/components/charts/Card.tsx`** — the bento card shell with header + CSV download. Reproduces `downloadCSV` and the per-card download button (only shown when there is array data).

```tsx
import { ReactNode } from "react";
import { Series } from "../../api";
import { useFilters } from "../../state/FiltersContext";

type Props = {
  title: string; meta?: ReactNode; spanClass: string; tall?: boolean;
  csvKey?: string; csvData?: Series[]; children: ReactNode;
};

export default function Card({ title, meta, spanClass, tall, csvKey, csvData, children }: Props) {
  const { state } = useFilters();
  const download = () => {
    if (!csvData?.length || !csvKey) return;
    const cols = Object.keys(csvData[0]);
    const csv = [
      cols.join(","),
      ...csvData.map((r) => cols.map((c) => `"${String((r as any)[c] ?? "").replace(/"/g, '""')}"`).join(",")),
    ].join("\n");
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
    const a = document.createElement("a");
    a.href = url; a.download = `${csvKey}_${state.season}.csv`; a.click();
    URL.revokeObjectURL(url);
  };
  return (
    <div className={`card ${spanClass}${tall ? " tall" : ""}`}>
      <div className="card-h">
        <span className="lbl">{title}</span>
        {meta != null && <span className="meta">{meta}</span>}
      </div>
      <div className="chart">{children}</div>
      {csvData && csvData.length > 0 && (
        <button className="dl" title="Download CSV" onClick={(e) => { e.stopPropagation(); download(); }}>⤓</button>
      )}
    </div>
  );
}
```

- [ ] **Step 9: Verify the build**

Run: `cd frontend && npm run build`
Expected: exits 0.

- [ ] **Step 10: Commit**

```bash
git add frontend/src/components && git commit -m "feat(frontend): chart components, card shell, reveal hook"
```

---

### Task 6: Filter deck (`FilterDeck.tsx`)

**Files:**
- Create: `frontend/src/components/FilterDeck.tsx`

Reproduces the filter deck: 8 selects + the min-balls range, the Reset button, the
active-filter chips, and the scope toggle row (the scope row markup lives in AskView
in the original, but the toggle state is shared via context — here the deck renders
only the chips; the scope row is rendered inside AskView in Task 13). Filter option
lists come from `getFilters()` (fetched in App, passed as props).

- [ ] **Step 1: Create `frontend/src/components/FilterDeck.tsx`**

```tsx
import { Filters, FilterState } from "../api";
import { useFilters, FLABEL, DEFAULTS } from "../state/FiltersContext";

export default function FilterDeck({ filters }: { filters: Filters | null }) {
  const { state, setFilter, reset, clearFilter } = useFilters();
  const seasons = filters?.seasons ?? [];
  const teams = filters?.teams ?? ["All"];
  const venues = filters?.venues ?? ["All"];

  const sel = (key: keyof FilterState) => ({
    value: String(state[key]),
    onChange: (e: React.ChangeEvent<HTMLSelectElement>) => setFilter(key, e.target.value),
  });

  // active chips
  const chips: { k: keyof FilterState; label: string; disp: string }[] = [];
  for (const [k, label] of Object.entries(FLABEL)) {
    const v = state[k as keyof FilterState];
    if (v !== "All")
      chips.push({ k: k as keyof FilterState, label, disp: k === "innings" ? (v === "1" ? "1st" : "2nd") : String(v) });
  }

  return (
    <section className="deck">
      <div className="deck-h">
        <span className="lbl">Filters</span>
        <button className="reset" type="button" onClick={reset}>⟲ Reset all</button>
      </div>
      <div className="deck-grid">
        <label className="field"><span>Season</span>
          <select {...sel("season")}>
            <option value="All">All seasons</option>
            {seasons.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </label>
        <label className="field"><span>Team</span>
          <select {...sel("team")}>
            {teams.map((t) => <option key={t} value={t}>{t === "All" ? "All Teams" : t}</option>)}
          </select>
        </label>
        <label className="field"><span>Opponent</span>
          <select {...sel("opponent")}>
            {teams.map((t) => <option key={t} value={t}>{t === "All" ? "Any Opponent" : t}</option>)}
          </select>
        </label>
        <label className="field"><span>Venue</span>
          <select {...sel("venue")}>
            {venues.map((v) => <option key={v} value={v}>{v === "All" ? "All Venues" : v}</option>)}
          </select>
        </label>
        <label className="field"><span>Innings</span>
          <select {...sel("innings")}>
            <option value="All">All</option><option value="1">1st innings</option><option value="2">2nd innings</option>
          </select>
        </label>
        <label className="field"><span>Phase</span>
          <select {...sel("phase")}>
            <option value="All">All</option><option value="powerplay">Powerplay</option>
            <option value="middle">Middle</option><option value="death">Death</option>
          </select>
        </label>
        <label className="field"><span>Vs Bowling</span>
          <select {...sel("bowltype")}>
            <option value="All">All</option><option value="pace">Pace</option><option value="spin">Spin</option>
          </select>
        </label>
        <label className="field"><span>Batter Hand</span>
          <select {...sel("bathand")}>
            <option value="All">All</option><option value="RHB">Right (RHB)</option><option value="LHB">Left (LHB)</option>
          </select>
        </label>
        <label className="field field-range">
          <span>Qualifier · <b>{state.min_balls}</b> balls</span>
          <input type="range" min={6} max={120} step={6} value={state.min_balls}
            onChange={(e) => setFilter("min_balls", +e.target.value)} />
        </label>
      </div>
      <div className="chips-active">
        {chips.map((c) => (
          <span className="fchip" key={c.k}>{c.label} <b>{c.disp}</b>
            <button onClick={() => clearFilter(c.k)}>×</button></span>
        ))}
        {state.min_balls !== DEFAULTS.min_balls && (
          <span className="fchip">Min <b>{state.min_balls} balls</b>
            <button onClick={() => clearFilter("min_balls")}>×</button></span>
        )}
      </div>
    </section>
  );
}
```

> **Parity note:** In the original, dragging the range only re-fetches on `change`
> (release), while the label updates on `input`. In React, `min_balls` updates on each
> change and `useDashboard` (Task 9) debounce is unnecessary because the range fires
> `onChange` on release in most browsers; if drag-thrash is observed, the data fetch
> can be moved to `onMouseUp`. Keep the simple version unless parity testing shows a
> problem.

- [ ] **Step 2: Verify the build**

Run: `cd frontend && npm run build`
Expected: exits 0.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/FilterDeck.tsx && git commit -m "feat(frontend): filter deck + active chips"
```

---

### Task 7: KPI ticker (`KpiTicker.tsx`)

**Files:**
- Create: `frontend/src/components/KpiTicker.tsx`

Reproduces `renderKPIs` + `countUp`. Clicking a KPI switches to Ask and fires a
templated question (handled via an `onExplain` callback passed from App, which calls
the analyst stream).

- [ ] **Step 1: Create `frontend/src/components/KpiTicker.tsx`**

```tsx
import { useEffect, useRef } from "react";
import { Kpis } from "../api";
import { useFilters } from "../state/FiltersContext";

const fmt = (n: number) => (n >= 1000 ? n.toLocaleString("en-US") : `${n}`);

function CountUp({ target, decimals }: { target: number; decimals: number }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = ref.current; if (!el) return;
    const dur = 950, t0 = performance.now();
    const ease = (t: number) => 1 - Math.pow(1 - t, 3);
    let raf = 0;
    const step = (now: number) => {
      const p = Math.min(1, (now - t0) / dur), v = target * ease(p);
      el.textContent = decimals ? v.toFixed(decimals) : fmt(Math.round(v));
      if (p < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [target, decimals]);
  return <div className="v" ref={ref}>0</div>;
}

type Cell = { value: number; label: string; decimals: number };

export default function KpiTicker({ kpis, onExplain }: { kpis: Kpis; onExplain: (label: string, value: number) => void }) {
  const { state } = useFilters();
  const cells: Cell[] = [
    { value: kpis.matches, label: "Matches", decimals: 0 },
    { value: kpis.runs, label: "Runs", decimals: 0 },
    { value: kpis.wickets, label: "Wickets", decimals: 0 },
    { value: kpis.sixes, label: "Sixes", decimals: 0 },
    { value: kpis.run_rate, label: "Run Rate", decimals: 2 },
  ];
  return (
    <section className="ticker">
      {cells.map((c, i) => (
        <div className="kpi" key={i} style={{ cursor: "pointer" }} title="Explain this number"
          onClick={() => onExplain(c.label, c.value)}>
          <CountUp target={c.value} decimals={c.decimals} />
          <div className="l">{c.label}</div>
          <div className="tick" />
        </div>
      ))}
    </section>
  );
}
```

> **Note:** `state` is imported for the season context used by the explain template;
> the template string itself is built in App's `onExplain` (Task 14) so it can reach
> the analyst stream. If `state` ends up unused here after wiring, remove the import to
> satisfy `noUnusedLocals`.

- [ ] **Step 2: Verify the build**

Run: `cd frontend && npm run build`
Expected: exits 0.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/KpiTicker.tsx && git commit -m "feat(frontend): KPI ticker with count-up"
```

---

### Task 8: Nav with sliding indicator (`Nav.tsx`)

**Files:**
- Create: `frontend/src/components/Nav.tsx`

Reproduces the 7-tab nav and the `nav-ink` underline that slides to the active
button (measured from the button's `offsetLeft`/`offsetWidth`, re-measured on resize
and when the active view changes).

- [ ] **Step 1: Create `frontend/src/components/Nav.tsx`**

```tsx
import { useEffect, useLayoutEffect, useRef } from "react";

const TABS: { view: string; label: string; ask?: boolean }[] = [
  { view: "overview", label: "Overview" },
  { view: "batting", label: "Batting" },
  { view: "bowling", label: "Bowling" },
  { view: "teams", label: "Teams" },
  { view: "insights", label: "Insights" },
  { view: "matchups", label: "Matchups" },
  { view: "ask", label: "Ask the Analyst", ask: true },
];

export default function Nav({ active, onSwitch }: { active: string; onSwitch: (v: string) => void }) {
  const navRef = useRef<HTMLElement>(null);
  const inkRef = useRef<HTMLSpanElement>(null);

  const moveInk = () => {
    const nav = navRef.current, ink = inkRef.current;
    if (!nav || !ink) return;
    const btn = nav.querySelector<HTMLButtonElement>(`.nav-btn[data-view="${active}"]`);
    if (!btn) return;
    ink.style.left = btn.offsetLeft + "px";
    ink.style.width = btn.offsetWidth + "px";
  };

  useLayoutEffect(moveInk, [active]);
  useEffect(() => {
    window.addEventListener("resize", moveInk);
    return () => window.removeEventListener("resize", moveInk);
  });

  return (
    <nav className="nav" ref={navRef}>
      {TABS.map((t) => (
        <button key={t.view}
          className={`nav-btn${t.ask ? " nav-ask" : ""}${active === t.view ? " is-active" : ""}`}
          data-view={t.view} onClick={() => onSwitch(t.view)}>{t.label}</button>
      ))}
      <span className="nav-ink" ref={inkRef} />
    </nav>
  );
}
```

- [ ] **Step 2: Verify the build**

Run: `cd frontend && npm run build`
Expected: exits 0.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/Nav.tsx && git commit -m "feat(frontend): nav with sliding indicator"
```

---

### Task 9: Dashboard data hook + Overview/Batting/Bowling/Teams views

**Files:**
- Create: `frontend/src/hooks/useDashboard.ts`
- Create: `frontend/src/components/views/OverviewView.tsx`
- Create: `frontend/src/components/views/BattingView.tsx`
- Create: `frontend/src/components/views/BowlingView.tsx`
- Create: `frontend/src/components/views/TeamsView.tsx`

The four views render `<Card>`s in the same bento layout/spans as the original HTML.
Each chart picks its renderer from the card's kind. Player rows are clickable in
non-team charts (original: `clickable = !key.startsWith("team")`).

- [ ] **Step 1: Create `frontend/src/hooks/useDashboard.ts`**

```ts
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
```

- [ ] **Step 2: Create `frontend/src/components/views/OverviewView.tsx`**

```tsx
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
```

- [ ] **Step 3: Create `frontend/src/components/views/BattingView.tsx`**

```tsx
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
```

- [ ] **Step 4: Create `frontend/src/components/views/BowlingView.tsx`**

```tsx
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
```

- [ ] **Step 5: Create `frontend/src/components/views/TeamsView.tsx`** (team rows are **not** clickable)

```tsx
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
```

- [ ] **Step 6: Verify the build**

Run: `cd frontend && npm run build`
Expected: exits 0.

- [ ] **Step 7: Commit**

```bash
git add frontend/src && git commit -m "feat(frontend): dashboard hook + overview/batting/bowling/teams views"
```

---

### Task 10: Insights view (`useInsights.ts` + `InsightsView.tsx`)

**Files:**
- Create: `frontend/src/hooks/useInsights.ts`
- Create: `frontend/src/components/views/InsightsView.tsx`

`useInsights` fetches `/api/insights?season=...`. The view shows two scatters + the
venues hbar. Original fetched on season only (not the other filters), lazily when the
view is first opened — here we fetch when the view becomes active and season changes.

- [ ] **Step 1: Create `frontend/src/hooks/useInsights.ts`**

```ts
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
```

- [ ] **Step 2: Create `frontend/src/components/views/InsightsView.tsx`**

```tsx
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
```

- [ ] **Step 3: Verify the build**

Run: `cd frontend && npm run build`
Expected: exits 0.

- [ ] **Step 4: Commit**

```bash
git add frontend/src && git commit -m "feat(frontend): insights view with scatters + venues"
```

---

### Task 11: Matchups view (`MatchupsView.tsx`)

**Files:**
- Create: `frontend/src/components/views/MatchupsView.tsx`

Reproduces `runMatchup` + the result markup.

- [ ] **Step 1: Create `frontend/src/components/views/MatchupsView.tsx`**

```tsx
import { useState } from "react";
import { Matchup, getMatchup } from "../../api";
import { useFilters } from "../../state/FiltersContext";

export default function MatchupsView({ active }: { active: boolean }) {
  const { state } = useFilters();
  const [batter, setBatter] = useState("");
  const [bowler, setBowler] = useState("");
  const [result, setResult] = useState<Matchup | null>(null);
  const [loading, setLoading] = useState(false);

  if (!active) return null;

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!batter.trim() || !bowler.trim()) return;
    setLoading(true); setResult(null);
    try {
      const d = await getMatchup(batter.trim(), bowler.trim(), state.season);
      setResult(d);
    } finally { setLoading(false); }
  };

  const kpis: [string, string | number][] = result?.found
    ? [["Balls", result.stats.balls ?? "—"], ["Runs", result.stats.runs ?? "—"],
       ["Strike Rate", result.stats.sr ?? "—"], ["Dismissals", result.stats.dismissals ?? "—"],
       ["Sixes", result.stats.sixes ?? "—"], ["Fours", result.stats.fours ?? "—"],
       ["Dot %", (result.stats.dot ?? "—") + "%"]]
    : [];

  return (
    <section className="view is-active">
      <div className="bento">
        <div className="card span-12">
          <div className="card-h">
            <span className="lbl">Batter vs Bowler</span>
            <span className="meta">head-to-head · all-time unless a season is set</span>
          </div>
          <form className="mu-form" onSubmit={submit}>
            <input placeholder="Batter — e.g. Kohli" autoComplete="off"
              value={batter} onChange={(e) => setBatter(e.target.value)} />
            <span className="mu-vs">VS</span>
            <input placeholder="Bowler — e.g. Bumrah" autoComplete="off"
              value={bowler} onChange={(e) => setBowler(e.target.value)} />
            <button type="submit">▸ Compare</button>
          </form>
          <div className="mu-result">
            {loading && <div className="rowsmini">crunching…</div>}
            {!loading && result && !result.found && (
              <div className="mu-note">No balls found between <b>{result.batter}</b> and <b>{result.bowler}</b>
                {state.season !== "All" ? " in " + state.season : ""}. Try other spellings, or set Season to <b>All seasons</b>.</div>
            )}
            {!loading && result && result.found && (
              <>
                <div className="mu-head"><b>{result.batter}</b><span className="vs">vs</span>{result.bowler}</div>
                <div className="mu-note">{result.season === "All" ? "All-time head-to-head" : "Season " + result.season}</div>
                <div className="mu-kpis">
                  {kpis.map(([l, v]) => (
                    <div className="pm-kpi" key={l}><div className="v">{v}</div><div className="l">{l}</div></div>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
```

- [ ] **Step 2: Verify the build**

Run: `cd frontend && npm run build`
Expected: exits 0.

- [ ] **Step 3: Commit**

```bash
git add frontend/src && git commit -m "feat(frontend): matchups view"
```

---

### Task 12: Player drilldown modal (`PlayerModal.tsx`)

**Files:**
- Create: `frontend/src/components/PlayerModal.tsx`

Reproduces `openPlayer`/`renderPlayer`/`roleTags`/`pseries` and the overlay markup.
Closes on backdrop click and Escape. Mapped per-player series use `pseries` shape
(`player`/`label`/`phase` all set to the row's `player`).

- [ ] **Step 1: Create `frontend/src/components/PlayerModal.tsx`**

```tsx
import { useEffect, useRef, useState } from "react";
import { Player, Series, getPlayer } from "../api";
import HBars from "./charts/HBars";
import VBars from "./charts/VBars";
import { useReveal } from "./hooks/useReveal";

const pseries = (arr: Series[] = []): Series[] =>
  arr.map((r) => ({ player: r.player, label: r.player, phase: r.player, value: r.value }));

function roleTags(d: Player): string[] {
  const b = d.batting || {}, tags: string[] = [], ph: Record<string, number> = {};
  (d.sr_by_phase || []).forEach((r) => { if (r.player) ph[r.player] = r.value; });
  const balls = b.balls || 0;
  if (d.is_bowler && balls >= 200) tags.push("All-rounder");
  else if (d.is_bowler) tags.push("Bowler");
  if (balls >= 100) {
    if ((ph.death || 0) >= 175 && (ph.death || 0) >= (ph.powerplay || 0)) tags.push("Finisher");
    if ((b.bat_avg || 0) >= 35 && (b.sr || 0) < 148) tags.push("Anchor");
    if ((b.sr || 0) >= 160) tags.push("Power hitter");
  }
  if (!tags.length && balls > 0) tags.push("Batter");
  return tags;
}

type CardSpec = [title: string, meta: string, data: Series[], kind: "vbar" | "hbar", color: string, full: boolean];

export default function PlayerModal({ name, season, onClose }: { name: string; season: string; onClose: () => void }) {
  const [data, setData] = useState<Player | null>(null);
  const cardRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    getPlayer(name, season).then((d) => { if (!cancelled) setData(d); });
    return () => { cancelled = true; };
  }, [name, season]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  useReveal(cardRef, data);

  const scope = !data ? "" : data.season === "All" ? "All-time / career" : `Season ${data.season}`;
  const kpis: [string, string | number][] = data ? (() => {
    const b = data.batting || {};
    const k: [string, string | number][] = [
      ["Runs", b.runs ?? "—"], ["Strike Rate", b.sr ?? "—"], ["Average", b.bat_avg ?? "—"],
      ["Sixes", b.sixes ?? "—"], ["Dot %", b.dot != null ? b.dot + "%" : "—"]];
    if (data.is_bowler) { const w = data.bowling || {}; k.push(["Wickets", w.wickets ?? "—"], ["Economy", w.econ ?? "—"]); }
    return k;
  })() : [];

  const cards: CardSpec[] = data ? (() => {
    const c: CardSpec[] = [
      ["Runs by Season", "career", data.runs_by_season, "vbar", "lime", true],
      ["Strike Rate by Phase", scope, data.sr_by_phase, "vbar", "cyan", false],
      ["Strike Rate vs Pace / Spin", scope, data.sr_vs_type, "vbar", "pink", false],
      ["Runs by Venue", scope, data.runs_by_venue, "hbar", "amber", false]];
    if (data.is_bowler) c.push(
      ["Wickets by Season", "career", data.wkts_by_season, "vbar", "lime", true],
      ["Economy by Season", "career", data.econ_by_season, "vbar", "cyan", true]);
    return c;
  })() : [];

  return (
    <div className="pmodal">
      <div className="pmodal-bg" onClick={onClose} />
      <div className="pmodal-card" ref={cardRef}>
        {!data ? (
          <div className="pm-head"><div className="pm-sub">loading {name}…</div></div>
        ) : (
          <>
            <div className="pm-head">
              <button className="pm-close" onClick={onClose}>✕</button>
              <h2>{data.name}</h2>
              <div className="pm-sub"><b>{(data.teams || []).join(" · ") || "—"}</b> · {scope} · {data.seasons?.length || 0} seasons played</div>
              {roleTags(data).length > 0 && (
                <div className="ptags">{roleTags(data).map((t) => <span className="ptag" key={t}>{t}</span>)}</div>
              )}
            </div>
            <div className="pm-kpis">
              {kpis.map(([l, v]) => <div className="pm-kpi" key={l}><div className="v">{v}</div><div className="l">{l}</div></div>)}
            </div>
            <div className="pm-body">
              {cards.map((c, i) => (
                <div className={`card ${c[5] ? "full" : ""}`} key={i}>
                  <div className="card-h"><span className="lbl">{c[0]}</span><span className="meta">{c[1]}</span></div>
                  <div className="chart">
                    {c[3] === "hbar"
                      ? <HBars data={pseries(c[2])} color={c[4]} />
                      : <VBars data={pseries(c[2])} color={c[4]} />}
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify the build**

Run: `cd frontend && npm run build`
Expected: exits 0.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/PlayerModal.tsx && git commit -m "feat(frontend): player drilldown modal"
```

---

### Task 13: Analyst stream hook + Ask view (`useAnalystStream.ts` + `AskView.tsx`)

**Files:**
- Create: `frontend/src/hooks/useAnalystStream.ts`
- Create: `frontend/src/components/views/AskView.tsx`

`useAnalystStream` wraps `EventSource`, accumulating an ordered list of message parts
per turn. The Ask view renders the transcript, the hint chips, the scope-toggle row,
the input bar, follow-ups, and the AI-offline notice. Markdown via npm `marked`.

The transcript model: each turn is `{ question, scoped, parts: Part[], done }`, where
`Part` is one of the streamed events (sql/chart/answer/error). New events from the SSE
append to the current (last) turn's `parts`.

- [ ] **Step 1: Create `frontend/src/hooks/useAnalystStream.ts`**

```ts
import { useRef, useState } from "react";
import { askStreamUrl } from "../api";
import { ChartSpec } from "../components/charts/AgentChart";

export type SqlPart = { type: "sql"; query: string; columns?: string[]; rows?: any[]; error?: string };
export type ChartPart = { type: "chart" } & ChartSpec;
export type AnswerPart = { type: "answer"; text: string };
export type ErrorPart = { type: "error"; text: string };
export type Part = SqlPart | ChartPart | AnswerPart | ErrorPart;

export type Turn = { question: string; scoped: string[]; parts: Part[]; done: boolean };

const newSid = () => "s" + Math.random().toString(36).slice(2) + Date.now().toString(36);

export function useAnalystStream() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [streaming, setStreaming] = useState(false);
  const sid = useRef(newSid());
  const es = useRef<EventSource | null>(null);

  const appendPart = (part: Part) =>
    setTurns((ts) => {
      if (!ts.length) return ts;
      const last = ts[ts.length - 1];
      return [...ts.slice(0, -1), { ...last, parts: [...last.parts, part] }];
    });
  const finishTurn = () =>
    setTurns((ts) => ts.length ? [...ts.slice(0, -1), { ...ts[ts.length - 1], done: true }] : ts);

  function ask(question: string, scopeParams: string[], scopedLabels: string[]) {
    if (streaming || !question.trim()) return;
    setStreaming(true);
    setTurns((ts) => [...ts, { question, scoped: scopedLabels, parts: [], done: false }]);

    const url = askStreamUrl(question, sid.current, scopeParams);
    const source = new EventSource(url);
    es.current = source;
    source.onmessage = (e) => {
      const ev = JSON.parse(e.data);
      if (ev.type === "done") {
        source.close(); setStreaming(false); finishTurn();
      } else if (ev.type === "sql" || ev.type === "chart" || ev.type === "answer" || ev.type === "error") {
        appendPart(ev as Part);
      }
    };
    source.onerror = () => { source.close(); setStreaming(false); finishTurn(); };
  }

  function newChat() {
    es.current?.close();
    sid.current = newSid();
    setTurns([]);
    setStreaming(false);
  }

  return { turns, streaming, ask, newChat };
}
```

- [ ] **Step 2: Create `frontend/src/components/views/AskView.tsx`**

```tsx
import { useEffect, useRef, useState } from "react";
import { marked } from "marked";
import { Health } from "../../api";
import { useFilters } from "../../state/FiltersContext";
import { useAnalystStream, Turn, SqlPart } from "../../hooks/useAnalystStream";
import AgentChart from "../charts/AgentChart";

const HINTS = [
  "analyze the best death-overs bowlers",
  "who hits spin the best?",
  "compare powerplay vs death run rates by team",
];
const FOLLOWUPS = ["Break this down by phase", "How does it compare across seasons?", "Show me a chart"];

export type AskHandle = { ask: (q: string) => void };

export default function AskView({ active, health, registerAsk }: {
  active: boolean; health: Health | null; registerAsk: (fn: (q: string) => void) => void;
}) {
  const { scopeOn, setScopeOn, activeFilters, scopeParams } = useFilters();
  const { turns, streaming, ask, newChat } = useAnalystStream();
  const [input, setInput] = useState("");
  const transcriptRef = useRef<HTMLDivElement>(null);
  const offline = health ? !health.has_key : false;

  const submit = (q: string) => {
    const labels = scopeOn ? activeFilters() : [];
    ask(q, scopeOn ? scopeParams() : [], labels);
  };

  // expose submit to the parent (KPI clicks switch to Ask and fire a question)
  useEffect(() => { registerAsk(submit); });

  // autoscroll
  useEffect(() => {
    const t = transcriptRef.current; if (t) t.scrollTop = t.scrollHeight;
  }, [turns]);

  if (!active) return null;
  const act = activeFilters();

  return (
    <section className="view is-active">
      <div className="console">
        <div className="console-h">
          <span className="lbl">Ask the Analyst</span>
          <span className="console-sub">investigates with live SQL &amp; charts · remembers your thread for follow-ups</span>
          <button className="newchat" type="button" onClick={newChat}>+ New chat</button>
        </div>
        <div className="transcript" ref={transcriptRef}>
          {offline && (
            <div className="ai-offline">⚠ <b>AI analyst offline.</b> Set <code>OPENROUTER_API_KEY</code> in <code>.env</code> and restart the server to ask questions. Every dashboard panel still works without it.</div>
          )}
          {turns.length === 0 ? (
            <div className="hint">
              <p>Type a question and watch it work. Try:</p>
              <div className="chips">
                {HINTS.map((h) => <button className="chip-q" key={h} onClick={() => submit(h)}>{h}</button>)}
              </div>
            </div>
          ) : turns.map((turn, i) => <TurnView key={i} turn={turn} streaming={streaming && i === turns.length - 1} onFollowup={submit} />)}
        </div>
        {act.length > 0 && (
          <div className={`scope-row${scopeOn ? " is-on" : ""}`}>
            <button className={`scope-toggle${scopeOn ? " on" : ""}`} type="button" onClick={() => setScopeOn(!scopeOn)}>
              <span className="sw" />{scopeOn ? "Scoped to filters" : "Scope to filters"}
            </button>
            <span className="scope-sum">{scopeOn ? "agent will apply — " + act.join(" · ") : "off · asking across all data"}</span>
          </div>
        )}
        <form className="ask-bar" onSubmit={(e) => { e.preventDefault(); submit(input); setInput(""); }}>
          <span className="caret">▸</span>
          <input autoComplete="off"
            placeholder={offline ? "AI analyst offline — set OPENROUTER_API_KEY in .env" : "Ask anything about IPL 2026…"}
            value={input} onChange={(e) => setInput(e.target.value)} />
          <button type="submit" disabled={streaming}>ANALYZE</button>
        </form>
      </div>
    </section>
  );
}

function TurnView({ turn, streaming, onFollowup }: { turn: Turn; streaming: boolean; onFollowup: (q: string) => void }) {
  return (
    <>
      <div className="msg user"><div className="bubble">{turn.question}</div></div>
      <div className="msg bot">
        {turn.scoped.length > 0 && <div className="scoped-badge">⦿ scoped · {turn.scoped.join(" · ")}</div>}
        {turn.parts.map((p, i) => {
          if (p.type === "sql") return <SqlStep key={i} part={p} />;
          if (p.type === "chart") return <AgentChart key={i} spec={p} />;
          if (p.type === "answer") return <div key={i} className="prose" dangerouslySetInnerHTML={{ __html: marked.parse(p.text || "") as string }} />;
          if (p.type === "error") return (
            <div key={i} className="agent-error"><b>⚠ analyst error</b><span>{p.text || "Something went wrong."}</span></div>
          );
          return null;
        })}
        {streaming && <div className="thinking"><i /><i /><i /> investigating</div>}
        {turn.done && (
          <div className="followups">
            {FOLLOWUPS.map((t) => <button className="fu" key={t} onClick={() => onFollowup(t)}>{t}</button>)}
          </div>
        )}
      </div>
    </>
  );
}

function SqlStep({ part }: { part: SqlPart }) {
  const cols = part.error ? "" : (part.rows?.length ? `${part.rows.length}+ rows · ${(part.columns || []).join(", ")}` : "0 rows");
  return (
    <details className="step">
      <summary><span className="q">◢ query</span> <span style={{ color: "var(--mute2)" }}>{cols}</span></summary>
      <pre>{part.query}</pre>
      {part.error && <div className="rowsmini" style={{ color: "var(--pink)" }}>{part.error}</div>}
    </details>
  );
}
```

> **Parity note:** The original shows the "investigating" dots while streaming and
> appends follow-up chips after `done`. `TurnView` reproduces both. The follow-up
> chips are static text (same three) matching the original.

- [ ] **Step 3: Verify the build**

Run: `cd frontend && npm run build`
Expected: exits 0.

- [ ] **Step 4: Commit**

```bash
git add frontend/src && git commit -m "feat(frontend): analyst stream hook + ask console"
```

---

### Task 14: Assemble `App.tsx` and wire everything together

**Files:**
- Modify: `frontend/src/App.tsx`

App owns: filter options (`getFilters`), health (`getHealth`), dashboard data
(`useDashboard`), the active view (from context), the player-modal target, and the
bridge that lets a KPI click switch to Ask and fire a templated question.

- [ ] **Step 1: Replace `frontend/src/App.tsx`**

```tsx
import { useEffect, useRef, useState } from "react";
import { Filters, Health, getFilters, getHealth } from "./api";
import { useFilters } from "./state/FiltersContext";
import { useDashboard } from "./hooks/useDashboard";
import Background from "./components/Background";
import Topbar from "./components/Topbar";
import Hero from "./components/Hero";
import Footer from "./components/Footer";
import FilterDeck from "./components/FilterDeck";
import KpiTicker from "./components/KpiTicker";
import Nav from "./components/Nav";
import OverviewView from "./components/views/OverviewView";
import BattingView from "./components/views/BattingView";
import BowlingView from "./components/views/BowlingView";
import TeamsView from "./components/views/TeamsView";
import InsightsView from "./components/views/InsightsView";
import MatchupsView from "./components/views/MatchupsView";
import AskView from "./components/views/AskView";
import PlayerModal from "./components/PlayerModal";

export default function App() {
  const { state, activeView, setActiveView } = useFilters();
  const data = useDashboard(state);
  const [filters, setFilters] = useState<Filters | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [player, setPlayer] = useState<string | null>(null);
  const askFn = useRef<((q: string) => void) | null>(null);

  useEffect(() => { getFilters().then(setFilters).catch((e) => console.error(e)); }, []);
  useEffect(() => { getHealth().then(setHealth).catch(() => {}); }, []);

  const onExplain = (label: string, value: number) => {
    setActiveView("ask");
    const scope = state.season === "All" ? "all-time" : "season " + state.season;
    const extra = (state.team !== "All" ? ", " + state.team : "") +
      (state.phase !== "All" ? ", " + state.phase + " overs" : "");
    const q = `Explain the ${label} figure (${value}) for ${scope}${extra} — how it's computed and what stands out.`;
    // defer until AskView has registered its handler / mounted
    setTimeout(() => askFn.current?.(q), 0);
  };

  const isActive = (v: string) => activeView === v;

  return (
    <>
      <Background />
      <Topbar matches={data?.kpis.matches ?? ""} />
      <main className="wrap">
        <Hero />
        <FilterDeck filters={filters} />
        {data && <KpiTicker kpis={data.kpis} onExplain={onExplain} />}
        <Nav active={activeView} onSwitch={setActiveView} />

        {data && <OverviewView active={isActive("overview")} data={data} onPlayer={setPlayer} />}
        {data && <BattingView active={isActive("batting")} data={data} onPlayer={setPlayer} />}
        {data && <BowlingView active={isActive("bowling")} data={data} onPlayer={setPlayer} />}
        {data && <TeamsView active={isActive("teams")} data={data} />}
        <InsightsView active={isActive("insights")} />
        <MatchupsView active={isActive("matchups")} />
        <AskView active={isActive("ask")} health={health} registerAsk={(fn) => { askFn.current = fn; }} />

        <Footer />
      </main>
      {player && <PlayerModal name={player} season={state.season} onClose={() => setPlayer(null)} />}
    </>
  );
}
```

> **Parity note on KPI → Ask:** AskView is only mounted when `active`. `onExplain`
> first switches to Ask (mounting AskView, which registers its `ask` via
> `registerAsk`), then defers the call with `setTimeout(…, 0)` so the handler exists.
> This matches the original's `switchView("ask"); ask(...)` ordering.

- [ ] **Step 2: Verify the build**

Run: `cd frontend && npm run build`
Expected: exits 0.

- [ ] **Step 3: Manual parity check against the running app**

Start both servers:
```bash
# terminal 1 (repo root)
uv run python server.py
# terminal 2
cd frontend && npm run dev
```
Open the Vite URL (e.g. http://localhost:5173) and verify against http://localhost:8765:
  - Hero/topbar season branding; KPI count-up; clicking a KPI jumps to Ask and asks.
  - All 8 filters + min-balls slider re-query the dashboard; active chips + reset work.
  - Each nav tab renders the same charts; the nav-ink underline slides; insights loads.
  - Player names open the drilldown modal (Esc + backdrop close); CSV download works.
  - Matchups compare returns stats / the not-found note.
  - Ask streams SQL steps, charts, and the markdown answer; follow-ups + new chat work;
    AI-offline notice shows when `OPENROUTER_API_KEY` is unset.
  - URL hash reflects non-default filters + non-overview view and restores on reload.

Expected: behavior matches the vanilla app.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/App.tsx && git commit -m "feat(frontend): assemble App and wire all views"
```

---

## Self-Review

**Spec coverage:**
- Vite standalone dev + `/api` proxy → Task 1 (vite.config). ✓
- TypeScript → Task 1 (tsconfig) + typed `api.ts` Task 2. ✓
- Reuse styles.css verbatim → Task 1 Step 7. ✓
- FiltersContext + URL-hash + scope → Task 3. ✓
- useDashboard / useInsights / useAnalystStream → Tasks 9 / 10 / 13. ✓
- All chart kinds (hbar/vbar/donut/duel/scatter/agentchart) → Task 5. ✓
- Card shell + CSV download → Task 5. ✓
- 7 nav tabs + sliding ink + reveal animations → Tasks 8 + useReveal Task 5. ✓
- KPI ticker + count-up + click-to-Ask → Task 7 + App Task 14. ✓
- Player modal (role tags, KPIs, per-player charts) → Task 12. ✓
- Matchups → Task 11. ✓
- Ask console (SSE events, offline notice, scope row, follow-ups, markdown) → Task 13. ✓
- marked via npm (user-confirmed) → Task 1 package.json + Task 13 import. ✓
- No backend changes → no task touches Python. ✓

**Placeholder scan:** No TBD/TODO; every code step contains complete code. ✓

**Type consistency:** `Series`, `FilterState`, `Dashboard`, `Player`, `Insights`,
`Matchup`, `ChartSpec`, `Part`/`Turn` are defined once (api.ts / hooks) and reused.
`useFilters()` shape matches its consumers. `onPlayer`/`onExplain`/`registerAsk`
callback signatures match between definition and call sites. ✓

**Known intentional deviations from vanilla (behavior preserved):**
- `marked` is an npm import rather than a CDN global.
- The reveal animation is driven by a `useReveal` hook keyed on data instead of the
  imperative `animateView` call after each render — same visual result.
- Inactive views return `null` (unmounted) rather than CSS `display:none`; the
  `.view.is-active` class is always present on rendered views, so the reveal animation
  still fires on switch. (If a parity issue appears with the view-in transition, render
  all views and toggle `is-active`; not expected to be needed.)
