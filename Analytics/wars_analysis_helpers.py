import pandas as pd
import streamlit as st
import re
import numpy as np

def select_opponent(df: pd.DataFrame):
    if "Opponent" not in df.columns:
        return [], df.iloc[0:0].copy()

    available_opponents = sorted(df["Opponent"].dropna().unique())

    selected_opponents = st.multiselect(
        "Select opponents",
        options=available_opponents,
        default=available_opponents,
    )

    if not selected_opponents:
        return [], df.iloc[0:0].copy()

    df_filtered = df[df["Opponent"].isin(selected_opponents)].copy()
    return selected_opponents, df_filtered

def select_war_result(df: pd.DataFrame):
    if "WarResult" not in df.columns:
        return [], df

    war_result_options = sorted(df["WarResult"].dropna().astype(str).unique().tolist())

    selected_war_results = st.multiselect(
        "Select War Results",
        options=war_result_options,
        default=war_result_options,
    )

    if not selected_war_results:
        return [], df.iloc[0:0].copy()

    df_filtered = df[df["WarResult"].isin(selected_war_results)].copy()
    return selected_war_results, df_filtered

def select_game_result(df: pd.DataFrame):
    if "GameResult" not in df.columns:
        return [], df

    game_result_options = sorted(df["GameResult"].dropna().astype(str).unique().tolist())

    selected_game_results = st.multiselect(
        "Select Game Results",
        options=game_result_options,
        default=game_result_options,
    )

    if not selected_game_results:
        return [], df.iloc[0:0].copy()

    df_filtered = df[df["GameResult"].isin(selected_game_results)].copy()
    return selected_game_results, df_filtered

def select_war_num(df: pd.DataFrame):
    if "WarNum" not in df.columns:
        return [], df

    available_war_nums = sorted(df["WarNum"].dropna().unique())

    selected_war_nums = st.multiselect(
        "Select War Numbers",
        options=available_war_nums,
        default=available_war_nums,
    )

    if not selected_war_nums:
        return [], df.iloc[0:0].copy()

    df_filtered = df[df["WarNum"].isin(selected_war_nums)].copy()
    return selected_war_nums, df_filtered

def select_home_game(df: pd.DataFrame):
    if "HomeGame" not in df.columns:
        return [], df

    available_home_games = sorted(df["HomeGame"].dropna().unique())

    selected_home_games = st.multiselect(
        "Select Home Games",
        options=available_home_games,
        default=available_home_games,
    )

    if not selected_home_games:
        return [], df.iloc[0:0].copy()

    df_filtered = df[df["HomeGame"].isin(selected_home_games)].copy()
    return selected_home_games, df_filtered

def select_conf_game(df: pd.DataFrame):
    if "ConfGame" not in df.columns:
        return [], df

    available_conf_games = sorted(df["ConfGame"].dropna().unique())

    selected_conf_games = st.multiselect(
        "Select Conference Games",
        options=available_conf_games,
        default=available_conf_games,
    )

    if not selected_conf_games:
        return [], df.iloc[0:0].copy()

    df_filtered = df[df["ConfGame"].isin(selected_conf_games)].copy()
    return selected_conf_games, df_filtered

def render_wars_summary_filtered(df: pd.DataFrame):
    if df.empty:
        st.info("No data to summarize.")
        return
    
    ## Filter by selected opponents
    selected_opponents, df = select_opponent(df)
    selected_war_results, df = select_war_result(df)
    selected_game_results, df = select_game_result(df)
    selected_war_nums, df = select_war_num(df)
    selected_home_games, df = select_home_game(df)
    selected_conf_games, df = select_conf_game(df)

    total_wars = len(df)
    wars_won = df['WarWon'].sum()
    wars_lost = df['WarLost'].sum()
    war_win_pct = wars_won / total_wars if total_wars > 0 else 0
    avg_bu_score = df['BU_Score'].mean() if total_wars > 0 else 0
    avg_opp_score = df['Opp_Score'].mean() if total_wars > 0 else 0


    st.subheader("War Summary")
    col1, col2, col3, col4, col5, col6 = st.columns(6)
        
    col1.metric("Total Wars", total_wars)
    col2.metric("Wars Won", wars_won)
    col3.metric("Wars Lost", wars_lost)
    col4.metric("War Win %", f"{war_win_pct:.1%}")
    col5.metric("Avg BU Score", f"{avg_bu_score:.1f}")
    col6.metric("Avg Opp Score", f"{avg_opp_score:.1f}")

    st.subheader("Full WARS Data")

    if not df.empty:
        st.dataframe(df, use_container_width=True)

    return df

## Create aggregated WARS summary view with filters
def group_by_game_result(df: pd.DataFrame):
    if df.empty:
        st.info("No data to summarize.")
        return
    
    summary_df = df.groupby('GameResult').agg(
        TotalWars=('WarNum', 'count'),
        WarsWon=('WarWon', 'sum'),
        WarsLost=('WarLost', 'sum'),
        AvgBUScore=('BU_Score', 'mean'),
        AvgOppScore=('Opp_Score', 'mean'),
        AvgScoreDiff=('ScoreDiff', 'mean'),
        MaxScoreDiff=('ScoreDiff', 'max'),
        MinScoreDiff=('ScoreDiff', 'min'),
        MaxBUScore=('BU_Score', 'max'),
        MaxOppScore=('Opp_Score', 'max'),
        MinBUScore=('BU_Score', 'min'),
        MinOppScore=('Opp_Score', 'min'),
    ).reset_index()

    ## Round numeric columns
    numeric_cols = ['AvgBUScore', 'AvgOppScore', 'AvgScoreDiff']
    summary_df[numeric_cols] = summary_df[numeric_cols].round(1)
    summary_df.set_index('GameResult', inplace=True)
    return summary_df

## Create aggregated WARS summary view with filters
def group_by_war_result(df: pd.DataFrame):
    if df.empty:
        st.info("No data to summarize.")
        return

    summary_df = df.groupby('WarResult').agg(
        TotalWars=('WarNum', 'count'),
        AvgBUScore=('BU_Score', 'mean'),
        AvgOppScore=('Opp_Score', 'mean'),
        AvgScoreDiff=('ScoreDiff', 'mean'),
        MaxScoreDiff=('ScoreDiff', 'max'),
        MinScoreDiff=('ScoreDiff', 'min'),
        MaxBUScore=('BU_Score', 'max'),
        MaxOppScore=('Opp_Score', 'max'),
        MinBUScore=('BU_Score', 'min'),
        MinOppScore=('Opp_Score', 'min'),
    ).reset_index()
    summary_df.set_index('WarResult', inplace=True)

    ## Round numeric columns
    numeric_cols = ['AvgBUScore', 'AvgOppScore', 'AvgScoreDiff']
    summary_df[numeric_cols] = summary_df[numeric_cols].round(1)
    return summary_df

## Create aggregated WARS summary view with filters
def group_by_war_num(df: pd.DataFrame):
    if df.empty:
        st.info("No data to summarize.")
        return

    summary_df = df.groupby('WarNum').agg(
        TotalWars=('WarNum', 'count'),
        WarsWon=('WarWon', 'sum'),
        WarsLost=('WarLost', 'sum'),
        AvgBUScore=('BU_Score', 'mean'),
        AvgOppScore=('Opp_Score', 'mean'),
        AvgScoreDiff=('ScoreDiff', 'mean'),
        MaxScoreDiff=('ScoreDiff', 'max'),
        MinScoreDiff=('ScoreDiff', 'min'),
        MaxBUScore=('BU_Score', 'max'),
        MaxOppScore=('Opp_Score', 'max'),
        MinBUScore=('BU_Score', 'min'),
        MinOppScore=('Opp_Score', 'min'),
    ).reset_index()
    summary_df.set_index('WarNum', inplace=True)

    ## Round numeric columns
    numeric_cols = ['AvgBUScore', 'AvgOppScore', 'AvgScoreDiff']
    summary_df[numeric_cols] = summary_df[numeric_cols].round(1)
    summary_df['WinPct'] = ((summary_df['WarsWon'] / summary_df['TotalWars'])*100).round(1)
    return summary_df
