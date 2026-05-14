"""Import Results — load scenarios into the dashboard.

Two paths to get data in (both always available):
  • Folder path (server-side scan) — fast for HPC / laptop where zips are
    already on disk. Pre-filled from `$BALMOREL_ROOT`.
  • Upload widget — drag-and-drop one or more `.zip` archives. Works
    everywhere, required on Streamlit Cloud.

Filters (scenarios / year / countries) live at the bottom of this page and
apply across every other dashboard page once set.
"""
from __future__ import annotations

import os

import streamlit as st

from lib import data

# Defensive: in normal use streamlit_app.py runs first and initializes state +
# fires the silent autoload, but be safe for direct page testing and bookmarked
# deep links. Both calls are idempotent.
data.ensure_state()
_DEFAULT_ROOT = os.environ.get("BALMOREL_ROOT", "")
if _DEFAULT_ROOT:
    data.autoload_from_root(_DEFAULT_ROOT)

st.title("📂 Import Results")
st.caption(
    "Load Balmorel scenarios from a folder of zip archives or upload them directly, "
    "then set the filters that apply across every analysis page."
)

# ── Status banner ───────────────────────────────────────────────────────────
all_scenarios = data.list_scenarios()
n_loaded = len(all_scenarios)

if n_loaded == 0:
    st.info(
        "👋 No scenarios loaded yet. Use one of the sections below to get started — "
        "either point at a folder of `.zip` archives on this machine, or drag-and-drop them."
    )
else:
    autoload_root = st.session_state.get("_autoload_done", "")
    autoload_count = st.session_state.get("_autoload_count", 0)
    if autoload_root and autoload_count > 0:
        st.success(
            f"✓ **{n_loaded} scenario(s) loaded** — {autoload_count} auto-loaded from "
            f"`{autoload_root}`. Head to **📊 Overview** or any analysis page to explore."
        )
    else:
        st.success(
            f"✓ **{n_loaded} scenario(s) loaded.** Head to **📊 Overview** or any "
            "analysis page to explore."
        )

st.divider()

# ── 1. Load from folder ─────────────────────────────────────────────────────
with st.expander(
    "📂 **Load from folder (server-side)**",
    expanded=(n_loaded == 0),
):
    st.caption(
        "Path on the machine running Streamlit (HPC or laptop). "
        "Scans for `<root>/*/output/zip_files/MainResults_*.zip`. "
        "Pre-filled from `$BALMOREL_ROOT` when set. Leave empty on cloud."
    )
    root_input = st.text_input(
        "Balmorel root folder",
        value=_DEFAULT_ROOT,
        placeholder="/path/to/Balmorel root",
        label_visibility="collapsed",
        key="import_results_root_input",
    ).strip()
    if root_input:
        n_found = data.autoload_from_root(root_input)
        if n_found == 0:
            st.warning(f"⚠ No archives found at `{root_input}`")
        else:
            if st.button("↻ Refresh folder", help="Re-scan for new or updated archives"):
                st.session_state.pop("_autoload_done", None)
                st.rerun()

# ── 2. Upload archives ──────────────────────────────────────────────────────
with st.expander(
    "📤 **Upload scenario archive(s)**",
    expanded=(n_loaded == 0),
):
    uploaded = st.file_uploader(
        "Drop .zip archives here",
        type=["zip"],
        accept_multiple_files=True,
        help="Each .zip is a Balmorel scenario produced by `python -m balmorel_dashboard`.",
        label_visibility="collapsed",
        key="import_results_uploader",
    )
    if uploaded:
        data.ingest_uploads(uploaded)

# Refresh the count after any new ingestions above
all_scenarios = data.list_scenarios()

# ── 3. Loaded scenarios list ────────────────────────────────────────────────
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

        c1, c2 = st.columns([0.92, 0.08])
        c1.markdown(
            f"**{name}**  \n"
            f"<span style='font-size:12px;color:#888'>"
            f"{badge_str} · {len(scn.symbols)} symbols · "
            f"{', '.join(scn.years) or '—'} · {len(scn.countries)} countries"
            f"</span>",
            unsafe_allow_html=True,
        )
        if c2.button("🗑", key=f"del_{name}", help="Remove this scenario from the session"):
            data.delete_scenario(name)
            st.rerun()

# ── 4. Filters ──────────────────────────────────────────────────────────────
if all_scenarios:
    st.divider()
    st.markdown("### 🔎 Filters")
    st.caption("These filters apply across every analysis page.")

    selected = st.multiselect(
        "Scenarios to include",
        options=all_scenarios,
        default=all_scenarios,
        key="import_results_scenario_filter",
    )
    st.session_state["selected_scenarios"] = selected

    years = data.available_years(selected) if selected else []
    if years:
        st.session_state["selected_year"] = st.selectbox(
            "Year",
            options=years,
            index=len(years) - 1,
            key="import_results_year_filter",
        )

    countries = data.available_countries(selected) if selected else []
    if countries:
        st.session_state["selected_countries"] = st.multiselect(
            "Countries",
            options=countries,
            default=countries,
            key="import_results_country_filter",
        )

# ── 5. About ────────────────────────────────────────────────────────────────
st.divider()
with st.expander("ℹ About"):
    st.markdown(
        "Built on [pybalmorel](https://github.com/Mathias157/pybalmorel). "
        "The dashboard reads `.zip` archives produced by the export CLI on a "
        "machine with GAMS installed.\n\n"
        "Source: [github.com/dhrsh-dtu/Balmorel_Results_Analysis_Tool]"
        "(https://github.com/dhrsh-dtu/Balmorel_Results_Analysis_Tool)"
    )
