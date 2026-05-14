"""Session state and scenario archive loading.

A "scenario" in the app is a single Balmorel run, loaded from a `.zip` archive
produced by `python -m balmorel_dashboard`. Each archive contains parquet files
(one per symbol) and a manifest.json.

State is session-scoped: uploaded archives live in `st.session_state` and are
gone when the browser session ends.
"""
from __future__ import annotations

import hashlib
import io
import json
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd
import streamlit as st

from lib import schemas

if TYPE_CHECKING:
    from streamlit.runtime.uploaded_file_manager import UploadedFile


@dataclass
class Scenario:
    """A single loaded scenario, fully in-memory.

    `tables`  → output symbols from MainResults.gdx
    `inputs`  → input symbols from all_endofmodel.gdx (empty for v0.1 archives)
    """

    name: str
    archive_hash: str
    manifest: dict
    tables: dict[str, pd.DataFrame] = field(default_factory=dict)
    inputs: dict[str, pd.DataFrame] = field(default_factory=dict)

    @property
    def years(self) -> list[str]:
        return list(map(str, self.manifest.get("years", [])))

    @property
    def countries(self) -> list[str]:
        return list(self.manifest.get("countries", []))

    @property
    def symbols(self) -> list[str]:
        return list(self.tables.keys())

    @property
    def input_symbols(self) -> list[str]:
        return list(self.inputs.keys())

    @property
    def capabilities(self) -> dict[str, bool]:
        return self.manifest.get("capabilities", {})

    @property
    def descriptions(self) -> dict[str, str]:
        return self.manifest.get("symbol_descriptions", {})

    def describe(self, symbol: str) -> str:
        return self.descriptions.get(symbol, "")


# ── Session state ────────────────────────────────────────────────────────────
def ensure_state() -> None:
    """Initialise session-state keys on first run."""
    st.session_state.setdefault("scenarios", {})  # name -> Scenario
    st.session_state.setdefault("selected_scenarios", [])
    st.session_state.setdefault("selected_year", None)
    st.session_state.setdefault("selected_countries", [])


def list_scenarios() -> list[str]:
    """Names of all loaded scenarios."""
    return list(st.session_state.get("scenarios", {}).keys())


def get_scenario(name: str) -> Scenario | None:
    return st.session_state.get("scenarios", {}).get(name)


def selected_scenarios() -> list[Scenario]:
    """Scenarios the user has selected in the sidebar (or all if none selected)."""
    names = st.session_state.get("selected_scenarios") or list_scenarios()
    return [s for s in (get_scenario(n) for n in names) if s is not None]


def selected_year() -> str | None:
    return st.session_state.get("selected_year")


def selected_countries() -> list[str]:
    return st.session_state.get("selected_countries", [])


# ── Archive ingestion ────────────────────────────────────────────────────────
def ingest_uploads(files: list["UploadedFile"]) -> None:
    """Load each uploaded archive into session state. Idempotent on archive hash."""
    for f in files:
        try:
            scn = _load_archive(f.getvalue(), fallback_name=f.name.removesuffix(".zip"))
        except Exception as e:
            st.sidebar.error(f"❌ Failed to load `{f.name}`: {e}")
            continue
        if scn.name in st.session_state["scenarios"] and \
                st.session_state["scenarios"][scn.name].archive_hash == scn.archive_hash:
            continue  # already loaded
        st.session_state["scenarios"][scn.name] = scn


def ingest_local_paths(paths: list[str | "os.PathLike"]) -> tuple[int, int]:
    """Load each local .zip path into session state.

    Used by `autoload_from_root` (env var driven) and by the Import Results
    page's folder text input. Scans for archives at
    `<BALMOREL_ROOT>/*/output/zip_files/*.zip` server-side.

    Returns (n_loaded, n_skipped) — skipped means already in session state
    with the same content hash.
    """
    import os as _os
    loaded = 0
    skipped = 0
    for p in paths:
        try:
            with open(p, "rb") as fh:
                payload = fh.read()
            scn = _load_archive(payload, fallback_name=_os.path.basename(str(p)).removesuffix(".zip"))
        except Exception as e:
            st.sidebar.error(f"❌ Failed to load `{p}`: {e}")
            continue
        existing = st.session_state["scenarios"].get(scn.name)
        if existing is not None and existing.archive_hash == scn.archive_hash:
            skipped += 1
            continue
        st.session_state["scenarios"][scn.name] = scn
        loaded += 1
    return loaded, skipped


def autoload_from_root(root: str) -> int:
    """Discover and ingest all `<root>/*/output/zip_files/*.zip` once per root.

    Idempotent — subsequent calls with the same `root` return the cached count
    without re-scanning. Used by both the module-level silent autoload in
    `streamlit_app.py` (driven by `$BALMOREL_ROOT`) and the editable text
    input on the Import Results page.

    Returns the number of archives found at this root (0 means the path
    resolved to nothing — invalid path or no zips yet).
    """
    cached_root = st.session_state.get("_autoload_done")
    if cached_root == root:
        return st.session_state.get("_autoload_count", 0)
    paths = sorted(Path(root).glob("*/output/zip_files/MainResults_*.zip"))
    if paths:
        ingest_local_paths(paths)
    st.session_state["_autoload_done"] = root
    st.session_state["_autoload_count"] = len(paths)
    return len(paths)


def _load_archive(payload: bytes, fallback_name: str) -> Scenario:
    """Parse a .zip archive into a Scenario object.

    Layout:
      manifest.json
      parquet/<sym>.parquet     ← outputs (MainResults)
      inputs/<sym>.parquet      ← inputs (all_endofmodel, schema_version ≥ 1.1)
    """
    h = hashlib.sha256(payload).hexdigest()[:16]
    with zipfile.ZipFile(io.BytesIO(payload)) as zf:
        names = zf.namelist()
        if "manifest.json" not in names:
            raise ValueError("archive is missing manifest.json")
        manifest = json.loads(zf.read("manifest.json"))
        scenario_name = manifest.get("scenario_name") or fallback_name

        tables: dict[str, pd.DataFrame] = {}
        inputs: dict[str, pd.DataFrame] = {}
        for nm in names:
            if nm.startswith("parquet/") and nm.endswith(".parquet"):
                symbol = nm.removeprefix("parquet/").removesuffix(".parquet")
                tables[symbol] = pd.read_parquet(io.BytesIO(zf.read(nm)))
            elif nm.startswith("inputs/") and nm.endswith(".parquet"):
                symbol = nm.removeprefix("inputs/").removesuffix(".parquet")
                inputs[symbol] = pd.read_parquet(io.BytesIO(zf.read(nm)))
    return Scenario(
        name=scenario_name, archive_hash=h,
        manifest=manifest, tables=tables, inputs=inputs,
    )


# ── Filter helpers ───────────────────────────────────────────────────────────
def available_years(names: list[str] | None = None) -> list[str]:
    scns = [get_scenario(n) for n in (names or list_scenarios())]
    years: set[str] = set()
    for s in scns:
        if s:
            years.update(s.years)
    return sorted(years)


def available_countries(names: list[str] | None = None) -> list[str]:
    scns = [get_scenario(n) for n in (names or list_scenarios())]
    countries: set[str] = set()
    for s in scns:
        if s:
            countries.update(s.countries)
    return sorted(countries)


def get_table(symbol: str, scenarios: list[Scenario] | None = None) -> pd.DataFrame:
    """Concatenate a single symbol across selected scenarios into one DataFrame.

    Returns an empty DataFrame if no loaded scenario has the symbol.
    """
    scns = scenarios if scenarios is not None else selected_scenarios()
    frames = []
    for s in scns:
        df = s.tables.get(symbol)
        if df is None or df.empty:
            continue
        if "Scenario" not in df.columns:
            df = df.assign(Scenario=s.name)
        frames.append(df)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def any_scenario_has(symbol: str) -> bool:
    return any(symbol in s.tables for s in selected_scenarios())


def any_scenario_has_capability(key: str) -> bool:
    return any(s.capabilities.get(key) for s in selected_scenarios())


def delete_scenario(name: str) -> None:
    """Remove a scenario from session state."""
    scenarios = st.session_state.get("scenarios", {})
    scenarios.pop(name, None)
    st.session_state["scenarios"] = scenarios
    # Also prune from selected list
    sel = [s for s in st.session_state.get("selected_scenarios", []) if s != name]
    st.session_state["selected_scenarios"] = sel


# ── Filter helpers (apply sidebar filters to a DataFrame) ───────────────────
def apply_filters(
    df: pd.DataFrame,
    *,
    year: bool = True,
    country: bool = True,
) -> pd.DataFrame:
    """Apply sidebar Year and Country filters to a DataFrame if the columns exist."""
    if df.empty:
        return df
    out = df
    if year and "Year" in out.columns:
        yr = selected_year()
        if yr is not None:
            out = out[out["Year"].astype(str) == str(yr)]
    if country and "Country" in out.columns:
        countries = selected_countries()
        if countries:
            out = out[out["Country"].isin(countries)]
    return out


def get_filtered(symbol: str, **filter_kwargs) -> pd.DataFrame:
    """Convenience: get_table + apply_filters in one call."""
    return apply_filters(get_table(symbol), **filter_kwargs)


# ── Summary helpers ─────────────────────────────────────────────────────────
def scenario_summary(s: Scenario) -> dict:
    """Per-scenario numbers for KPI display. All values are floats or ints."""
    out: dict[str, float | int | None] = {
        "name":         s.name,
        "n_symbols":    len(s.symbols),
        "n_years":      len(s.years),
        "n_countries":  len(s.countries),
        "total_cost":   None,
        "el_capacity":  None,
        "el_production": None,
        "max_tl":       None,
        "max_tl_indicator": None,
    }

    obj = s.tables.get("OBJ_YCR")
    if obj is not None and not obj.empty:
        out["total_cost"] = float(obj["Value"].sum())

    cap = s.tables.get("G_CAP_YCRAF")
    if cap is not None and not cap.empty and "Commodity" in cap.columns:
        el = cap[cap["Commodity"] == "ELECTRICITY"]
        out["el_capacity"] = float(el["Value"].sum())

    pro = s.tables.get("PRO_YCRAGF")
    if pro is not None and not pro.empty and "Commodity" in pro.columns:
        el = pro[pro["Commodity"] == "ELECTRICITY"]
        out["el_production"] = float(el["Value"].sum())

    # Max planetary-boundary transgression (any TL_* symbol)
    tl_max: float = 0.0
    tl_at: str | None = None
    for sym_name, df in s.tables.items():
        if sym_name.startswith("TL_") and not df.empty and "Value" in df.columns:
            v = float(df["Value"].max())
            if v > tl_max:
                tl_max = v
                tl_at = sym_name.removeprefix("TL_")
    if tl_at is not None:
        out["max_tl"] = tl_max
        out["max_tl_indicator"] = tl_at

    return out


def health_warnings(s: Scenario) -> list[str]:
    """Light heuristic warnings about a scenario's data."""
    warnings = []
    failed = s.manifest.get("symbols_failed", [])
    if failed:
        warnings.append(f"⚠ {len(failed)} symbol(s) failed to extract: " +
                        ", ".join(f["symbol"] for f in failed[:5]))
    empty = s.manifest.get("symbols_empty", [])
    if empty:
        warnings.append(f"ℹ {len(empty)} symbol(s) empty (no records): " +
                        ", ".join(empty[:5]))
    # EPS in electricity price
    el = s.tables.get("EL_PRICE_YCR")
    if el is not None and "Value" in el.columns:
        try:
            zero_count = int((el["Value"].astype(float) == 0).sum())
            if zero_count and zero_count == len(el):
                warnings.append("⚠ All EL_PRICE_YCR values are 0 — check for EPS values or solver issues")
        except (ValueError, TypeError):
            pass
    return warnings


def pages_overview_md() -> str:
    """Brief markdown of which pages are useful given the loaded data."""
    has_pb = any(schemas.has_pb_symbols(s.symbols) for s in selected_scenarios())
    rows = [
        "- **📊 Overview** — KPI summary",
        "- **⚡ Capacity** — installed generation capacity by tech/fuel",
        "- **🏭 Production** — annual production by tech/fuel",
        "- **💰 Prices and Demand** — electricity, heat, hydrogen prices and demand",
        "- **🔌 Transmission** — line capacities and flows between regions",
    ]
    if has_pb:
        rows.append("- **🌍 Planetary Boundaries** — TL_*/IS_* indicators")
    rows.append("- **🔍 Raw Explorer** — every symbol, filterable, CSV export")
    return "\n".join(rows)


# ── Transmission helpers ────────────────────────────────────────────────────
_REGION_TO_COUNTRY_LOOKUP_SYMBOLS = (
    "G_CAP_YCRAF", "PRO_YCRAGF", "EL_PRICE_YCR", "EL_DEMAND_YCR",
)


def region_to_country_map(scenarios: list[Scenario] | None = None) -> dict[str, str]:
    """Infer a Region → Country mapping by scanning symbols that have both columns.

    Returns {} if no suitable symbol is available. Mapping is union across selected
    scenarios; conflicts (same region in two countries) keep the first seen.
    """
    scns = scenarios if scenarios is not None else selected_scenarios()
    out: dict[str, str] = {}
    for s in scns:
        for sym in _REGION_TO_COUNTRY_LOOKUP_SYMBOLS:
            df = s.tables.get(sym)
            if df is None or df.empty:
                continue
            if "Region" not in df.columns or "Country" not in df.columns:
                continue
            for r, c in df[["Region", "Country"]].dropna().drop_duplicates().itertuples(index=False):
                out.setdefault(str(r), str(c))
            break  # one symbol per scenario is enough
    return out


def net_trade(symbol_flow: str, *, by: str = "Country",
              scenarios: list[Scenario] | None = None) -> pd.DataFrame:
    """Compute net trade (exports − imports) per region or country.

    `symbol_flow` is something like 'X_FLOW_YCR'. Returns columns
    [Scenario, by, Exports, Imports, Net].
    """
    scns = scenarios if scenarios is not None else selected_scenarios()
    r2c = region_to_country_map(scns) if by == "Country" else {}
    rows = []
    for s in scns:
        df = s.tables.get(symbol_flow)
        if df is None or df.empty or "From" not in df.columns or "To" not in df.columns:
            continue
        sub = df.copy()
        if by == "Country":
            sub["From_loc"] = sub["From"].map(r2c).fillna(sub["From"])
            sub["To_loc"]   = sub["To"].map(r2c).fillna(sub["To"])
            # Drop internal flows (within same country) — they're not real trade
            sub = sub[sub["From_loc"] != sub["To_loc"]]
        else:
            sub["From_loc"] = sub["From"]
            sub["To_loc"]   = sub["To"]
        # Cast From_loc/To_loc to string to avoid categorical-fillna issues
        sub["From_loc"] = sub["From_loc"].astype(str)
        sub["To_loc"]   = sub["To_loc"].astype(str)
        exports = sub.groupby(["From_loc"], as_index=False)["Value"].sum().rename(
            columns={"From_loc": by, "Value": "Exports"})
        imports = sub.groupby(["To_loc"], as_index=False)["Value"].sum().rename(
            columns={"To_loc": by, "Value": "Imports"})
        merged = exports.merge(imports, on=by, how="outer")
        merged[["Exports", "Imports"]] = merged[["Exports", "Imports"]].fillna(0.0)
        merged["Net"] = merged["Exports"] - merged["Imports"]
        merged.insert(0, "Scenario", s.name)
        rows.append(merged)
    if not rows:
        return pd.DataFrame(columns=["Scenario", by, "Exports", "Imports", "Net"])
    return pd.concat(rows, ignore_index=True)


def transmission_utilization(symbol_cap: str, symbol_flow: str,
                              scenarios: list[Scenario] | None = None) -> pd.DataFrame:
    """Utilization = flow_TWh / (capacity_GW × 8.760) per line.

    Returns columns [Scenario, From, To, Capacity_GW, Flow_TWh, Utilization].
    """
    scns = scenarios if scenarios is not None else selected_scenarios()
    HOURS = 8760 / 1000  # TWh = GW × 8760 h × 1e-3
    rows = []
    for s in scns:
        cap = s.tables.get(symbol_cap)
        flow = s.tables.get(symbol_flow)
        if cap is None or flow is None or cap.empty or flow.empty:
            continue

        # Cast From/To to string up-front: gams.transfer returns them as
        # categorical, which makes outer merges + fillna messy.
        cap = cap.assign(From=cap["From"].astype(str), To=cap["To"].astype(str))
        flow = flow.assign(From=flow["From"].astype(str), To=flow["To"].astype(str))

        # Aggregate cap across Category (Exo/Endo) before merging
        cap_agg = (
            cap.groupby(["From", "To"], as_index=False)["Value"].sum()
            .rename(columns={"Value": "Capacity_GW"})
        )
        flow_agg = (
            flow.groupby(["From", "To"], as_index=False)["Value"].sum()
            .rename(columns={"Value": "Flow_TWh"})
        )
        merged = cap_agg.merge(flow_agg, on=["From", "To"], how="outer")
        # Fill only the numeric columns; leave From/To untouched
        merged[["Capacity_GW", "Flow_TWh"]] = merged[["Capacity_GW", "Flow_TWh"]].fillna(0.0)
        merged["Utilization"] = merged.apply(
            lambda r: (r["Flow_TWh"] / (r["Capacity_GW"] * HOURS)) if r["Capacity_GW"] > 0 else 0.0,
            axis=1,
        )
        merged.insert(0, "Scenario", s.name)
        rows.append(merged)
    if not rows:
        return pd.DataFrame()
    return pd.concat(rows, ignore_index=True)


# ── Planetary boundary helpers ──────────────────────────────────────────────
def pb_indicators_present(scenarios: list[Scenario] | None = None) -> list[str]:
    """Return sorted list of PB indicator names (stripped of `TL_` prefix) that
    appear in at least one selected scenario."""
    scns = scenarios if scenarios is not None else selected_scenarios()
    inds: set[str] = set()
    for s in scns:
        for sym in s.symbols:
            if sym.startswith("TL_"):
                inds.add(sym.removeprefix("TL_"))
    return sorted(inds)


def pb_transgression_table(scenarios: list[Scenario] | None = None) -> pd.DataFrame:
    """Long-format TL values across scenarios.

    Columns: Scenario, Indicator, TL.
    """
    scns = scenarios if scenarios is not None else selected_scenarios()
    rows = []
    for s in scns:
        for sym, df in s.tables.items():
            if sym.startswith("TL_") and not df.empty and "Value" in df.columns:
                ind = sym.removeprefix("TL_")
                # one row per indicator per scenario (sum across years if multi-year)
                rows.append({"Scenario": s.name, "Indicator": ind,
                             "TL": float(df["Value"].astype(float).sum())})
    return pd.DataFrame(rows)


def pb_attribution_table(indicator: str, scenarios: list[Scenario] | None = None) -> pd.DataFrame:
    """Impact-score attribution for one PB indicator across scenarios.

    Returns a long DataFrame with columns: Scenario, Source, Value.
    Sources are Generation / Electricity transmission / H2 transmission / EVs.

    Generation is the year-aggregate `IS_<ind>` value (or sum of IS_<ind>_FFF
    when IS_<ind> itself is missing or empty).
    """
    scns = scenarios if scenarios is not None else selected_scenarios()
    rows = []
    for s in scns:
        def _agg(sym):
            df = s.tables.get(sym)
            if df is None or df.empty or "Value" not in df.columns:
                return None
            return float(df["Value"].astype(float).sum())

        gen = _agg(f"IS_{indicator}")
        if gen is None:
            gen = _agg(f"IS_{indicator}_FFF")
        x_el = _agg(f"IS_{indicator}_X")
        x_h2 = _agg(f"IS_{indicator}_X_H2")
        ev = _agg(f"IS_{indicator}_EV")

        for label, v in [
            ("Generation", gen),
            ("Electricity transmission", x_el),
            ("H2 transmission", x_h2),
            ("EVs", ev),
        ]:
            if v is not None:
                rows.append({"Scenario": s.name, "Source": label, "Value": v})
    return pd.DataFrame(rows)


def pb_fuel_breakdown(
    indicator: str,
    *,
    group_by: str = "Fuel",
    scenarios: list[Scenario] | None = None,
) -> pd.DataFrame:
    """Per-fuel (or per-technology) breakdown of `IS_<ind>_FFF` values."""
    scns = scenarios if scenarios is not None else selected_scenarios()
    sym = f"IS_{indicator}_FFF"
    frames = []
    for s in scns:
        df = s.tables.get(sym)
        if df is None or df.empty:
            continue
        cols_present = [c for c in ("Scenario", group_by, "Value") if c in df.columns]
        if "Value" not in cols_present:
            continue
        frames.append(df[cols_present])
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True)
    out = (
        out.groupby(["Scenario", group_by], as_index=False, observed=True)["Value"]
        .sum()
    )
    return out


# ── Number formatters ───────────────────────────────────────────────────────
def fmt_number(v: float | int | None, decimals: int = 1, unit: str = "") -> str:
    """Human-friendly number with thousands separator + unit. None → '—'."""
    if v is None:
        return "—"
    if abs(v) >= 1e6:
        return f"{v/1e6:,.{decimals}f}M{f' {unit}' if unit else ''}"
    if abs(v) >= 1e3:
        return f"{v/1e3:,.{decimals}f}k{f' {unit}' if unit else ''}"
    return f"{v:,.{decimals}f}{f' {unit}' if unit else ''}"


# ════════════════════════════════════════════════════════════════════════════
# Model Inputs helpers
# ════════════════════════════════════════════════════════════════════════════

def any_has_inputs(scenarios: list[Scenario] | None = None) -> bool:
    """True if at least one selected scenario has model-input data."""
    scns = scenarios if scenarios is not None else selected_scenarios()
    return any(s.capabilities.get("has_inputs") for s in scns)


def get_input_table(symbol: str, scenarios: list[Scenario] | None = None) -> pd.DataFrame:
    """Concatenate one input symbol across selected scenarios. Mirrors `get_table`."""
    scns = scenarios if scenarios is not None else selected_scenarios()
    frames = []
    for s in scns:
        df = s.inputs.get(symbol)
        if df is None or df.empty:
            continue
        if "Scenario" not in df.columns:
            df = df.assign(Scenario=s.name)
        frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


# ── GDATA pivot ─────────────────────────────────────────────────────────────
# GDATA is stored long-format: (Generation, Parameter, Value). The dashboard
# wants it wide: each generation unit a row, each parameter a column.

_GDATA_KEY_PARAMS = {
    # Identity
    "GDTYPE":         "Type",
    "GDFUEL":         "Fuel",
    "GDTECHGROUP":    "TechGroup",
    "GDSUBTECHGROUP": "SubTechGroup",
    # Costs (the headline ones for the Cost section)
    "GDINVCOST0":     "Capex",
    "GDOMFCOST0":     "FixedOM",
    "GDOMVCOST0":     "VarOM",
    "GDOMVCOSTIN":    "VarOMIn",
    # Performance
    "GDFE":           "FuelEff",
    "GDCV":           "Cv",
    "GDCB":           "Cb",
    "GDLOADLOSS":     "LoadLoss",
    "GDSTOLOSS":      "StorageLoss",
    # Ramping
    "GDRAMPUP":       "RampUp",
    "GDRAMPDOWN":     "RampDown",
    # Lifecycle
    "GDFROMYEAR":     "FromYear",
    "GDLASTYEAR":     "LastYear",
    "GDLIFETIME":     "Lifetime",
    # Emissions
    "GDDESO2":        "SO2",
    "GDNOX":          "NOX",
    "GDCH4":          "CH4",
}


def pivot_gdata(scenario: Scenario, drop_all_nan: bool = True) -> pd.DataFrame:
    """Pivot the GDATA long-form (Generation, Parameter, Value) into a wide table.

    Returns a DataFrame indexed by Generation, with one column per GDATASET
    parameter (renamed via `_GDATA_KEY_PARAMS` where possible).
    """
    df = scenario.inputs.get("GDATA")
    if df is None or df.empty:
        return pd.DataFrame()
    # Pivot
    pivot = df.pivot_table(
        index="Generation", columns="Parameter", values="Value",
        aggfunc="first", observed=True,
    )
    # Friendly column names (only for the ones we recognise; keep raw for others)
    pivot = pivot.rename(columns=_GDATA_KEY_PARAMS)
    if drop_all_nan:
        pivot = pivot.dropna(axis=1, how="all")
    return pivot


# ── Sector inference ────────────────────────────────────────────────────────
# Sectors are inferred from a combination of GDATA fields (Fuel, TechGroup)
# and the unit name pattern. The heuristic is conservative and labelled
# "Other / unknown" when uncertain.

_SECTOR_BY_FUEL = {
    # Heat-only fuels
    "HEAT": "Heat", "WASTEHEAT": "Heat",
    # Pure-electric fuels
    "ELECTRIC": "Electricity", "WIND": "Electricity",
    "SUN": "Electricity", "WATER": "Electricity", "NUCLEAR": "Electricity",
}

_SECTOR_BY_TECHGROUP_KEYWORDS = {
    "HEAT":     "Heat",
    "BOILER":   "Heat",
    "STORAGE":  "Storage",
    "ELECTRO":  "Hydrogen",   # ELECTROLYSER / ELECTROLYZER
    "FUELCELL": "Hydrogen",
    "STEAMREFORMING": "Hydrogen",
    "H2":       "Hydrogen",
    "WIND":     "Electricity",
    "SOLAR":    "Electricity",
    "HYDRO":    "Electricity",
    "CONDENS":  "Electricity",
    "CHP":      "Electricity & Heat (CHP)",
}

# Tokens in Balmorel generation-unit names → sector. Searched in order; the
# first match wins. Tokens are checked as substrings of the unit name in upper
# case, wrapped in word-ish delimiters so e.g. "_BO_" doesn't match "BIO".
_NAME_TOKEN_TO_SECTOR: list[tuple[str, str]] = [
    # Hydrogen
    ("_ELYS_",   "Hydrogen"),
    ("_ELZ_",    "Hydrogen"),
    ("ELECTROLY","Hydrogen"),
    ("_FC_",     "Hydrogen"),
    ("FUELCELL", "Hydrogen"),
    ("STEAMREFO","Hydrogen"),
    ("_H2_",     "Hydrogen"),
    ("METHANATION","Hydrogen"),
    # Heat / district heating
    ("_BO_",     "Heat"),
    ("BOILER",   "Heat"),
    ("_HP_",     "Heat"),     # heat pump
    ("HEATPUMP", "Heat"),
    ("_HS_",     "Storage"),  # heat storage
    ("SOLARHEAT","Heat"),
    ("SOLAR-HEAT","Heat"),
    # Electricity — renewables
    ("_WIN_",    "Electricity"),
    ("WIND",     "Electricity"),
    ("_SOL_",    "Electricity"),
    ("_PV_",     "Electricity"),
    ("SOLAR-PV", "Electricity"),
    ("_RES_",    "Electricity"),   # reservoir hydro
    ("_WTR_",    "Electricity"),   # water (hydro)
    ("HYDRO",    "Electricity"),
    ("NUCLEAR",  "Electricity"),
    # Electricity — thermal (often CHP if Cv+Cb present)
    ("_ST_",     "Electricity"),   # steam turbine
    ("_GT_",     "Electricity"),   # gas turbine
    ("_CC_",     "Electricity"),   # combined cycle
    ("_CCGT_",   "Electricity"),
    ("_GE_",     "Electricity"),   # gas engine
    ("_ENG_",    "Electricity"),   # engine (gas/bio)
    ("_CND_",    "Electricity"),   # condensing (electricity-only)
    ("CONDENS",  "Electricity"),
    ("BACKUP_E", "Electricity"),
    ("BACKUP_H", "Heat"),
    # Electricity storage
    ("_ES_",     "Storage"),
    ("BATT",     "Storage"),
    ("BATTERY",  "Storage"),
    # CCS
    ("_CCS_",    "CCS"),
    # Transport
    ("BEV_",     "Transport"),
    ("PHEV_",    "Transport"),
    ("V2G_",     "Transport"),
]


def infer_sector(unit_name: str, fuel: str | None, tech_group: str | None) -> str:
    """Best-effort mapping (unit_name, fuel, tech_group) → sector label."""
    if fuel:
        f = str(fuel).upper()
        if f in _SECTOR_BY_FUEL:
            return _SECTOR_BY_FUEL[f]
    if tech_group:
        tg = str(tech_group).upper()
        for kw, sector in _SECTOR_BY_TECHGROUP_KEYWORDS.items():
            if kw in tg:
                return sector
    # Name-token heuristic
    u = unit_name.upper()
    for token, sector in _NAME_TOKEN_TO_SECTOR:
        if token in u:
            return sector
    return "Other / unknown"


def gdata_with_sector(scenario: Scenario) -> pd.DataFrame:
    """Return pivoted GDATA enriched with a `Sector` column.

    Sector inference uses, in order:
      1. Cross-reference with `G_CAP_YCRAF` from MainResults (the unit's
         actual Commodity in this scenario) — bulletproof for deployed units.
      2. CHP detector: if both Cv and Cb are present in GDATA, it's a CHP unit.
      3. Storage detector: if GDSTOHLOAD or GDSTOHUNLD is present.
      4. Name-token heuristic (`infer_sector`).
    """
    pivot = pivot_gdata(scenario)
    if pivot.empty:
        return pivot

    # 1. Cross-reference with G_CAP_YCRAF
    deployed_commodity: dict[str, str] = {}
    cap = scenario.tables.get("G_CAP_YCRAF")
    if cap is not None and not cap.empty and "Generation" in cap.columns and "Commodity" in cap.columns:
        per_unit = cap.groupby("Generation", observed=True)["Commodity"].agg(set)
        for unit, commodities in per_unit.items():
            commodities = {str(c).title() for c in commodities if pd.notna(c)}
            if not commodities:
                continue
            if commodities == {"Electricity", "Heat"}:
                deployed_commodity[str(unit)] = "Electricity & Heat (CHP)"
            elif len(commodities) == 1:
                deployed_commodity[str(unit)] = next(iter(commodities))
            else:
                deployed_commodity[str(unit)] = " & ".join(sorted(commodities))

    fuel_col = pivot["Fuel"] if "Fuel" in pivot.columns else None
    tg_col   = pivot["TechGroup"] if "TechGroup" in pivot.columns else None
    has_cv   = pivot["Cv"]  if "Cv"  in pivot.columns else None
    has_cb   = pivot["Cb"]  if "Cb"  in pivot.columns else None
    has_hsl  = pivot.get("GDSTOHLOAD") if "GDSTOHLOAD" in pivot.columns else None
    has_hsu  = pivot.get("GDSTOHUNLD") if "GDSTOHUNLD" in pivot.columns else None

    sectors = []
    for idx in pivot.index:
        idx_s = str(idx)
        # 1. Deployed-capacity cross-ref wins if available
        if idx_s in deployed_commodity:
            sectors.append(deployed_commodity[idx_s])
            continue
        # 2. CHP detector
        cv_v = has_cv.loc[idx] if has_cv is not None and idx in has_cv.index else None
        cb_v = has_cb.loc[idx] if has_cb is not None and idx in has_cb.index else None
        if pd.notna(cv_v) and pd.notna(cb_v):
            sectors.append("Electricity & Heat (CHP)")
            continue
        # 3. Storage detector
        hsl_v = has_hsl.loc[idx] if has_hsl is not None and idx in has_hsl.index else None
        hsu_v = has_hsu.loc[idx] if has_hsu is not None and idx in has_hsu.index else None
        if pd.notna(hsl_v) or pd.notna(hsu_v):
            sectors.append("Storage")
            continue
        # 4. Name-token + (rarely populated) fuel/tech group
        sectors.append(infer_sector(
            idx_s,
            fuel_col.loc[idx] if fuel_col is not None and idx in fuel_col.index else None,
            tg_col.loc[idx] if tg_col is not None and idx in tg_col.index else None,
        ))

    pivot["Sector"] = sectors
    return pivot.reset_index()


# ── Demand summaries ────────────────────────────────────────────────────────

def sectors_present(scenarios: list[Scenario] | None = None) -> dict[str, dict]:
    """Detect which sectors the loaded scenarios actually cover.

    Returns {sector_name: {"present": bool, "evidence": str}}. Always returns
    all known sectors so the UI can show a consistent checklist.
    """
    scns = scenarios if scenarios is not None else selected_scenarios()
    out: dict[str, dict] = {
        "Electricity": {"present": False, "evidence": ""},
        "Heat":        {"present": False, "evidence": ""},
        "Hydrogen":    {"present": False, "evidence": ""},
        "Transport (EV)": {"present": False, "evidence": ""},
        "Biomethane":  {"present": False, "evidence": ""},
        "CCS":         {"present": False, "evidence": ""},
    }
    for s in scns:
        sym = set(s.symbols) | set(s.input_symbols)
        if any(k in sym for k in ("EL_PRICE_YCR", "EL_DEMAND_YCR", "DE")):
            out["Electricity"]["present"] = True
            out["Electricity"]["evidence"] = "DE, EL_DEMAND_YCR present"
        if any(k in sym for k in ("H_DEMAND_YCRA", "DH")):
            out["Heat"]["present"] = True
            out["Heat"]["evidence"] = "DH / H_DEMAND_YCRA present"
        if any(k in sym for k in ("H2_DEMAND_YCR", "HYDROGEN_DH2")):
            out["Hydrogen"]["present"] = True
            out["Hydrogen"]["evidence"] = "HYDROGEN_DH2 / H2_DEMAND_YCR present"
        if any(k in sym for k in ("V2G_FLEX_Y", "BEV_TECH_DATA")):
            out["Transport (EV)"]["present"] = True
            out["Transport (EV)"]["evidence"] = "BEV_TECH_DATA / V2G_FLEX present"
        if "BIOGASUPGRADING_DE" in sym or "METHANATION_DH2" in sym:
            out["Biomethane"]["present"] = True
            out["Biomethane"]["evidence"] = "BIOGASUPGRADING_DE / METHANATION_DH2 present"
        if any(k.startswith("CCS_") for k in sym):
            out["CCS"]["present"] = True
            out["CCS"]["evidence"] = "CCS_* parameters present"
    return out
