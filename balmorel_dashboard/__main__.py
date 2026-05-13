"""CLI entry — `python -m balmorel_dashboard /path/to/Balmorel-root`.

Two top-level workflows:

  Plain export:
      python -m balmorel_dashboard /path/to/Balmorel
        → writes <root>/<scn>/output/zip_files/MainResults_<scn>.zip per scenario

  Local launch (Balmorel user, single command, zero uploads):
      python -m balmorel_dashboard /path/to/Balmorel --serve
        → incrementally exports any out-of-date scenarios
        → launches Streamlit locally on http://localhost:8501
        → dashboard auto-loads every existing scenario archive

The cloud deployment continues to use the upload widget; this CLI is for
local use.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="balmorel-export",
        description=(
            "Export Balmorel run results to per-scenario .zip archives, "
            "and optionally launch the dashboard locally. "
            "Point at the Balmorel root folder containing base/, simex/, and "
            "any named scenario folders."
        ),
    )
    parser.add_argument(
        "balmorel_root",
        type=Path,
        help="Path to the Balmorel root folder (the one containing base/, simex/, "
             "and named scenario folders like 1_Scenario_Nordics/).",
    )
    parser.add_argument(
        "--scenario",
        action="append",
        dest="scenarios",
        help="Limit export / serve to one or more named scenarios. Repeat "
             "for several. Default: every scenario found.",
    )
    parser.add_argument(
        "--gams-dir",
        type=str,
        default=None,
        help="Path to GAMS system directory (default: auto-detected from PATH, "
             "GAMS_SYSDIR, or GAMSDIR). Not required for --serve --no-export.",
    )
    parser.add_argument(
        "--list-scenarios",
        action="store_true",
        help="Discover scenarios + file sizes and exit without exporting.",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose per-scenario progress.",
    )

    # ── --serve mode ────────────────────────────────────────────────────────
    serve_group = parser.add_argument_group("local dashboard launcher (--serve)")
    serve_group.add_argument(
        "--serve",
        action="store_true",
        help="After exporting, launch the Streamlit dashboard locally with "
             "all scenarios pre-loaded from <root>/*/output/zip_files/.",
    )
    serve_group.add_argument(
        "--no-export",
        action="store_true",
        help="With --serve: skip the export step entirely (just launch the UI "
             "on whatever zips already exist). Useful when GAMS isn't installed.",
    )
    serve_group.add_argument(
        "--force-reexport",
        action="store_true",
        help="With --serve: re-export every scenario, ignoring mtimes. "
             "Default is incremental (only scenarios whose GDX is newer "
             "than the existing zip).",
    )
    serve_group.add_argument(
        "--port",
        type=int,
        default=8501,
        help="Port for the local Streamlit server (default: 8501).",
    )
    serve_group.add_argument(
        "--no-browser",
        action="store_true",
        help="Don't auto-open the browser when serving.",
    )

    args = parser.parse_args(argv)

    # Deferred import — keeps `--help` working without GAMS available.
    from balmorel_dashboard.exporter import (
        discover_scenarios,
        export_balmorel_root,
        export_scenario,
        find_existing_zips,
        inspect_root,
        needs_reexport,
        _find_gams_system_dir,
    )

    if not args.balmorel_root.exists():
        print(f"error: {args.balmorel_root} does not exist", file=sys.stderr)
        return 2
    if not args.balmorel_root.is_dir():
        print(
            f"error: {args.balmorel_root} is not a directory.\n"
            f"This CLI now takes a Balmorel root folder, not a .gdx file. "
            f"See `python -m balmorel_dashboard --help`.",
            file=sys.stderr,
        )
        return 2

    if args.list_scenarios:
        inspect_root(args.balmorel_root)
        return 0

    # ── --serve path ────────────────────────────────────────────────────────
    if args.serve:
        return _serve(args, discover_scenarios, export_scenario,
                      find_existing_zips, needs_reexport, _find_gams_system_dir)

    # ── Plain export path ───────────────────────────────────────────────────
    try:
        written = export_balmorel_root(
            args.balmorel_root,
            gams_system_directory=args.gams_dir,
            only_scenarios=args.scenarios,
            verbose=args.verbose,
        )
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    if not args.verbose:
        root_resolved = args.balmorel_root.resolve()
        for p in written:
            try:
                rel = p.relative_to(root_resolved)
                print(f"✓ {rel}")
            except ValueError:
                print(f"✓ {p}")
    return 0 if written else 1


def _serve(
    args,
    discover_scenarios,
    export_scenario,
    find_existing_zips,
    needs_reexport,
    _find_gams_system_dir,
) -> int:
    """Implementation of `--serve`: incremental export + launch Streamlit."""
    balmorel_root = args.balmorel_root.resolve()

    # ── 1. Incremental export (unless --no-export) ─────────────────────────
    if not args.no_export:
        try:
            sysdir = _find_gams_system_dir(args.gams_dir)
        except FileNotFoundError as e:
            print(f"⚠ Skipping export step: {e}", file=sys.stderr)
            print("  (Use --no-export to silence this and serve only existing zips.)\n",
                  file=sys.stderr)
            sysdir = None

        scenarios = discover_scenarios(balmorel_root)
        if args.scenarios:
            wanted = set(args.scenarios)
            scenarios = [s for s in scenarios if s[0] in wanted]

        to_export: list[tuple[str, Path, str]] = []  # (name, model_dir, reason)
        for sc_name, model_dir in scenarios:
            if args.force_reexport:
                to_export.append((sc_name, model_dir, "forced"))
            elif needs_reexport(model_dir, sc_name):
                to_export.append((sc_name, model_dir, "out-of-date"))

        if not to_export:
            print("All scenario archives are up to date — skipping export.\n")
        elif sysdir is None:
            print(f"⚠ {len(to_export)} scenario(s) would be re-exported, but no GAMS "
                  "is available. Launching with existing zips.\n", file=sys.stderr)
        else:
            print(f"Exporting {len(to_export)} scenario(s) "
                  f"({', '.join(n for n, _, _ in to_export)}):")
            from balmorel_dashboard.exporter import scenario_zip_path
            for sc_name, model_dir, reason in to_export:
                out_path = scenario_zip_path(model_dir, sc_name)
                out_path.parent.mkdir(parents=True, exist_ok=True)
                try:
                    export_scenario(
                        scenario_name=sc_name,
                        model_dir=model_dir,
                        out_path=out_path,
                        gams_system_directory=sysdir,
                        verbose=args.verbose,
                    )
                    rel = out_path.relative_to(balmorel_root)
                    print(f"  ✓ {sc_name} ({reason}) → {rel}")
                except Exception as e:
                    print(f"  ❌ {sc_name} failed: {type(e).__name__}: {e}",
                          file=sys.stderr)
            print()

    # ── 2. Find existing zips to confirm there's something to serve ─────────
    existing = find_existing_zips(balmorel_root)
    if not existing:
        print(
            "error: no scenario archives found to serve.\n"
            "Run an export first (without --no-export) or check the Balmorel root.",
            file=sys.stderr,
        )
        return 1

    print(f"Launching dashboard with {len(existing)} scenario(s) auto-loaded:")
    for p in existing:
        try:
            rel = p.relative_to(balmorel_root)
            print(f"  📦 {rel}")
        except ValueError:
            print(f"  📦 {p}")

    # ── 3. Launch Streamlit ─────────────────────────────────────────────────
    pkg_dir = Path(__file__).resolve().parent.parent
    app_path = pkg_dir / "streamlit_app.py"
    if not app_path.is_file():
        print(f"error: {app_path} not found — is the package layout intact?",
              file=sys.stderr)
        return 1

    env = os.environ.copy()
    env["BALMOREL_ROOT"] = str(balmorel_root)

    cmd = [
        sys.executable, "-m", "streamlit", "run", str(app_path),
        "--server.port", str(args.port),
        "--browser.gatherUsageStats", "false",
    ]
    if args.no_browser:
        cmd.extend(["--server.headless", "true"])

    print(f"\n🚀 http://localhost:{args.port}  (Ctrl+C to stop)\n")
    try:
        return subprocess.call(cmd, env=env)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
