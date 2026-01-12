import streamlit as st
from Analytics.layout import app_header
from Team_Analysis import get_practice_data
from Analytics.loader import load_wars_analysis
from Analytics.wars_analysis_helpers import render_wars_summary_filtered, group_by_game_result, group_by_war_result, group_by_war_num
import pandas as pd

app_header()

# ---- Load WARS Analysis Data ----
@st.cache_data
def get_wars_data():
    return load_wars_analysis("Data/WarsAnalysis/WarsAnalysis.xlsx")

## Create WARS Summary View
# ---- Render WARS Analysis Page ----
def main():
    st.title("Full Season WAR Data")

    df = get_wars_data() ## Get the WARS data
    filtered_df = render_wars_summary_filtered(df) ## Call the WARS summary view

    if filtered_df.empty:
        st.warning("WARS dataset is empty.")
        return
    
    ## Group by Game Result & Display the Summary df
    st.subheader("WARS Data by Win v Loss")
    df_by_game_result = group_by_game_result(filtered_df)
    st.dataframe(df_by_game_result, use_container_width=True)

    ## Group by War Result & Display the Summary df
    st.subheader("WARS Data by War Win v Loss")
    df_by_war_result = group_by_war_result(filtered_df)
    st.dataframe(df_by_war_result, use_container_width=True)

    ## Group by War Number & Display the Summary df
    st.subheader("WARS Data by War Number")
    df_by_war_num = group_by_war_num(filtered_df)
    st.dataframe(df_by_war_num, use_container_width=True)

if __name__ == "__main__":
    main()