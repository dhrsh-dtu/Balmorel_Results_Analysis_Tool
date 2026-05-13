"""Integration test: full export + dashboard load roundtrip on a real GDX.

Skips automatically if no GAMS install is detectable. Designed to run locally
(where GAMS is available) and to be silently skipped in CI / Streamlit Cloud.
"""
from __future__ import annotations

import json
import os
import shutil
import zipfile
from pathlib import Path

import pytest

# ── Find a GDX to test against ──────────────────────────────────────────────
_CANDIDATE_GDX_PATHS = [
    Path("/work3/dhrsh/Balmorel/0_Balmorel_PB_Github/1_Results/MainResults_Nordics.gdx"),
    Path("/work3/dhrsh/Balmorel/PyBalmorel/pybalmorel/examples/files/MainResults_Example1.gdx"),
]


def _find_test_gdx() -> Path | None:
    for p in _CANDIDATE_GDX_PATHS:
        if p.is_file():
            return p
    return None


def _has_gams() -> bool:
    for d in os.environ.get("PATH", "").split(os.pathsep):
        if d and (Path(d) / "optgams.def").is_file():
            return True
    for var in ("GAMS_SYSDIR", "GAMSDIR"):
        v = os.environ.get(var)
        if v and (Path(v) / "optgams.def").is_file():
            return True
    return False


_TEST_GDX = _find_test_gdx()
_REQUIRE_GAMS = pytest.mark.skipif(
    not _has_gams() or _TEST_GDX is None,
    reason="No GAMS install or test GDX available",
)


# ── Tests ───────────────────────────────────────────────────────────────────
@_REQUIRE_GAMS
def test_export_roundtrip(tmp_path):
    """Export a GDX, then load the archive back via the dashboard's data layer."""
    from balmorel_dashboard.exporter import export_one
    from lib import data, schemas

    out_zip = tmp_path / "test.zip"
    export_one(gdx_path=_TEST_GDX, out_path=out_zip, scenario_name="TestScenario")

    assert out_zip.is_file()
    assert out_zip.stat().st_size > 0

    # Inspect the zip
    with zipfile.ZipFile(out_zip) as zf:
        names = zf.namelist()
        assert "manifest.json" in names
        assert any(n.startswith("parquet/") for n in names)
        manifest = json.loads(zf.read("manifest.json"))

    assert manifest["scenario_name"] == "TestScenario"
    assert manifest["schema_version"] == "1.0"
    assert manifest["symbols_loaded"], "no symbols loaded"
    assert "capabilities" in manifest

    # Now load it as the Streamlit app would
    payload = out_zip.read_bytes()
    scn = data._load_archive(payload, fallback_name="ignored")
    assert scn.name == "TestScenario"
    assert scn.symbols, "scenario has no loaded symbols"
    assert scn.years, "scenario has no years"


@_REQUIRE_GAMS
def test_export_nordics_pb_symbols(tmp_path):
    """Specific check: the Nordics GDX should expose PB symbols correctly."""
    # Skip if the specific Nordics file isn't available
    nordics = Path("/work3/dhrsh/Balmorel/0_Balmorel_PB_Github/1_Results/MainResults_Nordics.gdx")
    if not nordics.is_file():
        pytest.skip("Nordics GDX not available")

    from balmorel_dashboard.exporter import export_one
    from lib import data

    out_zip = tmp_path / "nordics.zip"
    export_one(gdx_path=nordics, out_path=out_zip)

    payload = out_zip.read_bytes()
    scn = data._load_archive(payload, fallback_name="ignored")

    # PB capability flag should be set
    assert scn.capabilities["has_pb"] is True

    # TL_CO2 should have exactly one row with Year=2050
    tl_co2 = scn.tables["TL_CO2"]
    assert "Year" in tl_co2.columns
    assert "Value" in tl_co2.columns
    assert len(tl_co2) == 1
    assert str(tl_co2["Year"].iloc[0]) == "2050"

    # IS_CO2_FFF should have rows with the right schema columns
    is_co2_fff = scn.tables["IS_CO2_FFF"]
    for col in ("Scenario", "Year", "Generation", "Fuel", "Technology", "Value"):
        assert col in is_co2_fff.columns, f"missing column {col}"

    # PRO_YCRAGF should have Unit column (Balmorel's UNITS dimension promoted to Unit)
    pro = scn.tables["PRO_YCRAGF"]
    assert "Unit" in pro.columns
    assert "Value" in pro.columns


def test_manifest_capabilities_when_no_pb():
    """has_pb / has_v2g / has_optiflow detection helpers."""
    from lib import schemas

    assert schemas.has_pb_symbols(["TL_CO2", "PRO_YCRAGF"]) is True
    assert schemas.has_pb_symbols(["PRO_YCRAGF", "G_CAP_YCRAF"]) is False
    assert schemas.has_v2g_symbols(["V2G_FLEX_Y"]) is True
    assert schemas.has_optiflow_symbols(["VFLOW_Opti_A"]) is True
