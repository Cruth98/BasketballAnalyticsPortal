import streamlit as st
import pandas as pd

from Analytics.loader import load_practice_data
from Analytics.transformations import prepare_practice_base
from Analytics.team_summary_view import render_team_summary
from Analytics.layout import app_header


# ---- PAGE CONFIG (must run before anything else UI-related) ----
st.set_page_config(
    page_title="Bellarmine Basketball Hub",
    page_icon="🏀",    # you can change this or remove it
    layout="wide",
)

@st.cache_data
def get_practice_data() -> pd.DataFrame:
    raw = load_practice_data("Data/PracticeData")
    df = prepare_practice_base(raw)
    return df


def main():
    app_header()
    df = get_practice_data()
    render_team_summary(df)  # <-- Call the team summary view


if __name__ == "__main__":
    main()