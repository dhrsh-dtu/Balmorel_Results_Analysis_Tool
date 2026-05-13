"""
Balmorel Results Analysis Tool — entrypoint.

Sidebar handles archive upload and global filters; pages render specific analyses.
Each page reads from `lib.data` and renders its own plots.
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

    uploaded = st.file_uploader(
        "📤 Upload scenario archive(s)",
        type=["zip"],
        accept_multiple_files=True,
        help="Each .zip is a Balmorel scenario produced by `python -m balmorel_dashboard`.",
        label_visibility="visible",
    )
    if uploaded:
        data.ingest_uploads(uploaded)

    all_scenarios = data.list_scenarios()
    if all_scenarios:
        st.divider()
        st.markdown("### 📂 Loaded scenarios")

        # Per-scenario row with delete button
        for name in all_scenarios:
            scn = data.get_scenario(name)
            if scn is None:
                continue
            caps = scn.capabilities
            badges = []
            if caps.get("has_pb"):
                badges.append("🌍 PB")
            if caps.get("has_v2g"):
                badges.append("🚗 V2G")
            if caps.get("has_optiflow"):
                badges.append("⚙ OptiFlow")
            badge_str = " · ".join(badges) if badges else "Balmorel"

            row = st.container()
            c1, c2 = row.columns([0.85, 0.15])
            c1.markdown(f"**{name}**  \n<span style='font-size:11px;color:#888'>{badge_str} · {len(scn.symbols)} symbols</span>",
                        unsafe_allow_html=True)
            if c2.button("🗑", key=f"del_{name}", help="Remove this scenario from the session"):
                data.delete_scenario(name)
                st.rerun()

        st.divider()
        st.markdown("### 🔎 Filters")

        selected = st.multiselect(
            "Scenarios to include",
            options=all_scenarios,
            default=all_scenarios,
        )
        st.session_state["selected_scenarios"] = selected

        years = data.available_years(selected) if selected else []
        if years:
            st.session_state["selected_year"] = st.selectbox(
                "Year",
                options=years,
                index=len(years) - 1,
            )

        countries = data.available_countries(selected) if selected else []
        if countries:
            st.session_state["selected_countries"] = st.multiselect(
                "Countries",
                options=countries,
                default=countries,
            )

    st.divider()
    with st.expander("ℹ About"):
        st.markdown(
            "Built on [pybalmorel](https://github.com/Mathias157/pybalmorel) — "
            "the dashboard reads `.zip` archives produced by the export CLI on "
            "a machine with GAMS installed.\n\n"
            "Source: [github.com/dhrsh-dtu/Balmorel_Results_Analysis_Tool]"
            "(https://github.com/dhrsh-dtu/Balmorel_Results_Analysis_Tool)"
        )


# ── Landing page ─────────────────────────────────────────────────────────────
st.title("🔋 Balmorel Results Analysis Tool")

if not data.list_scenarios():
    st.info(
        "👋 **Welcome.** Drag one or more scenario `.zip` archives into the sidebar to begin.\n\n"
        "Archives are produced by running `python -m balmorel_dashboard MainResults_*.gdx` "
        "on a machine with GAMS + pybalmorel installed."
    )
    with st.expander("How to create an archive", expanded=False):
        st.code(
            "git clone https://github.com/dhrsh-dtu/Balmorel_Results_Analysis_Tool.git\n"
            "cd Balmorel_Results_Analysis_Tool\n"
            "pip install -r requirements-export.txt\n"
            "python -m balmorel_dashboard MainResults_Nordics.gdx --verbose\n"
            "# → produces MainResults_Nordics.zip",
            language="bash",
        )
        st.markdown(
            "The archive contains one parquet file per Balmorel symbol plus a "
            "`manifest.json` describing the scenario's coverage. See the "
            "[README](https://github.com/dhrsh-dtu/Balmorel_Results_Analysis_Tool#readme) "
            "for full options."
        )
else:
    n = len(data.list_scenarios())
    st.success(f"✅ **{n} scenario{'s' if n > 1 else ''} loaded.** Use the pages on the left to explore.")
    st.markdown("### Available pages")
    st.markdown(data.pages_overview_md())

    st.markdown("### Loaded scenarios at a glance")
    cols = st.columns(min(n, 4))
    for i, scn in enumerate([data.get_scenario(name) for name in data.list_scenarios()]):
        if scn is None:
            continue
        c = cols[i % len(cols)]
        with c:
            st.markdown(f"**{scn.name}**")
            st.caption(
                f"{', '.join(scn.years) or '—'}  ·  "
                f"{len(scn.countries)} countries  ·  "
                f"{len(scn.symbols)} symbols"
            )
            caps = scn.capabilities
            tags = []
            if caps.get("has_pb"):
                tags.append("🌍 Planetary Boundaries")
            if caps.get("has_v2g"):
                tags.append("🚗 V2G")
            if caps.get("has_optiflow"):
                tags.append("⚙ OptiFlow")
            if tags:
                st.caption("Capabilities: " + ", ".join(tags))
