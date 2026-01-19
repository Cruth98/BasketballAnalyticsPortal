import streamlit as st
from Analytics.layout import app_header
from Team_Analysis import get_practice_data
from Analytics.defense_grading_helpers import (
    load_defense_game_data, transform_df, aggregate_full_df, layer_in_metrics, 
    load_full_season_defense_data, render_defense_summary_filtered, aggregate_by_opponent, aggregate_by_defense, create_defense_visual
)
import pandas as pd

app_header()

# ---- Load Defense Grading Data ----
@st.cache_data
def get_full_season_defense_data():
    return load_full_season_defense_data(folder_path="Data/DefenseGrading")


# ---- Render Defense Analysis Page ----
def main():
    st.title("Full Season Defense Data")

    df = get_full_season_defense_data() ## Get the Defense data
    filtered_df = render_defense_summary_filtered(df) ## Call the Defense summary view

    if filtered_df.empty:
        st.warning("Defense dataset is empty.")
        return
    
    ## Group by Opponent
    df_by_opponent = aggregate_by_opponent(filtered_df)
    
    ## Display Defense by Opponent in Streamlit
    st.subheader("Defense Data by Opponent")
    st.dataframe(df_by_opponent, use_container_width=True)

    ## Group by DefenseType
    df_by_defense = aggregate_by_defense(filtered_df)

    ## Display Defense by Defense Type in Streamlit
    st.subheader("Defense Data by Defense Type")
    st.dataframe(df_by_defense, use_container_width=True)

    ## Create Visualizations
    st.subheader("Defensive Metrics by Defense Type")
    metric_options = {
        'DRTG': 'Defense Rating',
        'FGM2': 'Made 2s',
        'FGA2': 'Attempted 2s',
        'FGM3': 'Made 3s',
        'FGA3': 'Attempted 3s',
        'FGM': 'Total Made Shots',
        'FGA': 'Total Attempted Shots',
        'FG%': 'Field Goal Percentage',
        'eFG%': 'Effective Field Goal Percentage',
        '2FG%': '2-Point Field Goal Percentage',
        '3FG%': '3-Point Field Goal Percentage',
        '3PAr': '3-Point Attempt Rate',
        'Possessions': 'Total Possessions',
        'PPA': 'Points Per Attempt',
        'PPP': 'Points Per Possession',
        'Points': 'Total Points Allowed',
        'TOV': 'TOVs Forced',
        'PaintTouch': 'Paint Touches Allowed',
        'OREB': 'Offensive Rebounds Allowed',
        'OppOREB%': 'Opponent Offensive Rebound Percentage',
        'PT%': 'Paint Touch Percentage',
        'OppTOV%': 'Opponent Turnover Percentage',
        'Game%': 'Percentage of Game Played',
        'AvgSQ': 'Average Shot Quality',
    }
    
    selected_metric = st.selectbox(
        label="Select metric to plot",
        options=list(metric_options.keys())
    )
    create_defense_visual(df_by_defense, metric=selected_metric)

if __name__ == "__main__":
    main()