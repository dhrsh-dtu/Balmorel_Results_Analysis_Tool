"""Smoke tests — make sure modules import without requiring GAMS or Streamlit runtime."""
from __future__ import annotations


def test_lib_imports():
    """All lib/ modules should import standalone."""
    from lib import data, plots, schemas, theme  # noqa: F401


def test_schemas_pb_detection():
    from lib.schemas import has_pb_symbols, has_v2g_symbols
    assert has_pb_symbols(["TL_CO2", "PRO_YCRAGF"])
    assert not has_pb_symbols(["PRO_YCRAGF"])
    assert has_v2g_symbols(["V2G_FLEX_Y"])
    assert not has_v2g_symbols(["PRO_YCRAGF"])


def test_theme_template_registered():
    import plotly.io as pio

    from lib import theme

    theme.apply()
    assert "balmorel" in pio.templates
    assert pio.templates.default == "balmorel"


def test_cli_module_imports():
    """CLI module imports without pulling pybalmorel/gamsapi (those are deferred)."""
    from balmorel_dashboard import __main__  # noqa: F401
