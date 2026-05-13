# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [semantic versioning](https://semver.org).

## [0.1.0] — 2026-05-13

First release: a Streamlit dashboard for exploring Balmorel results, with a
local export CLI that converts GDX files to portable `.zip` archives.

### Added
- **Export CLI** (`python -m balmorel_dashboard`): reads MainResults `.gdx`
  files via `gams.transfer`, writes `.zip` archives of parquet tables plus a
  `manifest.json`. Handles standard Balmorel symbols, the Planetary Boundary
  extensions (`TL_*`, `IS_*`), V2G symbols, and OptiFlow.
- **GAMS-canonical column name mapping** (`Y → Year`, `C → Country`,
  `RRR → Region`, `PRICE_CATEGORY/VARIABLE_CATEGORY → Category`, etc.) so
  column names are stable even when Balmorel adds dimensions outside
  pybalmorel's positional schema.
- **Symbol descriptions** captured into manifest and surfaced in the Raw
  Explorer page.
- **Streamlit web app** with seven pages:
  - 📊 **Overview** — per-scenario KPIs, cost breakdown, capacity mix,
    production donuts, health checks.
  - ⚡ **Capacity** — generation + storage tabs; stacked bars by Technology
    or Fuel, country heatmap, endo/exo filter.
  - 🏭 **Production** — annual totals, by-country, mix donuts.
  - 💰 **Prices and Demand** — auto-tabs (Electricity/Heat/Hydrogen);
    KPIs, regional prices, demand by category, hourly profile per region.
  - 🌍 **Planetary Boundaries** — radar of all `TL_*` with boundary ring,
    color-coded summary table, per-indicator drill-down (TL bar, source
    attribution, fuel/technology breakdown).
  - 🔌 **Transmission** — auto-tabs per commodity; flow matrix heatmap,
    net trade per country, top lines by capacity, line utilization.
  - 🔍 **Raw Explorer** — symbol search, family grouping, quick column
    filters, numeric summary, CSV download.
- **Plotly theme** (`lib/theme.py`) inheriting `pybalmorel.formatting.balmorel_colours`
  with extensions for PB indicators and a scenario-categorical palette.
- **Auto-hiding pages**: PB page hides if no `TL_*` symbols; commodity tabs
  hide if relevant symbols are absent.

### Deployment
- Configured for **Streamlit Community Cloud** deployment from a public
  GitHub repo; access controlled via Cloud's email-based Viewer allowlist.
- `requirements.txt` lists only webapp dependencies — Cloud installs from
  this file. `requirements-export.txt` is local-only for the export CLI.

### Known limitations
- Geographic transmission map deferred to v0.2 (would need bundled geofiles).
- Compare-scenario diff page deferred to v0.2 — multi-select in sidebar
  already provides cross-scenario comparison on every page.
- Hourly dispatch profile (PRO_YCRAGFST) not yet exposed in the UI.
- No persistent storage: uploaded archives are session-scoped.
