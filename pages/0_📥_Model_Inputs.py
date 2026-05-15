"""Model Inputs page.

Five sections:
  1. Sectors covered (inferred from loaded data — works on any archive)
  2. Technology portfolio per sector (from GDATA + cross-ref with G_CAP_YCRAF)
  3. Cost inputs per technology (capex, fixed/var O&M, lifetime, efficiency)
  4. Demand inputs per energy vector (raw DE, DH, HYDROGEN_DH2)
  5. Sector coupling (input demand → served demand transformation)

The page auto-hides itself with a friendly message if no scenario in the
session has `has_inputs=True` in its capabilities.
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from lib import data, plots
from lib.theme import TECH_FUEL_COLORS

data.ensure_state()
st.title("📥 Model Inputs")

data.render_page_filters("model_inputs")
scns = data.selected_scenarios()
if not scns:
    st.info("Upload at least one scenario archive in the sidebar to see content.")
    st.stop()

if not data.any_has_inputs(scns):
    st.warning(
        "No selected scenario contains model-input data. Re-export with the "
        "current CLI (`python -m balmorel_dashboard /path/to/Balmorel_root/`) "
        "to enable this page."
    )
    st.stop()

st.caption(
    f"Showing **{len(scns)}** scenario(s)  ·  Year: **{data.selected_year() or '—'}**  ·  "
    f"Countries: {', '.join(data.selected_countries() or ['all'])}"
)


# ────────────────────────────────────────────────────────────────────────────
# §1. Sectors covered
# ────────────────────────────────────────────────────────────────────────────
st.markdown("## 1. Sectors covered")

sectors = data.sectors_present(scns)
cols = st.columns(min(len(sectors), 3))
for i, (sector, info) in enumerate(sectors.items()):
    c = cols[i % len(cols)]
    with c:
        if info["present"]:
            st.markdown(f"### ✓ {sector}")
            st.caption(info["evidence"])
        else:
            st.markdown(f"### ⚪ {sector}")
            st.caption("not in this archive")

st.divider()


# ────────────────────────────────────────────────────────────────────────────
# §2. Technology portfolio per sector
# ────────────────────────────────────────────────────────────────────────────
st.markdown("## 2. Technology portfolio")
st.caption(
    "Catalog of generation units available to the model (from `GDATA` × `GGG`). "
    "Includes units that were not deployed — those would be invisible from the "
    "MainResults output alone."
)

# Build one combined catalog DataFrame across scenarios with a Sector column
catalog_frames = []
for s in scns:
    if not s.capabilities.get("has_inputs"):
        continue
    gws = data.gdata_with_sector(s)
    if gws.empty:
        continue
    gws = gws.assign(Scenario=s.name)
    catalog_frames.append(gws)

if not catalog_frames:
    st.info("No `GDATA` available in selected scenarios.")
else:
    catalog = pd.concat(catalog_frames, ignore_index=True)

    # Sector filter
    available_sectors = sorted(catalog["Sector"].unique())
    chosen = st.multiselect(
        "Filter by sector",
        options=available_sectors,
        default=available_sectors,
    )
    filtered = catalog[catalog["Sector"].isin(chosen)] if chosen else catalog

    # Bar chart: #units per sector (grouped by scenario)
    counts = (
        filtered.groupby(["Scenario", "Sector"], as_index=False, observed=True)["Generation"]
        .nunique()
        .rename(columns={"Generation": "Units"})
    )
    fig = px.bar(
        counts, x="Sector", y="Units", color="Scenario", barmode="group",
        title="Number of generation units per sector",
        category_orders={"Sector": chosen},
    )
    fig.update_layout(height=380)
    st.plotly_chart(fig, use_container_width=True)

    # Tech-type breakdown within sector — group by TechGroup if available else by Fuel
    group_col = "TechGroup" if "TechGroup" in filtered.columns and not filtered["TechGroup"].isna().all() else "Sector"
    plots.show_table_with_download(
        filtered[["Scenario", "Sector", "Generation"] + [c for c in ("TechGroup", "SubTechGroup", "Fuel") if c in filtered.columns]]
        .sort_values(["Scenario", "Sector", "Generation"])
        .set_index(["Scenario", "Sector"]),
        filename="tech_portfolio",
        label="📋 Full tech catalog",
    )

st.divider()


# ────────────────────────────────────────────────────────────────────────────
# §3. Cost inputs per technology
# ────────────────────────────────────────────────────────────────────────────
st.markdown("## 3. Cost inputs per technology")
st.caption(
    "Per-unit cost parameters from `GDATA`: investment cost (capex), fixed and "
    "variable O&M, lifetime, fuel efficiency. Bars below show the mean across "
    "all units in each sector — drill into the expander for the full per-unit table."
)

if not catalog_frames:
    st.info("Cost inputs require `GDATA`; not available.")
else:
    # The cost columns we care about (friendly names from pivot_gdata)
    cost_specs = [
        ("Capex",   "Investment cost (Money/MW)"),
        ("FixedOM", "Fixed O&M (Money/MW/year)"),
        ("VarOM",   "Variable O&M (Money/MWh)"),
        ("FuelEff", "Fuel efficiency (—)"),
        ("Lifetime", "Lifetime (years)"),
    ]

    # Sector filter for §3 too
    c1, c2 = st.columns(2)
    with c1:
        cost_sector = st.multiselect(
            "Filter by sector (cost view)",
            options=available_sectors,
            default=[s for s in available_sectors if s != "Other / unknown"],
            key="cost_sector",
        )
    with c2:
        agg_fn = st.radio(
            "Aggregate across units",
            ["mean", "median", "min", "max"],
            horizontal=True,
            index=0,
        )
    cost_df = catalog[catalog["Sector"].isin(cost_sector)] if cost_sector else catalog

    # One bar chart per cost column
    for col, label in cost_specs:
        if col not in cost_df.columns:
            continue
        sub = cost_df[["Scenario", "Sector", col]].dropna(subset=[col])
        if sub.empty:
            continue
        agg = (
            sub.groupby(["Scenario", "Sector"], as_index=False, observed=True)[col]
            .agg(agg_fn)
        )
        fig = px.bar(
            agg, x="Sector", y=col, color="Scenario", barmode="group",
            title=f"{label} — {agg_fn} per sector",
            category_orders={"Sector": cost_sector or available_sectors},
        )
        fig.update_layout(height=320)
        st.plotly_chart(fig, use_container_width=True)

    # Full per-unit table with expander
    detail_cols = ["Scenario", "Sector", "Generation"] + [c for c, _ in cost_specs if c in cost_df.columns]
    plots.show_table_with_download(
        cost_df[detail_cols].sort_values(["Scenario", "Sector", "Generation"])
        .set_index(["Scenario", "Sector"]),
        filename="cost_inputs_per_unit",
        label="📋 Per-unit cost detail",
        fmt="{:,.4g}",
    )

st.divider()


# ────────────────────────────────────────────────────────────────────────────
# §4. Demand inputs per energy vector
# ────────────────────────────────────────────────────────────────────────────
st.markdown("## 4. Demand inputs per energy vector")
st.caption(
    "Raw input demand fed to Balmorel. **Electricity** from `DE`, **Heat** from `DH`, "
    "**Hydrogen** from `HYDROGEN_DH2`. These are exogenous figures _before_ the "
    "model adds endogenous sector-coupling demand (which appears in §5)."
)

demand_specs = [
    ("Electricity", "DE",           "MWh", "Region"),
    ("Heat",        "DH",           "MWh", "Area"),
    ("Hydrogen",    "HYDROGEN_DH2", "MWh", "Location"),
]

# Active model scope: regions/areas that actually appear in MainResults
# (Balmorel reads full-Europe inputs even for a Nordic-only scenario, but the
# user only cares about the active scope).
def _active_regions(scenarios) -> set[str]:
    regs: set[str] = set()
    for s in scenarios:
        regs.update(s.manifest.get("regions", []))
    return regs

def _active_areas(scenarios) -> set[str]:
    areas: set[str] = set()
    for s in scenarios:
        areas.update(s.manifest.get("areas", []))
    return areas

active_regions = _active_regions(scns)
active_areas = _active_areas(scns)


def _years_in(*syms: str) -> list[str]:
    years: set[str] = set()
    for s in scns:
        for sym in syms:
            df = s.inputs.get(sym)
            if df is None or "Year" not in df.columns:
                continue
            years.update(df["Year"].astype(str).dropna().unique())
    return sorted(years)


def _restrict_to_scope(df: pd.DataFrame) -> pd.DataFrame:
    """Filter an input DataFrame to only rows in the active model scope."""
    if df.empty:
        return df
    if "Region" in df.columns and active_regions:
        df = df[df["Region"].astype(str).isin(active_regions)]
    if "Area" in df.columns and active_areas:
        df = df[df["Area"].astype(str).isin(active_areas)]
    # HYDROGEN_DH2 uses 'Location' which can be region or area
    if "Location" in df.columns and (active_regions or active_areas):
        scope = active_regions | active_areas
        df = df[df["Location"].astype(str).isin(scope)]
    return df


input_years = _years_in("DE", "DH", "HYDROGEN_DH2")
sel_year = data.selected_year()
default_year = sel_year if sel_year in input_years else (input_years[-1] if input_years else None)
c1, c2 = st.columns(2)
with c1:
    demand_year = st.selectbox(
        "Year to show",
        options=input_years or ["—"],
        index=(input_years.index(default_year) if default_year in input_years else 0),
        help="Input demand often spans multiple forecast years. Pick one.",
    )
with c2:
    restrict_scope = st.checkbox(
        "Restrict to active model scope",
        value=True,
        help=(
            "Balmorel reads the full-Europe input dataset even for region-limited "
            "scenarios. With this on, only regions/areas that appear in MainResults "
            "are shown."
        ),
    )

demand_data = []
for vector, sym, unit, locator in demand_specs:
    df = data.get_input_table(sym, scenarios=scns)
    if df.empty or "Value" not in df.columns:
        continue
    if "Year" in df.columns and demand_year != "—":
        df = df[df["Year"].astype(str) == str(demand_year)]
    if restrict_scope:
        df = _restrict_to_scope(df)
    if df.empty:
        continue
    # Convert MWh → TWh for readability
    grp_cols = [c for c in ("Scenario",) if c in df.columns]
    agg = df.groupby(grp_cols, observed=True)["Value"].sum().reset_index()
    agg["Value_TWh"] = agg["Value"] / 1e6
    agg["Vector"] = vector
    demand_data.append(agg)

if not demand_data:
    st.info("No raw demand input symbols available in the selected scenarios.")
else:
    combined = pd.concat(demand_data, ignore_index=True)
    fig = px.bar(
        combined,
        x="Vector", y="Value_TWh", color="Scenario", barmode="group",
        title=f"Annual input demand by energy vector — {demand_year} (TWh)",
        labels={"Value_TWh": "TWh"},
    )
    fig.update_layout(height=380)
    st.plotly_chart(fig, use_container_width=True)

    # Regional breakdown per vector
    sub_specs = st.tabs([s[0] for s in demand_specs])
    for tab, (vector, sym, unit, locator) in zip(sub_specs, demand_specs):
        with tab:
            df = data.get_input_table(sym, scenarios=scns)
            if df.empty:
                st.info(f"`{sym}` not in selected scenarios.")
                continue
            if "Year" in df.columns and demand_year != "—":
                df = df[df["Year"].astype(str) == str(demand_year)]
            if restrict_scope:
                df = _restrict_to_scope(df)
            loc_col = locator if locator in df.columns else (
                "Region" if "Region" in df.columns else (
                    "Area" if "Area" in df.columns else "Location"
                )
            )
            if loc_col not in df.columns:
                st.info(f"No regional column ({locator}) in `{sym}`.")
                continue
            agg = (
                df.groupby(["Scenario", loc_col], observed=True)["Value"].sum()
                .div(1e6)  # MWh → TWh
                .reset_index()
                .rename(columns={"Value": "TWh"})
            )
            if agg.empty:
                st.info(f"No data for {vector} in {demand_year}.")
                continue
            fig = px.bar(
                agg, x=loc_col, y="TWh", color="Scenario", barmode="group",
                title=f"{vector} demand input by {loc_col.lower()} — {demand_year} (TWh)",
            )
            fig.update_xaxes(tickangle=-45)
            fig.update_layout(height=340)
            st.plotly_chart(fig, use_container_width=True)
            plots.show_table_with_download(
                agg.set_index(["Scenario", loc_col]),
                filename=f"demand_input_{vector.lower()}_{demand_year}",
                label=f"📋 {vector} demand table",
            )

st.divider()


# ────────────────────────────────────────────────────────────────────────────
# §5. Sector coupling
# ────────────────────────────────────────────────────────────────────────────
st.markdown("## 5. Sector coupling")
st.caption(
    "How exogenous input demand (§4) becomes total served demand. The gap is "
    "**endogenous** demand the model adds: electric heating, EV charging, "
    "electrolyser electricity, distribution & transmission losses. Compare "
    "scenarios side-by-side to see how sector-coupling assumptions differ."
)

# Use EL_DEMAND_YCR (output) which has the full Category breakdown:
# EXOGENOUS, ENDOGENOUS_ELECT2HEAT, ENDO_EV, ENDO_H2, DIST_LOSSES, TRANS_LOSSES
el_dem = data.get_table("EL_DEMAND_YCR")
h2_dem = data.get_table("H2_DEMAND_YCR")

if el_dem.empty and h2_dem.empty:
    st.info("No demand-by-category data (EL_DEMAND_YCR, H2_DEMAND_YCR) in selected scenarios.")
else:
    coupling_tabs = st.tabs(["⚡ Electricity", "💧 Hydrogen"])

    # Pretty category labels
    _CAT_LABEL = {
        "EXOGENOUS":              "Exogenous (input)",
        "ENDOGENOUS_ELECT2HEAT":  "Electric heating",
        "ENDO_EV":                "EV charging",
        "ENDO_H2":                "Electrolysers (→ H2)",
        "ENDO_INTERSTO":          "Inter-seasonal storage",
        "DIST_LOSSES":            "Distribution losses",
        "TRANS_LOSSES":           "Transmission losses",
    }
    _CAT_ORDER = [
        "EXOGENOUS", "ENDOGENOUS_ELECT2HEAT", "ENDO_EV", "ENDO_H2",
        "ENDO_INTERSTO", "DIST_LOSSES", "TRANS_LOSSES",
    ]
    _CAT_COLORS = {
        "Exogenous (input)":         "#006460",
        "Electric heating":          "#FFA500",
        "EV charging":               "#cd6f00",
        "Electrolysers (→ H2)":      "#89e0ff",
        "Inter-seasonal storage":    "#E8C3A8",
        "Distribution losses":       "#bfbfbf",
        "Transmission losses":       "#7f7f7f",
    }

    def _render_coupling(df: pd.DataFrame, vector_label: str, unit_label: str = "TWh") -> None:
        if df.empty:
            st.info(f"No {vector_label} demand-by-category data.")
            return

        # Aggregate across countries within each (Scenario, Category)
        agg = df.groupby(["Scenario", "Category"], as_index=False, observed=True)["Value"].sum()
        agg["CategoryLabel"] = agg["Category"].astype(str).map(_CAT_LABEL).fillna(agg["Category"].astype(str))
        order_labels = [_CAT_LABEL.get(c, c) for c in _CAT_ORDER if _CAT_LABEL.get(c, c) in agg["CategoryLabel"].unique()]

        fig = px.bar(
            agg, x="Scenario", y="Value", color="CategoryLabel",
            color_discrete_map=_CAT_COLORS,
            category_orders={"CategoryLabel": order_labels},
            title=f"{vector_label} demand decomposition ({unit_label})",
            labels={"Value": unit_label, "CategoryLabel": ""},
        )
        fig.update_layout(barmode="stack", height=420)
        fig.update_traces(
            hovertemplate=(
                "<b>%{x}</b><br>%{fullData.name}: %{y:,.2f} " + unit_label + "<extra></extra>"
            )
        )
        st.plotly_chart(fig, use_container_width=True)

        # Side-by-side summary table
        pivot = agg.pivot(index="CategoryLabel", columns="Scenario", values="Value").fillna(0.0)
        pivot = pivot.reindex(order_labels)
        pivot.loc["── Total served"] = pivot.sum(axis=0)
        plots.show_table_with_download(
            pivot,
            filename=f"sector_coupling_{vector_label.lower()}",
            label=f"📋 {vector_label} category table",
            fmt="{:,.2f}",
        )

    with coupling_tabs[0]:
        _render_coupling(el_dem, "Electricity")
    with coupling_tabs[1]:
        _render_coupling(h2_dem, "Hydrogen")
