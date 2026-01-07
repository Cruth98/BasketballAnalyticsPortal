import streamlit as st
from Analytics.layout import app_header
from Team_Analysis import get_practice_data
from Analytics.defense_grading_helpers import load_defense_game_data, transform_df, aggregate_by_defense_per_game, layer_in_metrics
import pandas as pd

app_header()

# ---- Load Defense Grading Data ----
@st.cache_data

full_season_df = pd.DataFrame()
data_folder = '/Users/mbbfilm/Documents/BasketballAnalyticsPortal/Data/DefenseGrading/'
for file in data_folder:
    game_df = load_defense_game_data(file)
    game_df = transform_df(game_df)
    game_df = aggregate_by_defense_per_game(game_df)
    game_df = layer_in_metrics(game_df)
    full_season_df = pd.concat([full_season_df, game_df], ignore_index=True)


# ---- Render Defense Analysis Page ----
def main():
    st.title("Full Season Defense Data")

    df = full_season_df

    if df.empty:
        st.warning("Defense dataset is empty.")
        return

    st.dataframe(df, use_container_width=True)


if __name__ == "__main__":
    main()