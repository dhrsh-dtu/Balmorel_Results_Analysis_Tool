"""Transmission page — capacities, flows, net trade, and line utilization.

One tab per commodity (Electricity / Hydrogen / Heat). Tabs auto-hide when the
relevant symbols are absent. Geographic maps are deferred to a future version;
this page uses heatmaps and bar charts to convey the same information without
requiring geofiles in the deployed app.
"""
from __future__ import annotations

import streamlit as st

from lib import data, plots

data.ensure_state()
st.title("🔌 Transmission")

data.render_page_filters("transmission")
scns = data.selected_scenarios()
if not scns:
    st.info("Upload at least one scenario archive in the sidebar to see content.")
    st.stop()

st.caption(
    f"Showing **{len(scns)}** scenario(s)  ·  Year: **{data.selected_year() or '—'}**  ·  "
    f"Countries: {', '.join(data.selected_countries() or ['all'])}"
)


def render_commodity(
    label: str,
    cap_symbol: str,
    flow_symbol: str,
    flow_unit: str = "TWh",
    cap_unit: str = "GW",
) -> None:
    cap_df = data.get_filtered(cap_symbol)
    flow_df = data.get_filtered(flow_symbol)

    if (cap_df is None or cap_df.empty) and (flow_df is None or flow_df.empty):
        st.info(f"No {label.lower()} transmission symbols in selected scenarios.")
        return

    # ── KPI row ─────────────────────────────────────────────────────────────
    cols = st.columns(min(len(scns), 4))
    for i, scn in enumerate(scns):
        with cols[i % len(cols)]:
            st.markdown(f"**{scn.name}**")
            cap = scn.tables.get(cap_symbol)
            if cap is not None and not cap.empty:
                st.metric(
                    f"Total {label.lower()} capacity",
                    f"{float(cap['Value'].sum()):,.1f} {cap_unit}",
                )
            flow = scn.tables.get(flow_symbol)
            if flow is not None and not flow.empty:
                n_lines = flow[["From", "To"]].drop_duplicates().shape[0]
                st.metric(
                    f"Total annual flow",
                    f"{float(flow['Value'].sum()):,.1f} {flow_unit}",
                    delta=f"{n_lines} active connection(s)",
                    delta_color="off",
                )

    st.divider()

    # ── Flow matrix heatmap ─────────────────────────────────────────────────
    if flow_df is not None and not flow_df.empty:
        st.markdown(f"#### Flow matrix — From × To  ({flow_unit})")
        st.plotly_chart(
            plots.flow_matrix_heatmap(
                flow_df, value_label=flow_unit, title=None,
            ),
            use_container_width=True,
        )

    # ── Net trade per country ───────────────────────────────────────────────
    if flow_df is not None and not flow_df.empty:
        st.markdown(f"#### Net trade per country  ({flow_unit})")
        c1, c2 = st.columns([0.5, 0.5])
        with c1:
            agg_level = st.radio(
                "Aggregation",
                ["Country", "Region"],
                horizontal=True,
                key=f"net_{label}_agg",
                help="Country = aggregate intra-country flows out, Region = keep raw.",
            )
        net_df = data.net_trade(flow_symbol, by=agg_level, scenarios=scns)
        if net_df.empty:
            st.info("Net trade table came back empty (no inter-region flows after aggregation).")
        else:
            st.plotly_chart(
                plots.net_trade_bar(
                    net_df, region_col=agg_level, value_label=flow_unit,
                ),
                use_container_width=True,
            )
            plots.show_table_with_download(
                net_df.set_index(["Scenario", agg_level]),
                filename=f"{label.lower()}_net_trade",
                label=f"📋 {label} net-trade table",
            )

    st.divider()

    # ── Top lines by capacity ───────────────────────────────────────────────
    if cap_df is not None and not cap_df.empty:
        st.markdown(f"#### Top lines by capacity  ({cap_unit})")
        n_lines = st.slider("Show top N", min_value=5, max_value=30, value=15,
                            key=f"top_n_{label}")
        # Aggregate Category (Exo+Endo) before plotting
        cap_for_plot = (
            cap_df.groupby([c for c in ("Scenario", "From", "To") if c in cap_df.columns],
                           as_index=False, observed=True)["Value"].sum()
        )
        st.plotly_chart(
            plots.top_lines_bar(
                cap_for_plot, n=n_lines, value_label=cap_unit,
                title=None,
            ),
            use_container_width=True,
        )

    # ── Utilization ─────────────────────────────────────────────────────────
    if cap_df is not None and not cap_df.empty and flow_df is not None and not flow_df.empty:
        st.markdown("#### Line utilization")
        util_df = data.transmission_utilization(cap_symbol, flow_symbol, scenarios=scns)
        if util_df.empty:
            st.info("Utilization could not be computed.")
        else:
            # Optional threshold to hide near-idle lines
            min_util = st.number_input(
                "Min utilization to display",
                min_value=0.0, max_value=2.0, value=0.0, step=0.05,
                format="%.2f",
                key=f"min_util_{label}",
                help="Hide lines with utilization below this fraction.",
            )
            shown = util_df if min_util == 0 else util_df[util_df["Utilization"] >= min_util]
            if shown.empty:
                st.info(f"No lines above utilization {min_util:.0%}.")
            else:
                st.plotly_chart(
                    plots.utilization_heatmap(shown, title=None),
                    use_container_width=True,
                )
                plots.show_table_with_download(
                    util_df.set_index(["Scenario", "From", "To"]),
                    filename=f"{label.lower()}_utilization",
                    label=f"📋 {label} utilization table",
                )


# ── Build commodity tabs ────────────────────────────────────────────────────
def has_any(*syms: str) -> bool:
    return any(data.any_scenario_has(s) for s in syms)


tab_specs = []
if has_any("X_CAP_YCR", "X_FLOW_YCR"):
    tab_specs.append(("⚡ Electricity", "EL"))
if has_any("XH2_CAP_YCR", "XH2_FLOW_YCR"):
    tab_specs.append(("💧 Hydrogen", "H2"))
if has_any("XH_CAP_YCA", "XH_FLOW_YCA"):
    tab_specs.append(("🔥 Heat", "H"))

if not tab_specs:
    st.info("No transmission symbols (`X_*`, `XH2_*`, `XH_*`) in the loaded scenarios.")
    st.stop()

tabs = st.tabs([t[0] for t in tab_specs])

for tab, (_, kind) in zip(tabs, tab_specs):
    with tab:
        if kind == "EL":
            render_commodity(
                label="Electricity",
                cap_symbol="X_CAP_YCR",
                flow_symbol="X_FLOW_YCR",
                flow_unit="TWh",
                cap_unit="GW",
            )
        elif kind == "H2":
            render_commodity(
                label="Hydrogen",
                cap_symbol="XH2_CAP_YCR",
                flow_symbol="XH2_FLOW_YCR",
                flow_unit="TWh",
                cap_unit="GW",
            )
        elif kind == "H":
            render_commodity(
                label="Heat",
                cap_symbol="XH_CAP_YCA",
                flow_symbol="XH_FLOW_YCA",
                flow_unit="TWh",
                cap_unit="GW",
            )
