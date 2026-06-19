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
