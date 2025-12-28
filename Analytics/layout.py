import streamlit as st
from pathlib import Path

def app_header():
    """
    Displays the Bellarmine logo + title at the top of every page.
    """
    logo_path = Path("Assets/bellarmine_logo.png")

    col_logo, col_text = st.columns([1, 4])

    with col_logo:
        if logo_path.exists():
            st.image(str(logo_path), use_container_width=True)  # updated here
        else:
            st.write("")

    with col_text:
        st.markdown(
            """
            <div style="padding-top: 0.25rem;">
                <h1 style="
                    margin: 0;
                    color: #A6192E;        /* Bellarmine Scarlet */
                ">
                    Bellarmine Analytics Hub
                </h1>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("---")