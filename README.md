# Bellarmine University Basketball Analytics Portal

A production-deployed, end-to-end analytics platform built for a Division I men's basketball program. This is not a class project or demo — it is a fully operational decision-support system actively used by coaches and staff to evaluate player performance, practice efficiency, and defensive execution across the 2025-26 season.

The system was built independently by a single analyst. Staff at the University of Kentucky noted it contained analytical capabilities beyond what their own platform provided.

**Live Application:** https://bellarmineanalytics.streamlit.app/  
**Stack:** Python · Streamlit · Pandas · Plotly · NumPy · GitHub

---

## Architecture Overview

The portal is built as a modular Streamlit multi-page application with a clean separation between data ingestion, transformation, analytics logic, and presentation layers.

```
BasketballAnalyticsPortal/
├── Analytics/                          # All business logic — no UI code
│   ├── loader.py                       # Data ingestion & ETL pipelines
│   ├── transformations.py              # Possession-level transformation pipeline
│   ├── filter_helpers.py               # Reusable filter components
│   ├── player_analysis_helpers.py      # Player box score & WolfScore engine
│   ├── team_summary_view.py            # Team-level practice summary rendering
│   ├── wars_analysis_helpers.py        # WARS game metric engine
│   ├── defense_grading_helpers.py      # Defensive grading & aggregation
│   └── layout.py                       # Shared UI layout utilities
├── Data/
│   ├── PracticeData/                   # Season-long practice CSVs (YYMMDD format)
│   └── DefenseGrading/                 # Per-opponent defensive grading CSVs
├── Assets/                             # Branding
└── .streamlit/config.toml              # App configuration
```

---

## Data Pipeline

### Sources Integrated

Four independent data sources are ingested, transformed, and unified:

1. **Practice tracking data** — possession-level CSV exports from coaching staff film tagging software (YYMMDD filename convention); 18+ files ingested dynamically for the full season
2. **WARS game data** — team-defined game metric tracking from Excel (GameOrder, WarNum, half-level scoring segments, win/loss outcomes)
3. **Defensive grading data** — per-opponent defensive execution CSVs grading every defensive possession by type, shot quality, and outcome
4. **Player roster/lineup data** — embedded in practice possession tracking via on-court player tagging

### ETL Design

- **Dynamic file ingestion**: `loader.py` recursively loads all practice CSVs from a folder, parsing dates from filenames (YYMMDD → `pd.Timestamp`) and concatenating into a season-long DataFrame
- **UID generation**: each possession is assigned a unique composite identifier (`PracticeDate_Team_clipID`) for traceability
- **Modular transformation pipeline**: `transformations.py` runs possession data through a sequential `.pipe()` chain:
  - Default label imputation
  - Duplicate label cleaning
  - Non-actionable possession filtering
  - Shot result computation (regex-based action parsing → `ShotResult`)
  - Shooting metrics derivation (FGA/FGM splits, FTA, eFG%, EstPPP)
  - On-court one-hot encoding (player presence per possession)
  - Player stat extraction from action strings (AST, TOV, STL, BLK, DEFL, OREB, DREB, Crash%)
  - Ordered categorical type setting

---

## Analytics Modules

### 1. Team Practice Summary

Aggregated team-level offensive performance across any selection of practice dates, possession types, and drill categories.

**Metrics computed:**
- Points per possession (PPP), estimated PPP (EstPPP)
- FGA/FGM splits by 2PT, 3PT, FT
- eFG%, FG%, FT%
- Ball reversal counts and shot quality distribution (A/B/C/D grades)
- Box touch frequency analysis
- Drill-level and possession-type breakdowns (Half Court, Transition, Special, etc.)

### 2. Player Analysis

Individual player performance across any filtered subset of practices.

**Metrics computed:**
- Full shooting box score: Points, FGM/FGA (2PT/3PT), FT%, 2FG%, 3FG%, FG%, eFG%
- Advanced player stats: AST, TOV, AST/TOV ratio, STL, BLK, Deflections, OREB, DREB
- Cut efficiency: Cut Assists, Cut FGs
- Crash rate (OREB attempt rate)
- **WolfScore** — a composite player evaluation metric combining defensive activity, playmaking, efficiency, and hustle into a single weighted score:

```
WolfScore = DEFL + (1.25 × BLK) + (1.5 × STL) + DREB + (2 × OREB)
          + (2 × CutAST) + (2 × CutFG) + (2 × AST)
          + (10 × Crash%) - (1.5 × TOV)
```

- On-court possession tracking per player
- Average Shot Quality (AvgSQ) — quality of shot attempts generated

### 3. Defense Grading

Per-opponent and aggregate defensive execution analysis across 8 graded games.

**Metrics computed:**
- FGA/FGM/Points allowed by defensive scheme type
- Shot quality allowed (SQ grade) by coverage
- Turnovers forced, offensive rebounds allowed, paint touches allowed
- eFG% and PPP allowed by defense type
- Opponent-by-opponent comparative views

**Opponents graded:** Chattanooga, EKU, Lipscomb, NKU, Quincy, UCA, UNA, West Georgia

### 4. WARS Analysis

WARS (a team-defined scoring segment metric) tracks performance across discrete game segments — providing a granular view of momentum and execution beyond final score.

**Metrics computed:**
- War Win % by game result, war number, home/away, conference/non-conference
- Average BU Score and Opponent Score per war segment
- Score differential distribution (max, min, avg)
- Win/loss correlation between war outcomes and game outcomes
- Fully filterable by opponent, war result, game result, war number, home/away, conference status

### 5. Lineup Analysis *(scaffolded — not yet deployed)*

### 6. Game Analysis *(scaffolded — not yet deployed)*

---

## Technical Highlights

- **Separation of concerns**: all analytics logic lives in `Analytics/`; Streamlit pages contain no business logic
- **Reusable filter architecture**: `filter_helpers.py` provides composable, stateful filter functions used consistently across all views
- **Regex-based action parsing**: shot results extracted from free-text action strings using pattern matching (`+2`, `-3`, `1`, etc.) with edge case handling
- **Ordered categoricals**: shot quality and reversal labels set as ordered `pd.Categorical` types for correct sort behavior in charts
- **Plotly visualizations**: interactive charts throughout, rendered via `st.plotly_chart`
- **Git + GitHub deployment**: version controlled and deployed to Streamlit Community Cloud via GitHub integration

---

## Repository

**GitHub:** https://github.com/Cruth98/BasketballAnalyticsPortal  
**Live App:** https://bellarmineanalytics.streamlit.app/
