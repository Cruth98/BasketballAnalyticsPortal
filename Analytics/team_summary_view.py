from Analytics.filter_helpers import build_team_base
from Analytics.filter_helpers import select_practice_dates
from Analytics.filter_helpers import select_possession_types, filter_possession_type_contains
from Analytics.filter_helpers import build_practice_summary
from Analytics.filter_helpers import merge_player_totals
from Analytics.filter_helpers import add_rate_stats
from Analytics.filter_helpers import add_possessions
from Analytics.filter_helpers import add_efficiency_metrics
from Analytics.filter_helpers import select_drills

import streamlit as st
import pandas as pd
import re


def render_team_summary(df: pd.DataFrame) -> None:
    """Team Practice Summary view. Expects fully prepared df (prepare_practice_base)."""

    st.title("Team Practice Summary")
    
    ## ------------------- Filter to team-level possessions (Red / Grey) with valid Action ------------------- ##
    df_team_base = build_team_base(df)

    if df_team_base.empty:
        st.warning("No plays found for Teams 'Red' or 'Grey' with matching the filtered criteria.")
        return

    ## ----------------- DATE SELECTION & FILTERS ------------------------- ##
    selected_dates, df_team = select_practice_dates(df_team_base)

    if not selected_dates:
        st.warning("No practices selected. Please choose at least one date.")
        return

    if df_team.empty:
        st.warning("No practices found for the selected dates.")
        return

    # Remove "No Shot" offensive possessions from TEAM df (always on) ---
    if "ShotRating" in df_team.columns:
        df_team = df_team[df_team["ShotRating"] > 0].copy()
    elif "Shot Quality" in df_team.columns:
        # fallback if you still have old text column
        df_team = df_team[~df_team["Shot Quality"].astype(str).str.contains("No Shot", case=False, na=False)].copy()

    if df_team.empty:
        st.warning("No possessions available.")
        return

    ## --------------- FILTER BY POSSESSION TYPE (if selected) ----------------- ##
    selected_poss_types, df_team = select_possession_types(df_team)

    if df_team.empty:
        st.warning("No possessions remaining after applying filters.")
        return

    ## --------------- FILTER BY DRILL TYPE (if selected) ----------------- ##
    selected_drills, df_team = select_drills(df_team)

    if df_team.empty:
        st.warning("No possessions remaining after applying filters.")
        return

    ## ------------------ GENERATE PRACTICE SUMMARY METRICS ------------------- ##
    practice_summary = build_practice_summary(df_team)

    ## ------------------ MERGE PLAYER TOTALS INTO PRACTICE SUMMARY ------------------- ##
    practice_summary = merge_player_totals(
    practice_summary=practice_summary,
    df_full=df,
    selected_dates=selected_dates,
    selected_poss_types=selected_poss_types,
    selected_drills=selected_drills,
    )

    ## ------------------ ADD RATE STATS & POSSESSIONS TO PRACTICE SUMMARY ------------------- ##
    practice_summary = add_possessions(practice_summary) ## Add posseessions using KenPom possession formula
    practice_summary = add_efficiency_metrics(practice_summary) ## Add efficiency stats like PPP
    practice_summary = add_rate_stats(practice_summary) ## Add rate stats like ORTG, eFG%, AST%, TOV%, etc. using Possessions calculation

    ## ----------------------------- CREATE PRACTICE AVERAGE METRICS DISPLAY ----------------------------- ##
    # 3) Overall metrics across all practices (within selected dates)
    st.subheader("Practice Averages")

    avg_ortg      = practice_summary["ORTG"].mean()
    avg_efg       = practice_summary["eFG"].mean()
    avg_br        = practice_summary["BRperPoss"].mean()
    avg_bt        = practice_summary["BTperPoss"].mean()
    avg_tov       = practice_summary["TOV"].mean()
    avg_ast       = practice_summary["AST"].mean()
    avg_defl      = practice_summary["DEFL"].mean()
    avg_cutast    = practice_summary["CutAST"].mean()
    avg_cutfg     = practice_summary["CutFG"].mean()
    avg_astpct    = practice_summary["ASTpct"].mean()
    avg_tovpct    = practice_summary["TOVpct"].mean()
    avg_orebpct = practice_summary["OREBpct"].mean()
    avg_drebpct = practice_summary["DREBpct"].mean()

    col1, col2, col3, col4, col5, col6, col7, col8, col9, col10, col11, col12 = st.columns(12)
    
    col1.metric("ORTG", f"{avg_ortg:.1f}")
    col2.metric("eFG%", f"{avg_efg:.1f}")
    col3.metric("3FG%", f"{practice_summary['FG3Pct'].mean():.1f}")
    col4.metric("BT Per Poss", f"{avg_bt:.1f}")
    col5.metric("BR Per Poss", f"{avg_br:.1f}")
    col6.metric("Cut AST", f"{avg_cutast:.1f}")
    col7.metric("Cut FGs", f"{avg_cutfg:.1f}")
    col8.metric("AST", f"{avg_ast:.1f}")
    col9.metric("TOV", f"{avg_tov:.1f}")
    col10.metric("AST%", f"{avg_astpct:.1f}%")
    col11.metric("TOV%", f"{avg_tovpct:.1f}%")
    col12.metric("DEFL", f"{avg_defl:.1f}")

    st.markdown("---")

    # 4) Practice table
    st.subheader("Practice Metrics")

    display_df = practice_summary.copy()

    ## Set the practice date as the index for better display
    display_df = display_df.set_index("PracticeDate")

    display_df['Points'] = display_df['Points'].astype(int)
    display_df["FG%"]  = display_df["FGPct"].map(lambda x: f"{x:.1f}%")
    display_df["eFG%"] = display_df["eFG"].map(lambda x: f"{x:.1f}%")
    display_df["FG2%"] = display_df["FG2Pct"].map(lambda x: f"{x:.1f}%")
    display_df["FG3%"] = display_df["FG3Pct"].map(lambda x: f"{x:.1f}%")
    display_df["FT%"]  = display_df["FTPct"].map(lambda x: f"{x:.1f}%")

    display_df["ORTG"]   = display_df["ORTG"].map(lambda x: f"{x:.1f}")
    display_df["PPP"] = display_df["PPP"].map(lambda x: f"{x:.2f}")

    display_df["AvgSQ"] = display_df["AvgSQ"].round(1)
    display_df["BR per Poss"]    = display_df["BRperPoss"].round(1)
    display_df["BT per Poss"]   = display_df["BTperPoss"].round(1)
    display_df['AST%']        = display_df['ASTpct'].map(lambda x: f"{x:.1f}%")
    display_df['TOV%']        = display_df['TOVpct'].map(lambda x: f"{x:.1f}%")
    display_df["OREB%"] = display_df["OREBpct"].map(lambda x: f"{x:.1f}%")
    display_df["DREB%"] = display_df["DREBpct"].map(lambda x: f"{x:.1f}%")
    display_df["Crash%"] = (display_df["Crash"] / (display_df["Crash"] + display_df["No Crash"])* 100).round(1)
    display_df["WolfScore"] = ((display_df["DEFL"]) + (1.25*display_df["BLK"]) + (1.5*display_df["STL"]) + (display_df['DREB']) + (2*display_df["OREB"]) + (2*display_df["CutAST"]) + (2*display_df["CutFG"]) + (2*display_df["AST"]) + (10*(display_df["Crash%"]/100)) - (1.5*display_df["TOV"])).round(1)

    # Create AST/TOV ratio
    if "AST" in display_df.columns and display_df["AST"].sum() == 0 and display_df["TOV"].sum() > 0:
        display_df["AST/TOV"] = display_df["TOV"] * -1 # create negative ratio when no assists
    elif "AST" in display_df.columns and display_df["TOV"].sum() == 0:
        display_df["AST/TOV"] = display_df["AST"]  # create positive ratio when no turnovers (avoid divide by zero)
    else:
        display_df["AST/TOV"] = (display_df["AST"] / display_df["TOV"]).replace([float("inf"), -float("inf")], 0).fillna(0).round(1)

    int_cols = [
        "Possessions", "Points",
        "FGM", "FGA", "FGM2", "FGA2", "FGM3", "FGA3", "FTA", "FTM",
        "AST", "TOV", "STL", "BLK", "DEFL", "CutAST", "CutFG", "OREB", "DREB", "Crash", "No Crash"
    ]
    
    for col in int_cols:
        display_df[col] = display_df[col].astype(int)

    display_df = display_df[
        [
            "Points",
            "Possessions",
            "ORTG",
            "PPP",
            "PPA",
            "AvgSQ",
            "BR per Poss",
            "BT per Poss",
            "FGM", "FGA",
            "FG%", "eFG%",
            "FGM2", "FGA2", "FG2%",
            "FGM3", "FGA3", "FG3%",
            "FTM", "FTA", "FT%",
            "AST", "AST%", "TOV", "TOV%", "AST/TOV","STL", "BLK", "DEFL", "CutAST", "CutFG", "OREB", "DREB", "OREB%", "DREB%", "Crash", "No Crash", "Crash%", "WolfScore"
        ]
    ]

    st.dataframe(display_df, use_container_width=True)

    st.markdown("---")

    # 5) Trend chart
    st.subheader("ORTG, eFG% and 3FG% by Practice")

    trend_df = practice_summary.set_index("PracticeDate")[["ORTG", "eFG", "FG3Pct"]]
    st.line_chart(trend_df)

    ##### ---------------- CREATE METRIC VISUALIZATIONS BASED ON USER SELECTION ------------------------------- #####

    # 6) Custom metric comparison chart (combo plot)
    st.markdown("---")
    st.subheader("Metric Visualizations by Practice")

    # Nice labels → underlying column names in practice_summary
    metric_options = {
        "AvgSQ": "AvgSQ",
        "Points": "Points",
        "PPP": "PPP",
        "BR per Poss": "BRperPoss",
        "BT per Poss": "BTperPoss",
        "ORTG": "ORTG",
        "FG%": "FGPct",
        "eFG%": "eFG",
        "2FG%": "FG2Pct",
        "3FG%": "FG3Pct",
        'AST': 'AST',
        'AST%': 'ASTpct',
        'TOV': 'TOV',
        'TOV%': 'TOVpct',
        'STL': 'STL',
        'BLK': 'BLK',
        'DEFL': 'DEFL',
        'Cut AST': 'CutAST',
        'Cut FGs': 'CutFG',
        'FGM': 'FGM',
        'FGA': 'FGA',
        'FGM2': 'FGM2',
        'FGA2': 'FGA2',
        'FGM3': 'FGM3',
        'FGA3': 'FGA3',
        'OREB%': 'OREBpct',
        'DREB%': 'DREBpct',
    }

    import altair as alt
    import pandas as pd

    # Let user choose which metrics to visualize
    default_metrics = ["AvgSQ", "PPP", "BR per Poss"]
    selected_labels = st.multiselect(
        "Select metrics to plot",
        options=list(metric_options.keys()),
        default=default_metrics,
    )

    if selected_labels:
        selected_cols = [metric_options[label] for label in selected_labels]

        plot_df = practice_summary[["PracticeDate"] + selected_cols].copy()

        # Long format for Altair
        long_df = plot_df.melt(
            id_vars="PracticeDate",
            value_vars=selected_cols,
            var_name="Metric",
            value_name="Value",
        )

        # Map internal column names back to pretty labels
        reverse_label_map = {v: k for k, v in metric_options.items()}
        long_df["Metric"] = long_df["Metric"].map(reverse_label_map)

        combo_chart = (
            alt.Chart(long_df)
            .mark_line(point=True)
            .encode(
                x=alt.X("PracticeDate:T", title="Practice Date"),
                y=alt.Y("Value:Q", title="Value"),
                color=alt.Color("Metric:N", title="Metric"),
                tooltip=[
                    alt.Tooltip("PracticeDate:T", title="Practice"),
                    alt.Tooltip("Metric:N", title="Metric"),
                    alt.Tooltip("Value:Q", title="Value", format=".2f"),
                ],
            )
            .properties(height=350)
        )

        st.altair_chart(combo_chart, use_container_width=True)
    else:
        st.info("Select at least one metric to display the chart.")