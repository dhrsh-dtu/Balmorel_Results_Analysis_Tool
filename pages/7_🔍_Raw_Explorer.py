"""Raw Explorer — pick any symbol, inspect the DataFrame, filter, download as CSV.

Always available; useful escape hatch for users wanting custom analysis.
"""
from __future__ import annotations

import streamlit as st

from lib import data

data.ensure_state()
st.title("🔍 Raw Explorer")

data.render_page_filters("raw_explorer")
scns = data.selected_scenarios()
if not scns:
    st.info("Upload at least one scenario archive in the sidebar to see content.")
    st.stop()

# Union of all symbols across scenarios + their availability + descriptions
all_symbols: dict[str, dict] = {}
for s in scns:
    for sym in s.symbols:
        rec = all_symbols.setdefault(sym, {"in": [], "desc": ""})
        rec["in"].append(s.name)
        if not rec["desc"] and s.describe(sym):
            rec["desc"] = s.describe(sym)

if not all_symbols:
    st.warning("Selected scenarios have no symbols loaded.")
    st.stop()

# ── Symbol picker ────────────────────────────────────────────────────────────
c1, c2 = st.columns([0.65, 0.35])
with c1:
    search = st.text_input(
        "Search symbols",
        value="",
        placeholder="e.g. PRICE, CAP, TL_",
        help="Case-insensitive substring match on symbol name or description.",
    )
with c2:
    group_by = st.radio(
        "Group",
        ["Alphabetical", "By family"],
        horizontal=True,
        label_visibility="collapsed",
    )

# Filter
needle = search.strip().lower()
matched = sorted(
    sym for sym, rec in all_symbols.items()
    if (not needle)
    or needle in sym.lower()
    or needle in rec["desc"].lower()
)

if not matched:
    st.warning(f"No symbols match `{search}`.")
    st.stop()

# Group by family if requested (use prefix before first underscore)
display_list: list[str]
if group_by == "By family":
    families: dict[str, list[str]] = {}
    for sym in matched:
        # Family heuristic: prefix until 1st underscore, e.g. EL_, H2_, PRO_, G_, X_, XH2_, TL_, IS_
        fam_prefix = sym.split("_")[0]
        families.setdefault(fam_prefix, []).append(sym)
    # Flatten with section markers
    display_list = []
    for fam in sorted(families.keys()):
        display_list.extend(families[fam])
else:
    display_list = matched

symbol = st.selectbox(
    f"Symbol ({len(display_list)} match{'es' if len(display_list) != 1 else ''})",
    options=display_list,
    format_func=lambda s: f"{s}  —  {all_symbols[s]['desc'][:50]}" if all_symbols[s]["desc"] else s,
)

rec = all_symbols[symbol]
if rec["desc"]:
    st.markdown(f"_{rec['desc']}_")
present_in = rec["in"]
missing = [s.name for s in scns if s.name not in present_in]
if missing:
    st.caption(
        f"🔹 Present in: {', '.join(present_in)}  ·  "
        f"⚪ Missing from: {', '.join(missing)}"
    )

# ── Pull the data ───────────────────────────────────────────────────────────
df = data.get_table(symbol, scenarios=scns)
df_unfiltered = df.copy()

if df.empty:
    st.warning(f"`{symbol}` is empty in the selected scenarios.")
    st.stop()

# ── Quick column filters ────────────────────────────────────────────────────
quick_cols = [c for c in ("Year", "Country", "Region", "Commodity", "Category") if c in df.columns]
if quick_cols:
    with st.expander("🔎 Quick filters", expanded=False):
        cols = st.columns(min(len(quick_cols), 4))
        for i, qc in enumerate(quick_cols):
            with cols[i % len(cols)]:
                opts = sorted(df[qc].dropna().astype(str).unique())
                if not opts:
                    continue
                sel = st.multiselect(qc, opts, default=opts, key=f"qf_{symbol}_{qc}")
                if sel and sel != opts:
                    df = df[df[qc].astype(str).isin(sel)]

st.caption(f"**Shape:** {df.shape[0]:,} rows × {df.shape[1]} columns")
st.dataframe(df, use_container_width=True, height=520)

# Download — both filtered and unfiltered
c1, c2 = st.columns(2)
with c1:
    st.download_button(
        "⬇ Download filtered CSV",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name=f"{symbol}_filtered.csv",
        mime="text/csv",
    )
with c2:
    st.download_button(
        "⬇ Download full CSV (no filters)",
        data=df_unfiltered.to_csv(index=False).encode("utf-8"),
        file_name=f"{symbol}.csv",
        mime="text/csv",
    )

# Optional numeric summary
if "Value" in df.columns:
    with st.expander("📈 Numeric summary"):
        try:
            num_df = df.select_dtypes(include="number")
            if not num_df.empty:
                st.dataframe(num_df.describe().T, use_container_width=True)
        except Exception:
            st.caption("Could not compute numeric summary.")
