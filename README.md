# Balmorel Results Analysis Tool

A simple post-analysis tool built on [pybalmorel](https://github.com/Mathias157/pybalmorel) for exploring results from [Balmorel](https://www.balmorel.com/) energy-system runs. Upload a processed results archive, get interactive plots for capacity, production, prices, transmission and planetary-boundary indicators.

🔗 **Live app:** _(coming soon — deployed to Streamlit Community Cloud, access by approval)_

## Why two stages?

GAMS GDX files can only be read by the GAMS Python API, which requires a full GAMS install. Streamlit Community Cloud doesn't have GAMS, so we split:

```
┌───────────────────────────────────┐        ┌───────────────────────────────────┐
│ EXPORT (your machine, has GAMS)   │        │ DASHBOARD (Streamlit Cloud)       │
│                                   │        │                                   │
│ python -m balmorel_dashboard      │  .zip  │ Drag-drop the .zip in the sidebar │
│   MainResults_Foo.gdx             │ ─────▶ │ Interactive plots, image export   │
│                                   │        │                                   │
│ → MainResults_Foo.zip             │        │ No GAMS required                  │
└───────────────────────────────────┘        └───────────────────────────────────┘
```

You run the export CLI once per scenario on the machine where you ran Balmorel (it already has GAMS and pybalmorel). The resulting `.zip` contains parquet tables of every Balmorel symbol plus a manifest — small, portable, no GAMS dependency downstream.

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

Export a single GDX:

```bash
python -m balmorel_dashboard MainResults_Nordics.gdx
# → writes MainResults_Nordics.zip alongside the input
```

Export multiple at once:

```bash
python -m balmorel_dashboard MainResults_*.gdx --output-dir exports/
```

The CLI auto-detects `balmorel` vs `optiflow` result types and applies pybalmorel's column conventions.

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

## Access control

The app is deployed as a private Streamlit app with a viewer allowlist. To request access, contact the maintainer.

## License

MIT — see [LICENSE](LICENSE).

## Acknowledgements

- [Balmorel](https://www.balmorel.com/) — the energy-system model this analyses.
- [pybalmorel](https://github.com/Mathias157/pybalmorel) — Python helpers for Balmorel; this tool builds on its conventions and color palettes.
