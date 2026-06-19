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
