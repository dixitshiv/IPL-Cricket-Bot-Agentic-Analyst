# React Frontend Migration — Design

**Date:** 2026-06-19
**Status:** Approved (design); pending spec review

## Goal

Rewrite the existing vanilla-JS web frontend (`web/index.html` + `web/styles.css` +
`web/app.js`) as a React + TypeScript application, keeping the **design, layout, and
functionality identical**. Nothing changes on the Python/FastAPI side or in the
`/api/*` contract.

## Non-goals

- No visual or layout changes — the result must look and behave the same.
- No backend changes (`server.py`, `ask.py`, views, endpoints all untouched).
- No new features, no removed features.
- The existing `web/` folder stays in place and untouched.

## Decisions (confirmed with user)

- **Build tooling:** Vite + React, **standalone dev only**. Run the React dev
  server separately; do not change how FastAPI serves files. A Vite dev proxy
  forwards `/api` → `http://localhost:8765` so fetches and the SSE stream work in
  development. A production build (`npm run build`) is available but wiring it into
  FastAPI is out of scope for this task.
- **Language:** TypeScript.
- **Styling:** Reuse the existing `styles.css` verbatim — copied into the React app
  and imported once globally. Same class names and DOM structure guarantee a
  pixel-identical result.
- **State management:** React Context + hooks. No state library.

## Architecture

New `frontend/` directory (the existing `web/` is left untouched):

```
frontend/
  package.json
  tsconfig.json
  vite.config.ts            # dev server proxy: /api -> http://localhost:8765
  index.html                # mounts #root; keeps Google Fonts + marked CDN <link>/<script>
  src/
    main.tsx                # ReactDOM root
    App.tsx                 # composes the page; owns active-view + modal state
    styles.css              # existing file, copied verbatim, imported once in main.tsx
    api.ts                  # typed fetch wrappers + response types for every /api/* endpoint
    types.ts                # shared TypeScript types (or co-located in api.ts)
    state/
      FiltersContext.tsx    # filter state + setters; owns URL-hash read/write; scope toggle
    hooks/
      useDashboard.ts       # fetches /api/dashboard when filters change -> dashboard data
      useInsights.ts        # fetches /api/insights for the Insights view
      useAnalystStream.ts   # wraps EventSource for /api/ask; parses SSE events into messages
      useReveal.ts          # replays the grow-in chart animations when a view becomes active
    components/
      Background.tsx        # the fixed .bg atmosphere layers
      Topbar.tsx
      Hero.tsx              # season branding (year, mark, kicker)
      FilterDeck.tsx        # the 9 filter controls + reset + active chips
      KpiTicker.tsx         # 5 KPIs with count-up animation; click -> Ask
      Nav.tsx               # 7 tabs + sliding nav-ink indicator
      Footer.tsx
      PlayerModal.tsx       # player drilldown overlay (portal)
      views/
        OverviewView.tsx
        BattingView.tsx
        BowlingView.tsx
        TeamsView.tsx
        InsightsView.tsx
        MatchupsView.tsx
        AskView.tsx         # analyst console
      charts/
        Card.tsx            # bento card shell (header, CSV download button, hover)
        HBars.tsx
        VBars.tsx
        Donut.tsx
        Duel.tsx
        Scatter.tsx
        AgentChart.tsx      # inline chart rendered from an agent chart spec
```

## Components & responsibilities

Each unit has one clear purpose and a well-defined interface (props / context).

- **FiltersContext** — holds the filter `state` object (same shape and `DEFAULTS` as
  today: `season, team, opponent, venue, innings, phase, bowltype, bathand,
  min_balls`), exposes setters, a `reset()`, a `clearFilter(key)`, the `scopeOn`
  toggle, and derived helpers (`activeFilters()`, the query string). It reads the
  URL hash on mount and writes it back (via `history.replaceState`) whenever filters
  or the active view change — preserving the shareable-URL behavior. Active view is
  passed in so the hash can include it.
- **useDashboard** — given the current filter state, fetches `/api/dashboard?...` and
  returns the `DATA` object (kpis + per-chart series). Re-fetches when filters
  change. Exposes loading state.
- **useInsights** — fetches `/api/insights?season=...` for the scatter/venues view;
  fetched when the Insights view is first shown (mirrors today's lazy `loadInsights`).
- **useAnalystStream** — opens an `EventSource` for `/api/ask?q=...&sid=...` (plus
  scope params when `scopeOn`), accumulates a list of streamed message parts
  (`sql`, `chart`, `answer`, `error`) into React state, and closes on `done`/error.
  Owns the `sid` (session id) and `streaming` flag, exposes `ask(question)`,
  `messages`, `newChat()`.
- **Chart components** — pure presentational components that render the **same
  SVG/CSS markup** the current functions emit (`hbars`, `vbars`, `donut`, `duel`,
  `scatter`, `agentChart`). They take typed data props and a color. Player-name
  cells in `HBars` get the clickable `.nm.pl` treatment and call an `onPlayer`
  callback to open the modal.
- **Card** — the bento card shell: title + meta header and the CSV-download button
  (same `downloadCSV` logic). Wraps a chart component chosen by the card's kind.
- **KpiTicker** — renders the 5 KPI cells, runs the count-up animation on mount /
  data change, and on click switches to the Ask view and fires a templated question.
- **Nav** — renders the 7 buttons, tracks the active view, and positions the
  `nav-ink` underline (measuring the active button's offset/width, re-measured on
  resize). Lazy-triggers insights load when switching to Insights.
- **PlayerModal** — a portal overlay; fetches `/api/player?name=...&season=...`,
  renders KPIs + role tags + the per-player chart cards, closes on backdrop click
  and Escape.
- **AskView** — the console: hint chips, transcript (rendered from
  `useAnalystStream` messages), scope-toggle row, input bar, follow-up chips, and
  the AI-offline notice driven by `/api/health`. Markdown rendered with the global
  `marked` from the CDN.
- **api.ts** — one module with typed wrappers: `getFilters()`, `getDashboard(state)`,
  `getPlayer(name, season)`, `getInsights(season)`, `getMatchup(batter, bowler,
  season)`, `getHealth()`, and `askStreamUrl(question, sid, scopeParams)`. Defines
  the response types so views/charts consume typed data.

## Data flow

1. `App` mounts inside `FiltersProvider`. `api.getFilters()` populates the filter
   dropdown options.
2. `FiltersContext` reads the URL hash to seed filter state + start view.
3. `useDashboard` fetches `/api/dashboard` for the current state; `App`/views render
   cards from the returned `DATA`. Changing a filter updates context → re-fetch →
   re-render. The active-filter chips and the scope row update from context.
4. Switching to Insights triggers `useInsights`. Switching to a view replays its
   reveal animation via `useReveal`.
5. Clicking a player name opens `PlayerModal`, which fetches `/api/player`.
6. In Ask, submitting a question calls `useAnalystStream.ask()`, which opens the SSE
   connection and streams message parts into the transcript.

## Error handling

- `/api/health` is best-effort: if `has_key` is false, the Ask view shows the
  offline notice and disables/relabels the input — never blocks the rest of the UI.
- SSE `error` events render an inline analyst-error block; `EventSource.onerror`
  closes the stream and re-enables the input (same as today).
- Empty chart data renders the "no data for this filter" placeholder (same copy).
- Matchup with no balls renders the existing "No balls found…" note.
- Fetch failures in `getFilters`/`getDashboard` should fail visibly but not crash the
  app (basic try/catch with a console error, matching current best-effort behavior).

## Testing

The current repo has no frontend tests (only Python tests). To keep scope tight and
match the existing project, **no automated frontend test suite is added**. Validation
is manual and by parity:

- Run FastAPI (`uv run python server.py`) and the Vite dev server; confirm each view,
  filter, the KPI count-up, player modal, matchups, CSV download, URL-hash sharing,
  and the streaming analyst all behave identically to the vanilla version.
- `tsc --noEmit` and `vite build` must pass clean (type-check + production build).

(If the user later wants component tests, Vitest + React Testing Library would be the
natural fit, but that is out of scope here.)

## What stays identical by construction

Same `styles.css`, same class names, same DOM structure, same `/api/*` contract,
same animations, same URL-hash behavior, same session/SSE semantics. The Python side
does not change.
