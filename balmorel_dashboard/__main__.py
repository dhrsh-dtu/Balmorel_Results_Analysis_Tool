"""CLI entry — `python -m balmorel_dashboard <gdx files…>`."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="balmorel-export",
        description=(
            "Convert Balmorel MainResults GDX files to portable .zip archives "
            "(parquet + manifest) for use with the Balmorel Results Analysis "
            "Tool web dashboard."
        ),
    )
    parser.add_argument(
        "gdx_files",
        nargs="+",
        type=Path,
        help="One or more MainResults_*.gdx files",
    )
    parser.add_argument(
        "-o", "--output-dir",
        type=Path,
        default=None,
        help="Directory to write the .zip archives (default: alongside each input)",
    )
    parser.add_argument(
        "--gams-dir",
        type=str,
        default=None,
        help="Path to GAMS system directory (default: auto-detect from PATH)",
    )
    parser.add_argument(
        "--scenario-name",
        type=str,
        default=None,
        help="Override scenario name (default: derived from filename)",
    )
    parser.add_argument(
        "--result-type",
        choices=["balmorel", "optiflow"],
        default="balmorel",
        help="Result type (default: balmorel)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose logging",
    )
    args = parser.parse_args(argv)

    # Deferred import — pybalmorel + gamsapi only needed when actually running
    from balmorel_dashboard.exporter import export_one

    if len(args.gdx_files) > 1 and args.scenario_name:
        print("error: --scenario-name cannot be combined with multiple input files",
              file=sys.stderr)
        return 2

    exit_code = 0
    for gdx in args.gdx_files:
        if not gdx.exists():
            print(f"error: {gdx} does not exist", file=sys.stderr)
            exit_code = 1
            continue
        out_dir = args.output_dir or gdx.parent
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{gdx.stem}.zip"
        print(f"Exporting {gdx} → {out_path}")
        try:
            export_one(
                gdx_path=gdx,
                out_path=out_path,
                scenario_name=args.scenario_name,
                gams_system_directory=args.gams_dir,
                result_type=args.result_type,
                verbose=args.verbose,
            )
        except Exception as e:
            print(f"  ❌ failed: {e}", file=sys.stderr)
            exit_code = 1
            continue
        print(f"  ✅ done")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
