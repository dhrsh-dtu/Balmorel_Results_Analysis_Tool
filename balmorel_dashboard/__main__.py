"""CLI entry — `python -m balmorel_dashboard /path/to/Balmorel-root`.

Folder-mode only. The CLI discovers each scenario under the given root
(any subfolder containing `model/MainResults.gdx`) and produces one
`MainResults_<scenario>.zip` per scenario in `<root>/zip_files/`.

The legacy file-mode (`python -m balmorel_dashboard /path/to/some.gdx`)
was removed in 0.2.0 to keep the workflow simple.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="balmorel-export",
        description=(
            "Convert a Balmorel run folder (containing `base/`, `simex/`, and "
            "any number of named scenario folders) into one .zip archive per "
            "scenario for use with the Balmorel Results Analysis Tool web "
            "dashboard. Each archive bundles MainResults outputs (parquet/) "
            "and model inputs (inputs/) from all_endofmodel.gdx."
        ),
    )
    parser.add_argument(
        "balmorel_root",
        type=Path,
        help="Path to the Balmorel root folder (the one containing base/, simex/, "
             "and named scenario folders like 1_Scenario_Nordics/, 1_Scenario_EU/).",
    )
    parser.add_argument(
        "--scenario",
        action="append",
        dest="scenarios",
        help="Limit export to one or more named scenarios. Repeat for several "
             "(e.g. --scenario base --scenario 1_Scenario_Nordics). "
             "Default: export every scenario found.",
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
            f"This CLI now takes a Balmorel root folder, not a .gdx file. "
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
        for p in written:
            print(f"✓ {p}")
    return 0 if written else 1


if __name__ == "__main__":
    sys.exit(main())
