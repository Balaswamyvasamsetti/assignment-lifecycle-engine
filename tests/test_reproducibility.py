"""Reproducibility test suite: asserts deterministic hash equality across consecutive generations."""

import hashlib
from pathlib import Path
import pytest

from src.config import DEFAULT_SEED
from src.generator.orchestrator import run_pipeline


def compute_sha256(file_path: Path) -> str:
    """Computes the SHA-256 hex digest of a file."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def count_lines(file_path: Path) -> int:
    """Counts number of lines in a file."""
    with open(file_path, "r", encoding="utf-8") as f:
        return sum(1 for _ in f)


def test_generation_reproducibility(tmp_path: Path) -> None:
    """Running generation twice with the same seed MUST yield identical row counts and identical file SHA-256 checksums."""
    
    run1_dir = tmp_path / "run1"
    run1_raw = run1_dir / "raw"
    run1_gt = run1_dir / "ground_truth.csv"
    run1_db = run1_dir / "database.sqlite"

    run2_dir = tmp_path / "run2"
    run2_raw = run2_dir / "raw"
    run2_gt = run2_dir / "ground_truth.csv"
    run2_db = run2_dir / "database.sqlite"

    # Execution 1
    run1_csvs, _ = run_pipeline(
        scale="starter",
        seed=DEFAULT_SEED,
        out_dir=run1_raw,
        ground_truth_path=run1_gt,
        sqlite_db_path=run1_db,
    )

    # Execution 2
    run2_csvs, _ = run_pipeline(
        scale="starter",
        seed=DEFAULT_SEED,
        out_dir=run2_raw,
        ground_truth_path=run2_gt,
        sqlite_db_path=run2_db,
    )

    expected_files = [
        "courses.csv",
        "learners.csv",
        "enrollments.csv",
        "assignments.csv",
        "rubrics.csv",
        "rubric_criteria.csv",
        "submissions.csv",
        "submission_artifacts.csv",
        "grades.csv",
        "feedback.csv",
        "resubmissions.csv",
        "appeals.csv",
    ]

    # Verify all operational CSVs
    for filename in expected_files:
        f1 = run1_raw / filename
        f2 = run2_raw / filename

        assert f1.exists(), f"File {filename} missing in run 1"
        assert f2.exists(), f"File {filename} missing in run 2"

        lines1 = count_lines(f1)
        lines2 = count_lines(f2)
        assert lines1 == lines2, f"Line count mismatch for {filename}: {lines1} vs {lines2}"

        hash1 = compute_sha256(f1)
        hash2 = compute_sha256(f2)
        assert hash1 == hash2, f"SHA-256 checksum mismatch for {filename}:\nRun 1: {hash1}\nRun 2: {hash2}"

    # Verify ground_truth.csv
    assert run1_gt.exists()
    assert run2_gt.exists()
    assert count_lines(run1_gt) == count_lines(run2_gt)
    assert compute_sha256(run1_gt) == compute_sha256(run2_gt)
