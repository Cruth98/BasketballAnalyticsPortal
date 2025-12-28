import streamlit as st
from Analytics.layout import app_header
from Team_Analysis import get_practice_data

app_header()
df = get_practice_data()

st.title("Lineup Analysis Coming Soon")