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
