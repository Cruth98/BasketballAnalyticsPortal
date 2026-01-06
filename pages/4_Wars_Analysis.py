import streamlit as st
from Analytics.layout import app_header
from Team_Analysis import get_practice_data
from Analytics.loader import load_wars_analysis

app_header()

# ---- Load WARS Analysis Data ----
@st.cache_data
def get_wars_data():
    return load_wars_analysis("Data/WarsAnalysis/WarsAnalysis.xlsx")

# ---- Render WARS Analysis Page ----
def main():
    st.title("Full Season WAR Data")

    df = get_wars_data()

    if df.empty:
        st.warning("WARS dataset is empty.")
        return

    st.dataframe(df, use_container_width=True)


if __name__ == "__main__":
    main()