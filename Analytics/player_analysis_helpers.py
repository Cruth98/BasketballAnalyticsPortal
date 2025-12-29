import pandas as pd
import numpy as np

def build_player_box_score(df_players: pd.DataFrame) -> pd.DataFrame:
    """
    One row per player. Sums player stat columns + shooting totals from existing columns
    (Points, FGM2/FGA2, FGM3/FGA3), then computes 2FG%, 3FG%, eFG%.
    Expects df_players already filtered (dates/poss types/drills) and player rows only.
    """

    if df_players.empty:
        return pd.DataFrame()

    df = df_players.copy()

    # These should exist from the 'transformations.py' pipeline
    needed_numeric = ["Points", "FGM2", "FGA2", "FGM3", "FGA3", "FTM", "FTA", "ShotRating"]
    for c in needed_numeric:
        if c not in df.columns:
            df[c] = 0

    # Player stat cols you already created from Action
    stat_cols = ["AST", "TOV", "STL", "BLK", "DEFL", "CutAST", "CutFG", "OREB", "DREB", "Crash", "No Crash"]
    for c in stat_cols:
        if c not in df.columns:
            df[c] = 0

    agg_cols = stat_cols + needed_numeric

    box = (
        df.groupby("Team")[agg_cols]
        .sum()
        .reset_index()
        .rename(columns={"Team": "Player"})
        .sort_values("Player")
    )

    # Derived totals
    box["FGA"] = box["FGA2"] + box["FGA3"]
    box["FGM"] = box["FGM2"] + box["FGM3"]

    # Percentages (avoid divide-by-zero)
    box["FT%"] = np.where(box["FTA"] > 0, (box["FTM"] / box["FTA"]) * 100, 0.0)
    box["2FG%"] = np.where(box["FGA2"] > 0, (box["FGM2"] / box["FGA2"]) * 100, 0.0)
    box["3FG%"] = np.where(box["FGA3"] > 0, (box["FGM3"] / box["FGA3"]) * 100, 0.0)
    box["FG%"] = np.where(box["FGA"]  > 0, (box["FGM"]  / box["FGA"])  * 100, 0.0)
    box["eFG%"] = np.where(box["FGA"]  > 0, ((box["FGM2"] + (1.5 * box["FGM3"])) / box["FGA"]) * 100, 0.0)
    box["PPA"] = (box["Points"] / box["FGA"]).replace([float("inf"), -float("inf")], 0).fillna(0).round(2)
    box["AvgSQ"] = (box["ShotRating"] / (box["FGA"]+box["FTA"])).replace([float("inf")], 0).fillna(0).round(1)
    box["Crash%"] = (box["Crash"] / (box["Crash"] + box["No Crash"]).replace(0, np.nan) * 100).round(1)

    # Create AST/TOV ratio
    box["AST/TOV"] = 0.0
    mask_no_ast = (box["AST"] == 0) & (box["TOV"] > 0)
    mask_no_tov = (box["AST"] > 0) & (box["TOV"] == 0)
    mask_both   = (box["AST"] > 0) & (box["TOV"] > 0)
    box.loc[mask_no_ast, "AST/TOV"] = -box.loc[mask_no_ast, "TOV"]
    box.loc[mask_no_tov, "AST/TOV"] = box.loc[mask_no_tov, "AST"]
    box.loc[mask_both,   "AST/TOV"] = (box.loc[mask_both, "AST"] / box.loc[mask_both, "TOV"])
    box["AST/TOV"] = box["AST/TOV"].round(1)

    # Round for display friendliness (still numeric)
    box["FT%"] = box["FT%"].round(1)
    box["2FG%"] = box["2FG%"].round(1)
    box["3FG%"] = box["3FG%"].round(1)
    box["eFG%"] = box["eFG%"].round(1)
    box["FG%"] = box["FG%"].round(1)
    box["AvgSQ"] = box["AvgSQ"].round(1)

    ## Drop ShotRating after use
    if "ShotRating" in box.columns:
        box = box.drop(columns=["ShotRating"])

    return box

def merge_oncourt_possessions(
    box: pd.DataFrame,
    df_filtered: pd.DataFrame,
    player_col_prefix: str = "#",
    team_rows=("Red", "Grey"),
) -> pd.DataFrame:
    """
    Adds OnCourtPoss to the player box score by:
      - filtering df_filtered to TEAM rows (Red/Grey possessions)
      - summing each player's one-hot on-court column (0/1) across those possessions
      - merging counts onto box (player rows)

    IMPORTANT:
    - df_filtered must already have the UI filters applied (date/poss type/drill).
    - df_filtered must include one-hot player columns (e.g. '#12 Myles Watkins').

    Returns: box with an added 'OnCourtPoss' column (int).
    """

    if box.empty or df_filtered.empty:
        box = box.copy()
        box["OnCourtPoss"] = 0
        return box

    df = df_filtered.copy()

    # 1) Ensure only TEAM rows (Red/Grey possessions)
    if "Team" in df.columns:
        df_team_poss = df[df["Team"].isin(team_rows)].copy()
    else:
        df_team_poss = df.copy()

    if df_team_poss.empty:
        box = box.copy()
        box["OnCourtPoss"] = 0
        return box

    # 2) Ensure one-hot player columns exist
    onehot_player_cols = [c for c in df_team_poss.columns if str(c).startswith(player_col_prefix)]
    if not onehot_player_cols:
        box = box.copy()
        box["OnCourtPoss"] = 0
        return box

    # 3) Aggregate on-court possession counts per player (cast to numeric in case any columns are object dtype)
    poss_counts = (
        df_team_poss[onehot_player_cols]
        .apply(pd.to_numeric, errors="coerce")
        .fillna(0)
        .sum(axis=0)
        .astype(int)
        .rename("OnCourtPoss")
        .reset_index()
        .rename(columns={"index": "Player"})
    )

    # 4) Merge into box
    out = box.copy()
    out = out.merge(poss_counts, on="Player", how="left")
    out["OnCourtPoss"] = out["OnCourtPoss"].fillna(0).astype(int)

    return out

def add_player_rate_stats(box: pd.DataFrame, poss_col: str = "OnCourtPoss") -> pd.DataFrame:
    """
    Adds player rate stats that respond to filters:
      - AST% = AST / possessions
      - TOV% = TOV / possessions
    Expects box already includes AST, TOV and poss_col.
    """
    b = box.copy()

    # Ensure numeric
    for c in ["AST", "TOV", poss_col]:
        if c in b.columns:
            b[c] = pd.to_numeric(b[c], errors="coerce").fillna(0)

    denom = b[poss_col].replace(0, np.nan) if poss_col in b.columns else np.nan

    # Possession-based rates (use OnCourtPoss so it updates with filters)
    b["AST%"] = ((b.get("AST", 0) / denom) * 100).round(1)
    b["TOV%"] = ((b.get("TOV", 0) / denom) * 100).round(1)

    # Clean up NaNs from divide-by-zero
    for c in ["AST%", "TOV%"]:
        b[c] = b[c].fillna(0)

    return b

def build_player_practice_box_scores(
    df_players: pd.DataFrame,
    selected_player: str,
) -> pd.DataFrame:
    """
    Build per-practice box scores for a single player.
    Expects df_players to already be filtered by date / possession type / drill.
    """

    df_one = df_players[df_players["Team"].astype(str) == selected_player].copy()

    if df_one.empty:
        return pd.DataFrame()

    stat_cols = [
        "Points",
        "FGM2", "FGA2",
        "FGM3", "FGA3",
        "FGM", "FGA",
        "FTM", "FTA",
        "AST", "TOV", "STL", "BLK", "DEFL",
        "CutAST", "CutFG",
        "ShotRating", "OREB", "DREB", "Crash", "No Crash", 
    ]

    stat_cols = [c for c in stat_cols if c in df_one.columns]

    box = (
        df_one
        .groupby("PracticeDate")[stat_cols]
        .sum(numeric_only=True)
        .reset_index()
        .sort_values("PracticeDate")
    )

    # Shooting percentages
    if {"FGM2", "FGA2"}.issubset(box.columns):
        box["FG2Pct"] = ((box["FGM2"] / box["FGA2"]).replace([float("inf")], 0).fillna(0) * 100).round(1)

    if {"FGM3", "FGA3"}.issubset(box.columns):
        box["FG3Pct"] = ((box["FGM3"] / box["FGA3"]).replace([float("inf")], 0).fillna(0) * 100).round(1)

    if {"FGM", "FGA"}.issubset(box.columns):
        box["FGPct"] = ((box["FGM"] / box["FGA"]).replace([float("inf")], 0).fillna(0) * 100).round(1)
        box["eFGPct"] = (((box["FGM2"] + (box.get("FGM3", 0) *1.5)) / box["FGA"]) \
            .replace([float("inf")], 0).fillna(0) * 100).round(1)

    # Avg Shot Quality (using your SumSQ / FGA + FTA logic)
    if "ShotRating" in box.columns and "FGA" in box.columns and "FTA" in box.columns:
        box["AvgSQ"] = (box["ShotRating"] / (box["FGA"]+box["FTA"])).replace([float("inf")], 0).fillna(0)

    # Create Crash%
    box["Crash%"] = (box["Crash"] / (box["Crash"] + box["No Crash"]).replace(0, np.nan) * 100).round(1)

    # Create AST/TOV ratio
    box["AST/TOV"] = 0.0
    mask_no_ast = (box["AST"] == 0) & (box["TOV"] > 0)
    mask_no_tov = (box["AST"] > 0) & (box["TOV"] == 0)
    mask_both   = (box["AST"] > 0) & (box["TOV"] > 0)
    box.loc[mask_no_ast, "AST/TOV"] = -box.loc[mask_no_ast, "TOV"]
    box.loc[mask_no_tov, "AST/TOV"] = box.loc[mask_no_tov, "AST"]
    box.loc[mask_both,   "AST/TOV"] = (box.loc[mask_both, "AST"] / box.loc[mask_both, "TOV"])
    box["AST/TOV"] = box["AST/TOV"].round(1)

    pct_cols = ["FG2Pct", "FG3Pct", "FGPct", "eFGPct"]
    for c in pct_cols:
        if c in box.columns:
            box[c] = box[c].round(1)

    box["PPA"] = (box["Points"] / box["FGA"]).replace([float("inf"), -float("inf")], 0).fillna(0).round(2)

    if "AvgSQ" in box.columns:
        box["AvgSQ"] = box["AvgSQ"].round(1)

    # Drop ShotRating after use
    if "ShotRating" in box.columns:
        box = box.drop(columns=["ShotRating"])

    # Apply the SAME formatting used in the main player box score
    box = format_player_box_score(box)

    # Set PracticeDate as index (final step)
    box["PracticeDate"] = pd.to_datetime(box["PracticeDate"], errors="coerce").dt.date
    box = box.set_index("PracticeDate")

    return box

##### TEMPORARY HELPERS FOR CONSOLIDATION #####

def format_player_box_score(box: pd.DataFrame) -> pd.DataFrame:
    """
    Format player box score for display:
    1) Rename stat columns to basketball-friendly headers (e.g., FG3Pct -> 3FG%)
    2) Reorder columns into a standard box-score layout
    Safe: only touches columns that exist.
    """
    if box.empty:
        return box

    # ---- Rename for display ----
    rename_map = {
        "FGPct": "FG%",
        "FG2Pct": "2FG%",
        "FG3Pct": "3FG%",
        "eFG": "eFG%",
        "eFGPct": "eFG%",
        "FTPct": "FT%",
        "ASTpct": "AST%",
        "TOVpct": "TOV%",
    }
    box = box.rename(columns={k: v for k, v in rename_map.items() if k in box.columns})

    # ---- Standard order ----
    preferred = [
        "Player",
        "Possessions",
        "Points",
        "ORTG",
        "FGM", "FGA", "AvgSQ", "PPA", "FG%",
        "FGM2", "FGA2", "2FG%",
        "FGM3", "FGA3", "3FG%", "eFG%",
        "FTM", "FTA", "FT%",
        "AST", "AST%",
        "TOV", "TOV%", "AST/TOV",
        "STL", "BLK", "DEFL",
        "CutAST", "CutFG",
    ]

    existing = [c for c in preferred if c in box.columns]
    remaining = [c for c in box.columns if c not in existing]
    return box[existing + remaining]

def build_player_boxscore_view(df_players: pd.DataFrame, df_full_filtered: pd.DataFrame) -> pd.DataFrame:
    """
    Build the cumulative player box score using the same filtered universe
    as the UI filters (dates/poss types/drills).

    df_players: player rows only (Team starts with '#')
    df_full_filtered: full filtered df (player + team rows) used for on-court possessions
    """
    box = build_player_box_score(df_players)
    box = merge_oncourt_possessions(box, df_full_filtered)
    box = add_player_rate_stats(box)
    box = format_player_box_score(box)
    return box