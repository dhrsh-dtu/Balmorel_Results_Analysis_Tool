"""Balmorel-Results-Analysis-Tool: export CLI.

Reads GDX files via pybalmorel + gamsapi, writes portable `.zip` archives
containing parquet tables + manifest.json. Run on a machine with GAMS available.

Usage:
    python -m balmorel_dashboard MainResults_X.gdx
"""
__version__ = "0.1.0"
