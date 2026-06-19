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
