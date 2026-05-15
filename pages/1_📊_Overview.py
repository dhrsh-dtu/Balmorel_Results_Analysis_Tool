"""Overview page — KPIs and high-level summary across selected scenarios."""
from __future__ import annotations

import streamlit as st

from lib import data, plots

data.ensure_state()
st.title("📊 Overview")

data.render_page_filters("overview")
scns = data.selected_scenarios()
if not scns:
    st.info("Upload at least one scenario archive in the sidebar to see content.")
    st.stop()

year = data.selected_year() or "—"
st.caption(
    f"Showing **{len(scns)}** scenario(s)  ·  Year: **{year}**  ·  "
    f"Countries: {', '.join(data.selected_countries() or ['all'])}"
)

# ── KPI row (per-scenario, side-by-side) ─────────────────────────────────────
st.markdown("### Key figures by scenario")

cols = st.columns(min(len(scns), 4))
for i, scn in enumerate(scns):
    s = data.scenario_summary(scn)
    with cols[i % len(cols)]:
        st.markdown(f"#### {s['name']}")
        # Total cost
        st.metric(
            "💰 Total system cost",
            data.fmt_number(s["total_cost"], decimals=0, unit="Mmoney"),
        )
        st.metric(
            "⚡ Electricity capacity",
            data.fmt_number(s["el_capacity"], decimals=1, unit="GW"),
        )
        st.metric(
            "🏭 Electricity production",
            data.fmt_number(s["el_production"], decimals=1, unit="TWh"),
        )
        if s["max_tl"] is not None:
            label = f"🌍 Max TL ({s['max_tl_indicator']})"
            st.metric(
                label,
                f"{s['max_tl']:.4f}",
                delta=("within boundary" if s["max_tl"] < 1.0 else "TRANSGRESSED"),
                delta_color=("normal" if s["max_tl"] < 1.0 else "inverse"),
            )

st.divider()

# ── Cost breakdown ──────────────────────────────────────────────────────────
st.markdown("### System cost breakdown")
obj_df = data.get_filtered("OBJ_YCR")
if obj_df.empty:
    st.info("No `OBJ_YCR` data in selected scenarios.")
else:
    st.plotly_chart(plots.cost_breakdown_bar(obj_df), use_container_width=True)

    with st.expander("📋 Show as table"):
        agg = (
            obj_df.groupby(["Scenario", "Category"], as_index=False, observed=True)["Value"]
            .sum()
            .pivot(index="Category", columns="Scenario", values="Value")
            .fillna(0.0)
        )
        agg["Total"] = agg.sum(axis=1)
        agg = agg.sort_values("Total", ascending=False).drop(columns="Total")
        st.dataframe(agg.style.format("{:,.2f}"), use_container_width=True)

st.divider()

# ── Capacity mix ────────────────────────────────────────────────────────────
st.markdown("### Installed capacity")

c1, c2 = st.columns([0.7, 0.3])
with c2:
    color_by = st.radio(
        "Color by",
        ["Technology", "Fuel"],
        horizontal=True,
        label_visibility="collapsed",
    )
    min_cap = st.number_input(
        "Min display (GW)",
        min_value=0.0,
        value=0.01,
        step=0.01,
        format="%.2f",
        help="Hide capacity entries below this threshold.",
    )

cap_df = data.get_filtered("G_CAP_YCRAF")
if cap_df.empty:
    st.info("No `G_CAP_YCRAF` data in selected scenarios.")
else:
    st.plotly_chart(
        plots.capacity_by_commodity(cap_df, color_by=color_by, min_capacity=min_cap),
        use_container_width=True,
    )

st.divider()

# ── Production share ────────────────────────────────────────────────────────
st.markdown("### Production mix")

pro_df = data.get_filtered("PRO_YCRAGF")
if pro_df.empty:
    st.info("No `PRO_YCRAGF` data in selected scenarios.")
else:
    available_commodities = sorted(pro_df["Commodity"].dropna().unique()) if "Commodity" in pro_df.columns else []
    if available_commodities:
        commodity = st.radio(
            "Commodity",
            available_commodities,
            horizontal=True,
            label_visibility="collapsed",
        )
        donut_color_by = st.radio(
            "Donut color",
            ["Fuel", "Technology"],
            horizontal=True,
            label_visibility="collapsed",
            key="donut_color_by",
        )
        st.plotly_chart(
            plots.production_share_donuts(pro_df, commodity=commodity, color_by=donut_color_by),
            use_container_width=True,
        )

st.divider()

# ── Health checks ───────────────────────────────────────────────────────────
all_warnings: list[tuple[str, str]] = []
for scn in scns:
    for w in data.health_warnings(scn):
        all_warnings.append((scn.name, w))

if all_warnings:
    with st.expander(f"🩺 Health checks ({len(all_warnings)})", expanded=False):
        for sc_name, msg in all_warnings:
            st.markdown(f"**{sc_name}:** {msg}")
else:
    with st.expander("🩺 Health checks (0)", expanded=False):
        st.success("No warnings — all selected scenarios extracted cleanly.")
