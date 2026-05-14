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
        "An interactive web dashboard for exploring results from "
        "[Balmorel](https://www.balmorel.com/) energy-system optimisation runs. "
        "Head to **📂 Import Results** in the sidebar to load scenarios "
        "(folder path or upload), then explore live, downloadable plots of "
        "capacity, production, prices, transmission and planetary-boundary "
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
            "**Set environment variables** (add to `~/.bashrc` to persist across shells):"
        )
        st.code(
            "export GAMS_SYSDIR=/path/to/gams          # for export only; e.g. /appl/gams/50.4.1 on DTU HPC\n"
            "export BALMOREL_ROOT=/path/to/Balmorel    # tells the dashboard which folder to auto-load",
            language="bash",
        )
        st.caption(
            "`GAMS_SYSDIR` can be omitted if `gams` is already on `PATH`, or you can "
            "pass `--gams-dir /path/to/gams` to the CLI at run time. `BALMOREL_ROOT` "
            "is only needed for folder auto-load — leave unset to use the upload widget."
        )
        st.markdown(
            "**Export your scenarios** to portable `.zip` archives (one per scenario):"
        )
        st.code(
            "conda activate balmorel-results-viz\n"
            "python -m balmorel_dashboard $BALMOREL_ROOT",
            language="bash",
        )
        st.markdown(
            "**Launch the dashboard in the background** (uses `tmux` if "
            "available, falls back to `nohup` — terminal stays usable):"
        )
        st.code(
            "./launch.sh        # start (Linux/macOS)\n"
            "./stop.sh          # stop",
            language="bash",
        )
        st.markdown(
            "Open <http://localhost:8501> in your browser (SSH-tunnel that port "
            "if Streamlit runs on a remote machine). Scenarios pre-load from "
            "`$BALMOREL_ROOT`; head to **📂 Import Results** to add more via "
            "upload or change the folder path on the fly."
        )
        st.markdown(
            "**One-command remote launch (laptop → HPC):** if the dashboard runs "
            "on a remote host, `./start_dashboard.sh` on your laptop SSHes in, runs "
            "`./launch.sh` remotely, sets up the SSH tunnel, and opens your browser "
            "— all in one go. On DTU HPC, the entry host is auto-derived from "
            "`BALMOREL_DASH_PATH` (any `/work3/<user>/…` path implies `<user>@hpclogin1`), "
            "and a state file in the shared filesystem re-routes to whichever node "
            "actually holds the session. One env var is enough:"
        )
        st.code(
            "# One-time, in your laptop shell ~/.bashrc / ~/.zshrc:\n"
            "export BALMOREL_DASH_PATH=\"/work3/<your-user>/Balmorel/Balmorel_Results_Analysis_Tool\"\n"
            "\n"
            "# Then from your laptop clone — no host arg needed:\n"
            "./start_dashboard.sh    # start + tunnel + browser\n"
            "./stop_dashboard.sh     # stop remote + close tunnel",
            language="bash",
        )
        with st.expander("Other CLI options"):
            st.code(
                "# See what's there:\n"
                "python -m balmorel_dashboard --list-scenarios $BALMOREL_ROOT\n\n"
                "# Limit to specific scenarios:\n"
                "python -m balmorel_dashboard $BALMOREL_ROOT \\\n"
                "    --scenario base --scenario 1_Scenario_Nordics\n\n"
                "# One-shot GAMS path (no env var needed):\n"
                "python -m balmorel_dashboard --gams-dir /appl/gams/50.4.1 $BALMOREL_ROOT\n\n"
                "# Foreground launch (terminal occupied, live logs visible):\n"
                "streamlit run streamlit_app.py --server.headless=true",
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
    st.markdown("### What's on every page")
    st.markdown(
        "Filter once on **📂 Import Results** (scenarios, year, countries) — filters apply across all pages. "
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
