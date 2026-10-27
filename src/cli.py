"""Command-Line Interface (CLI) for data generation, validation, and SQL export."""

import argparse
import sys
from pathlib import Path

from src.config import DEFAULT_SEED, GROUND_TRUTH_PATH, RAW_DATA_DIR, SQLITE_DB_PATH
from src.exporter import export_csvs_to_sqlite
from src.generator.orchestrator import run_pipeline
from src.validator.runner import run_validations


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="assignment-lifecycle-engine",
        description="Synthetic Data Generator & Validation Engine for Assignment Lifecycle, Rubrics, and Appeals.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Command: generate
    gen_parser = subparsers.add_parser("generate", help="Generate synthetic datasets and ground truth.")
    gen_parser.add_argument(
        "--scale",
        type=str,
        default="starter",
        choices=["starter", "full"],
        help="Scale profile: starter or full benchmark (default: starter).",
    )
    gen_parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help=f"Deterministic integer seed (default: {DEFAULT_SEED}).",
    )
    gen_parser.add_argument(
        "--out",
        type=str,
        default=str(RAW_DATA_DIR),
        help="Target output directory for operational CSVs (default: data/raw).",
    )
    gen_parser.add_argument(
        "--ground-truth",
        type=str,
        default=str(GROUND_TRUTH_PATH),
        help="Path for ground_truth.csv export (default: data/ground_truth.csv).",
    )
    gen_parser.add_argument(
        "--db-path",
        type=str,
        default=str(SQLITE_DB_PATH),
        help="Target SQLite database file path (default: data/database.sqlite).",
    )

    # Command: validate
    val_parser = subparsers.add_parser("validate", help="Run comprehensive schema and business rule validations.")
    val_parser.add_argument(
        "--data-dir",
        type=str,
        default=str(RAW_DATA_DIR),
        help="Directory containing generated CSV files (default: data/raw).",
    )
    val_parser.add_argument(
        "--ground-truth",
        type=str,
        default=str(GROUND_TRUTH_PATH),
        help="Path to ground_truth.csv for anomaly reconciliation (default: data/ground_truth.csv).",
    )

    # Command: export-sql
    sql_parser = subparsers.add_parser("export-sql", help="Seed SQLite database directly from operational CSVs.")
    sql_parser.add_argument(
        "--data-dir",
        type=str,
        default=str(RAW_DATA_DIR),
        help="Directory containing operational CSV files (default: data/raw).",
    )
    sql_parser.add_argument(
        "--db-path",
        type=str,
        default=str(SQLITE_DB_PATH),
        help="Destination SQLite database file (default: data/database.sqlite).",
    )

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "generate":
        out_dir = Path(args.out)
        gt_path = Path(args.ground_truth)
        db_path = Path(args.db_path)

        print(f"Generating synthetic dataset: scale='{args.scale}', seed={args.seed}...")
        csv_paths, exported_db = run_pipeline(
            scale=args.scale,
            seed=args.seed,
            out_dir=out_dir,
            ground_truth_path=gt_path,
            sqlite_db_path=db_path,
        )
        print(f"Operational CSV files successfully written to {out_dir}")
        print(f"Ground truth labels written to {gt_path}")
        print(f"SQLite database created at {exported_db}")

    elif args.command == "validate":
        data_dir = Path(args.data_dir)
        gt_path = Path(args.ground_truth) if args.ground_truth else None

        result = run_validations(data_dir=data_dir, ground_truth_path=gt_path)
        if not result["is_clean"]:
            print(f"Validation completed with flagged issues or missed anomalies.")
            sys.exit(1)
        else:
            print("Validation successful: 100% anomaly recall and zero unexpected corruptions.")

    elif args.command == "export-sql":
        data_dir = Path(args.data_dir)
        db_path = Path(args.db_path)

        print(f"Seeding SQLite database from CSV files in {data_dir} into {db_path}...")
        export_csvs_to_sqlite(data_dir=data_dir, db_path=db_path)
        print(f"SQLite export completed successfully at {db_path}.")


if __name__ == "__main__":
    main()
