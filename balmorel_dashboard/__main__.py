"""CLI entry — `python -m balmorel_dashboard /path/to/Balmorel-root`.

Exports per-scenario .zip archives from a Balmorel run:

    python -m balmorel_dashboard /path/to/Balmorel
      → writes <root>/<scn>/output/zip_files/MainResults_<scn>.zip per scenario

To view the results, launch the Streamlit dashboard separately:

    export BALMOREL_ROOT=/path/to/Balmorel     # one-time, e.g. in ~/.bashrc
    streamlit run streamlit_app.py --server.headless=true

When BALMOREL_ROOT is set, the dashboard auto-loads every scenario archive it
finds. Otherwise users upload zips via the sidebar widget.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="balmorel-export",
        description=(
            "Export Balmorel run results to per-scenario .zip archives. "
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
        help="Limit export to one or more named scenarios. Repeat for several. "
             "Default: every scenario found.",
    )
    parser.add_argument(
        "--gams-dir",
        type=str,
        default=None,
        help="Path to GAMS system directory (default: auto-detected from PATH, "
             "GAMS_SYSDIR, or GAMSDIR).",
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

    args = parser.parse_args(argv)

    # Deferred import — keeps `--help` working without GAMS available.
    from balmorel_dashboard.exporter import export_balmorel_root, inspect_root

    if not args.balmorel_root.exists():
        print(f"error: {args.balmorel_root} does not exist", file=sys.stderr)
        return 2
    if not args.balmorel_root.is_dir():
        print(
            f"error: {args.balmorel_root} is not a directory.\n"
            f"This CLI takes a Balmorel root folder, not a .gdx file. "
            f"See `python -m balmorel_dashboard --help`.",
            file=sys.stderr,
        )
        return 2

    if args.list_scenarios:
        inspect_root(args.balmorel_root)
        return 0

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


if __name__ == "__main__":
    sys.exit(main())
