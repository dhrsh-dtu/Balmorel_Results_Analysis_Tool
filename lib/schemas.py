"""Column conventions for Balmorel result symbols.

Mirrors pybalmorel.formatting.balmorel_mainresults_symbol_columns plus extensions
for the Planetary Boundary (PB) symbols not covered by pybalmorel.

The exporter applies these schemas when converting GDX → parquet so the dashboard
always sees consistent column names.
"""
from __future__ import annotations

# Standard Balmorel symbols (mirrors pybalmorel) — Scenario column is added by exporter
BALMOREL_COLUMNS: dict[str, list[str]] = {
    "F_CONS_YCRA":      ["Year", "Country", "Region", "Area", "Generation", "Fuel", "Technology"],
    "F_CONS_YCRAST":    ["Year", "Country", "Region", "Area", "Generation", "Fuel", "Season", "Time", "Technology"],
    "G_CAP_YCRAF":      ["Year", "Country", "Region", "Area", "Generation", "Fuel", "Commodity", "Technology", "Category"],
    "G_STO_YCRAF":      ["Year", "Country", "Region", "Area", "Generation", "Fuel", "Commodity", "Technology", "Category"],
    "EL_DEMAND_YCR":    ["Year", "Country", "Region", "Category"],
    "EL_DEMAND_YCRST":  ["Year", "Country", "Region", "Season", "Time", "Category"],
    "EL_PRICE_YCR":     ["Year", "Country", "Region"],
    "EL_PRICE_YCRST":   ["Year", "Country", "Region", "Season", "Time"],
    "EL_BALANCE_YCRST": ["Year", "Country", "Region", "Technology", "Season", "Time"],
    "H2_DEMAND_YCR":    ["Year", "Country", "Region", "Category"],
    "H2_DEMAND_YCRST":  ["Year", "Country", "Region", "Season", "Time", "Category"],
    "H2_PRICE_YCR":     ["Year", "Country", "Region", "Category"],
    "H2_PRICE_YCRST":   ["Year", "Country", "Region", "Season", "Time"],
    "H_BALANCE_YCRAST": ["Year", "Country", "Region", "Area", "Technology", "Season", "Time"],
    "H_DEMAND_YCRA":    ["Year", "Country", "Region", "Area", "Category"],
    "H_DEMAND_YCRAST":  ["Year", "Country", "Region", "Area", "Season", "Time", "Category"],
    "H_PRICE_YCRA":     ["Year", "Country", "Region", "Area", "Category"],
    "H_PRICE_YCRAST":   ["Year", "Country", "Region", "Area", "Season", "Time"],
    "OBJ_YCR":          ["Year", "Country", "Region", "Category"],
    "PRO_YCRAGF":       ["Year", "Country", "Region", "Area", "Generation", "Fuel", "Commodity", "Technology"],
    "PRO_YCRAGFST":     ["Year", "Country", "Region", "Area", "Generation", "Fuel", "Season", "Time", "Commodity", "Technology"],
    "X_CAP_YCR":        ["Year", "Country", "From", "To", "Category"],
    "X_FLOW_YCR":       ["Year", "Country", "From", "To"],
    "X_FLOW_YCRST":     ["Year", "Country", "From", "To", "Season", "Time"],
    "XH2_CAP_YCR":      ["Year", "Country", "From", "To", "Category"],
    "XH2_FLOW_YCR":     ["Year", "Country", "From", "To"],
    "XH2_FLOW_YCRST":   ["Year", "Country", "From", "To", "Season", "Time"],
    "XH_CAP_YCA":       ["Year", "Country", "From", "To", "Category"],
    "XH_FLOW_YCA":      ["Year", "Country", "From", "To"],
    "XH_FLOW_YCAST":    ["Year", "Country", "From", "To", "Season", "Time"],
    "BIOMETH_PRICE_YST": ["Year", "Season", "Time"],
}

# Planetary boundary symbols (custom to this Balmorel fork)
PB_INDICATORS = [
    "CO2", "LU", "WU", "ACIDIFICATION", "EUTROPHICATION_FRESHWATER",
    "OZONE_DEPLETION", "PM", "ECOTOXICITY_FRESHWATER", "RESOURCE",
]

PB_COLUMNS: dict[str, list[str]] = {}
for ind in PB_INDICATORS:
    PB_COLUMNS[f"TL_{ind}"] = ["Year"]
    PB_COLUMNS[f"IS_{ind}"] = ["Year"]
    PB_COLUMNS[f"IS_{ind}_FFF"] = ["Year", "Generation", "Fuel", "Technology"]
    PB_COLUMNS[f"IS_{ind}_X"] = ["Year"]
    PB_COLUMNS[f"IS_{ind}_X_H2"] = ["Year"]
    PB_COLUMNS[f"IS_{ind}_EV"] = ["Year"]

# V2G symbols
V2G_COLUMNS: dict[str, list[str]] = {
    "V2G_FLEX_Y":          ["Year"],
    "V2G_FLEX_YCR":        ["Year", "Country", "Region"],
    "V2G_per_EV_FLEX_YCR": ["Year", "Country", "Region"],
}

ALL_COLUMNS: dict[str, list[str]] = {**BALMOREL_COLUMNS, **PB_COLUMNS, **V2G_COLUMNS}


# ── Universal GAMS → friendly column rename ────────────────────────────────
# Applied to EVERY extracted symbol so column names are stable in the
# dashboard regardless of whether a per-symbol schema in ALL_COLUMNS matches
# the actual GDX (Balmorel has been quietly adding dimensions like
# PRICE_CATEGORY to old symbols — schema-position-only rename misses these).
GAMS_TO_FRIENDLY: dict[str, str] = {
    # ── Output-side names (used by MainResults symbols) ────────────────
    "Y": "Year",
    "C": "Country",
    "RRR": "Region",
    "AAA": "Area",
    "G": "Generation",
    "FFF": "Fuel",
    "COMMODITY": "Commodity",
    "TECH_TYPE": "Technology",
    "UNITS": "Unit",
    "SSS": "Season",
    "TTT": "Time",
    "IRRRE": "From",
    "IRRRI": "To",
    "PRICE_CATEGORY": "Category",
    "VARIABLE_CATEGORY": "Category",
    "CATEGORY": "Category",
    "SUBCATEGORY": "Category",   # OBJ_YCR uses SUBCATEGORY for cost-category labels

    # ── Input-side names (used by all_endofmodel symbols) ──────────────
    # Balmorel's input data uses the *parent* set names (3-letter form).
    "YYY": "Year",
    "CCC": "Country",
    "GGG": "Generation",
    "GDATASET": "Parameter",     # set of GDATA parameter labels (GDFE, GDCAPEX, etc.)
    "DEUSER": "Category",        # electricity user category (residential, industry, …)
    "DHUSER": "Category",        # heat user category
    "CCCRRRAAA": "Location",     # universal location set
}


def has_pb_symbols(symbols: list[str]) -> bool:
    """True if any planetary-boundary symbols are present in the symbol list."""
    return any(s.startswith(("TL_", "IS_")) for s in symbols)


def has_v2g_symbols(symbols: list[str]) -> bool:
    """True if any V2G symbols are present."""
    return any(s.startswith("V2G_") for s in symbols)


def has_optiflow_symbols(symbols: list[str]) -> bool:
    """True if OptiFlow-specific symbols are present."""
    return any(s.startswith(("VFLOW_", "VFLOWBUFFER_", "VFLOTCCU_", "VFLOWSOURCE_")) for s in symbols)
