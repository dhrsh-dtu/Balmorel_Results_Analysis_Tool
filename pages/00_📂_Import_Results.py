"""Import Results — load scenarios into the dashboard.

Two paths to get data in (both always available):
  • Folder path (server-side scan) — fast for HPC / laptop where zips are
    already on disk. Pre-filled from `$BALMOREL_ROOT`.
  • Upload widget — drag-and-drop one or more `.zip` archives. Works
    everywhere, required on Streamlit Cloud.

Per-page filters (Scenarios / Year / Countries) live in the sidebar of each
analysis page, not here.
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

# ── Status banner ───────────────────────────────────────────────────────────
all_scenarios = data.list_scenarios()
n_loaded = len(all_scenarios)

if n_loaded == 0:
    st.info(
        "👋 No scenarios loaded — point at a folder or drag-and-drop `.zip` archives below."
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
    "📂 **Load from Balmorel Root**",
    expanded=False,
):
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
    st.caption(
        "- Path on the machine running Balmorel and Streamlit (HPC or laptop).\n"
        "- Scans for `<root>/*/output/zip_files/MainResults_*.zip`.\n"
        "- Pre-filled from `$BALMOREL_ROOT` when set. Leave empty on cloud."
    )

# ── 2. Upload archives ──────────────────────────────────────────────────────
with st.expander(
    "📤 **Upload**",
    expanded=False,
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

# ── 3. Loaded results list ──────────────────────────────────────────────────
if all_scenarios:
    st.divider()
    st.markdown("### 📂 Loaded Results")

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

