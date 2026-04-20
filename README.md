# Vancouver Sun Run — Team results (2026)

Interactive **Streamlit** dashboard for the **Vancouver Sun Run 10K** corporate / club **team competition**: explore race-wide stats, division comparisons, a single team’s scoring eight and full roster, and runner lookup. Data is loaded from CSV extracts of the public Sportstats results page.

---

## Features

| Area | What you get |
|------|----------------|
| **Overview** | KPIs, finish-time distribution (with field context), runners per division, cumulative finisher curve, searchable fastest-teams preview with overall rank |
| **My Team** | Pick a team, see top-8 team score, scoring-eight chart, full roster with who counts toward the team time |
| **Divisions** | Finish distributions by division, team scatter (roster size vs. top-8 time), participation vs. typical speed |
| **Runner lookup** | Search by name, see placement vs. the full field |

The UI uses a dark theme with **Plotly** charts aligned to the app shell.

---

## Stack

- **Python 3.11+** (see `sunrun.yml`)
- **Streamlit** ≥ 1.36 (`st.navigation` for multipage routing)
- **Pandas**, **Plotly**

---

## Quick start

### Option A — Conda (recommended)

```bash
conda env create -f sunrun.yml
conda activate sunrun
streamlit run app.py
```

### Option B — pip only

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Open the URL shown in the terminal (usually `http://localhost:8501`).

---

## Data pipeline

1. **Source:** public HTML from Sportstats (multiple `<pre>` blocks, one per division category).  
   - [10 km leaderboard](https://sportstats.one/event/vancouver-sun-run/leaderboard/146265)  
   - [2026 team results page](https://cdn-1.sportstats.one/SunRun2026_Teams.htm)

2. **Extract:** run `notebooks/sunrun_extract.ipynb` from the **repository root** so outputs land in `data/processed/`:
   - `sunrun_categories.csv`
   - `sunrun_teams.csv`
   - `sunrun_runners.csv`

3. **Parser:** `notebooks/sunrun_parse.py` — concatenates all `<pre>` blocks and parses team lines, runner lines (including two runners per line), times (`MM:SS` / `H:MM:SS`), and bibs.

The app **does not** call the network at runtime; it only reads the CSVs under `data/processed/`.

---

## Project layout

```
├── app.py                 # Streamlit entrypoint
├── requirements.txt
├── sunrun.yml             # Conda env (Python 3.11 + pip deps)
├── notebooks/
│   ├── sunrun_extract.ipynb
│   └── sunrun_parse.py
├── data/
│   ├── processed/         # Generated CSVs (commit or regenerate locally)
│   └── SunRun2026_Teams_raw.htm   # Optional local copy; often gitignored
└── LICENSE
```

---

## Configuration

- **Secrets:** optional `.env` (gitignored) if you extend the project with API keys; not required for the current dashboard.
- **Large HTML:** `data/SunRun2026_Teams_raw.htm` may be listed in `.gitignore`; you can rely on the notebook download from `SOURCE_URL` instead.

---

## License

MIT — see [LICENSE](LICENSE).

---

## Disclaimer

This project is an **unofficial** fan / analysis tool. Team and athlete names and times come from **public** race results published by the event’s timing provider; verify official standings on the organiser’s or Sportstats’ site if needed.
