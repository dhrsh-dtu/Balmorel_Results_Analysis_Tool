# Balmorel Results Analysis Tool

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

A simple post-analysis tool built on [pybalmorel](https://github.com/Mathias157/pybalmorel) for exploring results from [Balmorel](https://www.balmorel.com/) energy-system runs. Upload a processed results archive, get interactive plots for capacity, production, prices, transmission and planetary-boundary indicators.

🔗 **Live app:** _(coming soon — deployed to Streamlit Community Cloud, access by approval)_

## Highlights

- **Upload-and-go:** drag a `.zip` archive into the sidebar, get interactive plots immediately. No GAMS or Python install needed for viewers.
- **Built on pybalmorel:** inherits the community's tech/fuel color palette and column conventions so figures match what other Balmorel researchers produce.
- **Auto-adapts to the data:** the Planetary Boundaries page appears only when `TL_*` symbols are present; transmission tabs hide if a commodity isn't in the archive.
- **One archive ≈ one scenario:** small (typically <1 MB), portable, easy to share or archive.
- **Image export** on every chart via Plotly's toolbar.

## Why two stages?

GAMS GDX files can only be read by the GAMS Python API, which requires a full GAMS install. Streamlit Community Cloud doesn't have GAMS, so we split:

```
┌───────────────────────────────────┐        ┌───────────────────────────────────┐
│ EXPORT (your machine, has GAMS)   │        │ DASHBOARD (Streamlit Cloud)       │
│                                   │        │                                   │
│ python -m balmorel_dashboard      │  .zip  │ Drag-drop the .zip in the sidebar │
│   /path/to/Balmorel               │ ─────▶ │ Interactive plots, image export   │
│                                   │        │                                   │
│ → <root>/zip_files/               │        │ No GAMS required                  │
│     MainResults_<scenario>.zip    │        │                                   │
└───────────────────────────────────┘        └───────────────────────────────────┘
```

Point the CLI at your Balmorel root folder (the one containing `base/`, `simex/`, and any named scenarios). The CLI auto-discovers every scenario with a `model/MainResults.gdx` and produces one `.zip` per scenario in `<root>/zip_files/`. Each archive bundles:

- **Outputs** — every non-empty symbol from `MainResults.gdx`, as parquet
- **Inputs** — ~23 filtered parameters from `all_endofmodel.gdx` (GDATA, DE, DH, HYDROGEN_DH2, …) for the **Model Inputs** dashboard page

The input read is **filtered to specific symbols**, so even a 5 GB `all_endofmodel.gdx` takes <1 second to process.

## Quick start

### For users (viewing dashboards)

1. Visit the live app URL (above) and sign in with the email you were approved with.
2. Drag a `.zip` archive into the sidebar's upload box.
3. Explore the pages: Overview, Capacity, Production, Prices & Demand, Transmission, Planetary Boundaries, Raw Explorer.
4. Click the camera icon on any chart to download as PNG.

### For data producers (exporting from Balmorel)

Install the export CLI on a machine with GAMS available:

```bash
git clone https://github.com/dhrsh-dtu/Balmorel_Results_Analysis_Tool.git
cd Balmorel_Results_Analysis_Tool
pip install -r requirements-export.txt
pip install -e .
```

Export every scenario in a Balmorel folder:

```bash
python -m balmorel_dashboard /path/to/Balmorel --verbose
# → writes /path/to/Balmorel/zip_files/MainResults_<scenario>.zip  (one per scenario)
```

Limit to specific scenarios:

```bash
python -m balmorel_dashboard /path/to/Balmorel \
    --scenario base \
    --scenario 1_Scenario_Nordics
```

Inspect what's there without exporting (handy on a new run):

```bash
python -m balmorel_dashboard --list-scenarios /path/to/Balmorel
```

Useful flags:
- `--scenario <name>`: limit export; repeatable for several scenarios
- `--gams-dir <path>`: GAMS install (default: auto-detected from `PATH`, `GAMS_SYSDIR`, or `GAMSDIR`)
- `--list-scenarios`: discover scenarios + file sizes; no export
- `-v` / `--verbose`: per-scenario timings

The CLI uses `gams.transfer` for output extraction and a filtered read for input extraction. Column names are normalised via `lib/schemas.GAMS_TO_FRIENDLY` so the dashboard sees the same convention as pybalmorel users do (Year, Country, Region, Generation, …).

### For developers (running the dashboard locally)

```bash
git clone https://github.com/dhrsh-dtu/Balmorel_Results_Analysis_Tool.git
cd Balmorel_Results_Analysis_Tool
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Open <http://localhost:8501>, drag in a `.zip` to test.

## Architecture

```
Balmorel_Results_Analysis_Tool/
├── streamlit_app.py            Entrypoint — sidebar + upload + landing
├── pages/                      Auto-discovered Streamlit pages
├── lib/                        Webapp helpers (data, theme, plots, schemas)
├── balmorel_dashboard/         Export CLI (uses pybalmorel + gamsapi)
├── .streamlit/config.toml      Theme + upload size limits
├── requirements.txt            Webapp dependencies (Streamlit Cloud reads this)
├── requirements-export.txt     CLI dependencies (pybalmorel, gamsapi)
└── pyproject.toml              Makes the CLI installable as a package
```

**Design rationale:**

- Plotting library: **Plotly** — interactive, consistent theme across the app, free PNG export via toolbar.
- Color palette: **inherits `pybalmorel.formatting.balmorel_colours`** so figures match conventions used by the wider Balmorel community.
- Data format: **parquet** inside a zip archive — small (compressed), fast to read, types preserved, portable.
- Pages auto-hide based on archive contents (e.g. the Planetary Boundaries page only shows when `TL_*` symbols are present).
- Session-only state: uploaded archives live in the user's browser session; no cross-user data persistence.

**Archive layout (.zip):**

```
MainResults_X.zip
├── manifest.json              scenario name, years/countries/regions, symbol coverage, capabilities
└── parquet/
    ├── PRO_YCRAGF.parquet     one parquet per non-empty symbol
    ├── G_CAP_YCRAF.parquet
    ├── TL_CO2.parquet          (Planetary Boundary symbols if present)
    └── ...
```

The manifest's `capabilities` flags (`has_pb`, `has_v2g`, `has_optiflow`) drive which dashboard pages are shown for that scenario. Symbols that exist in the GDX but contain no records are listed in `symbols_empty`; symbols that failed to extract are in `symbols_failed` with an error message.

## Deployment

The app is deployed on **Streamlit Community Cloud** as a private app with an email-based viewer allowlist.

### Deploying your own instance

1. Fork or clone this repo to a GitHub account you control.
2. Visit <https://share.streamlit.io> and sign in with GitHub.
3. Click **New app** → fill in:
   - **Repository:** `<your-username>/Balmorel_Results_Analysis_Tool`
   - **Branch:** `main`
   - **Main file path:** `streamlit_app.py`
   - **Advanced settings → Python version:** 3.11 (3.10+ works)
4. Click **Deploy**. First boot takes ~1–2 minutes to install `requirements.txt`.
5. Once live, the app URL will be `https://<your-app-name>.streamlit.app`.

### Restricting access (viewer allowlist)

1. Open the app's settings on share.streamlit.io.
2. Go to the **Sharing** tab.
3. Toggle **This app is private**.
4. Add specific email addresses (Google, GitHub, or generic) to the **Viewers** list.
5. Approved users sign in once on first visit; subsequent visits are seamless.

The list can be edited any time without redeploying. Removing an email revokes access immediately.

### Secrets

`v0.1.0` doesn't use any secrets — viewer access is the only auth layer. If you add a feature that needs an API token, paste TOML content into Streamlit Cloud's **Secrets** panel (see `.streamlit/secrets.toml.example`). Never commit a real `secrets.toml`.

## Access control (for users)

To request viewer access to the live app, contact the repository maintainer with the email address you'd like added to the allowlist.

## License

MIT — see [LICENSE](LICENSE).

## Acknowledgements

- [Balmorel](https://www.balmorel.com/) — the energy-system model this analyses.
- [pybalmorel](https://github.com/Mathias157/pybalmorel) — Python helpers for Balmorel; this tool builds on its conventions and color palettes.
