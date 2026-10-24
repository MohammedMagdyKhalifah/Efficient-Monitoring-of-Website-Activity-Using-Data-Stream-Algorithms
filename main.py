"""Run an offline demo, full replay, or all reproducible experiments."""
import argparse
import json
from pathlib import Path

from stream import DATA, ROOT, profile, write_json
from experiments import run_case, run_experiments, write_csv


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["demo", "full", "experiments"], default="demo")
    parser.add_argument("--data", type=Path, default=DATA)
    parser.add_argument("--profile", action="store_true", help="audit the full source file first")
    args = parser.parse_args()
    if not args.data.is_file():
        parser.error("Data file missing. See README.md / download_data.py.")
    if args.profile:
        print("Profiling source data...", flush=True)
        write_json(ROOT / "data" / "manifest.json", profile(args.data))
    if args.mode == "experiments":
        rows = run_experiments(args.data)
        from plots import make_plots
        make_plots()
    else:
        rows = []
        for kind in ["bloom", "fm", "dgim"]:
            row, history, _ = run_case(kind, limit=10_000 if args.mode == "demo" else None,
                                      path=args.data, capture=True)
            rows.append(row)
            write_csv(ROOT / "results" / args.mode / f"{kind}_checkpoints.csv", history)
        write_csv(ROOT / "results" / args.mode / "summary.csv", rows)
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
