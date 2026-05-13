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
