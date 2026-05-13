"""Prices & Demand page — electricity, heat, hydrogen prices and demand.

Each commodity gets its own tab. Tabs gracefully show a friendly message if
the relevant symbols aren't in the loaded archive (e.g. no heat prices in
Nordics).
"""
from __future__ import annotations

import streamlit as st

from lib import data, plots

data.ensure_state()
st.title("💰 Prices and Demand")

scns = data.selected_scenarios()
if not scns:
    st.info("Upload at least one scenario archive in the sidebar to see content.")
    st.stop()

st.caption(
    f"Showing **{len(scns)}** scenario(s)  ·  Year: **{data.selected_year() or '—'}**  ·  "
    f"Countries: {', '.join(data.selected_countries() or ['all'])}"
)


# ── Shared helper: render one commodity's section ───────────────────────────
def render_commodity(
    label: str,
    price_annual: str,
    price_hourly: str,
    demand_annual: str,
    demand_hourly: str | None = None,
    price_unit: str = "money/MWh",
    demand_unit: str = "TWh",
    region_col: str = "Region",
) -> None:
    price_df = data.get_filtered(price_annual)
    price_hr_df = data.get_filtered(price_hourly) if price_hourly else None
    demand_df = data.get_filtered(demand_annual)
    demand_hr_df = data.get_filtered(demand_hourly) if demand_hourly else None

    if all(df is None or df.empty for df in (price_df, price_hr_df, demand_df, demand_hr_df)):
        st.info(f"No {label.lower()} price or demand symbols in the loaded scenarios.")
        return

    # ── KPI row ─────────────────────────────────────────────────────────────
    cols = st.columns(min(len(scns), 4))
    for i, scn in enumerate(scns):
        with cols[i % len(cols)]:
            st.markdown(f"**{scn.name}**")
            # Average price
            price_t = scn.tables.get(price_annual)
            if price_t is not None and not price_t.empty:
                try:
                    avg_price = float(price_t["Value"].astype(float).mean())
                    st.metric(f"Avg {label.lower()} price", f"{avg_price:,.1f} {price_unit}")
                except (ValueError, TypeError):
                    st.metric(f"Avg {label.lower()} price", "—")
            # Total demand
            demand_t = scn.tables.get(demand_annual)
            if demand_t is not None and not demand_t.empty:
                total = float(demand_t["Value"].sum())
                st.metric(f"Total {label.lower()} demand", f"{total:,.1f} {demand_unit}")

    st.divider()

    # ── Annual prices per region ────────────────────────────────────────────
    if price_df is not None and not price_df.empty:
        st.markdown(f"#### Average {label.lower()} price by region")
        # Some price symbols have a Category column (eg H2_PRICE_YCR); collapse it
        sub = price_df.copy()
        if "Category" in sub.columns:
            sub = sub.groupby(
                [c for c in sub.columns if c not in ("Category", "Value")],
                as_index=False, observed=True,
            )["Value"].mean()
        # Choose the most granular region-like column available
        region_choice = region_col if region_col in sub.columns else (
            "Area" if "Area" in sub.columns else "Country"
        )
        st.plotly_chart(
            plots.price_by_region_bar(
                sub, region_col=region_choice, value_label=price_unit,
                title=None,
            ),
            use_container_width=True,
        )
    else:
        st.info(f"No annual price symbol (`{price_annual}`) loaded.")

    # ── Demand by category ──────────────────────────────────────────────────
    if demand_df is not None and not demand_df.empty:
        st.markdown(f"#### {label} demand by category")
        st.plotly_chart(
            plots.demand_by_category_bar(
                demand_df, value_label=demand_unit, title=None,
            ),
            use_container_width=True,
        )
        plots.show_table_with_download(
            demand_df.groupby(
                [c for c in ("Scenario", "Country", "Region", "Area", "Category") if c in demand_df.columns],
                as_index=False, observed=True,
            )["Value"].sum().set_index(
                [c for c in ("Scenario", "Country") if c in demand_df.columns]
            ),
            filename=f"{demand_annual.lower()}",
            label=f"📋 {label} demand detail",
        )
    else:
        st.info(f"No annual demand symbol (`{demand_annual}`) loaded.")

    # ── Hourly profile ──────────────────────────────────────────────────────
    if price_hr_df is not None and not price_hr_df.empty:
        st.markdown(f"#### Hourly {label.lower()} price profile")
        regions = sorted(price_hr_df[region_col].dropna().unique()) if region_col in price_hr_df.columns else []
        if not regions:
            st.info("No regions in hourly price data.")
        else:
            c1, c2 = st.columns([0.5, 0.5])
            with c1:
                pick = st.selectbox(
                    f"Region for hourly {label.lower()} price",
                    regions,
                    index=0,
                    key=f"hrl_{label}_price_region",
                )
            sub = price_hr_df[price_hr_df[region_col] == pick]
            st.plotly_chart(
                plots.hourly_line(
                    sub, value_label=price_unit,
                    title=f"{pick} — hourly {label.lower()} price",
                ),
                use_container_width=True,
            )


# ── Build tabs based on available data ──────────────────────────────────────
def commodity_has_any(*symbols: str) -> bool:
    """True if any selected scenario contains any of the given symbols."""
    return any(data.any_scenario_has(s) for s in symbols)


tab_specs = []
if commodity_has_any("EL_PRICE_YCR", "EL_PRICE_YCRST", "EL_DEMAND_YCR", "EL_DEMAND_YCRST"):
    tab_specs.append(("⚡ Electricity", "EL"))
if commodity_has_any("H_PRICE_YCRA", "H_PRICE_YCRAST", "H_DEMAND_YCRA", "H_DEMAND_YCRAST"):
    tab_specs.append(("🔥 Heat", "H"))
if commodity_has_any("H2_PRICE_YCR", "H2_PRICE_YCRST", "H2_DEMAND_YCR", "H2_DEMAND_YCRST"):
    tab_specs.append(("💧 Hydrogen", "H2"))

if not tab_specs:
    st.info("No price or demand symbols in the loaded scenarios.")
    st.stop()

tabs = st.tabs([t[0] for t in tab_specs])

for tab, (_, kind) in zip(tabs, tab_specs):
    with tab:
        if kind == "EL":
            render_commodity(
                label="Electricity",
                price_annual="EL_PRICE_YCR",
                price_hourly="EL_PRICE_YCRST",
                demand_annual="EL_DEMAND_YCR",
                demand_hourly="EL_DEMAND_YCRST",
                price_unit="money/MWh",
                demand_unit="TWh",
                region_col="Region",
            )
        elif kind == "H":
            render_commodity(
                label="Heat",
                price_annual="H_PRICE_YCRA",
                price_hourly="H_PRICE_YCRAST",
                demand_annual="H_DEMAND_YCRA",
                demand_hourly="H_DEMAND_YCRAST",
                price_unit="money/MWh",
                demand_unit="TWh",
                region_col="Area",
            )
        elif kind == "H2":
            render_commodity(
                label="Hydrogen",
                price_annual="H2_PRICE_YCR",
                price_hourly="H2_PRICE_YCRST",
                demand_annual="H2_DEMAND_YCR",
                demand_hourly="H2_DEMAND_YCRST",
                price_unit="money/MWh",
                demand_unit="TWh",
                region_col="Region",
            )
