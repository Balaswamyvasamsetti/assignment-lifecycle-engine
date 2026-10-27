import csv
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from src.models import (
    AnomalyGroundTruth,
    Appeal,
    Assignment,
    Course,
    Enrollment,
    Feedback,
    Grade,
    Learner,
    Resubmission,
    Rubric,
    RubricCriterion,
    Submission,
    SubmissionArtifact,
)


def export_to_csv(
    data: List[Any],
    fieldnames: List[str],
    output_path: Path,
) -> None:
    """Exports a list of dataclass instances or dicts to a deterministic CSV file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
            lineterminator="\n",
            quoting=csv.QUOTE_MINIMAL,
        )
        writer.writeheader()
        for item in data:
            row_dict = item.to_dict() if hasattr(item, "to_dict") else item
            # Filter to specified fieldnames in consistent order
            filtered_row = {k: row_dict.get(k, "") for k in fieldnames}
            writer.writerow(filtered_row)


def export_to_json(
    data: List[Any],
    fieldnames: List[str],
    output_path: Path,
) -> None:
    """Exports a list of dataclass instances or dicts to a deterministic JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    records = []
    for item in data:
        row_dict = item.to_dict() if hasattr(item, "to_dict") else item
        filtered_row = {k: row_dict.get(k, "") for k in fieldnames}
        records.append(filtered_row)
    with open(output_path, mode="w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)


def export_all_csvs(
    output_dir: Path,
    ground_truth_path: Path,
    courses: List[Course],
    learners: List[Learner],
    enrollments: List[Enrollment],
    assignments: List[Assignment],
    rubrics: List[Rubric],
    rubric_criteria: List[RubricCriterion],
    submissions: List[Submission],
    artifacts: List[SubmissionArtifact],
    grades: List[Grade],
    feedbacks: List[Feedback],
    resubmissions: List[Resubmission],
    appeals: List[Appeal],
    ground_truth: List[AnomalyGroundTruth],
) -> Dict[str, Path]:
    """Deterministically exports all 12 operational entities and ground_truth.csv."""
    output_dir.mkdir(parents=True, exist_ok=True)
    ground_truth_path.parent.mkdir(parents=True, exist_ok=True)

    paths: Dict[str, Path] = {}

    # Sort deterministically by Primary Key
    sorted_courses = sorted(courses, key=lambda x: x.course_id)
    paths["courses"] = output_dir / "courses.csv"
    export_to_csv(
        sorted_courses,
        ["course_id", "title", "department", "term", "start_date_utc", "end_date_utc", "status"],
        paths["courses"],
    )

    sorted_learners = sorted(learners, key=lambda x: x.learner_id)
    paths["learners"] = output_dir / "learners.csv"
    export_to_csv(
        sorted_learners,
        ["learner_id", "full_name", "email", "timezone", "enrolled_date_utc", "status"],
        paths["learners"],
    )

    sorted_enrollments = sorted(enrollments, key=lambda x: x.enrollment_id)
    paths["enrollments"] = output_dir / "enrollments.csv"
    export_to_csv(
        sorted_enrollments,
        ["enrollment_id", "course_id", "learner_id", "enrolled_at_utc", "status"],
        paths["enrollments"],
    )

    sorted_assignments = sorted(assignments, key=lambda x: x.assignment_id)
    paths["assignments"] = output_dir / "assignments.csv"
    export_to_csv(
        sorted_assignments,
        ["assignment_id", "course_id", "title", "max_resubmissions", "due_date_utc", "late_penalty_percent", "status"],
        paths["assignments"],
    )

    sorted_rubrics = sorted(rubrics, key=lambda x: x.rubric_id)
    paths["rubrics"] = output_dir / "rubrics.csv"
    export_to_csv(
        sorted_rubrics,
        ["rubric_id", "assignment_id", "title", "total_points", "version"],
        paths["rubrics"],
    )

    sorted_criteria = sorted(rubric_criteria, key=lambda x: x.criterion_id)
    paths["rubric_criteria"] = output_dir / "rubric_criteria.csv"
    export_to_csv(
        sorted_criteria,
        ["criterion_id", "rubric_id", "title", "description", "max_points", "weight"],
        paths["rubric_criteria"],
    )

    sorted_submissions = sorted(submissions, key=lambda x: x.submission_id)
    paths["submissions"] = output_dir / "submissions.csv"
    export_to_csv(
        sorted_submissions,
        ["submission_id", "assignment_id", "learner_id", "version_number", "submitted_at_utc", "is_late", "hours_late", "status"],
        paths["submissions"],
    )

    sorted_artifacts = sorted(artifacts, key=lambda x: x.artifact_id)
    paths["submission_artifacts"] = output_dir / "submission_artifacts.csv"
    export_to_csv(
        sorted_artifacts,
        ["artifact_id", "submission_id", "file_name", "file_type", "file_size_kb", "file_sha256"],
        paths["submission_artifacts"],
    )

    sorted_grades = sorted(grades, key=lambda x: x.grade_id)
    paths["grades"] = output_dir / "grades.csv"
    export_to_csv(
        sorted_grades,
        ["grade_id", "submission_id", "raw_score", "late_penalty_applied", "final_score", "graded_by", "graded_at_utc"],
        paths["grades"],
    )

    sorted_feedbacks = sorted(feedbacks, key=lambda x: x.feedback_id)
    paths["feedback"] = output_dir / "feedback.csv"
    export_to_csv(
        sorted_feedbacks,
        ["feedback_id", "grade_id", "criterion_id", "points_awarded", "instructor_comment"],
        paths["feedback"],
    )

    sorted_resubmissions = sorted(resubmissions, key=lambda x: x.resubmission_id)
    paths["resubmissions"] = output_dir / "resubmissions.csv"
    export_to_csv(
        sorted_resubmissions,
        ["resubmission_id", "previous_submission_id", "new_submission_id", "requested_at_utc", "reason", "is_allowed_by_policy"],
        paths["resubmissions"],
    )

    sorted_appeals = sorted(appeals, key=lambda x: x.appeal_id)
    paths["appeals"] = output_dir / "appeals.csv"
    export_to_csv(
        sorted_appeals,
        ["appeal_id", "grade_id", "learner_id", "submitted_at_utc", "reason", "status", "original_score", "updated_score", "audit_logged"],
        paths["appeals"],
    )

    # Export Ground Truth (strictly separate file!)
    sorted_ground_truth = sorted(ground_truth, key=lambda x: x.issue_id)
    paths["ground_truth"] = ground_truth_path
    export_to_csv(
        sorted_ground_truth,
        ["issue_id", "issue_type", "entity_name", "record_id", "field_name", "expected_value", "actual_value", "description"],
        ground_truth_path,
    )

    return paths


def export_all_json(
    output_dir: Path,
    ground_truth_path: Path,
    courses: List[Course],
    learners: List[Learner],
    enrollments: List[Enrollment],
    assignments: List[Assignment],
    rubrics: List[Rubric],
    rubric_criteria: List[RubricCriterion],
    submissions: List[Submission],
    artifacts: List[SubmissionArtifact],
    grades: List[Grade],
    feedbacks: List[Feedback],
    resubmissions: List[Resubmission],
    appeals: List[Appeal],
    ground_truth: List[AnomalyGroundTruth],
) -> Dict[str, Path]:
    """Deterministically exports all 12 operational entities and ground truth to JSON files."""
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: Dict[str, Path] = {}

    paths["courses"] = output_dir / "courses.json"
    export_to_json(sorted(courses, key=lambda x: x.course_id), ["course_id", "title", "department", "term", "start_date_utc", "end_date_utc", "status"], paths["courses"])

    paths["learners"] = output_dir / "learners.json"
    export_to_json(sorted(learners, key=lambda x: x.learner_id), ["learner_id", "full_name", "email", "timezone", "enrolled_date_utc", "status"], paths["learners"])

    paths["enrollments"] = output_dir / "enrollments.json"
    export_to_json(sorted(enrollments, key=lambda x: x.enrollment_id), ["enrollment_id", "course_id", "learner_id", "enrolled_at_utc", "status"], paths["enrollments"])

    paths["assignments"] = output_dir / "assignments.json"
    export_to_json(sorted(assignments, key=lambda x: x.assignment_id), ["assignment_id", "course_id", "title", "max_resubmissions", "due_date_utc", "late_penalty_percent", "status"], paths["assignments"])

    paths["rubrics"] = output_dir / "rubrics.json"
    export_to_json(sorted(rubrics, key=lambda x: x.rubric_id), ["rubric_id", "assignment_id", "title", "total_points", "version"], paths["rubrics"])

    paths["rubric_criteria"] = output_dir / "rubric_criteria.json"
    export_to_json(sorted(rubric_criteria, key=lambda x: x.criterion_id), ["criterion_id", "rubric_id", "title", "description", "max_points", "weight"], paths["rubric_criteria"])

    paths["submissions"] = output_dir / "submissions.json"
    export_to_json(sorted(submissions, key=lambda x: x.submission_id), ["submission_id", "assignment_id", "learner_id", "version_number", "submitted_at_utc", "is_late", "hours_late", "status"], paths["submissions"])

    paths["submission_artifacts"] = output_dir / "submission_artifacts.json"
    export_to_json(sorted(artifacts, key=lambda x: x.artifact_id), ["artifact_id", "submission_id", "file_name", "file_type", "file_size_kb", "file_sha256"], paths["submission_artifacts"])

    paths["grades"] = output_dir / "grades.json"
    export_to_json(sorted(grades, key=lambda x: x.grade_id), ["grade_id", "submission_id", "raw_score", "late_penalty_applied", "final_score", "graded_by", "graded_at_utc"], paths["grades"])

    paths["feedback"] = output_dir / "feedback.json"
    export_to_json(sorted(feedbacks, key=lambda x: x.feedback_id), ["feedback_id", "grade_id", "criterion_id", "points_awarded", "instructor_comment"], paths["feedback"])

    paths["resubmissions"] = output_dir / "resubmissions.json"
    export_to_json(sorted(resubmissions, key=lambda x: x.resubmission_id), ["resubmission_id", "previous_submission_id", "new_submission_id", "requested_at_utc", "reason", "is_allowed_by_policy"], paths["resubmissions"])

    paths["appeals"] = output_dir / "appeals.json"
    export_to_json(sorted(appeals, key=lambda x: x.appeal_id), ["appeal_id", "grade_id", "learner_id", "submitted_at_utc", "reason", "status", "original_score", "updated_score", "audit_logged"], paths["appeals"])

    paths["ground_truth"] = ground_truth_path
    export_to_json(sorted(ground_truth, key=lambda x: x.issue_id), ["issue_id", "issue_type", "entity_name", "record_id", "field_name", "expected_value", "actual_value", "description"], ground_truth_path)

    return paths


def generate_source_manifest(
    manifest_path: Path,
    seed: int,
    scale_name: str,
    operational_csv_paths: Dict[str, Path],
    ground_truth_path: Path,
    sqlite_db_path: Path,
) -> Path:
    """Generates source manifest documenting lawful provenance, checksums, and actor roles."""
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    def file_sha256(p: Path) -> str:
        if not p.exists():
            return ""
        hasher = hashlib.sha256()
        with open(p, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    checksums = {}
    for name, p in operational_csv_paths.items():
        checksums[f"{name}.csv"] = file_sha256(p)
    if ground_truth_path.exists():
        checksums["ground_truth.csv"] = file_sha256(ground_truth_path)

    manifest_data = {
        "dataset_name": "assignment-lifecycle-synthetic-benchmark",
        "version": "1.0.0",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "seed": seed,
        "scale_profile": scale_name,
        "provenance": {
            "origin": "100% Fully Synthetic Data Generation Engine",
            "lawful_basis": (
                "Constructed via algorithmic state machines and deterministic random distributions. "
                "No private student records, proprietary LMS databases, or scraped PII were collected or used. "
                "Complies with educational privacy (FERPA/GDPR) and ethical synthetic benchmark standards."
            ),
            "license": "MIT Open Source License",
            "reproducibility": "Deterministic - identical SHA-256 hashes generated across environments with fixed seed.",
        },
        "primary_actors_and_roles": {
            "Learner": "Submits drafts, inspects grades and feedback, requests draft resubmission under policy, and petitions appeals.",
            "Instructor": "Publishes assignments with due dates and rubric criteria, grades submissions, and delivers criterion feedback.",
            "Academic Administrator": "Manages course catalogs, terms, department schedules, and oversees appeal arbitrations.",
            "Support Staff": "Diagnoses enrollment boundary conditions and troubleshoots artifact submission issues.",
            "Platform Administrator": "Configures system security, provisions term calendars, and audits event logging compliance.",
        },
        "files_and_checksums": checksums,
        "sqlite_database": {
            "path": (
                str(sqlite_db_path.relative_to(Path.cwd())).replace("\\", "/")
                if sqlite_db_path.is_absolute() and Path.cwd() in sqlite_db_path.parents
                else str(sqlite_db_path).replace("\\", "/")
            ),
            "status": "Available with active foreign key enforcement and relational indexes",
        },
    }

    with open(manifest_path, mode="w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)

    return manifest_path


def export_csvs_to_sqlite(data_dir: Path, db_path: Path) -> None:
    """Reads CSVs from data_dir and creates/seeds an SQLite database with tables, constraints, and indexes."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = ON;")

    # Schema definition
    schema_sql = """
    CREATE TABLE courses (
        course_id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        department TEXT NOT NULL,
        term TEXT NOT NULL,
        start_date_utc TEXT NOT NULL,
        end_date_utc TEXT NOT NULL,
        status TEXT NOT NULL
    );

    CREATE TABLE learners (
        learner_id TEXT PRIMARY KEY,
        full_name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        timezone TEXT NOT NULL,
        enrolled_date_utc TEXT NOT NULL,
        status TEXT NOT NULL
    );

    CREATE TABLE enrollments (
        enrollment_id TEXT PRIMARY KEY,
        course_id TEXT NOT NULL,
        learner_id TEXT NOT NULL,
        enrolled_at_utc TEXT NOT NULL,
        status TEXT NOT NULL,
        FOREIGN KEY (course_id) REFERENCES courses (course_id),
        FOREIGN KEY (learner_id) REFERENCES learners (learner_id),
        UNIQUE (course_id, learner_id)
    );

    CREATE TABLE assignments (
        assignment_id TEXT PRIMARY KEY,
        course_id TEXT NOT NULL,
        title TEXT NOT NULL,
        max_resubmissions INTEGER NOT NULL,
        due_date_utc TEXT NOT NULL,
        late_penalty_percent REAL NOT NULL,
        status TEXT NOT NULL,
        FOREIGN KEY (course_id) REFERENCES courses (course_id)
    );

    CREATE TABLE rubrics (
        rubric_id TEXT PRIMARY KEY,
        assignment_id TEXT UNIQUE NOT NULL,
        title TEXT NOT NULL,
        total_points REAL NOT NULL,
        version INTEGER NOT NULL,
        FOREIGN KEY (assignment_id) REFERENCES assignments (assignment_id)
    );

    CREATE TABLE rubric_criteria (
        criterion_id TEXT PRIMARY KEY,
        rubric_id TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        max_points REAL NOT NULL,
        weight REAL NOT NULL,
        FOREIGN KEY (rubric_id) REFERENCES rubrics (rubric_id)
    );

    CREATE TABLE submissions (
        submission_id TEXT PRIMARY KEY,
        assignment_id TEXT NOT NULL,
        learner_id TEXT NOT NULL,
        version_number INTEGER NOT NULL,
        submitted_at_utc TEXT NOT NULL,
        is_late TEXT NOT NULL,
        hours_late REAL NOT NULL,
        status TEXT NOT NULL,
        FOREIGN KEY (assignment_id) REFERENCES assignments (assignment_id),
        FOREIGN KEY (learner_id) REFERENCES learners (learner_id)
    );

    CREATE TABLE submission_artifacts (
        artifact_id TEXT PRIMARY KEY,
        submission_id TEXT NOT NULL,
        file_name TEXT NOT NULL,
        file_type TEXT NOT NULL,
        file_size_kb INTEGER NOT NULL,
        file_sha256 TEXT NOT NULL,
        FOREIGN KEY (submission_id) REFERENCES submissions (submission_id)
    );

    CREATE TABLE grades (
        grade_id TEXT PRIMARY KEY,
        submission_id TEXT UNIQUE NOT NULL,
        raw_score REAL NOT NULL,
        late_penalty_applied REAL NOT NULL,
        final_score REAL NOT NULL,
        graded_by TEXT NOT NULL,
        graded_at_utc TEXT NOT NULL,
        FOREIGN KEY (submission_id) REFERENCES submissions (submission_id)
    );

    CREATE TABLE feedback (
        feedback_id TEXT PRIMARY KEY,
        grade_id TEXT NOT NULL,
        criterion_id TEXT NOT NULL,
        points_awarded REAL NOT NULL,
        instructor_comment TEXT NOT NULL,
        FOREIGN KEY (grade_id) REFERENCES grades (grade_id),
        FOREIGN KEY (criterion_id) REFERENCES rubric_criteria (criterion_id)
    );

    CREATE TABLE resubmissions (
        resubmission_id TEXT PRIMARY KEY,
        previous_submission_id TEXT NOT NULL,
        new_submission_id TEXT NOT NULL,
        requested_at_utc TEXT NOT NULL,
        reason TEXT NOT NULL,
        is_allowed_by_policy TEXT NOT NULL,
        FOREIGN KEY (previous_submission_id) REFERENCES submissions (submission_id),
        FOREIGN KEY (new_submission_id) REFERENCES submissions (submission_id)
    );

    CREATE TABLE appeals (
        appeal_id TEXT PRIMARY KEY,
        grade_id TEXT NOT NULL,
        learner_id TEXT NOT NULL,
        submitted_at_utc TEXT NOT NULL,
        reason TEXT NOT NULL,
        status TEXT NOT NULL,
        original_score REAL NOT NULL,
        updated_score REAL,
        audit_logged TEXT NOT NULL,
        FOREIGN KEY (grade_id) REFERENCES grades (grade_id),
        FOREIGN KEY (learner_id) REFERENCES learners (learner_id)
    );

    -- Indices for high performance queries
    CREATE INDEX idx_enrollments_course ON enrollments(course_id);
    CREATE INDEX idx_enrollments_learner ON enrollments(learner_id);
    CREATE INDEX idx_assignments_course ON assignments(course_id);
    CREATE INDEX idx_submissions_assignment ON submissions(assignment_id);
    CREATE INDEX idx_submissions_learner ON submissions(learner_id);
    CREATE INDEX idx_grades_submission ON grades(submission_id);
    CREATE INDEX idx_feedback_grade ON feedback(grade_id);
    CREATE INDEX idx_appeals_grade ON appeals(grade_id);
    """
    cur.executescript(schema_sql)

    csv_table_mapping = [
        ("courses.csv", "courses", ["course_id", "title", "department", "term", "start_date_utc", "end_date_utc", "status"]),
        ("learners.csv", "learners", ["learner_id", "full_name", "email", "timezone", "enrolled_date_utc", "status"]),
        ("enrollments.csv", "enrollments", ["enrollment_id", "course_id", "learner_id", "enrolled_at_utc", "status"]),
        ("assignments.csv", "assignments", ["assignment_id", "course_id", "title", "max_resubmissions", "due_date_utc", "late_penalty_percent", "status"]),
        ("rubrics.csv", "rubrics", ["rubric_id", "assignment_id", "title", "total_points", "version"]),
        ("rubric_criteria.csv", "rubric_criteria", ["criterion_id", "rubric_id", "title", "description", "max_points", "weight"]),
        ("submissions.csv", "submissions", ["submission_id", "assignment_id", "learner_id", "version_number", "submitted_at_utc", "is_late", "hours_late", "status"]),
        ("submission_artifacts.csv", "submission_artifacts", ["artifact_id", "submission_id", "file_name", "file_type", "file_size_kb", "file_sha256"]),
        ("grades.csv", "grades", ["grade_id", "submission_id", "raw_score", "late_penalty_applied", "final_score", "graded_by", "graded_at_utc"]),
        ("feedback.csv", "feedback", ["feedback_id", "grade_id", "criterion_id", "points_awarded", "instructor_comment"]),
        ("resubmissions.csv", "resubmissions", ["resubmission_id", "previous_submission_id", "new_submission_id", "requested_at_utc", "reason", "is_allowed_by_policy"]),
        ("appeals.csv", "appeals", ["appeal_id", "grade_id", "learner_id", "submitted_at_utc", "reason", "status", "original_score", "updated_score", "audit_logged"]),
    ]

    for csv_file, table_name, cols in csv_table_mapping:
        file_path = data_dir / csv_file
        if not file_path.exists():
            continue
        with open(file_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = []
            for r in reader:
                row_vals = []
                for c in cols:
                    val = r.get(c, "")
                    if val == "" and c == "updated_score":
                        row_vals.append(None)
                    else:
                        row_vals.append(val)
                rows.append(row_vals)

            placeholders = ",".join(["?"] * len(cols))
            col_names = ",".join(cols)
            cur.executemany(
                f"INSERT INTO {table_name} ({col_names}) VALUES ({placeholders})",
                rows,
            )

    conn.commit()
    conn.close()
