# Balmorel Results Analysis Tool

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

A simple post-analysis tool built on [pybalmorel](https://github.com/Mathias157/pybalmorel) for exploring results from [Balmorel](https://www.balmorel.com/) energy-system runs. Two paths to use it depending on whether you have Balmorel set up locally:

- **🔧 Balmorel users:** export your scenarios to portable `.zip` archives, then launch the dashboard — it auto-loads everything from your Balmorel root, no uploads needed.
- **🤝 Collaborators:** visit the live URL, drag in a `.zip` someone shared with you, explore. No install required.

🔗 **Live app:** _(coming soon — deployed to Streamlit Community Cloud, access by approval)_

## Highlights

- **Local auto-load:** export with `python -m balmorel_dashboard /path/to/Balmorel`, point `BALMOREL_ROOT` at the same folder, and `streamlit run streamlit_app.py` finds and loads every scenario.
- **Cloud option for sharing:** same dashboard on Streamlit Cloud with email-allowlist access; collaborators drag-drop a `.zip`.
- **Built on pybalmorel:** inherits the community's tech/fuel color palette and column conventions so figures match what other Balmorel researchers produce.
- **Auto-adapts to the data:** the Planetary Boundaries page appears only when `TL_*` symbols are present; transmission tabs hide if a commodity isn't in the archive.
- **One archive ≈ one scenario:** small (typically <1 MB), portable, easy to share or archive.
- **Image export** on every chart via Plotly's toolbar.

## Why two stages?

GAMS GDX files can only be read by the GAMS Python API, which requires a full GAMS install. Streamlit Community Cloud doesn't have GAMS, so we split:

```
┌────────────────────────────────────────────┐        ┌───────────────────────────────────┐
│ EXPORT (your machine, has GAMS)            │        │ DASHBOARD (Streamlit Cloud)       │
│                                            │        │                                   │
│ python -m balmorel_dashboard /path/Balmorel│  .zip  │ Drag-drop the .zip in the sidebar │
│                                            │ ─────▶ │ Interactive plots, image export   │
│                                            │        │                                   │
│ → <root>/<scenario>/output/zip_files/      │        │ No GAMS required                  │
│       MainResults_<scenario>.zip           │        │                                   │
└────────────────────────────────────────────┘        └───────────────────────────────────┘
```

Point the CLI at your Balmorel root folder (the one containing `base/`, `simex/`, and any named scenarios). The CLI auto-discovers every scenario with a `model/MainResults.gdx` and produces one `.zip` per scenario inside that scenario's own `output/zip_files/` folder. Each archive bundles:

- **Outputs** — every non-empty symbol from `MainResults.gdx`, as parquet
- **Inputs** — ~23 filtered parameters from `all_endofmodel.gdx` (GDATA, DE, DH, HYDROGEN_DH2, …) for the **Model Inputs** dashboard page

The input read is **filtered to specific symbols**, so even a 5 GB `all_endofmodel.gdx` takes <1 second to process.

## Quick start

### 🔧 Path A — you have Balmorel set up locally

One-time setup (creates the `balmorel-results-viz` conda env if conda is available, or installs into your current Python if not):

```bash
git clone https://github.com/dhrsh-dtu/Balmorel_Results_Analysis_Tool.git
cd Balmorel_Results_Analysis_Tool
./setup.sh              # Linux/macOS
# setup.bat             # Windows
```

`setup.sh` also sanity-checks that GAMS is reachable (warns if not — the dashboard still works on already-exported zips even without GAMS).

Activate the env, set your paths, export scenarios, and launch the dashboard:

```bash
conda activate balmorel-results-viz

# 1. Tell the CLI where GAMS lives (only needed if `gams` isn't on PATH).
#    On DTU HPC this is /appl/gams/50.4.1.
export GAMS_SYSDIR=/path/to/gams

# 2. Tell the dashboard which folder to auto-load (add both exports to ~/.bashrc to persist):
export BALMOREL_ROOT=/path/to/Balmorel

# 3. Export Balmorel scenarios to portable zip archives:
python -m balmorel_dashboard $BALMOREL_ROOT

# 4. Launch the dashboard in the background (terminal stays usable):
./launch.sh
```

`launch.sh` backgrounds streamlit using `tmux` when available (attach later with `tmux attach -t balmorel-dash` to see live logs) and falls back to `nohup` + log file when it isn't. Stop with `./stop.sh`.

Open <http://localhost:8501> (SSH-tunnel that port if Streamlit runs on a remote host). Scenarios are pre-loaded; head to the **📂 Import Results** page to upload more or change the folder path.

If you'd rather pass paths on the command line instead of using env vars, both work — `--gams-dir /path/to/gams` for the CLI, and the text input on Import Results for the folder. To run streamlit interactively (terminal occupied, but you see live startup logs), use `streamlit run streamlit_app.py --server.headless=true` instead of `./launch.sh`.

#### 🔧 Path A' — start a remote dashboard from your laptop (one command)

When the dashboard runs on a remote host (e.g. HPC) and you're sitting at your laptop, `./start_dashboard.sh` collapses **SSH tunnel + remote launch + browser open** into one command. Clone the repo on your laptop too, then:

1. **One-time:** set the remote repo path in your laptop's `~/.bashrc` (or `~/.zshrc`) and make sure SSH key auth is working:

   ```bash
   export BALMOREL_DASH_PATH="/path/to/Balmorel_Results_Analysis_Tool"   # absolute path on the remote
   # Optional:
   # export BALMOREL_DASH_HOST="<user>@<hostname>"   # default host if you don't pass one explicitly
   # export BALMOREL_DASH_PORT=8501
   ```

2. **Start** — pass the host explicitly each time (DTU HPC's ssh round-robin means you may land on hpclogin1/2/3 depending on load):

   ```bash
   ./start_dashboard.sh dhrsh@hpclogin1.hpccluster.dtu.dk
   ```

   (Or, if you've set `BALMOREL_DASH_HOST`, just `./start_dashboard.sh`.)

   This SSHes in, runs `./launch.sh` on the remote (idempotent — won't double-start), opens an SSH tunnel in the background, and opens the dashboard in your default browser.

3. **Stop** — same calling convention:

   ```bash
   ./stop_dashboard.sh dhrsh@hpclogin1.hpccluster.dtu.dk
   ```

   Stops the remote streamlit and kills the local tunnel.

Watch the remote logs at any time with `ssh <host> -t "tmux attach -t balmorel-dash"` (Ctrl+b then d to detach).

### 🤝 Path B — you're a collaborator (no Balmorel install)

1. Receive a `.zip` archive from a Balmorel user (it's portable, typically <1 MB).
2. Visit the live app URL above and sign in with your approved email.
3. Drag the `.zip` into the **📤 Upload scenario archive(s)** box in the sidebar.
4. Explore.

### Other ways to use the CLI

Export every scenario in a Balmorel folder:

```bash
python -m balmorel_dashboard /path/to/Balmorel --verbose
# → writes /path/to/Balmorel/<scenario>/output/zip_files/MainResults_<scenario>.zip
#   (one .zip per scenario, beside the scenario's own model/ folder)
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
- `--scenario <name>`: limit export to one or more named scenarios; repeatable
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
