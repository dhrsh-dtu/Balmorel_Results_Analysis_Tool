# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [semantic versioning](https://semver.org).

## [0.5.0] — 2026-05-14

Separate "what is this tool" from "how do I load my data".

### Added
- **`📂 Import Results` page** (new, right after Tool Description in nav).
  All loading UI lives here now: folder path text input (prefilled from
  `$BALMOREL_ROOT`), upload widget, loaded-scenarios list with delete
  buttons, and the cross-page filters (scenarios / year / countries).
  Adaptive — shows a success banner with scenario count when loaded,
  or an info prompt when empty.
- **`data.autoload_from_root(root)` helper** in `lib/data.py` — idempotent
  folder scan + ingest, used by both the silent module-level autoload in
  `streamlit_app.py` and the editable text input on the Import Results page.

### Changed
- **Sidebar is now nav-only.** All loading controls and filters moved off
  the sidebar to the Import Results page. Streamlit's `st.navigation` is
  the only thing in the sidebar.
- **`streamlit_app.py` keeps a silent module-level autoload** (no UI) so
  bookmarked deep links to e.g. `?page=Overview` still see auto-loaded
  scenarios from `$BALMOREL_ROOT` without visiting Import Results first.
- **Tool Description** copy updated: introductory text and the
  "I'm a collaborator" tab point to the Import Results page instead of
  "the sidebar".

## [0.4.0] — 2026-05-14

Simplify dashboard surface: drop the Python launcher, expose folder load in the UI.

### Removed
- **`--serve` CLI mode** and its subprocess machinery in `__main__.py`.
  The dashboard is launched directly with `streamlit run streamlit_app.py`
  now; the CLI is export-only. Set `BALMOREL_ROOT` once in your shell
  (e.g. in `~/.bashrc`) to auto-load scenarios from a folder.
- **`--no-export`, `--force-reexport`, `--port`, `--no-browser`** flags
  (all were tied to `--serve`).
- **`needs_reexport` and `find_existing_zips` helpers** in `exporter.py`,
  used only by the removed `_serve()` function.

### Changed
- **Folder auto-load is now a sidebar text input** in `streamlit_app.py`,
  prefilled from `$BALMOREL_ROOT` when present, so a different folder can
  be loaded ad-hoc without restarting the dashboard. The upload widget
  stays visible alongside — same UI whether you're on HPC, laptop, or
  Streamlit Cloud.
- **Tool Description "I'm a Balmorel user" tab** rewritten to show the
  two-step export-then-launch flow (no `--serve` reference).
- **`setup.sh` / `setup.bat`** post-install next-steps updated to the new
  export + `streamlit run` workflow.
- **README** Path A quick-start and "Useful flags" list trimmed to the
  remaining export-only CLI surface (`--scenario`, `--gams-dir`,
  `--list-scenarios`, `-v`).

## [0.3.0] — 2026-05-13

Local-first workflow: one-command setup + one-command launch.

### Added
- **`environment.yml` + `setup.sh` / `setup.bat`**: one-command install.
  `./setup.sh` (or `setup.bat` on Windows) creates a `balmorel-results-viz`
  conda env with all deps if conda is available, falls back to `pip install`
  in the current Python otherwise, then `pip install -e .` so the CLI works
  from any directory. Also checks for a GAMS install on PATH/GAMS_SYSDIR/
  GAMSDIR and prints a friendly warning if missing (not a hard error —
  `--serve --no-export` still works).
- **`--serve` mode**: `python -m balmorel_dashboard --serve /path/to/Balmorel`
  does everything in one shot — incremental re-export of any out-of-date
  scenarios, then launches Streamlit on localhost with all scenarios already
  loaded in the sidebar. No upload step needed.
- **Incremental export logic** (`needs_reexport`): a scenario is re-exported
  only if its zip is missing or older than `MainResults.gdx` / `all_endofmodel.gdx`.
  `--force-reexport` to override.
- **`--no-export` flag**: with `--serve`, skip the export step. Useful when
  re-viewing scenarios on a machine without GAMS installed.
- **`--port` and `--no-browser` flags** for the local launch.
- **Dashboard auto-load**: when the `BALMOREL_ROOT` environment variable is set
  (which `--serve` does automatically), the dashboard discovers all
  `<root>/*/output/zip_files/MainResults_*.zip` on first load and ingests them
  into session state. Upload widget remains as an escape hatch.
- **Sidebar shows `📂 Auto-loaded from <root>`** in local mode with a
  ↻ Refresh button to re-scan after a new export.

### Changed
- **Tool Description page** has a tabbed "How to use" — clearly separates
  the Balmorel-user path (`--serve`) from the collaborator path (drag-drop
  a `.zip`); only one panel visible at a time, no column-collision.
- **README** restructured around the two paths; quick-start leads with the
  one-command local workflow (`./setup.sh` then `--serve`).
- **`base/` always listed first** in `--list-scenarios` and during batch
  export.

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
  one zip **inside each scenario's own `output/zip_files/` folder**
  (e.g. `<root>/<scenario>/output/zip_files/MainResults_<scenario>.zip`).
  The legacy file-mode (`python -m balmorel_dashboard /path/to/some.gdx`)
  was removed for clarity.
- **`base/` always listed first** in `--list-scenarios` and during batch
  export, matching Balmorel's own convention.
- **`--list-scenarios`** replaces the old `--list-symbols` flag and now shows
  an "Exported?" column with the zip's size and mtime when present.
- **Re-export prints `↻ overwriting existing …`** so it's visible when a
  scenario's existing archive is being replaced.
- **Non-verbose output uses paths relative to the Balmorel root** (e.g.
  `✓ 1_Scenario_Nordics/output/zip_files/MainResults_1_Scenario_Nordics.zip`).
- **Legacy `<root>/zip_files/` folder is detected** and a one-line note is
  printed both on `--list-scenarios` and on actual export
  (`ℹ Found legacy <root>/zip_files/ — Safe to delete.`).
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
