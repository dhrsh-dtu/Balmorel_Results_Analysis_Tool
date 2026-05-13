# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [semantic versioning](https://semver.org).

## [0.2.0] — 2026-05-13

Major upgrade: model-input extraction + new **Model Inputs** dashboard page.

### Added
- **📥 Model Inputs page** (new, sits between Tool Description and Overview
  in nav). Five sections:
  1. **Sectors covered** — auto-detected (Electricity, Heat, Hydrogen,
     Transport, Biomethane, CCS).
  2. **Technology portfolio** — full catalog grouped by inferred sector, with
     cross-reference against `G_CAP_YCRAF` for deployed-unit accuracy.
  3. **Cost inputs per technology** — capex, fixed/var O&M, lifetime, fuel
     efficiency, with mean/median/min/max aggregator across units in each
     sector + sortable per-unit table.
  4. **Demand inputs** — DE, DH, HYDROGEN_DH2 with year selector and
     active-scope filter (so a Nordics scenario shows Nordic regions, not
     full-Europe inputs).
  5. **Sector coupling** — exogenous-vs-endogenous demand decomposition for
     Electricity and Hydrogen, showing how input demand becomes total served
     demand via heat pumps, EVs, electrolysers, losses.
- **Filtered input extraction** in exporter — pulls 23 specific symbols
  (`GDATA`, `DE`, `DH`, `HYDROGEN_DH2`, `ANNUITYCG`, `CCS_*`, etc.) from
  `all_endofmodel.gdx` in <1 second even for 5 GB files (uses GDX index lookup,
  not full scan).
- **Sector inference heuristic** (`lib.data.infer_sector` /
  `gdata_with_sector`) — combines G_CAP_YCRAF deployed-commodity lookup, CHP
  detector (Cv+Cb present), storage detector (GDSTOH* present), and name-token
  patterns. Classifies ~90% of units on real data.
- **GAMS_TO_FRIENDLY map extended** with input-side column names: `YYY → Year`,
  `CCC → Country`, `GGG → Generation`, `GDATASET → Parameter`,
  `DEUSER`/`DHUSER → Category`, `CCCRRRAAA → Location`.
- **Manifest schema v1.1** — adds `inputs_loaded`, `inputs_empty`,
  `inputs_missing`, `inputs_source`, capability `has_inputs`.

### Changed
- **Export CLI is now folder-mode only.** Pass a Balmorel root path; the CLI
  auto-discovers every scenario containing `model/MainResults.gdx` and writes
  `<root>/zip_files/MainResults_<scenario>.zip`. The legacy file-mode
  (`python -m balmorel_dashboard /path/to/some.gdx`) was removed for clarity.
- **`--list-scenarios`** replaces the old `--list-symbols` flag.
- Tool Description page updated to reflect the new workflow.
- `streamlit_app.py` adds Model Inputs to the navigation.

### Tests
- Integration tests rewritten for the folder-mode API. All 8 pass on real
  data (Nordics scenario via `4_Balmorel_High_Res_PB_all_wo_FG_eq/` root).

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
