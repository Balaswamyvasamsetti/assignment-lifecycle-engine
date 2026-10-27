"""Engine orchestrator coordinating master, transactional, lifecycle, and anomaly pipelines."""

import random
from pathlib import Path
from typing import Dict, Tuple

from src.config import DEFAULT_SEED, SCALES, ScaleConfig
from src.exporter import export_all_csvs, export_csvs_to_sqlite
from src.generator.anomalies import inject_anomalies
from src.generator.lifecycle import generate_lifecycle_data
from src.generator.master import generate_master_data
from src.generator.transactions import generate_transaction_data


def run_pipeline(
    scale: str = "starter",
    seed: int = DEFAULT_SEED,
    out_dir: Path = Path("data/raw"),
    ground_truth_path: Path = Path("data/ground_truth.csv"),
    sqlite_db_path: Path = Path("data/database.sqlite"),
) -> Tuple[Dict[str, Path], Path]:
    """Executes the complete generation pipeline deterministically and exports all artifacts."""
    
    # Initialize random number generator with fixed seed
    rng = random.Random(seed)

    config = SCALES.get(scale.lower())
    if not config:
        raise ValueError(f"Unknown scale: {scale}. Must be one of {list(SCALES.keys())}")

    # 1. Generate master entities
    courses, learners, enrollments, assignments, rubrics, rubric_criteria = (
        generate_master_data(config, rng)
    )

    # 2. Generate transactional entities
    submissions, artifacts, grades, feedbacks, _ = generate_transaction_data(
        config, courses, enrollments, assignments, rubrics, rubric_criteria, rng
    )

    # 3. Generate lifecycle entities (Resubmissions, Appeals)
    resubmissions, appeals, submissions, artifacts, grades, feedbacks = (
        generate_lifecycle_data(
            config, assignments, submissions, artifacts, grades, feedbacks, rubric_criteria, rng
        )
    )

    # 4. Inject systematic anomalies and generate ground_truth.csv
    submissions, grades, feedbacks, appeals, ground_truth = inject_anomalies(
        config,
        assignments,
        enrollments,
        learners,
        submissions,
        grades,
        feedbacks,
        appeals,
        rubrics,
        rng,
        artifacts=artifacts,
        resubmissions=resubmissions,
    )

    # 5. Export all CSV files and ground_truth.csv
    csv_paths = export_all_csvs(
        out_dir,
        ground_truth_path,
        courses,
        learners,
        enrollments,
        assignments,
        rubrics,
        rubric_criteria,
        submissions,
        artifacts,
        grades,
        feedbacks,
        resubmissions,
        appeals,
        ground_truth,
    )

    # 6. Seed SQLite database
    export_csvs_to_sqlite(out_dir, sqlite_db_path)

    return csv_paths, sqlite_db_path
