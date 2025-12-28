import streamlit as st
import pandas as pd

from Analytics.loader import load_practice_data
from Analytics.transformations import prepare_practice_base

from Analytics.filter_helpers import (
    select_practice_dates,
    select_possession_types,
    select_drills,
)

from Analytics.player_analysis_helpers import (
    build_player_practice_box_scores,
    build_player_boxscore_view,
)


# ---- Customized Page Configuration ----
st.set_page_config(
    page_title="Bellarmine Basketball Hub",
    page_icon="🏀",    # you can change this or remove it
    layout="wide",
)

@st.cache_data
def get_practice_data() -> pd.DataFrame:
    raw = load_practice_data("Data/PracticeData")
    return prepare_practice_base(raw)


def render_player_analysis(df: pd.DataFrame) -> None:
    st.title("Player Analysis")

    # 1) Apply filters to the FULL df first (so team rows remain available)
    selected_dates, df_filtered = select_practice_dates(df)
    if df_filtered.empty:
        st.warning("No rows after date filter.")
        return

    selected_poss_types, df_filtered = select_possession_types(df_filtered)
    if df_filtered.empty:
        st.warning("No rows after possession type filter.")
        return

    selected_drills, df_filtered = select_drills(df_filtered)
    if df_filtered.empty:
        st.warning("No rows after drill filter.")
        return

    # 2) Now slice player rows out of the filtered full df
    player_mask = df_filtered["Team"].astype(str).str.startswith("#")
    df_players = df_filtered[player_mask].copy()

    if df_players.empty:
        st.warning("No player rows found for the selected filters.")
        return

    # 3) Build cumulative player box score view (wrapper)
    box = build_player_boxscore_view(
        df_players=df_players,
        df_full_filtered=df_filtered,
    )

    box = box.set_index("Player")  # Set Player as the df index
    st.subheader("Player Box Score")

    if box.empty: # Set warning if no stats found
        st.warning("No stats found for the selected filters.")
        return

    # 6) Display the box score
    st.dataframe(box, use_container_width=True)

    ## ----------------- Per-Player Practice Box Scores ----------------- ##
    st.markdown("---")
    st.subheader("Player Practice Recaps")

    player_options = sorted(df_players["Team"].dropna().astype(str).unique().tolist())

    selected_player = st.selectbox(
        "Select a player",
        options=player_options,
    )

    deep = build_player_practice_box_scores(
        df_players=df_players,
        selected_player=selected_player,
    )

    if deep.empty:
        st.info("No practice data available for this player.")
    else:
        st.subheader(f"{selected_player} Practice Box Scores")
        st.dataframe(deep, use_container_width=True)


def main():
    df = get_practice_data()
    render_player_analysis(df)


if __name__ == "__main__":
    main()
