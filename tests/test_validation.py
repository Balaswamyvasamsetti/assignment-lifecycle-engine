"""Validation test suite: tests schema constraints, business rules, and anomaly detection accuracy."""

import csv
from pathlib import Path
import pytest

from src.config import (
    ANOMALY_DOUBLE_LATE_PENALTY,
    ANOMALY_GRADE_EXCEEDS_MAX,
    ANOMALY_TYPES,
    ANOMALY_UNAUDITED_APPEAL,
    ANOMALY_UNENROLLED_SUBMISSION,
    DEFAULT_SEED,
)
from src.generator.orchestrator import run_pipeline
from src.validator.business_rules import parse_iso
from src.validator.runner import load_csv, run_validations
from src.validator.schema import (
    validate_enum_field,
    validate_fk_integrity,
    validate_pk_uniqueness,
)


@pytest.fixture(scope="module")
def generated_data(tmp_path_factory):
    """Generates a dataset fixture for test validations."""
    temp_dir = tmp_path_factory.mktemp("val_data")
    raw_dir = temp_dir / "raw"
    gt_file = temp_dir / "ground_truth.csv"
    sqlite_file = temp_dir / "database.sqlite"
    json_dir = temp_dir / "json"
    manifest_file = temp_dir / "manifest.json"

    run_pipeline(
        scale="starter",
        seed=DEFAULT_SEED,
        out_dir=raw_dir,
        ground_truth_path=gt_file,
        sqlite_db_path=sqlite_file,
        export_json=True,
        json_out_dir=json_dir,
        manifest_path=manifest_file,
    )
    return {
        "raw_dir": raw_dir,
        "gt_file": gt_file,
        "sqlite_file": sqlite_file,
    }


def test_full_validation_passes(generated_data):
    """Asserts that running validation against generated dataset produces 100% precision and recall."""
    result = run_validations(
        data_dir=generated_data["raw_dir"],
        ground_truth_path=generated_data["gt_file"],
    )

    assert result["is_clean"] is True
    assert result["precision"] == 1.0
    assert result["recall"] == 1.0
    assert result["f1_score"] == 1.0
    assert result["unexpected_errors"] == []
    assert result["false_positives"] == 0
    assert result["false_negatives"] == 0
    assert result["true_positives"] > 0


def test_all_four_anomaly_types_detected(generated_data):
    """Asserts that each of the four specified anomaly categories is injected and detected."""
    gt_records = load_csv(generated_data["gt_file"])
    gt_types = {r["issue_type"] for r in gt_records}

    expected_types = {
        ANOMALY_UNENROLLED_SUBMISSION,
        ANOMALY_GRADE_EXCEEDS_MAX,
        ANOMALY_DOUBLE_LATE_PENALTY,
        ANOMALY_UNAUDITED_APPEAL,
    }

    assert expected_types.issubset(gt_types), f"Missing anomaly types in ground truth: {expected_types - gt_types}"


def test_separate_ground_truth_no_data_leakage(generated_data):
    """Asserts that no anomaly labels appear inside operational CSV tables."""
    raw_dir = generated_data["raw_dir"]
    forbidden_terms = {"anomaly", "ground_truth", "issue_type", "issue_id", "corrupted"}

    for csv_file in raw_dir.glob("*.csv"):
        with open(csv_file, "r", encoding="utf-8") as f:
            header_line = f.readline().lower()
            for term in forbidden_terms:
                assert term not in header_line, f"Forbidden label '{term}' leaked into headers of {csv_file.name}"


def test_chronological_ordering(generated_data):
    """Asserts Course.start_date <= Assignment.due_date and Grade.graded_at >= Submission.submitted_at."""
    raw_dir = generated_data["raw_dir"]
    courses = {c["course_id"]: c for c in load_csv(raw_dir / "courses.csv")}
    assignments = {a["assignment_id"]: a for a in load_csv(raw_dir / "assignments.csv")}
    submissions = {s["submission_id"]: s for s in load_csv(raw_dir / "submissions.csv")}
    grades = load_csv(raw_dir / "grades.csv")
    appeals = load_csv(raw_dir / "appeals.csv")

    # Due dates within course start and end
    for asn in assignments.values():
        course = courses[asn["course_id"]]
        c_start = parse_iso(course["start_date_utc"])
        c_end = parse_iso(course["end_date_utc"])
        due_dt = parse_iso(asn["due_date_utc"])
        assert c_start <= due_dt <= c_end

    # Grade timestamp after submission
    for g in grades:
        sub = submissions[g["submission_id"]]
        sub_dt = parse_iso(sub["submitted_at_utc"])
        grd_dt = parse_iso(g["graded_at_utc"])
        assert grd_dt >= sub_dt

    # Appeal timestamp after grade
    grades_map = {g["grade_id"]: g for g in grades}
    for app in appeals:
        grd = grades_map[app["grade_id"]]
        grd_dt = parse_iso(grd["graded_at_utc"])
        app_dt = parse_iso(app["submitted_at_utc"])
        assert app_dt >= grd_dt


def test_arithmetic_reconciliation(generated_data):
    """Asserts raw_score == sum(feedback.points_awarded) for every non-anomalous grade."""
    raw_dir = generated_data["raw_dir"]
    grades = load_csv(raw_dir / "grades.csv")
    feedbacks = load_csv(raw_dir / "feedback.csv")

    fdb_sum_by_grade = {}
    for fb in feedbacks:
        gid = fb["grade_id"]
        fdb_sum_by_grade[gid] = round(fdb_sum_by_grade.get(gid, 0.0) + float(fb["points_awarded"]), 2)

    for g in grades:
        gid = g["grade_id"]
        raw = float(g["raw_score"])
        fb_sum = fdb_sum_by_grade.get(gid, 0.0)
        assert abs(raw - fb_sum) < 0.05, f"Grade {gid} raw_score {raw} != feedback sum {fb_sum}"


def test_schema_validator_catches_synthetic_corruptions():
    """Unit tests for schema validator: catches duplicate PK, orphan FK, and invalid enum values."""
    # 1. Duplicate PK
    data_with_dup = [
        {"course_id": "CRS-2026-000001"},
        {"course_id": "CRS-2026-000001"},
    ]
    errs = validate_pk_uniqueness(data_with_dup, "course_id", "Course")
    assert any(e.error_type == "PK_DUPLICATE" for e in errs)

    # 2. Orphan FK
    data_orphan = [{"enrollment_id": "ENR-01", "course_id": "CRS-NONEXISTENT"}]
    errs = validate_fk_integrity(data_orphan, "course_id", "Enrollment", {"CRS-01"}, "Course")
    assert any(e.error_type == "FK_ORPHAN" for e in errs)

    # 3. Invalid Enum
    data_invalid_enum = [{"status": "NOT_AN_ENUM_VALUE"}]
    errs = validate_enum_field(data_invalid_enum, "status", "Course", ["ACTIVE", "ARCHIVED"])
    assert any(e.error_type == "ENUM_INVALID_VALUE" for e in errs)

    # 4. Duplicate Unique Field (e.g., email)
    from src.validator.schema import validate_unique_field, validate_unique_composite_key
    data_dup_email = [
        {"learner_id": "LRN-01", "email": "test@univ.edu"},
        {"learner_id": "LRN-02", "email": "test@univ.edu"},
    ]
    errs = validate_unique_field(data_dup_email, "email", "Learner")
    assert any(e.error_type == "UNIQUE_FIELD_DUPLICATE" for e in errs)

    # 5. Duplicate Composite Key (course_id + learner_id)
    data_dup_enr = [
        {"enrollment_id": "ENR-01", "course_id": "CRS-01", "learner_id": "LRN-01"},
        {"enrollment_id": "ENR-02", "course_id": "CRS-01", "learner_id": "LRN-01"},
    ]
    errs = validate_unique_composite_key(data_dup_enr, ["course_id", "learner_id"], "Enrollment")
    assert any(e.error_type == "COMPOSITE_KEY_DUPLICATE" for e in errs)


def test_lifecycle_validator_catches_invalid_transitions():
    """Unit test for lifecycle validator catching illegal status transitions and policy violations."""
    from src.validator.business_rules import validate_lifecycle_transitions

    # 1. Submission marked RESUBMITTED without resubmission record
    bad_subs = [
        {"submission_id": "SUB-01", "status": "RESUBMITTED"}
    ]
    violations = validate_lifecycle_transitions(bad_subs, [], [], [], [])
    assert any(v.issue_type == "INVALID_LIFECYCLE_STATE_TRANSITION" for v in violations)

    # 2. Resubmission violating policy
    resubs = [
        {
            "resubmission_id": "RSB-01",
            "previous_submission_id": "SUB-01",
            "new_submission_id": "SUB-02",
            "is_allowed_by_policy": "True",  # Claimed allowed, but version 3 on max_resub 0
        }
    ]
    subs = [{"submission_id": "SUB-02", "assignment_id": "ASN-01", "version_number": "3"}]
    asns = [{"assignment_id": "ASN-01", "max_resubmissions": "0"}]
    violations = validate_lifecycle_transitions(subs, [], resubs, [], asns)
    assert any(v.issue_type == "RESUBMISSION_POLICY_MISMATCH" for v in violations)
