"""
Balmorel Results Analysis Tool — entrypoint.

Uses `st.navigation` so the home page can be labelled "Tool Description"
in the sidebar (instead of Streamlit's default "streamlit app"). The
sidebar (uploader + filters) is rendered on every page since this script
runs before each navigated page.
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
data.ensure_state()


# ── Sidebar (runs on every page) ────────────────────────────────────────────
def _render_sidebar() -> None:
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

                c1, c2 = st.columns([0.85, 0.15])
                c1.markdown(
                    f"**{name}**  \n"
                    f"<span style='font-size:11px;color:#888'>"
                    f"{badge_str} · {len(scn.symbols)} symbols</span>",
                    unsafe_allow_html=True,
                )
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
                "Built on [pybalmorel](https://github.com/Mathias157/pybalmorel). "
                "The dashboard reads `.zip` archives produced by the export CLI "
                "on a machine with GAMS installed.\n\n"
                "Source: [github.com/dhrsh-dtu/Balmorel_Results_Analysis_Tool]"
                "(https://github.com/dhrsh-dtu/Balmorel_Results_Analysis_Tool)"
            )


_render_sidebar()


# ── Tool Description page ──────────────────────────────────────────────────
def tool_description() -> None:
    st.title("🔋 Balmorel Results Analysis Tool")
    st.markdown(
        "An interactive web dashboard for exploring results from "
        "[Balmorel](https://www.balmorel.com/) energy-system optimisation runs. "
        "Upload a scenario archive in the sidebar to see live, downloadable plots "
        "of capacity, production, prices, transmission and planetary-boundary "
        "indicators."
    )

    st.divider()

    # ── Key features ────────────────────────────────────────────────────────
    st.markdown("### What this tool does")
    f1, f2 = st.columns(2)
    with f1:
        st.markdown(
            "**📊 Overview** — KPI cards (cost, capacity, production, max TL), "
            "cost-category breakdown, capacity mix, production donuts, health checks.\n\n"
            "**⚡ Capacity** — generation and storage tabs, stacked bars by "
            "Technology or Fuel, country heatmap, endogenous/exogenous filter.\n\n"
            "**🏭 Production** — annual totals, by-country breakdown, "
            "per-scenario donut grids.\n\n"
            "**💰 Prices & Demand** — auto-tabs for Electricity, Heat, Hydrogen; "
            "regional prices, demand by category, hourly profiles."
        )
    with f2:
        st.markdown(
            "**🌍 Planetary Boundaries** — radar of all `TL_*` indicators against "
            "the boundary ring; per-indicator drill-down with source attribution "
            "(generation / transmission / EVs) and fuel/technology breakdown.\n\n"
            "**🔌 Transmission** — flow matrix heatmap, net trade per country, "
            "top lines by capacity, line utilization.\n\n"
            "**🔍 Raw Explorer** — search any symbol by name or description, "
            "quick filters, numeric summary, CSV download.\n\n"
            "**🖼️ Image export** is available on every chart via the Plotly toolbar."
        )

    st.divider()

    # ── How to use ──────────────────────────────────────────────────────────
    st.markdown("### How to use")
    st.markdown(
        "1. **Get an archive.** On a machine with GAMS installed, pass any "
        "GDX path to the export CLI (full or relative path — you don't need "
        "to `cd` anywhere first):\n"
        "   ```bash\n"
        "   python -m balmorel_dashboard /path/to/MainResults_Nordics.gdx\n"
        "   ```\n"
        "   The `.zip` is written **next to the input file** by default "
        "(e.g. `/path/to/MainResults_Nordics.zip`). Use `-o some/folder` "
        "to choose a different output directory, or pass several GDX paths "
        "at once.\n"
        "2. **Upload.** Drag one or more `.zip` archives into the **📤 Upload "
        "scenario archive(s)** box in the sidebar. Multiple uploads accumulate "
        "as separate scenarios.\n"
        "3. **Explore.** Use the navigation on the left to open Overview, "
        "Capacity, Production, and the other analysis pages. The Planetary "
        "Boundaries page auto-hides if `TL_*` symbols are absent.\n"
        "4. **Filter.** Pick scenarios, year, and countries in the sidebar — "
        "filters apply across all pages.\n"
        "5. **Export.** Click the 📷 icon on any chart to download a PNG. "
        "Most pages also offer CSV downloads of the underlying tables."
    )

    if not data.list_scenarios():
        with st.expander("📦 First-time setup of the export CLI", expanded=False):
            st.markdown(
                "**One-time install on a machine with GAMS + Python:**"
            )
            st.code(
                "git clone https://github.com/dhrsh-dtu/Balmorel_Results_Analysis_Tool.git\n"
                "cd Balmorel_Results_Analysis_Tool\n"
                "pip install -r requirements-export.txt -e .",
                language="bash",
            )
            st.markdown(
                "The `-e .` makes the `balmorel_dashboard` command available "
                "from any working directory, so step 2 below works no matter "
                "where your GDX files live.\n\n"
                "**Export a single GDX (the path can be anywhere on disk):**"
            )
            st.code(
                "python -m balmorel_dashboard /work3/runs/MainResults_Nordics.gdx --verbose\n"
                "# → writes /work3/runs/MainResults_Nordics.zip",
                language="bash",
            )
            st.markdown(
                "**Or batch-export many at once into a separate folder:**"
            )
            st.code(
                "python -m balmorel_dashboard /work3/runs/MainResults_*.gdx --output-dir ./exports/",
                language="bash",
            )
            st.caption(
                "The export CLI uses `gams.transfer` to read the GDX, applies "
                "pybalmorel column conventions, and writes one parquet per "
                "non-empty symbol plus a `manifest.json`. Only this step needs "
                "GAMS — the dashboard itself runs anywhere."
            )

    st.divider()

    # ── Built on / links ────────────────────────────────────────────────────
    st.markdown("### Built on")
    st.markdown(
        "- **[Balmorel](https://www.balmorel.com/)** — the open-source "
        "energy-system optimisation model whose results this dashboard analyses.\n"
        "- **[pybalmorel](https://github.com/Mathias157/pybalmorel)** — Python "
        "helpers for Balmorel. The dashboard inherits its column conventions "
        "(`Year`, `Country`, `Region`, …) and tech/fuel color palette.\n"
        "- **[Planetary Boundaries fork](https://github.com/dhrsh-dtu/Balmorel_PlanetaryBoundaries)** — "
        "Balmorel extended with `TL_*` / `IS_*` symbols for impact-score and "
        "transgression-level outputs.\n"
        "- **[Streamlit](https://streamlit.io/)** and **[Plotly](https://plotly.com/python/)** — "
        "web framework and interactive plotting library."
    )

    st.markdown("### Links")
    st.markdown(
        "- 💻 **Source code:** [github.com/dhrsh-dtu/Balmorel_Results_Analysis_Tool]"
        "(https://github.com/dhrsh-dtu/Balmorel_Results_Analysis_Tool)\n"
        "- 📝 **Changelog:** [CHANGELOG.md]"
        "(https://github.com/dhrsh-dtu/Balmorel_Results_Analysis_Tool/blob/main/CHANGELOG.md)\n"
        "- 🐛 **Report an issue:** [GitHub issues]"
        "(https://github.com/dhrsh-dtu/Balmorel_Results_Analysis_Tool/issues)\n"
        "- 📜 **License:** MIT"
    )

    st.markdown("### Access")
    st.info(
        "This is a private deployment. If you'd like viewer access, contact "
        "the repository maintainer with the email address you'd like added to "
        "the allowlist."
    )

    # ── Loaded scenarios (only when data is present) ───────────────────────
    scns = data.list_scenarios()
    if scns:
        st.divider()
        n = len(scns)
        st.markdown(f"### 📂 Loaded scenarios ({n})")
        cols = st.columns(min(n, 4))
        for i, scn in enumerate([data.get_scenario(name) for name in scns]):
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


# ── Navigation ──────────────────────────────────────────────────────────────
# Explicit `st.Page` entries give each page a clean sidebar label and an icon.
# When using `st.navigation`, the `pages/` folder is NOT auto-discovered — every
# page must be listed here.
pages = [
    st.Page(tool_description, title="Tool Description", icon="🔋", default=True, url_path=""),
    st.Page("pages/1_📊_Overview.py",                 title="Overview",              icon="📊"),
    st.Page("pages/2_⚡_Capacity.py",                  title="Capacity",              icon="⚡"),
    st.Page("pages/3_🏭_Production.py",                title="Production",            icon="🏭"),
    st.Page("pages/4_💰_Prices_and_Demand.py",         title="Prices and Demand",     icon="💰"),
    st.Page("pages/5_🌍_Planetary_Boundaries.py",      title="Planetary Boundaries",  icon="🌍"),
    st.Page("pages/6_🔌_Transmission.py",              title="Transmission",          icon="🔌"),
    st.Page("pages/7_🔍_Raw_Explorer.py",              title="Raw Explorer",          icon="🔍"),
]

pg = st.navigation(pages)
pg.run()
