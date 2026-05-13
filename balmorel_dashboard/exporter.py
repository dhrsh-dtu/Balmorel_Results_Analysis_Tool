"""GDX → .zip archive exporter.

The archive layout is:

    archive.zip
    ├── manifest.json              # scenario name, years, countries, symbols, capabilities
    └── parquet/
        ├── PRO_YCRAGF.parquet
        ├── G_CAP_YCRAF.parquet
        └── ...                    # one file per loaded symbol

This module is the only piece that requires pybalmorel + gamsapi (and therefore
a GAMS install). The dashboard webapp reads parquet only.

Implementation lands in Phase 1 — this file is a stub for P0.
"""
from __future__ import annotations

from pathlib import Path


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
    # TODO P1:
    #   1. Resolve GAMS system directory (arg, env, or auto-detect from PATH)
    #   2. Load GDX via pybalmorel.MainResults
    #   3. For each known symbol in lib/schemas.py, call get_result() and apply
    #      pre-defined columns; fall back to raw columns otherwise.
    #   4. Build manifest.json with scenario metadata + symbol coverage.
    #   5. Pack parquet files + manifest into a zip.
    #   6. Return the output path.
    raise NotImplementedError(
        "Exporter implementation lands in Phase 1. "
        "P0 scaffolding complete; see README and balmorel_dashboard/__main__.py."
    )
