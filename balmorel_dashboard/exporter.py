"""Balmorel-root → .zip archives exporter.

Folder-mode only: point the CLI at a Balmorel root folder containing
`base/`, `simex/`, and zero or more named scenario folders. For each
scenario, the exporter reads:

  - `<scenario>/model/MainResults.gdx`     (outputs)
  - `<scenario>/model/all_endofmodel.gdx`  (filtered for ~23 input symbols)

…and writes:

  - `<balmorel_root>/zip_files/MainResults_<scenario>.zip`

Each archive layout:

    archive.zip
    ├── manifest.json              scenario metadata + symbol coverage + capabilities
    ├── parquet/                   MainResults outputs (one per non-empty symbol)
    │   ├── PRO_YCRAGF.parquet
    │   └── ...
    └── inputs/                    Filtered all_endofmodel inputs (one per non-empty symbol)
        ├── GDATA.parquet
        ├── DE.parquet
        └── ...

This module is the only piece that requires a GAMS install (via `gams.transfer`).
The dashboard webapp only reads parquet, no GAMS dependency.
"""
from __future__ import annotations

import io
import json
import os
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from pybalmorel import Balmorel


# ── Input symbols we extract from all_endofmodel.gdx ───────────────────────
INPUT_SYMBOLS = [
    # Identity & ranges
    "GDATA", "GDATASET", "GGG", "AGKN", "AGKN2", "ANNUITYCG",
    # Demand & profiles
    "DE", "DH", "HYDROGEN_DH2",
    "DE_VAR_T", "DH_VAR_T", "HYDROGEN_DH2_VAR_T",
    "DEFP_BASE", "DHFP_BASE",
    # Sector coupling demand
    "BIOGASUPGRADING_DE", "DAC_DE", "DAC_DH", "METHANATION_DH2",
    # CCS
    "CCS_CO2CAPTEFF_G", "CCS_DECO2COMP_G", "CCS_TRANSPORTCOST",
    # EV
    "BEV_TECH_DATA",
    # Time
    "CHRONOHOUR",
]


# ── GAMS install resolution ─────────────────────────────────────────────────

# Cluster-installed GAMS paths probed when nothing on PATH / env vars matches.
# DTU HPC keeps system-wide installs under /appl/gams/; gamsapi >= 53.5 needs
# 50.x, so we point at the current version explicitly. Update when DTU upgrades.
_COMMON_HPC_GAMS_PATHS = [
    "/appl/gams/50.4.1",   # DTU HPC
]


def _find_gams_system_dir(explicit: str | None) -> str:
    """Resolve a GAMS install directory.

    Preference: explicit arg > env var (GAMS_SYSDIR / GAMSDIR) > PATH scan >
    well-known cluster paths.
    """
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
        if p and (Path(p) / "optgams.def").is_file():
            return p

    for p in _COMMON_HPC_GAMS_PATHS:
        if (Path(p) / "optgams.def").is_file():
            return p

    raise FileNotFoundError(
        "Could not locate a GAMS installation. Either:\n"
        "  • pass --gams-dir /path/to/gams\n"
        "  • set GAMS_SYSDIR or GAMSDIR env var\n"
        "  • add the GAMS directory to PATH"
    )


# ── Scenario discovery ─────────────────────────────────────────────────────

def discover_scenarios(balmorel_root: Path) -> list[tuple[str, Path]]:
    """Walk a Balmorel root for scenario folders that have a `model/MainResults.gdx`.

    Returns a list of (scenario_name, model_folder_path), with `base` first
    (Balmorel convention) and the rest alphabetical. Skips `simex/`, the
    legacy root `zip_files/`, and any non-scenario directories (no `model/`
    subfolder).
    """
    # FIX: This assumes that scenarios are called "MainResults.gdx"
    # Use Balmorel.locate_results() or Balmorel.collect_reuslts() instead
    # to allow for more MainResults*.gdx files.
    if not balmorel_root.is_dir():
        raise NotADirectoryError(f"{balmorel_root} is not a directory")

    scenarios: list[tuple[str, Path]] = []
    for child in sorted(balmorel_root.iterdir()):
        if not child.is_dir() or child.name in {"simex", "zip_files"}:
            continue
        if child.name.startswith("."):  # skip .git etc.
            continue
        model_dir = child / "model"
        mr = model_dir / "MainResults.gdx"
        if mr.is_file():
            scenarios.append((child.name, model_dir))

    # Sort: 'base' first (case-insensitive), then alphabetical
    scenarios.sort(key=lambda t: (t[0].lower() != "base", t[0].lower()))
    return scenarios


def scenario_zip_path(model_dir: Path, scenario_name: str) -> Path:
    """Conventional destination: `<scn>/output/zip_files/MainResults_<scn>.zip`."""
    return model_dir.parent / "output" / "zip_files" / f"MainResults_{scenario_name}.zip"


def _check_legacy_root_zip_files(balmorel_root: Path) -> Path | None:
    """Return the legacy `<root>/zip_files/` path if it exists, else None."""
    legacy = balmorel_root / "zip_files"
    return legacy if legacy.is_dir() else None


def _fmt_size(n_bytes: int) -> str:
    if n_bytes >= 1e9:
        return f"{n_bytes/1e9:.1f} GB"
    if n_bytes >= 1e6:
        return f"{n_bytes/1e6:.1f} MB"
    if n_bytes >= 1e3:
        return f"{n_bytes/1e3:.1f} kB"
    return f"{n_bytes} B"


# ── Per-symbol extraction ──────────────────────────────────────────────────

def _extract_symbol(sym, schema_columns: list[str] | None) -> pd.DataFrame | None:
    """Convert one gams.transfer symbol → DataFrame with friendly column names.

    Returns None if the symbol has no records.
    """
    import gams.transfer as gt

    # Local import to avoid circular: schemas imports nothing dashboard-specific
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from lib.schemas import GAMS_TO_FRIENDLY

    df = sym.records
    if df is None or len(df) == 0:
        return None
    df = df.copy()

    # ── 1. Rename the value-related columns ─────────────────────────────────
    if isinstance(sym, gt.Parameter):
        df = df.rename(columns={"value": "Value"})
    elif isinstance(sym, (gt.Variable, gt.Equation)):
        df = df.rename(columns={
            "level": "Value",
            "marginal": "Marginal",
            "lower": "Lower",
            "upper": "Upper",
            "scale": "Scale",
        })
    elif isinstance(sym, gt.Set):
        df = df.rename(columns={"element_text": "ElementText"})
    else:
        return None

    # ── 2. Rename GAMS canonical domain names to friendly names ─────────────
    rename_map = {c: GAMS_TO_FRIENDLY[c] for c in df.columns if c in GAMS_TO_FRIENDLY}
    if rename_map:
        seen_targets: set[str] = set()
        clean_map: dict[str, str] = {}
        for src, dst in rename_map.items():
            if dst in df.columns and src != dst:
                continue
            if dst in seen_targets:
                continue
            clean_map[src] = dst
            seen_targets.add(dst)
        if clean_map:
            df = df.rename(columns=clean_map)

    # ── 3. Positional schema, only as a safety net ──────────────────────────
    if schema_columns is not None:
        value_cols = ["Value", "Marginal", "Lower", "Upper", "Scale", "ElementText", "Unit"]
        friendly_cols = set(GAMS_TO_FRIENDLY.values())
        unrenamed = [c for c in df.columns if c not in friendly_cols and c not in value_cols]
        if unrenamed and len(unrenamed) == len(schema_columns):
            df = df.rename(columns=dict(zip(unrenamed, schema_columns)))

    return df


# ── Dimension discovery for manifest ───────────────────────────────────────

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


# ── Single-scenario export ─────────────────────────────────────────────────

def export_scenario(
    scenario_name: str,
    model_dir: Path,
    out_path: Path,
    *,
    gams_system_directory: str,
    result_type: str = "balmorel",
    verbose: bool = False,
) -> Path:
    """Export one scenario: MainResults (full) + all_endofmodel (filtered) → one zip.

    Returns the path of the written archive.
    """
    import gams.transfer as gt

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from lib import schemas

    mr_path = model_dir / "MainResults.gdx"
    em_path = model_dir / "all_endofmodel.gdx"

    if not mr_path.is_file():
        raise FileNotFoundError(f"MainResults.gdx not found in {model_dir}")

    # ── Read MainResults (full) ─────────────────────────────────────────────
    if verbose:
        size_mb = mr_path.stat().st_size / 1e6
        print(f"  Reading {mr_path.name} ({size_mb:.1f} MB) ...", end=" ", flush=True)
    t0 = time.time()
    mr_container = gt.Container(load_from=str(mr_path), system_directory=gams_system_directory)
    mr_names = mr_container.listSymbols()
    if verbose:
        print(f"{time.time()-t0:.1f}s  ({len(mr_names)} symbols)")

    tables: dict[str, pd.DataFrame] = {}
    loaded: list[str] = []
    failed: list[dict] = []
    empty: list[str] = []
    descriptions: dict[str, str] = {}

    for name in mr_names:
        try:
            sym = mr_container[name]
            descriptions[name] = (sym.description or "").strip()
            df = _extract_symbol(sym, schemas.ALL_COLUMNS.get(name))
            if df is None:
                empty.append(name)
                continue
            df.insert(0, "Scenario", scenario_name)
            tables[name] = df
            loaded.append(name)
        except Exception as e:
            failed.append({"symbol": name, "error": f"{type(e).__name__}: {e}"})

    # ── Read all_endofmodel (filtered, ~23 input symbols) ───────────────────
    inputs_tables: dict[str, pd.DataFrame] = {}
    inputs_loaded: list[str] = []
    inputs_failed: list[dict] = []
    inputs_empty: list[str] = []
    inputs_descriptions: dict[str, str] = {}
    inputs_source: str | None = None

    if em_path.is_file():
        size_mb = em_path.stat().st_size / 1e6
        if verbose:
            print(f"  Reading inputs from {em_path.name} ({size_mb:,.1f} MB) ...", end=" ", flush=True)
        t0 = time.time()
        em_container = gt.Container(system_directory=gams_system_directory)
        em_container.read(str(em_path), symbols=INPUT_SYMBOLS)
        if verbose:
            print(f"{time.time()-t0:.1f}s  ({len(em_container.listSymbols())} of {len(INPUT_SYMBOLS)} symbols)")
        inputs_source = em_path.name

        for name in em_container.listSymbols():
            try:
                sym = em_container[name]
                inputs_descriptions[name] = (sym.description or "").strip()
                df = _extract_symbol(sym, None)
                if df is None:
                    inputs_empty.append(name)
                    continue
                df.insert(0, "Scenario", scenario_name)
                inputs_tables[name] = df
                inputs_loaded.append(name)
            except Exception as e:
                inputs_failed.append({"symbol": name, "error": f"{type(e).__name__}: {e}"})

        # Report which requested symbols weren't found at all
        missing = [s for s in INPUT_SYMBOLS if s not in em_container.listSymbols()]
        inputs_missing = missing
    else:
        if verbose:
            print(f"  ⚠ all_endofmodel.gdx not found in {model_dir} — Model Inputs page will be empty for this scenario")
        inputs_missing = INPUT_SYMBOLS[:]

    # ── Manifest ────────────────────────────────────────────────────────────
    discovery = _discover_dimensions(tables)
    capabilities = {
        "has_pb":         schemas.has_pb_symbols(loaded),
        "has_v2g":        schemas.has_v2g_symbols(loaded),
        "has_optiflow":   schemas.has_optiflow_symbols(loaded),
        "has_inputs":     bool(inputs_loaded),
    }
    manifest = {
        "schema_version":  "1.1",
        "scenario_name":   scenario_name,
        "source_main":     str(mr_path),
        "source_inputs":   str(em_path) if em_path.is_file() else None,
        "exported_at":     datetime.now(timezone.utc).isoformat(),
        "result_type":     result_type,
        **discovery,
        "symbols_loaded":   sorted(loaded),
        "symbols_empty":    sorted(empty),
        "symbols_failed":   failed,
        "inputs_loaded":    sorted(inputs_loaded),
        "inputs_empty":     sorted(inputs_empty),
        "inputs_missing":   sorted(inputs_missing),
        "inputs_failed":    inputs_failed,
        "inputs_source":    inputs_source,
        "symbol_descriptions": {k: v for k, v in {**descriptions, **inputs_descriptions}.items() if v},
        "capabilities":     capabilities,
        "exporter_version": "0.2.0",
    }

    # ── Pack zip ────────────────────────────────────────────────────────────
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if verbose:
        print(f"  Writing {out_path.name} ...", end=" ", flush=True)
    t0 = time.time()
    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, indent=2, default=str))
        for name, df in tables.items():
            buf = io.BytesIO()
            df.to_parquet(buf, engine="pyarrow", compression="snappy")
            zf.writestr(f"parquet/{name}.parquet", buf.getvalue())
        for name, df in inputs_tables.items():
            buf = io.BytesIO()
            df.to_parquet(buf, engine="pyarrow", compression="snappy")
            zf.writestr(f"inputs/{name}.parquet", buf.getvalue())
    if verbose:
        size_mb = out_path.stat().st_size / 1e6
        print(f"{time.time()-t0:.1f}s  ({size_mb:.1f} MB on disk)")
        print(
            f"    Outputs: {len(loaded)} loaded · {len(empty)} empty · {len(failed)} failed\n"
            f"    Inputs:  {len(inputs_loaded)} loaded · {len(inputs_missing)} missing"
        )

    return out_path


# ── Multi-scenario batch (the main entry point) ────────────────────────────

def export_balmorel_root(
    balmorel_root: Path,
    *,
    gams_system_directory: str | None = None,
    only_scenarios: list[str] | None = None,
    verbose: bool = False,
) -> list[Path]:
    """Discover scenarios under a Balmorel root and export each one.

    Output zips go to `<balmorel_root>/<scenario>/output/zip_files/MainResults_<scenario>.zip`.
    Returns the list of written archive paths.
    """
    balmorel_root = balmorel_root.resolve()
    sysdir = _find_gams_system_dir(gams_system_directory)

    # Legacy folder check (single-line informational note)
    legacy = _check_legacy_root_zip_files(balmorel_root)
    if legacy is not None:
        print(
            f"ℹ Found legacy {legacy.relative_to(balmorel_root.parent)}/ — "
            f"outputs now go to <scenario>/output/zip_files/. Safe to delete the old folder."
        )

    if verbose:
        print(f"GAMS system directory: {sysdir}")
        print(f"Balmorel root:         {balmorel_root}")

    scenarios = discover_scenarios(balmorel_root)
    if only_scenarios:
        wanted = set(only_scenarios)
        scenarios = [s for s in scenarios if s[0] in wanted]
        if not scenarios:
            raise ValueError(
                f"No scenarios matching {sorted(wanted)} found under {balmorel_root}"
            )

    if not scenarios:
        raise FileNotFoundError(
            f"No scenarios found under {balmorel_root}\n"
            f"Expected layout: <root>/<scenario>/model/MainResults.gdx"
        )

    if verbose:
        print(f"Scenarios found:       {', '.join(s[0] for s in scenarios)}\n")

    written: list[Path] = []
    for sc_name, model_dir in scenarios:
        if verbose:
            print(f"━━ {sc_name} ━━")
        out_path = scenario_zip_path(model_dir, sc_name)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        if out_path.exists():
            print(f"  ↻ overwriting existing {out_path.name}")
        try:
            export_scenario(
                scenario_name=sc_name,
                model_dir=model_dir,
                out_path=out_path,
                gams_system_directory=sysdir,
                verbose=verbose,
            )
            written.append(out_path)
        except Exception as e:
            print(f"  ❌ {sc_name} failed: {type(e).__name__}: {e}")
            continue
        if verbose:
            print()

    return written


# ── Inspection helper (used by --list-scenarios) ───────────────────────────

def inspect_root(balmorel_root: Path) -> None:
    """Print discovered scenarios + file sizes + whether an export exists."""
    from datetime import datetime

    balmorel_root = balmorel_root.resolve()
    print(f"\nBalmorel root: {balmorel_root}\n")

    legacy = _check_legacy_root_zip_files(balmorel_root)
    if legacy is not None:
        print(
            f"ℹ Found legacy {legacy.relative_to(balmorel_root.parent)}/ — "
            f"outputs now go to <scenario>/output/zip_files/. Safe to delete.\n"
        )

    try:
        scenarios = discover_scenarios(balmorel_root)
    except NotADirectoryError as e:
        print(f"  Error: {e}")
        return
    if not scenarios:
        print("  No scenarios discovered (looking for <scenario>/model/MainResults.gdx).")
        return

    print(
        f"{'Scenario':<26} {'MainResults':>12}  {'all_endofmodel':>15}  "
        f"{'BALBASE4_p':>12}  {'Exported?':<28}"
    )
    print("─" * 100)
    for name, model_dir in scenarios:
        mr = model_dir / "MainResults.gdx"
        em = model_dir / "all_endofmodel.gdx"
        bp = model_dir / "BALBASE4_p.gdx"
        sizes = [(_fmt_size(p.stat().st_size) if p.is_file() else "—") for p in (mr, em, bp)]

        zip_path = scenario_zip_path(model_dir, name)
        if zip_path.is_file():
            zip_size = _fmt_size(zip_path.stat().st_size)
            zip_mtime = datetime.fromtimestamp(zip_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            exported = f"✓ {zip_size}, {zip_mtime}"
        else:
            exported = "—"

        print(
            f"{name:<26} {sizes[0]:>12}  {sizes[1]:>15}  {sizes[2]:>12}  {exported:<28}"
        )
    print()
