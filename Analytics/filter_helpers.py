import pandas as pd
import streamlit as st
import re
import numpy as np

def build_team_base(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filter to team-level possessions (Red / Grey) with valid Action.
    """
    team_mask = df["Team"].isin(["Red", "Grey"])
    action_mask = (
        df["Action"].notna()
        & (df["Action"] != "")
        & (df["Action"] != "NONE")
    )

    return df[team_mask & action_mask].copy()

## -------------------------------------------------------------------------------------------------------------- ##

def select_practice_dates(df: pd.DataFrame):
    if "PracticeDate" not in df.columns:
        return [], df.iloc[0:0].copy()

    available_dates = sorted(df["PracticeDate"].dropna().dt.date.unique())

    selected_dates = st.multiselect(
        "Select practice dates",
        options=available_dates,
        default=available_dates,
    )

    if not selected_dates:
        return [], df.iloc[0:0].copy()

    df_filtered = df[df["PracticeDate"].dt.date.isin(selected_dates)].copy()
    return selected_dates, df_filtered

def select_possession_types(df: pd.DataFrame):
    if "PossessionType" not in df.columns:
        return [], df

    poss_options = sorted(df["PossessionType"].dropna().astype(str).unique().tolist())

    selected_poss_types = st.multiselect(
        "Select Possession Types",
        options=poss_options,
        default=poss_options,
    )

    if not selected_poss_types:
        return [], df.iloc[0:0].copy()

    df_filtered = df[df["PossessionType"].isin(selected_poss_types)].copy()
    return selected_poss_types, df_filtered

## -------------------------------------------------------------------------------------------------------------- ##

def select_drills(df: pd.DataFrame):
    if "LiveDrills" not in df.columns:
        return [], df

    drill_options = sorted(df["LiveDrills"].dropna().astype(str).unique().tolist())

    selected_drills = st.multiselect(
        "Select Drills",
        options=drill_options,
        default=drill_options,
    )

    if not selected_drills:
        return [], df.iloc[0:0].copy()

    df_filtered = df[df["LiveDrills"].isin(selected_drills)].copy()
    return selected_drills, df_filtered


## -------------------------------------------------------------------------------------------------------------- ##

def filter_possession_type_contains(df: pd.DataFrame, selected_poss_types):
    """
    Apply a PossessionType filter using contains() for cases where
    values may be comma-separated or multi-labeled.

    Returns df unchanged if PossessionType missing or no selections provided.
    """
    if not selected_poss_types or "PossessionType" not in df.columns:
        return df

    pattern = "|".join(map(re.escape, selected_poss_types))
    return df[df["PossessionType"].astype(str).str.contains(pattern, na=False)].copy()

## -------------------------------------------------------------------------------------------------------------- ##

def build_practice_summary(df_team: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate team possessions into per-practice summary metrics.
    Expects df_team to already be filtered (dates, possession types, ShotRating > 0, etc.)
    """
    practice_summary = (
        df_team
        .groupby("PracticeDate")
        .agg(
            ShotRating=("ShotRating", "sum"),
            BallReversals=("BallRevCnt", "sum"),
            BoxTouches=("BoxTouchCnt", "sum"),
            Points=("Points", "sum"),
            FGM2=("FGM2", "sum"),
            FGA2=("FGA2", "sum"),
            FGM3=("FGM3", "sum"),
            FGA3=("FGA3", "sum"),
            FGM=("FGM", "sum"),
            FGA=("FGA", "sum"),
            FTA=("FTA", "sum"),
            FTM=("FTM", "sum"),
            PossCount=("UID", "count"),
        )
        .reset_index()
        .sort_values("PracticeDate")
    )

    # Shooting percentages
    practice_summary["FGPct"]  = ((practice_summary["FGM"]  / practice_summary["FGA"])  * 100).round(1)
    practice_summary["FG2Pct"] = ((practice_summary["FGM2"] / practice_summary["FGA2"]) * 100).round(1)
    practice_summary["FG3Pct"] = ((practice_summary["FGM3"] / practice_summary["FGA3"]) * 100).round(1)
    practice_summary["FTPct"]  = ((practice_summary["FTM"]  / practice_summary["FTA"])  * 100).round(1)
    practice_summary["eFG"]    = (
        ((practice_summary["FGM2"] + 1.5 * practice_summary["FGM3"]) / practice_summary["FGA"]) * 100
    ).round(1)

    # Points per Attempt (PPA)
    practice_summary["PPA"] = (practice_summary["Points"] / practice_summary["FGA"]).replace(
        [float("inf"), -float("inf")], 0
    ).fillna(0).round(1)

    practice_summary['AvgSQ'] = (practice_summary['ShotRating'] / practice_summary['FGA']).fillna(0).round(1)

    # Avoid inf/NaN in % cols when denominators are zero
    for col in ["FGPct", "FG2Pct", "FG3Pct", "FTPct", "eFG"]:
        practice_summary[col] = practice_summary[col].replace([pd.NA, float("inf"), -float("inf")], 0).fillna(0)

    return practice_summary

## -------------------------------------------------------------------------------------------------------------- ##

def merge_player_totals(
    practice_summary: pd.DataFrame,
    df_full: pd.DataFrame,
    selected_dates,
    selected_poss_types,
    selected_drills=None,
    player_stat_cols=None,
) -> pd.DataFrame:
    """
    Aggregate player-row stats per practice and merge into practice_summary.

    Player rows are identified where Team starts with '#'.
    Applies the same date + possession type + drill filters used in the team view.
    """
    if player_stat_cols is None:
        player_stat_cols = ["AST", "TOV", "STL", "BLK", "DEFL", "CutAST", "CutFG", "OREB", "DREB"]

    df = df_full.copy()

    # Player rows = Team starts with '#'
    team_str = df["Team"].astype(str)
    player_mask = team_str.str.startswith("#")

    # Date filter aligned to team selection
    date_mask = df["PracticeDate"].dt.date.isin(selected_dates)

    df_players = df[player_mask & date_mask].copy()

    # Apply possession type filter if selections exist
    if selected_poss_types and "PossessionType" in df_players.columns:
        df_players = df_players[df_players["PossessionType"].isin(selected_poss_types)].copy()

    # Apply drill filter if selections exist
    if selected_drills and "LiveDrills" in df_players.columns:
        df_players = df_players[df_players["LiveDrills"].isin(selected_drills)].copy()

    stat_cols_present = [c for c in player_stat_cols if c in df_players.columns]

    if stat_cols_present and not df_players.empty:
        player_practice_totals = (
            df_players
            .groupby("PracticeDate")[stat_cols_present]
            .sum()
            .reset_index()
        )

        practice_summary = practice_summary.merge(
            player_practice_totals,
            on="PracticeDate",
            how="left",
        )

        for col in stat_cols_present:
            practice_summary[col] = practice_summary[col].fillna(0)
    else:
        # Ensure columns exist so downstream display doesn't break
        for col in player_stat_cols:
            if col not in practice_summary.columns:
                practice_summary[col] = 0

    return practice_summary

def add_possessions(practice_summary: pd.DataFrame) -> pd.DataFrame:
    """
    Adds formula possessions that automatically recompute after filters.

    Requires: FGA, OREB, TOV, FTA
    Keeps: PossCount if present (row count diagnostic)
    Creates: Possessions (formula)
    """
    df = practice_summary.copy()

    for col in ["FGA", "OREB", "TOV", "FTA"]:
        if col not in df.columns:
            raise ValueError(f"Missing required column for possessions formula: {col}")

    df["Possessions"] = (
        df["FGA"].fillna(0)
        - df["OREB"].fillna(0)
        + df["TOV"].fillna(0)
        + (0.475 * df["FTA"].fillna(0))
    )

    return df

## -------------------------------------------------------------------------------------------------------------- ##

def add_rate_stats(practice_summary: pd.DataFrame) -> pd.DataFrame:
    """
    Add rate-based metrics to practice_summary:
    - ASTpct, TOVpct (% of possessions)
    - OREBpct, DREBpct (share of total rebounds)
    - Using possessions formula from add_possessions()
    """
    ps = practice_summary.copy()

    if "Possessions" in ps.columns:
        denom = ps["Possessions"].replace(0, pd.NA)

        ps["ASTpct"] = (ps.get("AST", 0) / denom).fillna(0) * 100
        ps["TOVpct"] = (ps.get("TOV", 0) / denom).fillna(0) * 100

        # Add these for consistency with the new possessions denominator
        ps["BTperPoss"] = (ps.get("BoxTouches", 0) / denom).fillna(0)
        ps["BRperPoss"] = (ps.get("BallReversals", 0) / denom).fillna(0)


    else:
        ps["ASTpct"] = 0
        ps["TOVpct"] = 0
        ps["BTperPoss"] = 0
        ps["BRperPoss"] = 0

    if "OREB" in ps.columns and "DREB" in ps.columns:
        oreb = pd.to_numeric(ps["OREB"], errors="coerce").fillna(0)
        dreb = pd.to_numeric(ps["DREB"], errors="coerce").fillna(0)

        reb_denom = (oreb + dreb).astype(float)

        ps["OREBpct"] = np.where(reb_denom > 0, (oreb / reb_denom) * 100, 0.0)
        ps["DREBpct"] = np.where(reb_denom > 0, (dreb / reb_denom) * 100, 0.0)
    else:
        ps["OREBpct"] = 0
        ps["DREBpct"] = 0

    return ps

## -------------------------------------------------------------------------------------------------------------- ##

def add_efficiency_metrics(practice_summary: pd.DataFrame) -> pd.DataFrame:
    """
    Add efficiency metrics.
    Current definition:
      ORTG = PPP * 100
    """
    df = practice_summary.copy()

    denom = df["Possessions"].replace(0, pd.NA)

    df["PPP"] = (df["Points"] / denom).fillna(0)
    df["ORTG"] = (df["PPP"] * 100).round(1)

    return df