"""Plotly chart builders shared across pages.

All charts inherit `lib.theme.balmorel` template (set globally in `theme.apply()`)
so visual style is consistent without per-plot config.

Each helper returns a `plotly.graph_objects.Figure`. Pages call `st.plotly_chart(fig)`.
The plotly toolbar's built-in camera icon provides PNG download — no extra code needed.
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from lib.theme import PB_INDICATOR_COLORS, TECH_FUEL_COLORS

# ── Cost breakdown ──────────────────────────────────────────────────────────

# pretty-format OBJ_YCR Category labels: "GENERATION_CAPITAL_COSTS" → "Generation capital costs"
def _pretty_cat(s: str) -> str:
    return s.replace("_", " ").capitalize()


def cost_breakdown_bar(df: pd.DataFrame) -> go.Figure:
    """Horizontal stacked bar of OBJ_YCR cost categories per scenario.

    Expects columns: Scenario, Category, Value (Mmoney).
    """
    if df.empty:
        return _empty("No cost data (OBJ_YCR) available.")
    agg = (
        df.groupby(["Scenario", "Category"], as_index=False, observed=True)["Value"]
        .sum()
    )
    agg["CategoryLabel"] = agg["Category"].map(_pretty_cat)
    # Order categories: capital → fixed → operational → fuel → transmission
    order = sorted(agg["Category"].unique(), key=_cost_sort_key)
    label_order = [_pretty_cat(c) for c in order]
    fig = px.bar(
        agg,
        x="Value",
        y="Scenario",
        color="CategoryLabel",
        orientation="h",
        category_orders={"CategoryLabel": label_order},
        title="System cost by category (Mmoney)",
        labels={"Value": "Mmoney", "CategoryLabel": "Cost category"},
    )
    fig.update_layout(barmode="stack", height=80 + 70 * agg["Scenario"].nunique())
    fig.update_traces(hovertemplate="<b>%{y}</b><br>%{fullData.name}: %{x:,.1f} Mmoney<extra></extra>")
    return fig


_COST_ORDER_PREFIXES = [
    "GENERATION_CAPITAL", "GENERATION_FIXED", "GENERATION_OPERATIONAL",
    "GENERATION_FUEL", "TRANSMISSION_CAPITAL", "TRANSMISSION_OPERATIONAL",
    "HEAT_TRANSMISSION", "H2_TRANSMISSION",
]


def _cost_sort_key(cat: str) -> tuple[int, str]:
    for i, p in enumerate(_COST_ORDER_PREFIXES):
        if cat.startswith(p):
            return (i, cat)
    return (len(_COST_ORDER_PREFIXES), cat)


# ── Capacity mix ────────────────────────────────────────────────────────────

def capacity_by_commodity(
    df: pd.DataFrame,
    *,
    color_by: str = "Technology",
    min_capacity: float = 0.01,
) -> go.Figure:
    """Stacked bar: capacity per scenario per commodity, stacked by Technology or Fuel.

    Expects columns: Scenario, Commodity, Technology, Fuel, Value (GW).
    """
    if df.empty:
        return _empty("No capacity data (G_CAP_YCRAF) available.")
    if color_by not in df.columns:
        return _empty(f"Column `{color_by}` not in capacity data.")
    agg = (
        df.groupby(["Scenario", "Commodity", color_by], as_index=False, observed=True)["Value"]
        .sum()
    )
    agg = agg[agg["Value"].abs() >= min_capacity]
    if agg.empty:
        return _empty("All capacity values are below the display threshold.")

    fig = px.bar(
        agg,
        x="Scenario",
        y="Value",
        color=color_by,
        facet_col="Commodity",
        facet_col_spacing=0.05,
        color_discrete_map=TECH_FUEL_COLORS,
        title=f"Installed capacity by {color_by.lower()} (GW)",
        labels={"Value": "GW"},
    )
    fig.update_layout(barmode="stack", height=460)
    fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
    fig.update_traces(hovertemplate="<b>%{x}</b><br>%{fullData.name}: %{y:,.2f} GW<extra></extra>")
    return fig


# ── Production share ────────────────────────────────────────────────────────

def production_share_donuts(
    df: pd.DataFrame,
    *,
    commodity: str = "ELECTRICITY",
    color_by: str = "Fuel",
) -> go.Figure:
    """One donut per scenario showing fuel mix of total production for a commodity.

    Expects columns: Scenario, Commodity, Fuel/Technology, Value (TWh).
    """
    if df.empty:
        return _empty("No production data (PRO_YCRAGF) available.")
    sub = df[df.get("Commodity") == commodity] if "Commodity" in df.columns else df
    if sub.empty:
        return _empty(f"No {commodity.title()} production data.")
    if color_by not in sub.columns:
        return _empty(f"Column `{color_by}` not in production data.")

    scenarios = sorted(sub["Scenario"].unique())
    if not scenarios:
        return _empty("No scenarios in production data.")

    n = len(scenarios)
    from plotly.subplots import make_subplots
    fig = make_subplots(
        rows=1, cols=n,
        specs=[[{"type": "domain"}] * n],
        subplot_titles=scenarios,
    )
    for i, sc in enumerate(scenarios, start=1):
        agg = (
            sub[sub["Scenario"] == sc]
            .groupby(color_by, as_index=False, observed=True)["Value"]
            .sum()
        )
        agg = agg[agg["Value"] > 0].sort_values("Value", ascending=False)
        colors = [TECH_FUEL_COLORS.get(k, "#bfbfbf") for k in agg[color_by]]
        fig.add_trace(
            go.Pie(
                labels=agg[color_by],
                values=agg["Value"],
                hole=0.55,
                marker=dict(colors=colors),
                hovertemplate="<b>%{label}</b><br>%{value:,.1f} TWh<br>%{percent}<extra></extra>",
                textinfo="none",
            ),
            row=1, col=i,
        )
    fig.update_layout(
        title=f"{commodity.title()} production mix by {color_by.lower()}",
        height=380,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5),
    )
    return fig


# ── PB radar (for the Planetary Boundaries page later) ──────────────────────

def pb_radar(values_by_scenario: dict[str, dict[str, float]], *, boundary: float = 1.0) -> go.Figure:
    """Radar/spider plot of TL_* values across scenarios.

    `values_by_scenario` is {scenario: {indicator: TL_value}}.
    """
    if not values_by_scenario:
        return _empty("No PB transgression-level data.")

    indicators = sorted({ind for v in values_by_scenario.values() for ind in v})
    if not indicators:
        return _empty("No PB indicators in selected scenarios.")

    fig = go.Figure()
    for sc, by_ind in values_by_scenario.items():
        r = [by_ind.get(ind, 0.0) for ind in indicators]
        fig.add_trace(go.Scatterpolar(
            r=r + [r[0]],
            theta=indicators + [indicators[0]],
            fill="toself",
            name=sc,
            opacity=0.45,
            hovertemplate="<b>%{theta}</b><br>" + sc + ": TL = %{r:.4f}<extra></extra>",
        ))
    # Boundary ring (TL = 1.0)
    fig.add_trace(go.Scatterpolar(
        r=[boundary] * (len(indicators) + 1),
        theta=indicators + [indicators[0]],
        mode="lines",
        line=dict(color="#d35050", dash="dash", width=1.5),
        name=f"Boundary (TL = {boundary})",
        hoverinfo="skip",
    ))
    max_r = max(max(v.values(), default=0) for v in values_by_scenario.values()) or 1.0
    fig.update_layout(
        title="Planetary boundary transgression levels (TL)",
        polar=dict(radialaxis=dict(visible=True, range=[0, max(max_r * 1.1, boundary * 1.2)])),
        height=520,
    )
    return fig


# ── Generic helpers (kept for older callers / future pages) ─────────────────

def stacked_bar(
    df: pd.DataFrame,
    *,
    x: str,
    y: str = "Value",
    color: str,
    facet: str | None = None,
    title: str | None = None,
    color_map: dict[str, str] | None = None,
) -> go.Figure:
    """Generic stacked bar, used for ad-hoc plots."""
    cmap = color_map or (TECH_FUEL_COLORS if color in ("Technology", "Fuel") else None)
    fig = px.bar(df, x=x, y=y, color=color, facet_col=facet, title=title, color_discrete_map=cmap)
    fig.update_layout(barmode="stack")
    if facet:
        fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
    return fig


def heatmap(
    df: pd.DataFrame,
    *,
    x: str,
    y: str,
    z: str = "Value",
    title: str | None = None,
    colorscale: str = "Blues",
) -> go.Figure:
    pivot = df.pivot_table(index=y, columns=x, values=z, aggfunc="sum", fill_value=0)
    return go.Figure(
        data=go.Heatmap(
            z=pivot.values,
            x=pivot.columns.astype(str),
            y=pivot.index.astype(str),
            colorscale=colorscale,
            hovertemplate=f"{x}: %{{x}}<br>{y}: %{{y}}<br>{z}: %{{z:.2f}}<extra></extra>",
        ),
        layout=go.Layout(title=title),
    )


def _empty(msg: str) -> go.Figure:
    """Empty figure with a centered explanatory annotation."""
    fig = go.Figure()
    fig.add_annotation(text=msg, showarrow=False, xref="paper", yref="paper",
                       x=0.5, y=0.5, font=dict(size=14, color="#888"))
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    fig.update_layout(height=200, margin=dict(l=20, r=20, t=20, b=20))
    return fig
