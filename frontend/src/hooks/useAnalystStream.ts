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
