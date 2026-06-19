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
