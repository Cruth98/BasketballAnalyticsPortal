import streamlit as st
from Analytics.layout import app_header
from Team_Analysis import get_practice_data
from Analytics.defense_grading_helpers import load_defense_game_data, transform_df, aggregate_by_defense_per_game, layer_in_metrics, load_full_season_defense_data
import pandas as pd

app_header()

# ---- Load Defense Grading Data ----
@st.cache_data
def get_full_season_defense_data():
    return load_full_season_defense_data(folder_path="Data/DefenseGrading")


# ---- Render Defense Analysis Page ----
def main():
    st.title("Full Season Defense Data")

    df = get_full_season_defense_data()

    if df.empty:
        st.warning("Defense dataset is empty.")
        return

    st.dataframe(df, use_container_width=True)


if __name__ == "__main__":
    main()