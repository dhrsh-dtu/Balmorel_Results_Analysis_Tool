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
from typing import TYPE_CHECKING

import pandas as pd
import streamlit as st

from lib import schemas

if TYPE_CHECKING:
    from streamlit.runtime.uploaded_file_manager import UploadedFile


@dataclass
class Scenario:
    """A single loaded scenario, fully in-memory."""

    name: str
    archive_hash: str
    manifest: dict
    tables: dict[str, pd.DataFrame] = field(default_factory=dict)

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


def _load_archive(payload: bytes, fallback_name: str) -> Scenario:
    """Parse a .zip archive into a Scenario object."""
    h = hashlib.sha256(payload).hexdigest()[:16]
    with zipfile.ZipFile(io.BytesIO(payload)) as zf:
        names = zf.namelist()
        if "manifest.json" not in names:
            raise ValueError("archive is missing manifest.json")
        manifest = json.loads(zf.read("manifest.json"))
        scenario_name = manifest.get("scenario_name") or fallback_name
        tables: dict[str, pd.DataFrame] = {}
        for nm in names:
            if nm.endswith(".parquet"):
                symbol = nm.removeprefix("parquet/").removesuffix(".parquet")
                tables[symbol] = pd.read_parquet(io.BytesIO(zf.read(nm)))
    return Scenario(name=scenario_name, archive_hash=h, manifest=manifest, tables=tables)


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
