"""Integration tests: full export + dashboard load roundtrip on a real Balmorel root.

Skips automatically if no GAMS install + suitable Balmorel root is detectable.
Designed to run locally (where GAMS is available) and to be silently skipped
in CI / Streamlit Cloud.
"""
from __future__ import annotations

import json
import os
import zipfile
from pathlib import Path

import pytest

# ── Find a Balmorel root to test against ────────────────────────────────────
_CANDIDATE_ROOTS = [
    Path("/work3/dhrsh/Balmorel/0_Balmorel_PB_Github/4_Balmorel_High_Res_PB_all_wo_FG_eq"),
]
_PREFERRED_SCENARIO = "1_Scenario_Nordics"


def _find_test_root() -> Path | None:
    for p in _CANDIDATE_ROOTS:
        if p.is_dir() and (p / _PREFERRED_SCENARIO / "model" / "MainResults.gdx").is_file():
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


_TEST_ROOT = _find_test_root()
_REQUIRE_GAMS = pytest.mark.skipif(
    not _has_gams() or _TEST_ROOT is None,
    reason="No GAMS install or test Balmorel root available",
)


# ── Tests ───────────────────────────────────────────────────────────────────
@_REQUIRE_GAMS
def test_export_balmorel_root_roundtrip(tmp_path, monkeypatch):
    """Export one scenario from a real Balmorel root, then reload the archive."""
    from balmorel_dashboard.exporter import export_balmorel_root
    from lib import data

    # Redirect output dir to tmp by exporting into a fake root layout (symlinked)
    # Simpler: call export_scenario directly so we control the out_path.
    from balmorel_dashboard.exporter import export_scenario, _find_gams_system_dir

    sysdir = _find_gams_system_dir(None)
    model_dir = _TEST_ROOT / _PREFERRED_SCENARIO / "model"

    out_zip = tmp_path / f"MainResults_{_PREFERRED_SCENARIO}.zip"
    export_scenario(
        scenario_name=_PREFERRED_SCENARIO,
        model_dir=model_dir,
        out_path=out_zip,
        gams_system_directory=sysdir,
    )

    assert out_zip.is_file()
    assert out_zip.stat().st_size > 0

    with zipfile.ZipFile(out_zip) as zf:
        names = zf.namelist()
        assert "manifest.json" in names
        assert any(n.startswith("parquet/") for n in names), "no MainResults parquets"
        assert any(n.startswith("inputs/") for n in names), "no input parquets"
        manifest = json.loads(zf.read("manifest.json"))

    # New schema_version is 1.1 (added inputs section)
    assert manifest["schema_version"] == "1.1"
    assert manifest["scenario_name"] == _PREFERRED_SCENARIO
    assert manifest["capabilities"]["has_inputs"] is True
    assert manifest["inputs_loaded"], "no input symbols loaded"

    # Roundtrip via dashboard data layer
    payload = out_zip.read_bytes()
    scn = data._load_archive(payload, fallback_name="ignored")
    assert scn.name == _PREFERRED_SCENARIO
    assert scn.symbols, "no output symbols"
    assert scn.input_symbols, "no input symbols"
    assert "GDATA" in scn.input_symbols, "GDATA missing — expected in all_endofmodel"


@_REQUIRE_GAMS
def test_export_nordics_pb_and_inputs(tmp_path):
    """End-to-end: Nordics archive should include PB symbols AND model inputs."""
    from balmorel_dashboard.exporter import export_scenario, _find_gams_system_dir
    from lib import data

    sysdir = _find_gams_system_dir(None)
    model_dir = _TEST_ROOT / _PREFERRED_SCENARIO / "model"

    out_zip = tmp_path / "nordics.zip"
    export_scenario(
        scenario_name="Nordics",
        model_dir=model_dir,
        out_path=out_zip,
        gams_system_directory=sysdir,
    )

    payload = out_zip.read_bytes()
    scn = data._load_archive(payload, fallback_name="ignored")

    # MainResults outputs
    assert scn.capabilities["has_pb"] is True
    tl_co2 = scn.tables["TL_CO2"]
    assert "Year" in tl_co2.columns and "Value" in tl_co2.columns
    pro = scn.tables["PRO_YCRAGF"]
    assert "Unit" in pro.columns and "Value" in pro.columns

    # Inputs
    assert scn.capabilities["has_inputs"] is True
    gd = scn.inputs.get("GDATA")
    assert gd is not None and not gd.empty
    for col in ("Generation", "Parameter", "Value"):
        assert col in gd.columns, f"GDATA missing {col} column"

    # Sector inference
    gws = data.gdata_with_sector(scn)
    assert not gws.empty
    assert "Sector" in gws.columns
    # Most units should be classified (i.e., not 'Other / unknown')
    unknown_frac = (gws["Sector"] == "Other / unknown").mean()
    assert unknown_frac < 0.30, f"too many unclassified units ({unknown_frac:.0%})"


def test_manifest_capabilities_when_no_pb():
    """has_pb / has_v2g / has_optiflow detection helpers."""
    from lib import schemas

    assert schemas.has_pb_symbols(["TL_CO2", "PRO_YCRAGF"]) is True
    assert schemas.has_pb_symbols(["PRO_YCRAGF", "G_CAP_YCRAF"]) is False
    assert schemas.has_v2g_symbols(["V2G_FLEX_Y"]) is True
    assert schemas.has_optiflow_symbols(["VFLOW_Opti_A"]) is True


def test_discover_scenarios():
    """Scenario discovery returns the expected scenarios under a Balmorel root."""
    if _TEST_ROOT is None:
        pytest.skip("No test Balmorel root available")
    from balmorel_dashboard.exporter import discover_scenarios
    scs = discover_scenarios(_TEST_ROOT)
    names = [n for n, _ in scs]
    assert _PREFERRED_SCENARIO in names, f"{_PREFERRED_SCENARIO} not in {names}"
    # `simex/` must NOT be discovered as a scenario
    assert "simex" not in names
