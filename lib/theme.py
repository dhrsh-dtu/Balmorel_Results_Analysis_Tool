"""Plotly theme and color palette for the dashboard.

The colors inherit from pybalmorel's convention where possible so plots produced
here are visually consistent with pybalmorel's own plot_bar_chart / plot_map
outputs.
"""
from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio

# FIX: Maybe replace the hardcoded dictionary below with this instead?
from pybalmorel.format import tech_colours

# ── Color palette ────────────────────────────────────────────────────────────
# Mirrors pybalmorel.formatting.balmorel_colours so figures match conventions.
# Duplicated here so the deployed app does not depend on pybalmorel.

TECH_FUEL_COLORS: dict[str, str] = {
    # Technologies
    "HYDRO-RESERVOIRS": "#33b1ff",
    "HYDRO-RUN-OF-RIVER": "#4589ff",
    "HYDRO": "#33b1ff",
    "WIND-ON": "#006460",
    "WIND-ONSHORE": "#006460",
    "WIND-OFF": "#08bdba",
    "WIND-OFFSHORE": "#08bdba",
    "SOLAR-PV": "#d2a106",
    "SOLAR-HEATING": "#FF69B4",
    "BOILERS": "#8B008B",
    "ELECT-TO-HEAT": "#FFA500",
    "INTERSEASONAL-HEAT-STORAGE": "#FFD700",
    "INTRASEASONAL-HEAT-STORAGE": "#00FFFF",
    "INTRASEASONAL-ELECT-STORAGE": "#ba4e00",
    "CHP-BACK-PRESSURE": "#E5D8D8",
    "CHP-EXTRACTION": "#ff7eb6",
    "CHP": "#E5D8D8",
    "CONDENSING": "#8a3ffc",
    "STEAMREFORMING": "#00BFFF",
    "SMR-CCS": "#00BFFF",
    "SMR": "#d1b9b9",
    "ELECTROLYZER": "#ADD8E6",
    "FUELCELL": "#d4bbff",
    "H2-STORAGE": "#E8C3A8",
    "SALT-CAVERN": "#E8C3A8",
    "STEEL-TANK": "#C0C0C0",
    "IMPORT H2": "#cd6f00",
    # Fuels
    "BIOGAS": "#23932d",
    "COAL": "#595959",
    "ELECTRIC": "#BA000F",
    "OIL": "#7b4c42",
    "FUELOIL": "#666666",
    "LIGHTOIL": "#666666",
    "MUNIWASTE": "#757501",
    "BIOMASS": "#006460",
    "HEAT": "#a5e982",
    "NATGAS": "#850017",
    "NATGAS-CCS": "#d35050",
    "OTHER": "#bfbfbf",
    "SOLAR": "#fad254",
    "SUN": "#ffff00",
    "NUCLEAR": "#cd6f00",
    "LIGNITE": "#2b1d1d",
    "HYDROGEN": "#89e0ff",
    "WATER": "#3f2500",
    "WIND": "#53f385",
    "WOODCHIPS": "#e94343",
    "WOODPELLETS": "#d73c3c",
    "PEAT": "#cccccc",
    "STRAW": "#f18787",
    "WASTEHEAT": "#ff0000",
    "IMPORT": "#96b9fc",
}

# Categorical palette for scenarios (when comparing multiple)
SCENARIO_PALETTE: list[str] = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
    "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
]

# Planetary boundary indicator colors
PB_INDICATOR_COLORS: dict[str, str] = {
    "CO2": "#d35050",
    "LU": "#23932d",
    "WU": "#33b1ff",
    "ACIDIFICATION": "#8a3ffc",
    "EUTROPHICATION_FRESHWATER": "#08bdba",
    "OZONE_DEPLETION": "#cd6f00",
    "PM": "#595959",
    "ECOTOXICITY_FRESHWATER": "#23932d",
    "RESOURCE": "#d2a106",
}

# ── Plotly template ──────────────────────────────────────────────────────────
_GRID = "#eef0f3"
_AXIS = "#1a1a1a"
_FONT = 'Inter, "Helvetica Neue", Arial, sans-serif'

_template = go.layout.Template(
    layout=go.Layout(
        font=dict(family=_FONT, size=13, color=_AXIS),
        title=dict(font=dict(size=16, family=_FONT, color=_AXIS), x=0.02, xanchor="left"),
        paper_bgcolor="white",
        plot_bgcolor="white",
        xaxis=dict(
            gridcolor=_GRID, gridwidth=1,
            linecolor=_AXIS, linewidth=1,
            ticks="outside", tickcolor=_AXIS,
            zeroline=False,
        ),
        yaxis=dict(
            gridcolor=_GRID, gridwidth=1,
            linecolor=_AXIS, linewidth=1,
            ticks="outside", tickcolor=_AXIS,
            zeroline=False,
        ),
        colorway=SCENARIO_PALETTE,
        margin=dict(l=60, r=20, t=60, b=60),
        hoverlabel=dict(bgcolor="white", font_size=12, font_family=_FONT, bordercolor="#dde1e6"),
        legend=dict(
            bgcolor="rgba(255,255,255,0.85)",
            bordercolor="#dde1e6",
            borderwidth=1,
        ),
    )
)

pio.templates["balmorel"] = _template


def apply() -> None:
    """Apply the balmorel plotly template as the default. Call once on app start."""
    pio.templates.default = "balmorel"
