"""
Balmorel Results Analysis Tool — entrypoint.

Two ways to load scenarios into the dashboard, both always available:
  • Folder path (sidebar text input). Prefilled from $BALMOREL_ROOT if set.
    The Streamlit server scans `<root>/*/output/zip_files/MainResults_*.zip`
    and auto-loads everything. Useful on HPC / laptop where the zips already
    live on the same machine as Streamlit.
  • Upload widget. Drag-and-drop one or more `.zip` archives. Works
    everywhere, including Streamlit Cloud where the server has no access
    to the user's filesystem.

Uses `st.navigation` so the home page can be labelled "Tool Description"
in the sidebar (instead of Streamlit's default "streamlit app").
"""
from __future__ import annotations

import os
from pathlib import Path

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


# ── Folder auto-load helper ────────────────────────────────────────────────
_DEFAULT_ROOT = os.environ.get("BALMOREL_ROOT", "")


def _autoload_from_root(root: str) -> int:
    """Discover and ingest all `<root>/*/output/zip_files/*.zip` once per root.

    Returns the number of archives found at this root (0 means the path
    resolved to nothing — invalid path, or no zips yet).
    """
    cached_root = st.session_state.get("_autoload_done")
    if cached_root == root:
        return st.session_state.get("_autoload_count", 0)
    paths = sorted(Path(root).glob("*/output/zip_files/MainResults_*.zip"))
    if paths:
        data.ingest_local_paths(paths)
    st.session_state["_autoload_done"] = root
    st.session_state["_autoload_count"] = len(paths)
    return len(paths)


# ── Sidebar (runs on every page) ────────────────────────────────────────────
def _render_sidebar() -> None:
    with st.sidebar:
        st.markdown("## 🔋 Balmorel Results")

        root_input = st.text_input(
            "📂 Load from folder (server-side)",
            value=_DEFAULT_ROOT,
            placeholder="/path/to/Balmorel root",
            help=(
                "Path on the machine running Streamlit (HPC or laptop). "
                "Scans for `<root>/*/output/zip_files/MainResults_*.zip`. "
                "Pre-filled from `$BALMOREL_ROOT` when set. Leave empty on cloud."
            ),
        ).strip()

        if root_input:
            n = _autoload_from_root(root_input)
            if n == 0:
                st.caption(f"⚠ No archives found at `{root_input}`")
            else:
                if st.button("↻ Refresh", help="Re-scan for new or updated archives"):
                    st.session_state.pop("_autoload_done", None)
                    st.rerun()

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
    st.caption("Pick the path that matches your setup:")

    tab_balm, tab_collab = st.tabs([
        "🔧 I'm a Balmorel user",
        "🤝 I'm a collaborator",
    ])

    with tab_balm:
        st.markdown(
            "You run Balmorel locally — have GAMS + Python on your machine.\n\n"
            "**One-time setup** (creates the `balmorel-results-viz` conda env "
            "if conda is available, or installs into your current Python "
            "otherwise; warns if GAMS isn't on PATH):"
        )
        st.code(
            "git clone https://github.com/dhrsh-dtu/Balmorel_Results_Analysis_Tool.git\n"
            "cd Balmorel_Results_Analysis_Tool\n"
            "./setup.sh           # Linux / macOS\n"
            "# setup.bat          # Windows",
            language="bash",
        )
        st.markdown(
            "**Export your scenarios** to portable `.zip` archives (one per scenario):"
        )
        st.code(
            "conda activate balmorel-results-viz\n"
            "python -m balmorel_dashboard /path/to/Balmorel",
            language="bash",
        )
        st.markdown(
            "**Point the dashboard at the Balmorel root and launch:**"
        )
        st.code(
            "export BALMOREL_ROOT=/path/to/Balmorel    # add to ~/.bashrc for persistence\n"
            "streamlit run streamlit_app.py --server.headless=true",
            language="bash",
        )
        st.markdown(
            "Open <http://localhost:8501> in your browser (SSH-tunnel that port "
            "if Streamlit runs on a remote machine). Scenarios pre-load from the "
            "folder; the upload widget stays available for ad-hoc archives."
        )
        with st.expander("Other CLI options"):
            st.code(
                "# See what's there:\n"
                "python -m balmorel_dashboard --list-scenarios /path/to/Balmorel\n\n"
                "# Limit to specific scenarios:\n"
                "python -m balmorel_dashboard /path/to/Balmorel \\\n"
                "    --scenario base --scenario 1_Scenario_Nordics",
                language="bash",
            )

    with tab_collab:
        st.markdown(
            "You don't have Balmorel installed — you just want to view results "
            "someone shared with you.\n\n"
            "1. **Receive a `.zip`** from a Balmorel user (it's a portable archive "
            "of one scenario's parquet tables — typically <1 MB).\n"
            "2. **Visit the live app URL** and sign in with the email you were "
            "approved with.\n"
            "3. **Drag the `.zip`** into the **📤 Upload scenario archive(s)** "
            "box in the sidebar. Multiple uploads accumulate as separate "
            "scenarios you can compare.\n"
            "4. **Explore** — Overview, Capacity, Production, Prices & Demand, "
            "Planetary Boundaries, Transmission, Raw Explorer. Pages auto-hide "
            "if their relevant symbols aren't in the archive.\n\n"
            "**No install required.**"
        )
        with st.expander("What's in a `.zip`?"):
            st.markdown(
                "- One parquet file per Balmorel output symbol (production, "
                "capacity, prices, transmission, …)\n"
                "- A `manifest.json` describing the scenario's coverage\n"
                "- Filtered input parameters from `all_endofmodel.gdx` (capex, "
                "demand, fuel costs, etc.) — used to populate the "
                "**📥 Model Inputs** page\n\n"
                "No GAMS install needed on the dashboard side; the archive is "
                "fully self-contained."
            )

    st.divider()
    st.markdown("### What's on every page")
    st.markdown(
        "Filter once in the sidebar (scenarios, year, countries) — filters apply across all pages. "
        "Click the 📷 icon on any Plotly chart to download a PNG. Most pages also offer CSV "
        "downloads of the underlying tables."
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
    st.Page("pages/0_📥_Model_Inputs.py",              title="Model Inputs",          icon="📥"),
    st.Page("pages/1_📊_Overview.py",                  title="Overview",              icon="📊"),
    st.Page("pages/2_⚡_Capacity.py",                   title="Capacity",              icon="⚡"),
    st.Page("pages/3_🏭_Production.py",                 title="Production",            icon="🏭"),
    st.Page("pages/4_💰_Prices_and_Demand.py",          title="Prices and Demand",     icon="💰"),
    st.Page("pages/5_🌍_Planetary_Boundaries.py",       title="Planetary Boundaries",  icon="🌍"),
    st.Page("pages/6_🔌_Transmission.py",               title="Transmission",          icon="🔌"),
    st.Page("pages/7_🔍_Raw_Explorer.py",               title="Raw Explorer",          icon="🔍"),
]

pg = st.navigation(pages)
pg.run()
