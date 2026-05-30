// IPL 2026 · Command Center — frontend logic
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const PALETTE = { lime: "#C6FF3A", cyan: "#34E7FF", pink: "#FF4D9D", amber: "#FFC14D", violet: "#A78BFA" };

const DEFAULTS = { season: "2026", team: "All", opponent: "All", venue: "All", innings: "All", phase: "All", bowltype: "All", bathand: "All", min_balls: 30 };
const state = { ...DEFAULTS };
const FLABEL = { team: "Team", opponent: "vs", venue: "Venue", innings: "Innings", phase: "Phase", bowltype: "Vs", bathand: "Hand" };
let DATA = null;

function applySeasonBranding() {
  const s = state.season, label = s === "All" ? "ALL-TIME" : s;
  $("#hero-year").textContent = s === "All" ? "ALL‑TIME" : s;
  $("#hero-mark").textContent = s === "All" ? "∞" : s;
  $("#kicker-txt").textContent = `${s === "All" ? "ALL SEASONS" : "SEASON " + s} · LIVE INTELLIGENCE`;
  const m = DATA?.kpis?.matches ?? "";
  $("#top-meta").innerHTML = `IPL ${label} · ${m} MATCHES · <span>LIVE</span>`;
}

// ── shareable URL state (filters + active view live in the hash) ──
function updateHash() {
  const parts = [];
  for (const k of Object.keys(DEFAULTS)) if (state[k] !== DEFAULTS[k]) parts.push(`${k}=${encodeURIComponent(state[k])}`);
  const view = $(".nav-btn.is-active")?.dataset.view;
  if (view && view !== "overview") parts.push(`view=${view}`);
  history.replaceState(null, "", parts.length ? "#" + parts.join("&") : location.pathname + location.search);
}
function applyHash() {
  const h = location.hash.slice(1), o = {};
  if (h) h.split("&").forEach((p) => { const [k, v] = p.split("="); if (k) o[k] = decodeURIComponent(v || ""); });
  for (const k of Object.keys(DEFAULTS)) if (o[k] != null) state[k] = k === "min_balls" ? +o[k] : o[k];
  Object.keys(FLABEL).forEach((k) => { const el = $("#f-" + k); if (el) el.value = state[k]; });
  if ($("#f-season")) $("#f-season").value = state.season;
  $("#f-minballs").value = state.min_balls; $("#mb-val").textContent = state.min_balls;
  return o.view;
}

// ───────────────────────── helpers ─────────────────────────
const fmt = (n) => n >= 1000 ? n.toLocaleString("en-US") : `${n}`;
async function getJSON(url) { const r = await fetch(url); return r.json(); }

function countUp(el, target, decimals = 0) {
  const dur = 950, t0 = performance.now();
  const ease = (t) => 1 - Math.pow(1 - t, 3);
  function step(now) {
    const p = Math.min(1, (now - t0) / dur), v = target * ease(p);
    el.textContent = decimals ? v.toFixed(decimals) : fmt(Math.round(v));
    if (p < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

// ───────────────────────── KPI ticker ─────────────────────────
function renderKPIs(k) {
  const cells = [
    [k.matches, "Matches", 0], [k.runs, "Runs", 0], [k.wickets, "Wickets", 0],
    [k.sixes, "Sixes", 0], [k.run_rate, "Run Rate", 2],
  ];
  const t = $("#ticker");
  t.innerHTML = cells.map(([, l]) =>
    `<div class="kpi"><div class="v">0</div><div class="l">${l}</div><div class="tick"></div></div>`).join("");
  $$(".kpi", t).forEach((kpi, i) => {
    countUp($(".v", kpi), cells[i][0], cells[i][2]);
    kpi.style.cursor = "pointer";
    kpi.title = "Explain this number";
    kpi.onclick = () => {
      const [val, lab] = cells[i];
      switchView("ask");
      ask(`Explain the ${lab} figure (${val}) for ${state.season === "All" ? "all-time" : "season " + state.season}${state.team !== "All" ? ", " + state.team : ""}${state.phase !== "All" ? ", " + state.phase + " overs" : ""} — how it's computed and what stands out.`);
    };
  });
}

// ───────────────────────── chart renderers ─────────────────────────
function hbars(el, data, color = "lime", clickable = false) {
  if (!data.length) { el.innerHTML = `<div class="rowsmini">no data for this filter</div>`; return; }
  const max = Math.max(...data.map((d) => d.value)) || 1;
  el.innerHTML = `<div class="hbars">${data.map((d, i) => {
    const nm = d.player ?? "—", e = String(nm).replace(/"/g, "&quot;");
    return `<div class="hbar c-${color}">
      <span class="rk">${String(i + 1).padStart(2, "0")}</span>
      <span class="nm${clickable ? " pl" : ""}" data-player="${e}" title="${e}">${nm}</span>
      <div class="track"><div class="fill" data-w="${Math.max(2, (d.value / max) * 100)}%"></div></div>
      <span class="val">${d.value ?? "—"}</span>
    </div>`;
  }).join("")}</div>`;
}

const PHASE_ORDER = { powerplay: 0, middle: 1, death: 2 };
function vbars(el, data, color = "lime") {
  if (data.some((d) => d.phase)) data = [...data].sort((a, b) => (PHASE_ORDER[a.phase] ?? 9) - (PHASE_ORDER[b.phase] ?? 9));
  const max = Math.max(...data.map((d) => d.value)) || 1;
  el.innerHTML = `<div class="vbars c-${color}">${data.map((d) => `
    <div class="vbar c-${color}">
      <div class="col" data-h="${(d.value / max) * 100}%"><span class="vv">${d.value}</span></div>
      <span class="vl">${d.label ?? d.phase}</span>
    </div>`).join("")}</div>`;
}

function duel(el, data) {
  const total = data.reduce((s, d) => s + d.value, 0) || 1;
  const bf = data.find((d) => d.label === "Bat First") || { value: 0 };
  const ch = data.find((d) => d.label === "Chasing") || { value: 0 };
  el.innerHTML = `<div class="duel">
    <div class="side bat"><div class="big">${bf.value}</div><div class="pct">${(bf.value / total * 100).toFixed(0)}% of decided</div><div class="cap">Bat First wins</div></div>
    <div class="side chase"><div class="big">${ch.value}</div><div class="pct">${(ch.value / total * 100).toFixed(0)}% of decided</div><div class="cap">Chasing wins</div></div>
  </div>`;
}

function donut(el, data) {
  const colors = [PALETTE.lime, PALETTE.cyan, PALETTE.pink, PALETTE.amber];
  const order = { powerplay: 0, middle: 1, death: 2 };
  data = [...data].sort((a, b) => (order[a.phase] ?? 9) - (order[b.phase] ?? 9));
  const total = data.reduce((s, d) => s + d.value, 0) || 1;
  const R = 52, C = 2 * Math.PI * R; let off = 0;
  const segs = data.map((d, i) => {
    const len = (d.value / total) * C, s = `<circle class="seg" r="${R}" cx="64" cy="64" fill="none"
      stroke="${colors[i]}" stroke-width="15" stroke-dasharray="${len} ${C - len}"
      stroke-dashoffset="${-off}" data-dash="${len} ${C - len}"></circle>`;
    off += len; return s;
  }).join("");
  el.innerHTML = `<div class="donut">
    <div class="donut-wrap">
      <svg width="128" height="128" viewBox="0 0 128 128">
        <circle r="${R}" cx="64" cy="64" fill="none" stroke="rgba(255,255,255,.05)" stroke-width="15"></circle>${segs}
      </svg>
      <div class="donut-ctr"><b>${fmt(total)}</b><span>runs</span></div>
    </div>
    <div class="legend">${data.map((d, i) => `<div class="lg"><span class="dot" style="background:${colors[i]}"></span>${d.phase}<b>${(d.value / total * 100).toFixed(0)}%</b></div>`).join("")}</div>
  </div>`;
}

function scatter(el, points, opts = {}) {
  if (!points.length) { el.innerHTML = `<div class="rowsmini">not enough data for this scope</div>`; return; }
  const W = 540, H = 340, pad = 46;
  const xs = points.map((p) => p.x), ys = points.map((p) => p.y);
  const xmin = Math.min(...xs), xmax = Math.max(...xs), ymin = Math.min(...ys), ymax = Math.max(...ys);
  const px = (v) => pad + (v - xmin) / ((xmax - xmin) || 1) * (W - pad - 14);
  const py = (v) => H - pad - (v - ymin) / ((ymax - ymin) || 1) * (H - pad - 16);
  const col = opts.color || PALETTE.lime;
  const dots = points.map((p) => `<circle cx="${px(p.x).toFixed(1)}" cy="${py(p.y).toFixed(1)}" r="5" fill="${col}" opacity=".82"><title>${p.player} — ${opts.xlabel}: ${p.x}, ${opts.ylabel}: ${p.y}</title></circle>`).join("");
  const top = [...points].sort((a, b) => b.y - a.y).slice(0, 6);
  const labels = top.map((p) => `<text x="${(px(p.x) + 7).toFixed(1)}" y="${(py(p.y) + 3).toFixed(1)}" fill="#AEB8A2" font-size="9" font-family="IBM Plex Mono">${p.player}</text>`).join("");
  el.innerHTML = `<svg class="scatter" viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid meet">
    <line x1="${pad}" y1="${H - pad}" x2="${W - 6}" y2="${H - pad}" stroke="rgba(255,255,255,.13)"/>
    <line x1="${pad}" y1="6" x2="${pad}" y2="${H - pad}" stroke="rgba(255,255,255,.13)"/>
    <text x="${W - 6}" y="${H - pad + 22}" fill="#86927C" font-size="9" font-family="IBM Plex Mono" text-anchor="end">${opts.xlabel} →</text>
    <text x="${pad - 8}" y="14" fill="#86927C" font-size="9" font-family="IBM Plex Mono">↑ ${opts.ylabel}</text>
    ${dots}${labels}</svg>`;
}

async function loadInsights() {
  const d = await getJSON(`/api/insights?season=${encodeURIComponent(state.season)}`);
  scatter($("#ins-bowlers .chart"), d.bowlers, { xlabel: "economy", ylabel: "wickets", color: PALETTE.cyan });
  scatter($("#ins-batters .chart"), d.batters, { xlabel: "average", ylabel: "strike rate", color: PALETTE.lime });
  hbars($("#ins-venues .chart"), d.venues, "amber");
}

async function runMatchup() {
  const batter = $("#mu-batter").value.trim(), bowler = $("#mu-bowler").value.trim();
  if (!batter || !bowler) return;
  const res = $("#mu-result"); res.innerHTML = `<div class="rowsmini">crunching…</div>`;
  const d = await getJSON(`/api/matchup?batter=${encodeURIComponent(batter)}&bowler=${encodeURIComponent(bowler)}&season=${encodeURIComponent(state.season)}`);
  if (!d.found) { res.innerHTML = `<div class="mu-note">No balls found between <b>${d.batter}</b> and <b>${d.bowler}</b>${state.season !== "All" ? " in " + state.season : ""}. Try other spellings, or set Season to <b>All seasons</b>.</div>`; return; }
  const s = d.stats;
  const kpis = [["Balls", s.balls], ["Runs", s.runs], ["Strike Rate", s.sr], ["Dismissals", s.dismissals], ["Sixes", s.sixes], ["Fours", s.fours], ["Dot %", s.dot + "%"]];
  res.innerHTML = `<div class="mu-head"><b>${d.batter}</b><span class="vs">vs</span>${d.bowler}</div>
    <div class="mu-note">${d.season === "All" ? "All-time head-to-head" : "Season " + d.season}</div>
    <div class="mu-kpis">${kpis.map(([l, v]) => `<div class="pm-kpi"><div class="v">${v}</div><div class="l">${l}</div></div>`).join("")}</div>`;
}

function downloadCSV(name, data) {
  if (!data?.length) return;
  const cols = Object.keys(data[0]);
  const csv = [cols.join(","), ...data.map((r) => cols.map((c) => `"${String(r[c] ?? "").replace(/"/g, '""')}"`).join(","))].join("\n");
  const url = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
  const a = document.createElement("a"); a.href = url; a.download = `${name}_${state.season}.csv`; a.click();
  URL.revokeObjectURL(url);
}

function renderCard(card) {
  const key = card.dataset.chart, type = card.dataset.type || "hbar";
  const color = card.dataset.color || "lime";
  const el = $(".chart", card), data = DATA[key] || [];
  if (Array.isArray(data) && data.length && !$(".dl", card)) {
    const btn = document.createElement("button");
    btn.className = "dl"; btn.title = "Download CSV"; btn.textContent = "⤓";
    btn.onclick = (e) => { e.stopPropagation(); downloadCSV(key, DATA[key]); };
    card.appendChild(btn);
  }
  if (type === "donut") donut(el, data);
  else if (type === "vbar") vbars(el, data, color);
  else if (type === "duel") duel(el, data);
  else hbars(el, data, color, !key.startsWith("team"));
}

// ───────────────────────── player drilldown ─────────────────────────
const pseries = (arr) => (arr || []).map((r) => ({ player: r.player, label: r.player, phase: r.player, value: r.value }));

function openPlayer(name) {
  $("#pmodal").hidden = false;
  $("#pmodal-card").innerHTML = `<div class="pm-head"><div class="pm-sub">loading ${name}…</div></div>`;
  getJSON(`/api/player?name=${encodeURIComponent(name)}&season=${encodeURIComponent(state.season)}`).then(renderPlayer);
}
function closePlayer() { $("#pmodal").hidden = true; }

function roleTags(d) {
  const b = d.batting || {}, tags = [], ph = {};
  (d.sr_by_phase || []).forEach((r) => (ph[r.player] = r.value));
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

function renderPlayer(d) {
  const b = d.batting || {}, w = d.bowling || {};
  const scope = d.season === "All" ? "All-time / career" : `Season ${d.season}`;
  const kpis = [["Runs", b.runs ?? "—"], ["Strike Rate", b.sr ?? "—"], ["Average", b.bat_avg ?? "—"],
    ["Sixes", b.sixes ?? "—"], ["Dot %", b.dot != null ? b.dot + "%" : "—"]];
  if (d.is_bowler) kpis.push(["Wickets", w.wickets ?? "—"], ["Economy", w.econ ?? "—"]);

  const cards = [
    ["Runs by Season", "career", d.runs_by_season, "vbar", "lime", true],
    ["Strike Rate by Phase", scope, d.sr_by_phase, "vbar", "cyan", false],
    ["Strike Rate vs Pace / Spin", scope, d.sr_vs_type, "vbar", "pink", false],
    ["Runs by Venue", scope, d.runs_by_venue, "hbar", "amber", false]];
  if (d.is_bowler) cards.push(
    ["Wickets by Season", "career", d.wkts_by_season, "vbar", "lime", true],
    ["Economy by Season", "career", d.econ_by_season, "vbar", "cyan", true]);

  $("#pmodal-card").innerHTML = `
    <div class="pm-head">
      <button class="pm-close" id="pm-close">✕</button>
      <h2>${d.name}</h2>
      <div class="pm-sub"><b>${(d.teams || []).join(" · ") || "—"}</b> · ${scope} · ${d.seasons?.length || 0} seasons played</div>
      ${roleTags(d).length ? `<div class="ptags">${roleTags(d).map((t) => `<span class="ptag">${t}</span>`).join("")}</div>` : ""}
    </div>
    <div class="pm-kpis">${kpis.map(([l, v]) => `<div class="pm-kpi"><div class="v">${v}</div><div class="l">${l}</div></div>`).join("")}</div>
    <div class="pm-body">${cards.map((c, i) => `<div class="card ${c[5] ? "full" : ""}" data-i="${i}"><div class="card-h"><span class="lbl">${c[0]}</span><span class="meta">${c[1]}</span></div><div class="chart"></div></div>`).join("")}</div>`;

  const body = $(".pm-body");
  cards.forEach((c, i) => {
    const el = $(`.card[data-i="${i}"] .chart`, body);
    if (c[3] === "hbar") hbars(el, pseries(c[2]), c[4]);
    else vbars(el, pseries(c[2]), c[4]);
  });
  $("#pm-close").onclick = closePlayer;
  animateView($("#pmodal-card"));
}

function renderDashboard() {
  renderKPIs(DATA.kpis);
  applySeasonBranding();
  $$(".qual").forEach((q) => q.textContent = `min ${state.min_balls} balls`);
  $$(".card").forEach(renderCard);
  animateView($(".view.is-active"));
}

// ───────────────────────── animation on reveal ─────────────────────────
function animateView(view) {
  if (!view) return;
  $$(".fill", view).forEach((f, i) => {
    const w = f.dataset.w; f.style.width = "0";
    setTimeout(() => requestAnimationFrame(() => (f.style.width = w)), 40 + i * 35);
  });
  $$(".col", view).forEach((c, i) => {
    const h = c.dataset.h; c.style.height = "0";
    setTimeout(() => requestAnimationFrame(() => (c.style.height = h)), 60 + i * 60);
  });
  $$(".seg", view).forEach((s, i) => {
    const dash = s.getAttribute("stroke-dasharray").split(" ")[0];
    s.style.strokeDasharray = `0 9999`;
    setTimeout(() => { s.style.transition = "stroke-dasharray 1.1s cubic-bezier(.2,.7,.2,1)"; s.style.strokeDasharray = s.dataset.dash; }, 120 + i * 140);
  });
}

// ───────────────────────── nav ─────────────────────────
function moveInk(btn) {
  const ink = $("#nav-ink");
  ink.style.left = btn.offsetLeft + "px";
  ink.style.width = btn.offsetWidth + "px";
}
function switchView(name) {
  $$(".nav-btn").forEach((b) => b.classList.toggle("is-active", b.dataset.view === name));
  $$(".view").forEach((v) => v.classList.toggle("is-active", v.id === `view-${name}`));
  moveInk($(`.nav-btn[data-view="${name}"]`));
  animateView($(`#view-${name}`));
  if (name === "insights") loadInsights();
  updateHash();
}

// ───────────────────────── data load ─────────────────────────
async function loadDashboard() {
  const qs = Object.entries(state).map(([k, v]) => `${k}=${encodeURIComponent(v)}`).join("&");
  DATA = await getJSON(`/api/dashboard?${qs}`);
  renderDashboard();
  renderChips();
  updateHash();
  if ($("#view-insights").classList.contains("is-active")) loadInsights();
}

function renderChips() {
  const box = $("#chips-active"), chips = [];
  for (const [k, label] of Object.entries(FLABEL)) {
    if (state[k] !== "All") {
      const disp = k === "innings" ? (state[k] === "1" ? "1st" : "2nd") : state[k];
      chips.push(`<span class="fchip">${label} <b>${disp}</b><button data-k="${k}">×</button></span>`);
    }
  }
  if (state.min_balls !== 30) chips.push(`<span class="fchip">Min <b>${state.min_balls} balls</b><button data-k="min_balls">×</button></span>`);
  box.innerHTML = chips.join("");
  $$("button", box).forEach((b) => b.onclick = () => clearFilter(b.dataset.k));
  updateScopeRow();
}

function activeFilters() {
  const out = [];
  if (state.season !== "2026") out.push(`Season ${state.season === "All" ? "all-time" : state.season}`);
  for (const [k, l] of Object.entries(FLABEL)) {
    if (state[k] !== "All") out.push(`${l} ${k === "innings" ? (state[k] === "1" ? "1st" : "2nd") : state[k]}`);
  }
  return out;
}
function updateScopeRow() {
  const row = $("#scope-row"); if (!row) return;
  const act = activeFilters();
  if (!act.length) { row.hidden = true; scopeOn = false; return; }
  row.hidden = false;
  row.classList.toggle("is-on", scopeOn);
  row.innerHTML = `<button class="scope-toggle ${scopeOn ? "on" : ""}" id="scope-btn" type="button"><span class="sw"></span>${scopeOn ? "Scoped to filters" : "Scope to filters"}</button>
    <span class="scope-sum">${scopeOn ? "agent will apply — " + act.join(" · ") : "off · asking across all data"}</span>`;
  $("#scope-btn").onclick = () => { scopeOn = !scopeOn; updateScopeRow(); };
}
function clearFilter(k) {
  if (k === "min_balls") { state.min_balls = 30; $("#f-minballs").value = 30; $("#mb-val").textContent = 30; }
  else { state[k] = "All"; const el = $("#f-" + k); if (el) el.value = "All"; }
  loadDashboard();
}
function resetFilters() {
  Object.assign(state, DEFAULTS);
  Object.keys(FLABEL).forEach((k) => { const el = $("#f-" + k); if (el) el.value = "All"; });
  $("#f-season").value = "2026";
  $("#f-minballs").value = 30; $("#mb-val").textContent = 30;
  loadDashboard();
}

// ───────────────────────── analyst console (SSE) ─────────────────────────
let streaming = false, scopeOn = false;
const newSid = () => "s" + Math.random().toString(36).slice(2) + Date.now().toString(36);
let sid = newSid();
let HINT = "";
let AI_OFFLINE = false;
const aiOfflineNotice = () =>
  `<div class="ai-offline">⚠ <b>AI analyst offline.</b> Set <code>OPENROUTER_API_KEY</code> in <code>.env</code> and restart the server to ask questions. Every dashboard panel still works without it.</div>`;

function wireChips() {
  $$(".chip-q").forEach((c) => c.onclick = () => { switchView("ask"); ask(c.textContent); });
}
function clearChat() {
  sid = newSid();
  $("#transcript").innerHTML = HINT;
  wireChips();
}

function agentChart(spec) {
  const data = (spec.data || []).map((r) => ({ player: r[spec.x], value: r[spec.y] }))
    .filter((d) => d.value != null);
  const wrap = document.createElement("div");
  wrap.className = "agentchart";
  wrap.innerHTML = `<div class="ac-t">${spec.title || ""}</div><div class="chart"></div>`;
  if (spec.kind === "line") vbars($(".chart", wrap), data.map((d) => ({ label: d.player, value: d.value })), "cyan");
  else hbars($(".chart", wrap), data.slice(0, 12), "lime");
  return wrap;
}

function ask(question) {
  if (streaming || !question.trim()) return;
  streaming = true;
  $("#ask-send").disabled = true;
  const tr = $("#transcript");
  $(".hint", tr)?.remove();
  const u = document.createElement("div"); u.className = "msg user";
  u.innerHTML = `<div class="bubble"></div>`; $(".bubble", u).textContent = question;
  tr.appendChild(u);
  const bot = document.createElement("div"); bot.className = "msg bot";
  bot.innerHTML = `<div class="thinking"><i></i><i></i><i></i> investigating</div>`;
  if (scopeOn && activeFilters().length) {
    const badge = document.createElement("div");
    badge.className = "scoped-badge"; badge.textContent = "⦿ scoped · " + activeFilters().join(" · ");
    bot.insertBefore(badge, bot.firstChild);
  }
  tr.appendChild(bot); tr.scrollTop = tr.scrollHeight;

  let url = `/api/ask?q=${encodeURIComponent(question)}&sid=${sid}`;
  if (scopeOn) {
    const params = [];
    if (state.season !== "2026") params.push(`season=${encodeURIComponent(state.season)}`);
    Object.keys(FLABEL).filter((k) => state[k] !== "All").forEach((k) => params.push(`${k}=${encodeURIComponent(state[k])}`));
    if (params.length) url += "&scope=1&" + params.join("&");
  }
  const es = new EventSource(url);
  const think = $(".thinking", bot);
  es.onmessage = (e) => {
    const ev = JSON.parse(e.data);
    if (ev.type === "sql") {
      const d = document.createElement("details"); d.className = "step";
      const cols = ev.error ? "" : (ev.rows?.length ? `${ev.rows.length}+ rows · ${ev.columns.join(", ")}` : "0 rows");
      d.innerHTML = `<summary><span class="q">◢ query</span> <span style="color:var(--mute2)">${cols}</span></summary>
        <pre>${ev.query.replace(/</g, "&lt;")}</pre>${ev.error ? `<div class="rowsmini" style="color:var(--pink)">${ev.error}</div>` : ""}`;
      bot.insertBefore(d, think);
    } else if (ev.type === "chart") {
      bot.insertBefore(agentChart(ev), think);
    } else if (ev.type === "answer") {
      const p = document.createElement("div"); p.className = "prose";
      p.innerHTML = marked.parse(ev.text || "");
      bot.insertBefore(p, think);
    } else if (ev.type === "error") {
      const p = document.createElement("div"); p.className = "agent-error";
      p.innerHTML = `<b>⚠ analyst error</b><span></span>`;
      $("span", p).textContent = ev.text || "Something went wrong.";
      bot.insertBefore(p, think);
    } else if (ev.type === "done") {
      es.close(); think.remove(); streaming = false; $("#ask-send").disabled = false;
      $("#ask-input").focus();
      const fu = document.createElement("div"); fu.className = "followups";
      ["Break this down by phase", "How does it compare across seasons?", "Show me a chart"]
        .forEach((t) => { const c = document.createElement("button"); c.className = "fu"; c.textContent = t; c.onclick = () => ask(t); fu.appendChild(c); });
      bot.appendChild(fu);
    }
    tr.scrollTop = tr.scrollHeight;
  };
  es.onerror = () => { es.close(); think?.remove(); streaming = false; $("#ask-send").disabled = false; };
}

// ───────────────────────── init ─────────────────────────
async function init() {
  // filters
  const f = await getJSON("/api/filters");
  $("#f-season").innerHTML = `<option value="All">All seasons</option>` +
    f.seasons.map((s) => `<option value="${s}"${s === "2026" ? " selected" : ""}>${s}</option>`).join("");
  $("#f-team").innerHTML = f.teams.map((t) => `<option value="${t}">${t === "All" ? "All Teams" : t}</option>`).join("");
  $("#f-opponent").innerHTML = f.teams.map((t) => `<option value="${t}">${t === "All" ? "Any Opponent" : t}</option>`).join("");
  $("#f-venue").innerHTML = f.venues.map((v) => `<option value="${v}">${v === "All" ? "All Venues" : v}</option>`).join("");
  [["f-season", "season"], ["f-team", "team"], ["f-opponent", "opponent"], ["f-venue", "venue"], ["f-innings", "innings"],
   ["f-phase", "phase"], ["f-bowltype", "bowltype"], ["f-bathand", "bathand"]].forEach(([id, key]) => {
    $("#" + id).onchange = (e) => { state[key] = e.target.value; loadDashboard(); };
  });
  const mb = $("#f-minballs");
  mb.oninput = (e) => { state.min_balls = +e.target.value; $("#mb-val").textContent = e.target.value; };
  mb.onchange = () => loadDashboard();
  $("#reset").onclick = resetFilters;

  // nav
  $$(".nav-btn").forEach((b) => b.onclick = () => switchView(b.dataset.view));
  window.addEventListener("resize", () => moveInk($(".nav-btn.is-active")));

  // player drilldown
  document.addEventListener("click", (e) => { const pl = e.target.closest(".nm.pl"); if (pl) openPlayer(pl.dataset.player); });
  $("#pmodal-bg").onclick = closePlayer;
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") closePlayer(); });

  // ask — proactively flag if the AI analyst has no key (the dashboard still works)
  try {
    const h = await getJSON("/api/health");
    if (!h.has_key) {
      AI_OFFLINE = true;
      $("#transcript").insertAdjacentHTML("afterbegin", aiOfflineNotice());
      const inp = $("#ask-input"); if (inp) inp.placeholder = "AI analyst offline — set OPENROUTER_API_KEY in .env";
    }
  } catch (_) { /* health is best-effort; never block the UI on it */ }
  HINT = $("#transcript").innerHTML;
  $("#ask-form").onsubmit = (e) => { e.preventDefault(); ask($("#ask-input").value); $("#ask-input").value = ""; };
  $("#newchat").onclick = clearChat;
  wireChips();

  // matchups
  $("#mu-form").onsubmit = (e) => { e.preventDefault(); runMatchup(); };

  const startView = applyHash();
  await loadDashboard();
  if (startView) switchView(startView); else moveInk($(".nav-btn.is-active"));
}
init();
