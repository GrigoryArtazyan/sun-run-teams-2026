"""
Vancouver Sun Run 2026 — team results dashboard.
Loads CSVs from data/processed/ (produce with sunrun_extract.ipynb).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

BASE = Path(__file__).resolve().parent
DATA = BASE / "data" / "processed"

# Shell — one place to tune the full-page background (Streamlit + Plotly)
APP_BG = "#0f172a"
APP_BG_ELEVATED = "#1e293b"
APP_BG_MUTED = "#334155"
APP_BORDER = "#475569"

# Accent palette (readable on APP_BG)
C_PRIMARY = "#38bdf8"
C_TRACK = "#334155"
C_MARKER = "#22d3ee"
C_GRID = "#475569"
C_TEXT = "#e2e8f0"
C_TEXT_MUTED = "#94a3b8"

def fmt_hms(total_seconds: float) -> str:
    s = int(round(total_seconds))
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{sec:02d}"
    return f"{m}:{sec:02d}"


def fmt_pace_compact(seconds_per_km: float) -> str:
    s = int(round(seconds_per_km))
    m, sec = divmod(s, 60)
    return f"{m}:{sec:02d}/km"


def plotly_theme() -> dict:
    """Dark Plotly layout — matches app shell."""
    return dict(
        template="plotly_dark",
        paper_bgcolor=APP_BG,
        plot_bgcolor=APP_BG,
        font=dict(color=C_TEXT, size=12),
        margin=dict(l=8, r=8, t=44, b=8),
        xaxis=dict(
            gridcolor=C_GRID,
            zerolinecolor=C_GRID,
            linecolor=C_GRID,
            tickfont=dict(size=11),
        ),
        yaxis=dict(
            gridcolor=C_GRID,
            zerolinecolor=C_GRID,
            linecolor=C_GRID,
            tickfont=dict(size=11),
        ),
    )


def chart_height(rows: int = 1, per_row: int = 28, base: int = 200) -> int:
    """Scale chart height with content; cap for typical laptop viewports."""
    h = base + rows * per_row
    return min(640, max(180, h))


@st.cache_data
def load_tables() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    runners = pd.read_csv(DATA / "sunrun_runners.csv")
    teams = pd.read_csv(DATA / "sunrun_teams.csv")
    categories = pd.read_csv(DATA / "sunrun_categories.csv")
    runners["team_id"] = runners["team_id"].astype(int)
    teams["team_id"] = teams["team_id"].astype(int)
    categories["category_id"] = categories["category_id"].astype(int)
    if "runner_bib" in runners.columns:
        runners["runner_bib"] = pd.to_numeric(runners["runner_bib"], errors="coerce").astype("Int64")
    # CSV may only have category_id; charts need division labels
    if "category_name" not in runners.columns:
        cats = categories.drop_duplicates(subset=["category_id"], keep="first")
        runners = runners.merge(
            cats[["category_id", "category_name"]],
            on="category_id",
            how="left",
            validate="many_to_one",
        )
    return runners, teams, categories


def prepare_teams(
    runners: pd.DataFrame, teams: pd.DataFrame, categories: pd.DataFrame
) -> pd.DataFrame:
    categories = categories.drop_duplicates(subset=["category_id"], keep="first")
    teams = teams.merge(
        categories[["category_id", "category_name"]],
        on="category_id",
        how="left",
        validate="many_to_one",
    )
    teams = teams.drop_duplicates(subset=["team_id"], keep="first")
    teams["category_name"] = teams["category_name"].fillna("Unknown category")

    ids_teams = set(teams["team_id"])
    ids_runners = set(runners["team_id"].unique())
    missing_ids = sorted(ids_runners - ids_teams)
    if missing_ids:
        filler = (
            runners[runners["team_id"].isin(missing_ids)]
            .sort_values("team_id")
            .drop_duplicates(subset=["team_id"], keep="first")
        )
        filler = filler.merge(
            categories[["category_id", "category_name"]],
            on="category_id",
            how="left",
            validate="many_to_one",
        )
        teams = pd.concat([teams, filler], ignore_index=True)
        teams = teams.drop_duplicates(subset=["team_id"], keep="first")

    return teams


def scoring_and_rest(team_runners: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    ordered = team_runners.sort_values("runner_seconds", ascending=True).reset_index(drop=True)
    scoring = ordered.head(8).copy()
    rest = ordered.iloc[8:].copy()
    return scoring, rest


def team_top8_seconds(runners_df: pd.DataFrame) -> pd.Series:
    fastest8 = runners_df.sort_values("runner_seconds").groupby("team_id").head(8)
    return fastest8.groupby("team_id")["runner_seconds"].sum()


def inject_css() -> None:
    _css_head = f"""
<style>
:root {{
  --color-text-primary: #e2e8f0;
  --color-text-secondary: #94a3b8;
  --color-text-tertiary: #64748b;
  --color-border: {APP_BORDER};
  --color-bg: {APP_BG};
  --color-bg-elevated: {APP_BG_ELEVATED};
  --color-bg-muted: {APP_BG_MUTED};
  --accent: {C_PRIMARY};
  --font-sans: ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
  --pad-inline: clamp(12px, 3vw, 28px);
  --pad-block: clamp(10px, 2vw, 18px);
  --radius: clamp(8px, 1vw, 12px);
}}
/* Full-app canvas (Streamlit root + main) */
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"] > .main,
section.main,
section.main > div {{
  background-color: var(--color-bg) !important;
}}
"""
    _css_tail = """
section.main > div.block-container {
  max-width: min(1600px, 98vw) !important;
  padding-left: var(--pad-inline) !important;
  padding-right: var(--pad-inline) !important;
  padding-top: clamp(0.5rem, 1.2vw, 1rem) !important;
  padding-bottom: clamp(0.75rem, 2vw, 1.5rem) !important;
}
/* Metrics — match shell colors */
[data-testid="stMetricLabel"] { color: var(--color-text-secondary) !important; }
[data-testid="stMetricValue"] { color: var(--color-text-primary) !important; }
[data-testid="stMetricDelta"] { color: var(--color-text-tertiary) !important; }
header[data-testid="stHeader"] {
  background: linear-gradient(180deg, #1a2332 0%, var(--color-bg) 100%) !important;
  border-bottom: 1px solid var(--color-border) !important;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.25);
}
/* Streamlit st.navigation (position=sidebar) — vertical page list */
[data-testid="stSidebar"] [data-testid="stNavigation"] {
  flex-direction: column !important;
  align-items: stretch !important;
  gap: 0.35rem !important;
  width: 100% !important;
  padding: 0.25rem 0 0.75rem !important;
}
[data-testid="stHeader"] [data-testid="stNavigation"] {
  align-items: center !important;
  gap: 0.2rem !important;
  padding-left: 0.35rem !important;
}
[data-testid="stSidebarNavLink"] a,
[data-testid="stSidebarNavLink"] span,
[data-testid="stNavLink"] a,
[data-testid="stNavLink"] span {
  color: var(--color-text-secondary) !important;
  font-weight: 500 !important;
  border-radius: 8px !important;
  padding: 0.35rem 0.7rem !important;
  transition: background 0.15s ease, color 0.15s ease !important;
}
[data-testid="stSidebar"] [data-testid="stSidebarNavLink"] a,
[data-testid="stSidebar"] [data-testid="stSidebarNavLink"] span {
  display: block !important;
  width: 100% !important;
  box-sizing: border-box !important;
}
[data-testid="stSidebarNavLink"] a:hover,
[data-testid="stNavLink"] a:hover {
  background: rgba(56, 189, 248, 0.1) !important;
  color: var(--color-text-primary) !important;
}
[data-testid="stSidebarNavLink"][aria-current="page"] a,
[data-testid="stSidebarNavLink"][aria-current="page"] span,
[data-testid="stNavLink"][aria-current="page"] a,
[data-testid="stNavLink"][aria-current="page"] span {
  color: #e0f2fe !important;
  background: linear-gradient(135deg, rgba(56, 189, 248, 0.22) 0%, rgba(51, 65, 85, 0.55) 100%) !important;
  box-shadow: 0 0 0 1px rgba(56, 189, 248, 0.35) !important;
}
/* Fallback: top nav links (Streamlit wraps in header; test ids vary by version) */
header[data-testid="stHeader"] nav[aria-label="Page navigation"] a,
header[data-testid="stHeader"] [data-testid="stNavigation"] a {
  color: var(--color-text-secondary) !important;
  font-weight: 500 !important;
  border-radius: 8px !important;
  padding: 0.35rem 0.7rem !important;
  text-decoration: none !important;
}
header[data-testid="stHeader"] nav[aria-label="Page navigation"] a[aria-current="page"],
header[data-testid="stHeader"] [data-testid="stNavigation"] a[aria-current="page"] {
  color: #e0f2fe !important;
  background: linear-gradient(135deg, rgba(56, 189, 248, 0.22) 0%, rgba(51, 65, 85, 0.55) 100%) !important;
  box-shadow: 0 0 0 1px rgba(56, 189, 248, 0.35) !important;
}
[data-testid="stSidebar"] { background-color: var(--color-bg) !important; }
[data-testid="stSidebar"] > div { background-color: var(--color-bg) !important; }
/* Default text on dark */
[data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] li {
  color: var(--color-text-primary);
}
[data-testid="stCaptionContainer"] { color: var(--color-text-secondary) !important; }
.bp { font-family: var(--font-sans); color: var(--color-text-primary); }
.label {
  font-size: clamp(10px, 1vw, 12px);
  font-weight: 600;
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: .07em;
  margin-bottom: clamp(6px, 1vw, 10px);
}
.section-head {
  font-size: clamp(13px, 1.15vw, 15px);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 clamp(8px, 1.2vw, 12px) 0;
}
.card {
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: var(--pad-block) clamp(12px, 2.5vw, 18px);
  margin-bottom: clamp(12px, 2vw, 18px);
}
.card-muted {
  background: var(--color-bg-muted);
  border-radius: calc(var(--radius) - 2px);
  padding: clamp(10px, 1.8vw, 14px) clamp(12px, 2vw, 16px);
}
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, clamp(100px, 22vw, 200px)), 1fr));
  gap: clamp(8px, 1.5vw, 14px);
  margin-bottom: clamp(10px, 2vw, 16px);
}
.col { min-width: 0; }
.kpi-val {
  font-size: clamp(1rem, 2.2vw, 1.35rem);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 4px 0 0;
  line-height: 1.2;
}
.kpi-lbl {
  font-size: clamp(10px, 1vw, 12px);
  color: var(--color-text-secondary);
  font-weight: 500;
}
.runner-row {
  display: flex;
  align-items: center;
  gap: clamp(6px, 1.2vw, 10px);
  padding: clamp(6px, 1vw, 10px) 0;
  border-bottom: 1px solid var(--color-border);
}
.runner-row:last-child { border-bottom: none; }
.divider { border: none; border-top: 1px solid var(--color-border); margin: clamp(10px, 2vw, 16px) 0; }
/* Tabs — proportional tap targets */
div[data-testid="stTabs"] [data-baseweb="tab-list"] {
  gap: clamp(4px, 1vw, 8px);
  flex-wrap: wrap;
  background: var(--color-bg-elevated);
  padding: clamp(4px, 0.8vw, 8px);
  border-radius: var(--radius);
  border: 1px solid var(--color-border);
}
div[data-testid="stTabs"] button[data-baseweb="tab"] {
  font-size: clamp(12px, 1.05vw, 14px) !important;
  font-weight: 500 !important;
  border-radius: clamp(6px, 0.8vw, 10px) !important;
  min-height: clamp(38px, 5vw, 46px) !important;
  padding-left: clamp(12px, 2vw, 18px) !important;
  padding-right: clamp(12px, 2vw, 18px) !important;
  color: var(--color-text-secondary) !important;
}
div[data-testid="stTabs"] [aria-selected="true"] {
  background: var(--color-bg-muted) !important;
  color: var(--accent) !important;
}
/* Inputs & select — scale with viewport */
.stTextInput input, .stSelectbox [data-baseweb="select"] > div {
  min-height: clamp(40px, 5vw, 48px) !important;
  font-size: clamp(13px, 1.1vw, 15px) !important;
  background-color: var(--color-bg-muted) !important;
  border-color: var(--color-border) !important;
  color: var(--color-text-primary) !important;
  border-radius: clamp(6px, 0.8vw, 10px) !important;
}
/* Dataframe / tables */
[data-testid="stDataFrame"] { border: 1px solid var(--color-border); border-radius: var(--radius); overflow: hidden; }
[data-testid="stDataFrame"] [data-testid="stHorizontalBlock"] { background: var(--color-bg-elevated); }
/* Alerts */
[data-testid="stAlert"] {
  background-color: var(--color-bg-muted) !important;
  border: 1px solid var(--color-border) !important;
  color: var(--color-text-primary) !important;
}
.stButton > button {
  min-height: clamp(38px, 5vw, 46px) !important;
  font-size: clamp(13px, 1.1vw, 15px) !important;
  border-radius: clamp(6px, 0.8vw, 10px) !important;
  background-color: var(--color-bg-muted) !important;
  border: 1px solid var(--color-border) !important;
  color: var(--accent) !important;
}
/* Left sidebar — branded nav */
[data-testid="stSidebar"] {
  border-right: 1px solid var(--color-border) !important;
  min-width: 268px !important;
  max-width: 320px !important;
  background:
    linear-gradient(180deg, rgba(56, 189, 248, 0.06) 0%, transparent 28%),
    linear-gradient(165deg, #1a2332 0%, var(--color-bg) 48%, #0c1220 100%) !important;
  box-shadow:
    4px 0 32px rgba(0, 0, 0, 0.45),
    inset -1px 0 0 rgba(255, 255, 255, 0.04);
}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
  padding-top: 1.1rem;
  padding-left: 0.65rem;
  padding-right: 0.65rem;
  padding-bottom: 1.25rem;
  gap: 0.65rem;
}
[data-testid="stSidebar"] .nav-brand-wrap {
  position: relative;
  padding: 0.85rem 0.9rem 1.05rem;
  margin-bottom: 0.15rem;
  border-radius: clamp(10px, 1.2vw, 14px);
  border: 1px solid rgba(56, 189, 248, 0.22);
  background:
    linear-gradient(145deg, rgba(56, 189, 248, 0.14) 0%, rgba(15, 23, 42, 0.4) 55%, rgba(15, 23, 42, 0.85) 100%);
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.06) inset,
    0 8px 28px rgba(0, 0, 0, 0.35);
  overflow: hidden;
}
[data-testid="stSidebar"] .nav-brand-wrap::before {
  content: "";
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, var(--accent), #22d3ee 45%, rgba(56, 189, 248, 0.2) 100%);
  opacity: 0.95;
}
[data-testid="stSidebar"] .nav-brand {
  font-size: 1.12rem;
  font-weight: 700;
  letter-spacing: -0.03em;
  color: var(--color-text-primary);
  line-height: 1.15;
  text-shadow: 0 1px 12px rgba(56, 189, 248, 0.25);
}
[data-testid="stSidebar"] .nav-sub {
  font-size: 0.68rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.16em;
  color: var(--accent);
  margin-top: 0.35rem;
  opacity: 0.92;
}
</style>
"""
    st.markdown(_css_head + _css_tail, unsafe_allow_html=True)


def page_header(n_teams: int, n_runners: int, n_divisions: int) -> None:
    st.markdown(
        f"""
<div class="bp" style="padding: clamp(4px,1vw,8px) 0 clamp(8px,1.5vw,12px);">
  <div style="font-size:clamp(1rem,2.2vw,1.25rem);font-weight:600;color:var(--color-text-primary);">Sun Run 2026 — Dashboard</div>
  <div style="font-size:clamp(11px,1vw,13px);color:var(--color-text-secondary);margin-top:6px;">
    {n_teams:,} teams · {n_runners:,} runners · {n_divisions} divisions (full extract)
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )


def fig_overview_histogram(runners: pd.DataFrame):
    mins = runners["runner_seconds"] / 60.0
    if mins.empty:
        fig = px.histogram()
        fig.update_layout(**plotly_theme(), title="Finish time distribution (no data)")
        return fig

    p10 = float(mins.quantile(0.10))
    p25 = float(mins.quantile(0.25))
    p50 = float(mins.quantile(0.50))
    p75 = float(mins.quantile(0.75))
    p90 = float(mins.quantile(0.90))

    fig = px.histogram(
        x=mins,
        nbins=42,
        histnorm="percent",
        color_discrete_sequence=[C_PRIMARY],
    )
    fig.update_layout(
        **plotly_theme(),
        height=min(560, max(360, chart_height(8, 0, 280))),
        title=(
            f"Finish time — where the field sits<br>"
            f"<sup>Median {p50:.1f} min · fastest 10% under {p10:.1f} min · "
            f"slowest 10% over {p90:.1f} min · shaded band = middle 50% (Q1–Q3)</sup>"
        ),
        xaxis_title="Finish time (minutes)",
        yaxis_title="% of all runners (per bin)",
        showlegend=False,
    )
    fig.update_traces(marker_line_width=0, hovertemplate="%{x:.1f} min<br>%{y:.1f}% of field<extra></extra>")
    # Middle 50% of finish times (IQR) — typical “pack” spread
    fig.add_vrect(
        x0=p25,
        x1=p75,
        fillcolor=C_MARKER,
        opacity=0.14,
        layer="below",
        line_width=0,
    )
    fig.add_vline(
        x=p50,
        line_width=2.5,
        line_color=C_MARKER,
        line_dash="solid",
    )
    # Light guides for the long tails (10th / 90th percentiles)
    fig.add_vline(
        x=p10,
        line_width=1,
        line_color=C_GRID,
        line_dash="dot",
    )
    fig.add_vline(
        x=p90,
        line_width=1,
        line_color=C_GRID,
        line_dash="dot",
    )
    return fig


def fig_runners_by_division(runners: pd.DataFrame):
    """Horizontal bar: roster size per division (uses category_name on runner rows)."""
    c = (
        runners.dropna(subset=["category_name"])
        .groupby("category_name", observed=True)
        .size()
        .reset_index(name="runners")
        .sort_values("runners", ascending=True)
    )
    h = min(520, max(260, 40 + len(c) * 18))
    fig = px.bar(
        c,
        x="runners",
        y="category_name",
        orientation="h",
        color_discrete_sequence=[C_PRIMARY],
    )
    fig.update_layout(
        **plotly_theme(),
        height=h,
        title="Runners per division",
        xaxis_title="Runners",
        yaxis_title="",
        showlegend=False,
    )
    fig.update_yaxes(autorange="reversed", tickfont=dict(size=10))
    fig.update_traces(hovertemplate="%{y}<br>%{x} runners<extra></extra>")
    return fig


def fig_finish_time_ecdf(runners: pd.DataFrame):
    """Cumulative % of runners who finished at or before each minute (race field shape)."""
    m = runners["runner_seconds"].sort_values().astype(float).to_numpy() / 60.0
    n = len(m)
    if n == 0:
        fig = px.line()
        fig.update_layout(**plotly_theme(), title="Cumulative finishers (no data)")
        return fig
    y = (pd.Series(range(1, n + 1), dtype=float) / float(n) * 100.0).to_numpy()
    fig = px.line(x=m, y=y, color_discrete_sequence=[C_MARKER])
    fig.update_layout(
        **plotly_theme(),
        height=min(520, max(340, chart_height(8, 0, 260))),
        title="Cumulative finishers — % of field by time",
        xaxis_title="Finish time (minutes)",
        yaxis_title="% of runners (≤ this time)",
        showlegend=False,
    )
    fig.update_traces(line=dict(width=2), hovertemplate="%{x:.1f} min<br>%{y:.1f}%<extra></extra>")
    return fig


def fig_scoring_eight(scoring: pd.DataFrame):
    def _bar_label(row: pd.Series) -> str:
        return str(row["runner_name"])[:32]

    df = scoring.assign(
        minutes=lambda d: d["runner_seconds"] / 60.0,
        name=lambda d: d.apply(_bar_label, axis=1),
    )
    fig = px.bar(
        df,
        x="minutes",
        y="name",
        orientation="h",
        color_discrete_sequence=[C_PRIMARY],
    )
    fig.update_layout(
        **plotly_theme(),
        height=chart_height(max(1, len(df)), 32, 120),
        title="Scoring eight — finish times (minutes)",
        xaxis_title="Minutes",
        yaxis_title="",
        showlegend=False,
    )
    fig.update_yaxes(autorange="reversed")
    fig.update_traces(hovertemplate="%{y}<br>%{x:.2f} min<extra></extra>")
    return fig


def leaderboard_table_height(n_rows: int) -> int:
    """Taller table when many teams; keeps scroll usable on small screens."""
    return int(min(720, max(280, min(620, 36 + n_rows * 28))))


def fig_division_box(runners: pd.DataFrame):
    """Uses category_name on runner rows (already merged in load_tables)."""
    m = runners.dropna(subset=["category_name"]).copy()
    m["minutes"] = m["runner_seconds"] / 60.0
    fig = px.box(m, x="category_name", y="minutes")
    fig.update_traces(
        fillcolor=C_TRACK,
        line=dict(color=C_MARKER, width=1),
        marker=dict(color=C_MARKER, opacity=0.6),
    )
    fig.update_layout(
        **plotly_theme(),
        height=chart_height(12, 18, 200),
        title="Distribution of finish times — every runner by division",
        xaxis_title="",
        yaxis_title="Minutes",
        showlegend=False,
    )
    fig.update_xaxes(tickangle=-45)
    return fig


def fig_division_scatter(leaderboard: pd.DataFrame):
    fig = px.scatter(
        leaderboard,
        x="size",
        y="top8_hours",
        hover_data=["team_name", "category_name", "top8_time"],
    )
    fig.update_traces(
        marker=dict(color=C_PRIMARY, size=9, opacity=0.45, line=dict(width=0)),
    )
    fig.update_layout(
        **plotly_theme(),
        height=chart_height(8, 0, 260),
        title="Every team — roster size vs. top-8 total time",
        xaxis_title="Runners on team",
        yaxis_title="Top 8 total (h)",
        showlegend=False,
    )
    return fig


_DIV_BAR_COLORS = ["#06b6d4", "#38bdf8", "#64748b", "#fbbf24", "#fb7185"]


def fig_division_participation_vs_speed(runners: pd.DataFrame):
    """Bubble: big divisions vs. typical speed vs. how many teams entered."""
    m = runners.dropna(subset=["category_name"]).copy()
    m["minutes"] = m["runner_seconds"] / 60.0
    agg = (
        m.groupby("category_name", observed=True)
        .agg(
            n_runners=("runner_seconds", "count"),
            median_min=("minutes", "median"),
            n_teams=("team_id", "nunique"),
        )
        .reset_index()
    )
    if agg.empty:
        fig = px.scatter()
        fig.update_layout(**plotly_theme(), title="Participation vs. speed (no data)")
        return fig
    fig = px.scatter(
        agg,
        x="n_runners",
        y="median_min",
        size="n_teams",
        size_max=56,
        color="median_min",
        color_continuous_scale=_DIV_BAR_COLORS,
        hover_name="category_name",
        custom_data=["n_teams"],
    )
    fig.update_layout(
        **plotly_theme(),
        height=min(520, chart_height(10, 0, 300)),
        title="Participation vs. typical speed — bubble size = # of teams",
        xaxis_title="Runners in division",
        yaxis_title="Median finish (minutes)",
        showlegend=False,
    )
    fig.update_coloraxes(
        colorbar=dict(
            title=dict(text="Median min", side="right", font=dict(size=11)),
            tickfont=dict(size=10),
        )
    )
    fig.update_traces(
        hovertemplate=(
            "<b>%{hovertext}</b><br>"
            "Runners: %{x}<br>"
            "Median finish: %{y:.1f} min<br>"
            "Teams: %{customdata[0]}<extra></extra>"
        )
    )
    return fig


def build_leaderboard(runners: pd.DataFrame, teams: pd.DataFrame) -> pd.DataFrame:
    top8 = team_top8_seconds(runners)
    sizes = runners.groupby("team_id").size().rename("size")
    lb = teams.set_index("team_id").join(top8.rename("top8_seconds")).join(sizes)
    lb = lb.reset_index().dropna(subset=["top8_seconds"])
    lb["top8_time"] = lb["top8_seconds"].map(fmt_hms)
    lb["top8_hours"] = lb["top8_seconds"] / 3600.0
    scoring8 = runners.sort_values("runner_seconds").groupby("team_id").head(8)
    avg_pace = scoring8.groupby("team_id")["runner_seconds"].mean() / 10.0
    lb = lb.merge(avg_pace.rename("avg_pace_sec"), on="team_id", how="left")
    lb["avg_pace"] = lb["avg_pace_sec"].map(lambda s: fmt_pace_compact(s) if pd.notna(s) else "—")
    lb["label"] = lb["team_name"].astype(str) + " · " + lb["category_name"].astype(str)
    lb = lb.sort_values("top8_seconds", ascending=True).reset_index(drop=True)
    lb.insert(0, "#", range(1, len(lb) + 1))
    return lb


def main() -> None:
    st.set_page_config(
        page_title="Sun Run 2026 — Dashboard",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_css()

    runners, teams_raw, categories = load_tables()
    teams = prepare_teams(runners, teams_raw, categories)
    leaderboard = build_leaderboard(runners, teams)
    page_header(
        len(teams),
        len(runners),
        int(categories["category_id"].nunique()),
    )

    team_pick = teams.sort_values(["team_name", "category_name"], na_position="last").copy()
    team_pick["dropdown_label"] = (
        team_pick["team_name"].astype(str) + " · " + team_pick["category_name"].astype(str)
    )

    qp = st.query_params
    tc_list = team_pick.reset_index(drop=True)

    with st.sidebar:
        st.markdown(
            """
<div class="nav-brand-wrap">
  <div class="nav-brand">Sun Run</div>
  <div class="nav-sub">Teams · Vancouver · 2026</div>
</div>
            """,
            unsafe_allow_html=True,
        )

    def _page_overview() -> None:
        st.markdown(
            '<div class="bp label" style="margin-bottom:4px;">Race snapshot</div>',
            unsafe_allow_html=True,
        )
        n_finish = len(runners)
        n_teams = len(teams)
        n_div = categories["category_id"].nunique()
        med_team_sec = float(leaderboard["top8_seconds"].median()) if len(leaderboard) else 0.0

        k1, k2, k3, k4 = st.columns(4, gap="small")
        k1.metric("Runners", f"{n_finish:,}")
        k2.metric("Teams", f"{n_teams:,}")
        k3.metric("Divisions", f"{int(n_div)}")
        k4.metric("Median team score (top 8)", fmt_hms(med_team_sec))

        oc1, oc2, oc3 = st.columns(3, gap="medium")
        with oc1:
            st.plotly_chart(fig_overview_histogram(runners), use_container_width=True)
        with oc2:
            st.plotly_chart(fig_runners_by_division(runners), use_container_width=True)
        with oc3:
            st.plotly_chart(fig_finish_time_ecdf(runners), use_container_width=True)

        st.markdown(
            '<div class="bp label" style="margin:12px 0 4px;">Fastest teams (top 100 preview)</div>',
            unsafe_allow_html=True,
        )
        f_ov = st.text_input(
            "Search any team",
            key="ov_preview_filter",
            label_visibility="collapsed",
            placeholder="Search any team or division — shows overall rank (#)",
        )
        q = f_ov.strip()
        if not q:
            _pv = leaderboard.head(100)
            cap = (
                f"Preview: top {min(100, len(leaderboard))} of {len(leaderboard):,} teams. "
                "Type above to search the full list and see any team’s rank."
            )
        else:
            _m = (
                leaderboard["label"].str.contains(q, case=False, na=False)
                | leaderboard["category_name"].str.contains(q, case=False, na=False)
                | leaderboard["team_name"].str.contains(q, case=False, na=False)
            )
            _all = leaderboard.loc[_m]
            n_hit = len(_all)
            if n_hit > 400:
                _pv = _all.head(400)
                cap = (
                    f"Found {n_hit} team(s) matching “{q}”; showing first 400. "
                    "Column # is overall rank (1 = fastest). Refine your search."
                )
            else:
                _pv = _all
                cap = (
                    f"Found {n_hit} team(s) matching “{q}”. "
                    "Column # is overall rank (1 = fastest)."
                )

        if len(_pv) == 0:
            st.info("No teams match that search.")
        else:
            prev = _pv[["#", "label", "top8_time", "avg_pace", "size"]].rename(
                columns={"label": "Team", "top8_time": "Top 8", "avg_pace": "Pace", "size": "Size"}
            )
            st.caption(cap)
            st.dataframe(
                prev,
                use_container_width=True,
                height=leaderboard_table_height(len(prev)),
                hide_index=True,
            )

    def _page_my_team() -> None:
        st.markdown(
            '<div class="bp label" style="margin-bottom:4px;">One team</div>',
            unsafe_allow_html=True,
        )

        f_mt = st.text_input(
            "Filter teams",
            key="mt_team_filter",
            label_visibility="collapsed",
            placeholder="Filter by team or division…",
        )
        _flt = tc_list
        if f_mt.strip():
            qm = f_mt.strip().lower()
            _flt = tc_list[
                tc_list["team_name"].str.lower().str.contains(qm, na=False)
                | tc_list["category_name"].str.lower().str.contains(qm, na=False)
                | tc_list["dropdown_label"].str.lower().str.contains(qm, na=False)
            ]
        tc_use = _flt.reset_index(drop=True)
        if tc_use.empty:
            st.warning("No teams match this filter — clear the box to see all teams.")
        else:
            _def = 0
            if "team" in qp:
                qteam = str(qp["team"]).lower()
                for pos in range(len(tc_use)):
                    row = tc_use.iloc[pos]
                    if qteam in str(row["team_name"]).lower() or qteam in str(
                        row["dropdown_label"]
                    ).lower():
                        _def = pos
                        break
            pick_idx = st.selectbox(
                "Team",
                options=list(range(len(tc_use))),
                index=min(_def, max(0, len(tc_use) - 1)),
                format_func=lambda i: tc_use.iloc[i]["dropdown_label"],
                key="my_team_pick",
            )
            tid = int(tc_use.iloc[pick_idx]["team_id"])
            st.query_params["team"] = str(tc_use.iloc[pick_idx]["team_name"])

            tr = runners[runners["team_id"] == tid].copy()
            scoring, rest = scoring_and_rest(tr)
            top8_sec = scoring["runner_seconds"].sum() if len(scoring) else 0.0
            avg_pace_sec = (scoring["runner_seconds"] / 10.0).mean() if len(scoring) else float("nan")
            n_roster = len(tr)
            n_bench = len(rest)

            st.markdown(
                f"""
<div class="kpi-grid">
  <div class="card-muted col">
    <div class="kpi-lbl">Top 8 time (team score)</div>
    <div class="kpi-val">{fmt_hms(top8_sec)}</div>
  </div>
  <div class="card-muted col">
    <div class="kpi-lbl">Avg pace (scoring eight)</div>
    <div class="kpi-val">{fmt_pace_compact(avg_pace_sec) if pd.notna(avg_pace_sec) else "—"}</div>
  </div>
  <div class="card-muted col">
    <div class="kpi-lbl">Roster size</div>
    <div class="kpi-val">{n_roster}</div>
  </div>
  <div class="card-muted col">
    <div class="kpi-lbl">Not in scoring 8</div>
    <div class="kpi-val">{n_bench}</div>
  </div>
</div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown(
                '<div class="section-head">Scoring eight (team score)</div>',
                unsafe_allow_html=True,
            )
            st.plotly_chart(fig_scoring_eight(scoring), use_container_width=True)

            roster = tr.sort_values("runner_seconds", ascending=True).reset_index(drop=True)
            roster["finish_rank"] = range(1, len(roster) + 1)
            roster["counts_for_team"] = roster["finish_rank"] <= 8
            roster["pace_10k"] = roster["runner_seconds"].map(lambda s: fmt_pace_compact(s / 10.0))
            roster_disp = roster[
                [
                    "finish_rank",
                    "runner_name",
                    "runner_time",
                    "pace_10k",
                    "counts_for_team",
                ]
            ].rename(
                columns={
                    "finish_rank": "#",
                    "runner_name": "Name",
                    "runner_time": "Time",
                    "pace_10k": "Pace (10K)",
                    "counts_for_team": "Counts for team score",
                }
            )
            roster_disp["Counts for team score"] = roster_disp["Counts for team score"].map(
                {True: "Yes (top 8)", False: "No"}
            )

            st.markdown(
                '<div class="section-head">Full roster — fastest to slowest</div>',
                unsafe_allow_html=True,
            )
            st.caption(
                "Team score uses each team’s eight fastest finishers. "
                "Everyone else still appears on the roster and supports the club, but does not add to the team time."
            )
            st.dataframe(
                roster_disp,
                use_container_width=True,
                height=min(520, max(220, 48 + len(roster_disp) * 35)),
                hide_index=True,
            )

    def _page_divisions() -> None:
        st.markdown(
            '<div class="bp label" style="margin-bottom:4px;">By division</div>',
            unsafe_allow_html=True,
        )
        st.caption(
            "Compare **individual** finish patterns, **team** scores vs. roster size, and participation vs. typical speed — "
            "each chart highlights a different slice of the race."
        )
        r1a, r1b = st.columns(2, gap="medium")
        with r1a:
            st.plotly_chart(fig_division_box(runners), use_container_width=True)
        with r1b:
            st.plotly_chart(fig_division_scatter(leaderboard), use_container_width=True)

        st.plotly_chart(fig_division_participation_vs_speed(runners), use_container_width=True)

    def _page_runner_lookup() -> None:
        q = st.text_input(
            "runner_lookup_q",
            key="runner_q",
            label_visibility="hidden",
            placeholder="Search by runner name…",
        )
        if q.strip():
            m = runners["runner_name"].str.contains(q.strip(), case=False, na=False)
            hit = runners.loc[m].nsmallest(1, "runner_seconds") if m.any() else pd.DataFrame()
            if hit.empty:
                st.info("No match.")
            else:
                r0 = hit.iloc[0]
                all_sorted = runners.sort_values("runner_seconds")
                rank = int((all_sorted["runner_seconds"] < r0["runner_seconds"]).sum()) + 1
                n_all = len(runners)
                pct_fast = (1.0 - (rank - 1) / max(1, n_all)) * 100.0
                tw = teams.loc[teams["team_id"] == int(r0["team_id"])].iloc[0]
                label = f"{tw['team_name']} · {tw['category_name']}"
                bib_html = ""
                if "runner_bib" in r0.index and pd.notna(r0["runner_bib"]):
                    bib_html = f'<div style="font-size:11px;color:var(--color-text-secondary);">Bib {int(r0["runner_bib"])}</div>'
                st.markdown(
                    f"""
<div class="runner-row" style="padding:8px 0;">
  <div style="flex:1;">
    <div style="font-size:13px;font-weight:500;">{r0["runner_name"]}</div>
    <div style="font-size:11px;color:var(--color-text-secondary);">{label}</div>
    {bib_html}
  </div>
  <div style="text-align:right;">
    <div style="font-size:13px;font-weight:500;">{r0["runner_time"]}</div>
    <div style="font-size:11px;color:var(--color-text-secondary);">{fmt_pace_compact(r0["runner_seconds"]/10)} · ~{pct_fast:.0f}% faster than field</div>
  </div>
</div>
                    """,
                    unsafe_allow_html=True,
                )
                bar_w = max(4.0, min(96.0, 100.0 * rank / float(n_all)))
                st.markdown(
                    f"""
<div style="background:var(--color-bg-muted);border-radius:clamp(6px,0.8vw,8px);height:clamp(26px,4vw,34px);margin:6px 0 0;position:relative;">
  <div style="position:absolute;left:0;top:0;height:100%;width:{bar_w:.1f}%;background:{C_MARKER};border-radius:inherit;"></div>
</div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.caption("Type to search.")

    nav = st.navigation(
        [
            st.Page(_page_overview, title="Overview", icon="📊", default=True),
            st.Page(_page_my_team, title="My Team", icon="👥"),
            st.Page(_page_divisions, title="Divisions", icon="📈"),
            st.Page(_page_runner_lookup, title="Runner lookup", icon="🔎"),
        ],
        position="sidebar",
        expanded=True,
    )
    nav.run()


if __name__ == "__main__":
    main()
