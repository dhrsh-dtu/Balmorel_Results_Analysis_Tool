"""
Balmorel Results Analysis Tool — entrypoint.

Sidebar handles archive upload and global filters; pages render specific analyses.
Each page reads from `lib.data.get_state()` and renders its own plots.
"""
from __future__ import annotations

import streamlit as st

from lib import data, theme

st.set_page_config(
    page_title="Balmorel Results Analysis",
    page_icon="🔋",
    layout="wide",
    initial_sidebar_state="expanded",
)

theme.apply()

# ── Session state ────────────────────────────────────────────────────────────
data.ensure_state()

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🔋 Balmorel Results")
    st.caption("Upload one or more `.zip` archives produced by `python -m balmorel_dashboard`.")

    uploaded = st.file_uploader(
        "📤 Upload scenario archive(s)",
        type=["zip"],
        accept_multiple_files=True,
        help="Each .zip is a Balmorel scenario exported from a GDX file.",
    )
    if uploaded:
        data.ingest_uploads(uploaded)

    scenarios = data.list_scenarios()
    if scenarios:
        st.divider()
        st.markdown("### 📂 Loaded scenarios")
        selected = st.multiselect(
            "Scenarios to include",
            options=scenarios,
            default=scenarios,
            label_visibility="collapsed",
        )
        st.session_state["selected_scenarios"] = selected

        years = data.available_years(selected)
        if years:
            st.session_state["selected_year"] = st.selectbox(
                "Year",
                options=years,
                index=len(years) - 1,
            )

        countries = data.available_countries(selected)
        if countries:
            st.session_state["selected_countries"] = st.multiselect(
                "Countries",
                options=countries,
                default=countries,
            )

# ── Landing page ─────────────────────────────────────────────────────────────
st.title("🔋 Balmorel Results Analysis Tool")

if not data.list_scenarios():
    st.info(
        "👋 **Welcome.** Drag one or more scenario `.zip` archives into the sidebar to begin.\n\n"
        "Archives are produced by running `python -m balmorel_dashboard MainResults_*.gdx` "
        "on a machine with GAMS + pybalmorel installed. See the README for details."
    )
    st.markdown("### How to get a `.zip` archive")
    st.code(
        "git clone https://github.com/dhrsh-dtu/Balmorel_Results_Analysis_Tool.git\n"
        "cd Balmorel_Results_Analysis_Tool\n"
        "pip install -r requirements-export.txt\n"
        "python -m balmorel_dashboard MainResults_Nordics.gdx\n"
        "# → produces MainResults_Nordics.zip",
        language="bash",
    )
    st.markdown(
        "### What's inside a `.zip`\n"
        "- One `parquet` file per Balmorel result symbol\n"
        "- `manifest.json` describing the scenario, years, countries, symbols available\n"
        "- No GAMS dependency — pandas reads the parquet directly"
    )
else:
    st.success(
        f"✅ {len(data.list_scenarios())} scenario(s) loaded. "
        "Choose a page from the sidebar to explore."
    )
    st.markdown("### Available pages")
    st.markdown(data.pages_overview_md())
