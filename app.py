"""IPL 2026 — Command Center.

A rich BI dashboard over the IPL 2026 ball-by-ball data, plus the agentic
analyst from ask.py wired into an "Ask" tab. Deterministic leaderboard/KPI
panels query the rule-encoding views directly (no LLM, instant); the Ask tab
hands free-form questions to the agent, which investigates and renders its own
Plotly charts inline.

Aesthetic: "Broadcast Command Center" — charcoal, electric lime + cyan, Anton
display type, IBM Plex Mono telemetry digits.

Run:  uv run streamlit run app.py
"""
from __future__ import annotations

import json
import os

import duckdb
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

from ask import MAX_STEPS, RULEBOOK, TOOLS, client

load_dotenv()

DB = "data/cricket.duckdb"
WICKET_CREDIT = "('bowled','caught','lbw','caught and bowled','stumped','hit wicket')"

# Command-Center palette
LIME = "#B8FF2E"
CYAN = "#27E8FF"
PINK = "#FF4D9D"
AMBER = "#FFB627"
VIOLET = "#9B8CFF"
COLORWAY = [LIME, CYAN, PINK, AMBER, VIOLET]

st.set_page_config(page_title="IPL 2026 · Command Center", page_icon="🏏", layout="wide")


# ───────────────────────────── data layer ─────────────────────────────
@st.cache_resource
def get_con():
    return duckdb.connect(DB, read_only=True)


@st.cache_data(show_spinner=False)
def q(sql: str):
    return get_con().execute(sql).df()


def esc(v: str) -> str:
    return v.replace("'", "''")


def wsql(phase: str, team: str | None = None, team_col: str = "batting_team") -> str:
    parts = []
    if phase and phase != "All":
        parts.append(f"phase = '{esc(phase)}'")
    if team and team != "All":
        parts.append(f"{team_col} = '{esc(team)}'")
    return " AND ".join(parts) or "TRUE"


@st.cache_data(show_spinner=False)
def teams():
    return ["All"] + [r for (r,) in get_con().execute(
        "SELECT DISTINCT batting_team FROM v_deliveries ORDER BY 1"
    ).fetchall()]


# ───────────────────────────── styling ─────────────────────────────
def inject_css():
    st.markdown(
        """
<style>
@import url('https://fonts.googleapis.com/css2?family=Anton&family=IBM+Plex+Mono:wght@400;500;600&family=Hanken+Grotesk:wght@400;500;700;800&display=swap');

:root{
  --bg:#0B0F0A; --panel:#10150D; --line:rgba(184,255,46,.14);
  --lime:#B8FF2E; --cyan:#27E8FF; --ink:#EAEAE0; --dim:#7E8A72;
}
html, body, [class*="css"]{ font-family:'Hanken Grotesk',sans-serif; }
.stApp{
  background:
    radial-gradient(1100px 500px at 12% -8%, rgba(184,255,46,.10), transparent 60%),
    radial-gradient(900px 480px at 100% 0%, rgba(39,232,255,.08), transparent 55%),
    var(--bg);
}
/* faint grain */
.stApp::before{
  content:""; position:fixed; inset:0; pointer-events:none; opacity:.05; z-index:0;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='120' height='120'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='2'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
}
#MainMenu, footer{visibility:hidden;}
header[data-testid="stHeader"]{background:transparent;}
.block-container{padding-top:1.4rem; max-width:1500px;}

/* ── masthead ── */
.masthead{ position:relative; border:1px solid var(--line); border-radius:14px;
  padding:26px 30px; margin-bottom:18px; overflow:hidden;
  background:linear-gradient(120deg, rgba(184,255,46,.08), rgba(39,232,255,.04) 55%, transparent);
}
.masthead .kicker{ font-family:'IBM Plex Mono',monospace; letter-spacing:.32em;
  font-size:.72rem; color:var(--lime); text-transform:uppercase; }
.masthead h1{ font-family:'Anton',sans-serif; font-weight:400; line-height:.92;
  font-size:clamp(2.6rem,6vw,4.6rem); letter-spacing:.01em; margin:.1em 0 .05em;
  color:var(--ink); text-transform:uppercase; }
.masthead h1 em{ font-style:normal; color:var(--lime); }
.masthead .sub{ color:var(--dim); font-size:.95rem; max-width:60ch; }
.livedot{ display:inline-block; width:8px; height:8px; border-radius:50%;
  background:var(--lime); box-shadow:0 0 0 0 rgba(184,255,46,.6);
  animation:pulse 1.8s infinite; margin-right:7px; vertical-align:middle; }
@keyframes pulse{ 70%{box-shadow:0 0 0 9px rgba(184,255,46,0);} 100%{box-shadow:0 0 0 0 rgba(184,255,46,0);} }

/* ── KPI cards ── */
.kpi{ border:1px solid var(--line); border-radius:12px; padding:16px 18px 14px;
  background:linear-gradient(180deg, rgba(255,255,255,.02), transparent);
  position:relative; opacity:0; transform:translateY(8px);
  animation:rise .5s ease forwards; }
.kpi:hover{ border-color:rgba(184,255,46,.5); }
@keyframes rise{ to{opacity:1; transform:none;} }
.kpi .val{ font-family:'IBM Plex Mono',monospace; font-weight:600;
  font-size:2.05rem; color:var(--ink); line-height:1; }
.kpi .lab{ font-family:'IBM Plex Mono',monospace; font-size:.66rem; letter-spacing:.2em;
  text-transform:uppercase; color:var(--dim); margin-top:9px; }
.kpi .tick{ height:3px; width:34px; background:var(--lime); border-radius:2px; margin-top:11px; }

/* ── section headers ── */
.sec{ font-family:'Anton',sans-serif; text-transform:uppercase; letter-spacing:.02em;
  font-size:1.18rem; color:var(--ink); margin:.2rem 0 .1rem;
  display:flex; align-items:center; gap:10px; }
.sec::before{ content:""; width:14px; height:14px; background:var(--lime);
  clip-path:polygon(0 0,100% 0,100% 100%); display:inline-block; }

/* ── tabs ── */
.stTabs [data-baseweb="tab-list"]{ gap:4px; border-bottom:1px solid var(--line); }
.stTabs [data-baseweb="tab"]{ font-family:'IBM Plex Mono',monospace; text-transform:uppercase;
  letter-spacing:.16em; font-size:.74rem; color:var(--dim); background:transparent; }
.stTabs [aria-selected="true"]{ color:var(--lime) !important; }
.stTabs [data-baseweb="tab-highlight"]{ background:var(--lime); }

/* sidebar + widgets */
section[data-testid="stSidebar"]{ background:var(--panel); border-right:1px solid var(--line); }
section[data-testid="stSidebar"] .sec{ font-size:1rem; }
.stChatMessage{ background:rgba(255,255,255,.015); border:1px solid var(--line); border-radius:12px; }
code, .stCode{ font-family:'IBM Plex Mono',monospace !important; }
</style>
""",
        unsafe_allow_html=True,
    )


def section(title: str):
    st.markdown(f'<div class="sec">{title}</div>', unsafe_allow_html=True)


def style_fig(fig, height: int = 340, horizontal: bool = False):
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="IBM Plex Mono, monospace", color="#AEB8A2", size=11),
        colorway=COLORWAY,
        margin=dict(l=8, r=12, t=34, b=8),
        height=height,
        showlegend=False,
        title=dict(font=dict(family="Anton", size=15, color="#EAEAE0")),
        xaxis=dict(gridcolor="rgba(255,255,255,.05)", zeroline=False),
        yaxis=dict(gridcolor="rgba(255,255,255,.05)", zeroline=False),
    )
    return fig


def bar(df, x, y, title, color=LIME, height=340, horizontal=False):
    if horizontal:
        df = df.iloc[::-1]
        fig = px.bar(df, x=y, y=x, orientation="h", title=title)
    else:
        fig = px.bar(df, x=x, y=y, title=title)
    fig.update_traces(marker_color=color, marker_line_width=0)
    return style_fig(fig, height)


# ───────────────────────────── KPI computation ─────────────────────────────
def render_kpis(phase: str, team: str):
    wb = wsql(phase, team, "batting_team")
    wbowl = wsql(phase, team, "bowling_team")
    bat = q(f"""SELECT SUM(runs_total) runs,
                  6.0*SUM(runs_total)/NULLIF(COUNT(*) FILTER(WHERE is_legal_ball),0) rr,
                  COUNT(*) FILTER(WHERE runs_batter=6) sixes
                FROM v_deliveries WHERE {wb}""").iloc[0]
    wk = q(f"SELECT COUNT(*) w FROM v_deliveries WHERE {wbowl} AND wicket_kind IN {WICKET_CREDIT}").iloc[0]
    if team == "All":
        m = q("SELECT COUNT(*) m FROM v_matches").iloc[0]["m"]
    else:
        m = q(f"""SELECT COUNT(DISTINCT match_id) m FROM v_deliveries
                  WHERE batting_team='{esc(team)}' OR bowling_team='{esc(team)}'""").iloc[0]["m"]
    cards = [
        (f"{int(m)}", "Matches"),
        (f"{int(bat['runs'] or 0):,}", "Runs"),
        (f"{int(wk['w'] or 0)}", "Wickets"),
        (f"{int(bat['sixes'] or 0)}", "Sixes"),
        (f"{(bat['rr'] or 0):.2f}", "Run Rate"),
    ]
    cols = st.columns(len(cards))
    for i, (c, (val, lab)) in enumerate(zip(cols, cards)):
        c.markdown(
            f'<div class="kpi" style="animation-delay:{i*70}ms">'
            f'<div class="val">{val}</div><div class="lab">{lab}</div>'
            f'<div class="tick"></div></div>',
            unsafe_allow_html=True,
        )


# ───────────────────────────── dashboard tabs ─────────────────────────────
def tab_overview(phase, team):
    wb = wsql(phase, team, "batting_team")
    wbowl = wsql(phase, team, "bowling_team")
    c1, c2 = st.columns(2)
    with c1:
        section("Top Run Scorers")
        df = q(f"""SELECT batter_name AS player, SUM(runs_batter) runs FROM v_deliveries
                   WHERE {wb} GROUP BY 1 ORDER BY runs DESC LIMIT 10""")
        st.plotly_chart(bar(df, "player", "runs", "RUNS", LIME, horizontal=True), width="stretch")
    with c2:
        section("Top Wicket-Takers")
        df = q(f"""SELECT bowler_name AS player, COUNT(*) wkts FROM v_deliveries
                   WHERE {wbowl} AND wicket_kind IN {WICKET_CREDIT}
                   GROUP BY 1 ORDER BY wkts DESC LIMIT 10""")
        st.plotly_chart(bar(df, "player","wkts", "WICKETS", CYAN, horizontal=True), width="stretch")
    c3, c4 = st.columns(2)
    with c3:
        section("Runs by Phase")
        df = q(f"""SELECT phase, SUM(runs_total) runs FROM v_deliveries
                   WHERE {wsql('All', team, 'batting_team')} GROUP BY 1""")
        order = {"powerplay": 0, "middle": 1, "death": 2}
        df = df.sort_values("phase", key=lambda s: s.map(order))
        fig = px.pie(df, names="phase", values="runs", hole=.62, title="SHARE OF RUNS")
        fig.update_traces(marker=dict(colors=COLORWAY), textfont=dict(family="IBM Plex Mono"))
        st.plotly_chart(style_fig(fig, 340), width="stretch")
    with c4:
        section("Bat First vs Chasing")
        df = q("""WITH fb AS (SELECT match_id, batting_team FROM v_innings WHERE innings=1)
                  SELECT CASE WHEN m.effective_winner=f.batting_team THEN 'Bat First' ELSE 'Chasing' END side,
                         COUNT(*) wins
                  FROM v_matches m JOIN fb f ON f.match_id=m.match_id
                  WHERE m.effective_winner IS NOT NULL GROUP BY 1""")
        st.plotly_chart(bar(df, "side", "wins", "MATCHES WON", AMBER, 340), width="stretch")


def tab_batting(phase, team):
    wb = wsql(phase, team, "batting_team")
    mb = st.session_state.min_balls
    c1, c2 = st.columns(2)
    with c1:
        section(f"Strike Rate Leaders · min {mb} balls")
        df = q(f"""SELECT batter_name AS player,
                     ROUND(100.0*SUM(runs_batter)/NULLIF(COUNT(*) FILTER(WHERE is_legal_ball),0),1) sr
                   FROM v_deliveries WHERE {wb}
                   GROUP BY 1 HAVING COUNT(*) FILTER(WHERE is_legal_ball) >= {mb}
                   ORDER BY sr DESC LIMIT 10""")
        st.plotly_chart(bar(df, "player","sr", "STRIKE RATE", LIME, horizontal=True), width="stretch")
    with c2:
        section("Most Sixes")
        df = q(f"""SELECT batter_name AS player, COUNT(*) sixes FROM v_deliveries
                   WHERE {wb} AND runs_batter=6 GROUP BY 1 ORDER BY sixes DESC LIMIT 10""")
        st.plotly_chart(bar(df, "player","sixes", "SIXES", PINK, horizontal=True), width="stretch")
    section(f"Batting Average Leaders · min {mb} balls")
    df = q(f"""SELECT batter_name AS player,
                 ROUND(SUM(runs_batter)*1.0/NULLIF(COUNT(*) FILTER(WHERE player_out=batter_id),0),1) avg
               FROM v_deliveries WHERE {wb}
               GROUP BY 1 HAVING COUNT(*) FILTER(WHERE is_legal_ball) >= {mb}
                  AND COUNT(*) FILTER(WHERE player_out=batter_id) > 0
               ORDER BY avg DESC LIMIT 12""")
    st.plotly_chart(bar(df, "player", "avg", "AVERAGE", CYAN, height=360, horizontal=True), width="stretch")


def tab_bowling(phase, team):
    wbowl = wsql(phase, team, "bowling_team")
    mb = st.session_state.min_balls
    c1, c2 = st.columns(2)
    with c1:
        section(f"Best Economy · min {mb} balls")
        df = q(f"""SELECT bowler_name AS player,
                     ROUND(6.0*SUM(bowler_conceded)/NULLIF(COUNT(*) FILTER(WHERE is_legal_ball),0),2) econ
                   FROM v_deliveries WHERE {wbowl}
                   GROUP BY 1 HAVING COUNT(*) FILTER(WHERE is_legal_ball) >= {mb}
                   ORDER BY econ ASC LIMIT 10""")
        st.plotly_chart(bar(df, "player","econ", "ECONOMY (LOWER=BETTER)", LIME, horizontal=True), width="stretch")
    with c2:
        section(f"Highest Dot-Ball % · min {mb} balls")
        df = q(f"""SELECT bowler_name AS player,
                     ROUND(100.0*COUNT(*) FILTER(WHERE is_legal_ball AND runs_batter=0)
                           /NULLIF(COUNT(*) FILTER(WHERE is_legal_ball),0),1) dot
                   FROM v_deliveries WHERE {wbowl}
                   GROUP BY 1 HAVING COUNT(*) FILTER(WHERE is_legal_ball) >= {mb}
                   ORDER BY dot DESC LIMIT 10""")
        st.plotly_chart(bar(df, "player","dot", "DOT %", CYAN, horizontal=True), width="stretch")
    section("Economy by Phase (league)")
    df = q("""SELECT phase,
                ROUND(6.0*SUM(bowler_conceded)/NULLIF(COUNT(*) FILTER(WHERE is_legal_ball),0),2) econ
              FROM v_deliveries GROUP BY 1""")
    order = {"powerplay": 0, "middle": 1, "death": 2}
    df = df.sort_values("phase", key=lambda s: s.map(order))
    st.plotly_chart(bar(df, "phase", "econ", "RUNS PER OVER", AMBER, 320), width="stretch")


def tab_teams(phase):
    section("Matches Won")
    df = q("""SELECT effective_winner team, COUNT(*) wins FROM v_matches
              WHERE effective_winner IS NOT NULL GROUP BY 1 ORDER BY wins DESC""")
    st.plotly_chart(bar(df, "team", "wins", "WINS", LIME, height=380, horizontal=True), width="stretch")
    c1, c2 = st.columns(2)
    with c1:
        section("Runs Scored by Team")
        df = q(f"""SELECT batting_team team, SUM(runs_total) runs FROM v_deliveries
                   WHERE {wsql(phase)} GROUP BY 1 ORDER BY runs DESC""")
        st.plotly_chart(bar(df, "team", "runs", "RUNS", CYAN, height=400, horizontal=True), width="stretch")
    with c2:
        section("Run Rate by Team")
        df = q(f"""SELECT batting_team team,
                     ROUND(6.0*SUM(runs_total)/NULLIF(COUNT(*) FILTER(WHERE is_legal_ball),0),2) rr
                   FROM v_deliveries WHERE {wsql(phase)} GROUP BY 1 ORDER BY rr DESC""")
        st.plotly_chart(bar(df, "team", "rr", "RUN RATE", PINK, height=400, horizontal=True), width="stretch")


# ───────────────────────────── Ask the Analyst ─────────────────────────────
def agent_chart(con, query, kind, x, y, title):
    try:
        df = con.execute(query).df()
    except Exception as e:
        return None, f"SQL ERROR: {e}"
    if df.empty:
        return None, "(0 rows)"
    if x not in df.columns or y not in df.columns:
        return None, f"missing columns: need {x},{y}; have {list(df.columns)}"
    if kind == "line":
        fig = px.line(df, x=x, y=y, markers=True, title=title.upper())
        fig.update_traces(line_color=LIME)
    else:
        fig = bar(df, x, y, title.upper(), LIME, 360)
        return style_fig(fig, 360), f"chart rendered: {title}"
    return style_fig(fig, 360), f"chart rendered: {title}"


def investigate_web(cli, con, question):
    messages = [{"role": "system", "content": RULEBOOK}, {"role": "user", "content": question}]
    for _ in range(MAX_STEPS):
        resp = cli.chat.completions.create(
            model=os.environ.get("CRICKET_MODEL", "deepseek/deepseek-v4-pro"),
            temperature=0, tools=TOOLS, tool_choice="auto", messages=messages,
        )
        msg = resp.choices[0].message
        messages.append(msg.model_dump(exclude_none=True))
        if not msg.tool_calls:
            yield ("answer", msg.content or "_(no answer)_")
            return
        for tc in msg.tool_calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            if tc.function.name == "run_sql":
                sql = args.get("query", "")
                try:
                    df = con.execute(sql).df()
                    result = df.head(50).to_markdown(index=False) if len(df) else "(0 rows)"
                except Exception as e:
                    df, result = None, f"SQL ERROR: {e}"
                yield ("sql", sql, df)
            else:
                fig, result = agent_chart(con, args.get("query", ""), args.get("kind", "bar"),
                                          args.get("x", ""), args.get("y", ""), args.get("title", ""))
                if fig is not None:
                    yield ("chart", fig)
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
    yield ("answer", "_(reached the step limit — try narrowing the question.)_")


def render_event(ev):
    if ev[0] == "sql":
        with st.expander("◢ query", expanded=False):
            st.code(ev[1], language="sql")
            if ev[2] is not None and len(ev[2]):
                st.dataframe(ev[2].head(25), width="stretch", hide_index=True)
    elif ev[0] == "chart":
        st.plotly_chart(ev[1], width="stretch")
    elif ev[0] == "answer":
        st.markdown(ev[1])


def tab_ask(con):
    section("Ask the Analyst")
    st.caption("Free-form questions go to the agent — it investigates with SQL and charts. "
               "e.g. *“analyze the best death-overs bowlers”* or *“who hits spin best?”*")
    if "chat" not in st.session_state:
        st.session_state.chat = []
    for turn in st.session_state.chat:
        with st.chat_message("user"):
            st.markdown(turn["q"])
        with st.chat_message("assistant"):
            for ev in turn["events"]:
                render_event(ev)

    with st.form("ask", clear_on_submit=True):
        prompt = st.text_input("Question", placeholder="Ask anything about IPL 2026…",
                               label_visibility="collapsed")
        go = st.form_submit_button("▸ Analyze")
    if go and prompt.strip():
        with st.chat_message("user"):
            st.markdown(prompt)
        events = []
        with st.chat_message("assistant"):
            if not os.environ.get("OPENROUTER_API_KEY"):
                st.warning("Set OPENROUTER_API_KEY in .env to use the analyst.")
            else:
                with st.spinner("Investigating…"):
                    for ev in investigate_web(client(), con, prompt.strip()):
                        render_event(ev)
                        events.append(ev)
        st.session_state.chat.append({"q": prompt.strip(), "events": events})


# ───────────────────────────── layout ─────────────────────────────
def main():
    inject_css()

    with st.sidebar:
        st.markdown('<div class="sec">Filters</div>', unsafe_allow_html=True)
        team = st.selectbox("Team", teams())
        phase = st.selectbox("Phase", ["All", "powerplay", "middle", "death"])
        st.session_state.min_balls = st.slider("Min legal balls (qualifier)", 6, 120, 30, 6)
        st.markdown("---")
        st.caption("IPL 2026 · 70 matches · numbers computed live over the "
                   "rule-encoding DuckDB views.")

    st.markdown(
        '<div class="masthead">'
        '<div class="kicker"><span class="livedot"></span>Season 2026 · Command Center</div>'
        '<h1>IPL <em>2026</em> ANALYTICS</h1>'
        '<div class="sub">Ball-by-ball intelligence — leaderboards and live metrics over the '
        'rule-encoding views, plus an AI analyst that investigates any question for you.</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    render_kpis(phase, team)
    st.write("")

    t1, t2, t3, t4, t5 = st.tabs(["Overview", "Batting", "Bowling", "Teams", "Ask the Analyst"])
    with t1:
        tab_overview(phase, team)
    with t2:
        tab_batting(phase, team)
    with t3:
        tab_bowling(phase, team)
    with t4:
        tab_teams(phase)
    with t5:
        tab_ask(get_con())


if __name__ == "__main__":
    main()
