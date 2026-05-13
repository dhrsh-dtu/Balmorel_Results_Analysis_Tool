"""Plotly chart builders shared across pages.

All charts inherit `lib.theme.balmorel` template (set globally in `theme.apply()`)
so visual style is consistent without per-plot config.

These are minimal stubs for P0 — full implementations land in P3+.
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from lib.theme import TECH_FUEL_COLORS


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
    """Stacked bar chart, optionally faceted by `facet`.

    Honors TECH_FUEL_COLORS when `color` is Technology or Fuel.
    """
    cmap = color_map or (TECH_FUEL_COLORS if color in ("Technology", "Fuel") else None)
    fig = px.bar(
        df,
        x=x,
        y=y,
        color=color,
        facet_col=facet,
        title=title,
        color_discrete_map=cmap,
    )
    fig.update_layout(barmode="stack")
    return fig


def line(
    df: pd.DataFrame,
    *,
    x: str,
    y: str = "Value",
    color: str,
    title: str | None = None,
) -> go.Figure:
    return px.line(df, x=x, y=y, color=color, title=title)


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


def radar(
    indicators: list[str],
    values_by_scenario: dict[str, list[float]],
    *,
    title: str | None = None,
    reference_ring: float | None = 1.0,
) -> go.Figure:
    """Radar / spider plot for Planetary Boundary transgression levels.

    A reference ring at value=1.0 marks the planetary boundary; values >1 are
    transgressions.
    """
    fig = go.Figure()
    for scn, vals in values_by_scenario.items():
        fig.add_trace(
            go.Scatterpolar(
                r=vals + [vals[0]],
                theta=indicators + [indicators[0]],
                fill="toself",
                name=scn,
                opacity=0.4,
            )
        )
    if reference_ring is not None:
        fig.add_trace(
            go.Scatterpolar(
                r=[reference_ring] * (len(indicators) + 1),
                theta=indicators + [indicators[0]],
                mode="lines",
                line=dict(color="red", dash="dash", width=1),
                name=f"Boundary (TL = {reference_ring})",
                showlegend=True,
            )
        )
    fig.update_layout(
        title=title,
        polar=dict(radialaxis=dict(visible=True, range=[0, max(reference_ring or 1, 1.5)])),
    )
    return fig
