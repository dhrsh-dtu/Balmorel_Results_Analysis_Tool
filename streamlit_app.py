"""
Balmorel Results Analysis Tool — entrypoint.

This module sets up the page config, runs a silent module-level autoload
from `$BALMOREL_ROOT` (so scenarios are available even if the user lands
directly on an analysis page), and configures `st.navigation`. All loading
UI — folder text input, upload widget, loaded-scenarios list, and global
filters — lives on the `📂 Import Results` page.

The sidebar contains only page navigation.
"""
from __future__ import annotations

import os

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


# ── Silent autoload from $BALMOREL_ROOT ────────────────────────────────────
# Runs on every script execution so scenarios are available even when the
# user lands directly on an analysis page (e.g. via bookmark) without
# visiting the Import Results page first. Idempotent — re-running with the
# same root is a no-op via the session_state cache in data.autoload_from_root.
_BALMOREL_ROOT_ENV = os.environ.get("BALMOREL_ROOT", "")
if _BALMOREL_ROOT_ENV:
    data.autoload_from_root(_BALMOREL_ROOT_ENV)


# ── Tool Description page ──────────────────────────────────────────────────
def tool_description() -> None:
    st.title("🔋 Balmorel Results Analysis Tool")
    st.markdown(
        "An interactive web dashboard for exploring "
        "[Balmorel](https://github.com/balmorelcommunity/Balmorel) "
        "energy-system optimisation results."
    )

    st.divider()

    # ── Key features ────────────────────────────────────────────────────────
    st.markdown("### What this tool does")
    f1, f2 = st.columns(2)
    with f1:
        st.markdown(
            "**📥 Model Inputs** — sector coverage, technology portfolio, "
            "cost inputs (capex, O&M, lifetime), demand by category, "
            "sector-coupling decomposition.\n\n"
            "**📊 Overview** — KPI cards (cost, capacity, production, max TL), "
            "cost-category breakdown, capacity mix, production donuts, health checks.\n\n"
            "**⚡ Capacity** — generation and storage tabs, stacked bars by "
            "Technology or Fuel, country heatmap, endogenous/exogenous filter.\n\n"
            "**🏭 Production** — annual totals, by-country breakdown, "
            "per-scenario donut grids."
        )
    with f2:
        st.markdown(
            "**💰 Prices & Demand** — auto-tabs for Electricity, Heat, Hydrogen; "
            "regional prices, demand by category, hourly profiles.\n\n"
            "**🌍 Planetary Boundaries** — radar of all `TL_*` indicators against "
            "the boundary ring; per-indicator drill-down with source attribution "
            "(generation / transmission / EVs) and fuel/technology breakdown.\n\n"
            "**🔌 Transmission** — flow matrix heatmap, net trade per country, "
            "top lines by capacity, line utilization.\n\n"
            "**🔍 Raw Explorer** — search any symbol by name or description, "
            "quick filters, numeric summary, CSV download."
        )
    st.caption(
        "🖼️ Image export (PNG) is available on every chart via the Plotly toolbar; "
        "most pages also offer CSV downloads of the underlying tables."
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
        with st.expander("1️⃣ Setup", expanded=False):
            st.markdown(
                "**One-time only.** Clone the repo + run `setup.sh` to create "
                "the conda env, then add two lines to your HPC `~/.bashrc` so "
                "every shell auto-activates the env and knows which run folder "
                "to load — no per-session typing later."
            )
            st.code(
                "# Clone + install (creates the balmorel-results-viz conda env):\n"
                "git clone https://github.com/dhrsh-dtu/Balmorel_Results_Analysis_Tool.git\n"
                "cd Balmorel_Results_Analysis_Tool\n"
                "./setup.sh                          # Linux/macOS\n"
                "\n"
                "# Add these two lines to ~/.bashrc on HPC — set once, forget forever:\n"
                "conda activate balmorel-results-viz                  # activate dashboard env\n"
                "export BALMOREL_ROOT=/path/to/your/Balmorel/         # Results auto-load",
                language="bash",
            )
            st.caption(
                "Assumes `conda init <shell>` was run once during your miniconda "
                "install (standard). If `conda activate` errors with `conda: "
                "command not found`, run `conda init bash` (or `zsh`) and reopen "
                "your shell. GAMS is auto-detected on DTU HPC (`/appl/gams/50.4.1`); "
                "on other clusters also `export GAMS_SYSDIR=…` or pass `--gams-dir` "
                "at import time."
            )

        with st.expander("2️⃣ Import Results", expanded=False):
            st.markdown(
                "Convert your Balmorel GDX outputs into portable `.zip` archives "
                "(one per scenario). Run this when scenarios are new or change:"
            )
            st.code(
                "python -m balmorel_dashboard $BALMOREL_ROOT",
                language="bash",
            )
            st.caption(
                "The archives land at `<scenario>/output/zip_files/MainResults_*.zip` "
                "inside `$BALMOREL_ROOT`. The dashboard's **📂 Import Results** "
                "page reads them from there and auto-loads them on launch."
            )

        with st.expander("3️⃣ Run Dashboard", expanded=False):
            st.code(
                "./start_dashboard.sh    # detached tmux session, terminal stays usable\n"
                "./stop_dashboard.sh     # stop when done",
                language="bash",
            )
            st.caption(
                "Open `http://localhost:8501` in your laptop browser. In "
                "**VS Code / Cursor / JetBrains Remote SSH** the port auto-forwards "
                "— just click the URL. From **plain SSH**, first run "
                "`ssh -L 8501:localhost:8501 <user>@hpclogin1.hpccluster.dtu.dk` on "
                "your laptop."
            )

        with st.expander("Other CLI options"):
            st.code(
                "# See what scenarios are present (no export):\n"
                "python -m balmorel_dashboard --list-scenarios $BALMOREL_ROOT\n\n"
                "# Limit to specific scenarios:\n"
                "python -m balmorel_dashboard $BALMOREL_ROOT \\\n"
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
            "3. **Go to 📂 Import Results** in the sidebar and drag your `.zip` "
            "into the **Upload scenario archive(s)** section. Multiple uploads "
            "accumulate as separate scenarios you can compare.\n"
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

    # ── Built on / links ────────────────────────────────────────────────────
    st.markdown("### Built on")
    st.markdown(
        "- **[Balmorel](https://github.com/balmorelcommunity/Balmorel)** — the open-source "
        "energy-system optimisation model whose results this dashboard analyses.\n"
        "- **[pybalmorel](https://github.com/Mathias157/pybalmorel)** — Python "
        "helpers for Balmorel. The dashboard inherits its column conventions "
        "(`Year`, `Country`, `Region`, …) and tech/fuel color palette.\n"
        "- **[Planetary Boundaries fork](https://github.com/balmorelcommunity/Balmorel/tree/Planetary_Boundaries)** — "
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



# ── Navigation ──────────────────────────────────────────────────────────────
# Explicit `st.Page` entries give each page a clean sidebar label and an icon.
# When using `st.navigation`, the `pages/` folder is NOT auto-discovered — every
# page must be listed here.
pages = [
    st.Page(tool_description, title="Tool Description", icon="🔋", default=True, url_path=""),
    st.Page("pages/00_📂_Import_Results.py",           title="Import Results",        icon="📂"),
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
