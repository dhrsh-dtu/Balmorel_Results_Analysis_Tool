"""GDX → .zip archive exporter.

Archive layout:

    archive.zip
    ├── manifest.json              scenario name, years, countries, symbols, capabilities
    └── parquet/
        ├── PRO_YCRAGF.parquet
        ├── G_CAP_YCRAF.parquet
        └── ...                    one file per non-empty symbol

This module is the only piece that requires a GAMS install (via `gams.transfer`).
The dashboard webapp only reads parquet, no GAMS dependency.
"""
from __future__ import annotations

import io
import json
import os
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

# We import gams.transfer lazily inside export_one so that `python -m
# balmorel_dashboard --help` works without GAMS being available.


# ── GAMS install resolution ──────────────────────────────────────────────────

def _find_gams_system_dir(explicit: str | None) -> str:
    """Resolve a GAMS install directory. Preference: arg > env var > PATH scan."""
    if explicit:
        if not (Path(explicit) / "optgams.def").is_file():
            raise FileNotFoundError(
                f"--gams-dir '{explicit}' does not look like a GAMS install "
                f"(missing optgams.def)"
            )
        return explicit

    env = os.environ.get("GAMS_SYSDIR") or os.environ.get("GAMSDIR")
    if env and (Path(env) / "optgams.def").is_file():
        return env

    for p in os.environ.get("PATH", "").split(os.pathsep):
        if not p:
            continue
        if (Path(p) / "optgams.def").is_file():
            return p

    raise FileNotFoundError(
        "Could not locate a GAMS installation. Either:\n"
        "  • pass --gams-dir /path/to/gams\n"
        "  • set GAMS_SYSDIR or GAMSDIR env var\n"
        "  • add the GAMS directory to PATH"
    )


# ── Scenario name derivation ─────────────────────────────────────────────────

def _derive_scenario_name(gdx_path: Path) -> str:
    stem = gdx_path.stem
    if stem.startswith("MainResults_"):
        return stem[len("MainResults_"):]
    if stem == "MainResults":
        # Use the parent folder name (e.g. "Nordics/model/MainResults.gdx" → "Nordics")
        # Look one level up if parent is "model" (Balmorel convention)
        parent = gdx_path.parent
        if parent.name == "model" and parent.parent.name:
            return parent.parent.name
        return parent.name or "scenario"
    return stem


# ── Per-symbol extraction ────────────────────────────────────────────────────

def _extract_symbol(sym, schema_columns: list[str] | None) -> pd.DataFrame | None:
    """Convert one gams.transfer symbol → DataFrame with cleaned column names.

    Returns None if the symbol is empty.
    """
    import gams.transfer as gt

    df = sym.records
    if df is None or len(df) == 0:
        return None
    df = df.copy()

    # Identify the value-related column block depending on symbol type
    if isinstance(sym, gt.Parameter):
        # records: [domain cols ..., 'value']
        value_block_n = 1
        df = df.rename(columns={"value": "Value"})
        value_block_names = ["Value"]
    elif isinstance(sym, (gt.Variable, gt.Equation)):
        # records: [domain cols ..., level, marginal, lower, upper, scale]
        value_block_n = 5
        df = df.rename(columns={
            "level": "Value",
            "marginal": "Marginal",
            "lower": "Lower",
            "upper": "Upper",
            "scale": "Scale",
        })
        value_block_names = ["Value", "Marginal", "Lower", "Upper", "Scale"]
    elif isinstance(sym, gt.Set):
        # records: [domain cols ..., 'element_text']
        value_block_n = 1
        df = df.rename(columns={"element_text": "ElementText"})
        value_block_names = ["ElementText"]
    else:
        return None

    n_domain = len(df.columns) - value_block_n

    # Apply schema column names where we can match
    if schema_columns is not None:
        if n_domain == len(schema_columns):
            df.columns = schema_columns + value_block_names
        elif n_domain == len(schema_columns) + 1:
            # The "extra" column is conventionally a Unit dimension in Balmorel
            df.columns = schema_columns + ["Unit"] + value_block_names
        # else: count mismatch — leave the raw column names from gams.transfer

    return df


# ── Dimension discovery for manifest ────────────────────────────────────────

_DISCOVERY_COLS = {
    "years":       "Year",
    "countries":   "Country",
    "regions":     "Region",
    "areas":       "Area",
    "commodities": "Commodity",
    "seasons":     "Season",
    "fuels":       "Fuel",
    "technologies": "Technology",
}


def _discover_dimensions(tables: dict[str, pd.DataFrame]) -> dict[str, list]:
    out: dict[str, set] = {k: set() for k in _DISCOVERY_COLS}
    for df in tables.values():
        for key, col in _DISCOVERY_COLS.items():
            if col in df.columns:
                vals = df[col].dropna()
                if not vals.empty:
                    out[key].update(vals.astype(str).unique())
    return {k: sorted(v) for k, v in out.items()}


# ── Main entry point ────────────────────────────────────────────────────────

def export_one(
    gdx_path: Path,
    out_path: Path,
    scenario_name: str | None = None,
    gams_system_directory: str | None = None,
    result_type: str = "balmorel",
    verbose: bool = False,
) -> Path:
    """Export a single GDX → zip archive.

    Returns the path of the written archive.
    """
    import gams.transfer as gt

    # Defer imports of dashboard library to avoid forcing them at CLI module level
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from lib import schemas

    gdx_path = gdx_path.resolve()
    out_path = out_path.resolve()

    if not gdx_path.is_file():
        raise FileNotFoundError(f"GDX not found: {gdx_path}")

    sysdir = _find_gams_system_dir(gams_system_directory)
    if verbose:
        print(f"  GAMS system directory: {sysdir}")

    scenario_name = scenario_name or _derive_scenario_name(gdx_path)
    if verbose:
        print(f"  Scenario name: {scenario_name}")

    container = gt.Container(load_from=str(gdx_path), system_directory=sysdir)
    all_names = container.listSymbols()
    if verbose:
        print(f"  Found {len(all_names)} symbols in GDX")

    tables: dict[str, pd.DataFrame] = {}
    loaded: list[str] = []
    failed: list[dict] = []
    empty: list[str] = []

    for name in all_names:
        try:
            sym = container[name]
            schema_cols = schemas.ALL_COLUMNS.get(name)
            df = _extract_symbol(sym, schema_cols)
            if df is None:
                empty.append(name)
                continue
            # Prepend Scenario column
            df.insert(0, "Scenario", scenario_name)
            tables[name] = df
            loaded.append(name)
            if verbose:
                marker = "✓" if schema_cols else "·"
                print(f"    {marker} {name:34s} {df.shape[0]:>7,} rows × {df.shape[1]} cols")
        except Exception as e:
            failed.append({"symbol": name, "error": f"{type(e).__name__}: {e}"})
            if verbose:
                print(f"    ✗ {name}: {e}")

    # Manifest
    discovery = _discover_dimensions(tables)
    capabilities = {
        "has_pb":        schemas.has_pb_symbols(loaded),
        "has_v2g":       schemas.has_v2g_symbols(loaded),
        "has_optiflow":  schemas.has_optiflow_symbols(loaded),
    }
    manifest = {
        "schema_version": "1.0",
        "scenario_name":  scenario_name,
        "source_gdx":     gdx_path.name,
        "source_path":    str(gdx_path),
        "exported_at":    datetime.now(timezone.utc).isoformat(),
        "result_type":    result_type,
        **discovery,
        "symbols_loaded":  sorted(loaded),
        "symbols_empty":   sorted(empty),
        "symbols_failed":  failed,
        "capabilities":    capabilities,
        "exporter_version": "0.1.0",
    }

    # Pack zip
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, indent=2, default=str))
        for name, df in tables.items():
            buf = io.BytesIO()
            df.to_parquet(buf, engine="pyarrow", compression="snappy")
            zf.writestr(f"parquet/{name}.parquet", buf.getvalue())

    if verbose:
        size_mb = out_path.stat().st_size / 1e6
        print(
            f"\n  Wrote {out_path}  ({size_mb:.2f} MB)\n"
            f"  Symbols: {len(loaded)} loaded, {len(empty)} empty, {len(failed)} failed"
        )

    return out_path


def inspect_gdx(gdx_path: Path, gams_system_directory: str | None = None) -> None:
    """Print a summary of a GDX file without exporting (useful for `--list-symbols`)."""
    import gams.transfer as gt

    sysdir = _find_gams_system_dir(gams_system_directory)
    container = gt.Container(load_from=str(gdx_path), system_directory=sysdir)
    names = container.listSymbols()
    print(f"\n{gdx_path.name} — {len(names)} symbols")
    print(f"GAMS system directory: {sysdir}\n")
    print(f"{'Symbol':<34} {'Type':<10} {'Dims':<5} {'Rows':>10}  Description")
    print("-" * 100)
    for name in names:
        sym = container[name]
        rows = len(sym.records) if sym.records is not None else 0
        kind = type(sym).__name__
        desc = (sym.description or "")[:40]
        print(f"{name:<34} {kind:<10} {len(sym.domain):<5} {rows:>10,}  {desc}")
