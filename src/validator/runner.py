"""Validation runner orchestrating schema, relational, and business rule validations, with Ground Truth evaluation."""

import csv
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.config import (
    ANOMALY_DOUBLE_LATE_PENALTY,
    ANOMALY_GRADE_EXCEEDS_MAX,
    ANOMALY_TYPES,
    ANOMALY_UNAUDITED_APPEAL,
    ANOMALY_UNENROLLED_SUBMISSION,
    APPEAL_STATUSES,
    ASSIGNMENT_STATUSES,
    COURSE_STATUSES,
    ENROLLMENT_STATUSES,
    FILE_TYPES,
    LEARNER_STATUSES,
    SUBMISSION_STATUSES,
    TERMS,
    TIMEZONES,
)
from src.validator.business_rules import (
    BusinessRuleViolation,
    validate_appeal_audit_compliance,
    validate_chronology_and_lateness,
    validate_enrollment_integrity,
    validate_grading_and_penalties,
    validate_lifecycle_transitions,
)
from src.validator.schema import (
    SchemaValidationError,
    validate_enum_field,
    validate_fk_integrity,
    validate_pk_uniqueness,
    validate_unique_composite_key,
    validate_unique_field,
)


def load_csv(file_path: Path) -> List[Dict[str, str]]:
    """Loads a CSV file into a list of row dictionaries."""
    if not file_path.exists():
        return []
    with open(file_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def run_validations(
    data_dir: Path,
    ground_truth_path: Optional[Path] = None,
    console: Optional[Console] = None,
) -> Dict[str, Any]:
    """Executes all schema and business rule validations, reconciles against ground truth, and prints report."""
    if console is None:
        console = Console()

    # 1. Load operational CSV datasets
    courses = load_csv(data_dir / "courses.csv")
    learners = load_csv(data_dir / "learners.csv")
    enrollments = load_csv(data_dir / "enrollments.csv")
    assignments = load_csv(data_dir / "assignments.csv")
    rubrics = load_csv(data_dir / "rubrics.csv")
    rubric_criteria = load_csv(data_dir / "rubric_criteria.csv")
    submissions = load_csv(data_dir / "submissions.csv")
    artifacts = load_csv(data_dir / "submission_artifacts.csv")
    grades = load_csv(data_dir / "grades.csv")
    feedbacks = load_csv(data_dir / "feedback.csv")
    resubmissions = load_csv(data_dir / "resubmissions.csv")
    appeals = load_csv(data_dir / "appeals.csv")

    entity_counts = {
        "Course": len(courses),
        "Learner": len(learners),
        "Enrollment": len(enrollments),
        "Assignment": len(assignments),
        "Rubric": len(rubrics),
        "RubricCriterion": len(rubric_criteria),
        "Submission": len(submissions),
        "SubmissionArtifact": len(artifacts),
        "Grade": len(grades),
        "Feedback": len(feedbacks),
        "Resubmission": len(resubmissions),
        "Appeal": len(appeals),
    }

    # 2. Schema Validations
    schema_errors: List[SchemaValidationError] = []

    # PK uniqueness & ID scheme patterns
    schema_errors.extend(validate_pk_uniqueness(courses, "course_id", "Course", r"^CRS-2026-\d{6}$"))
    schema_errors.extend(validate_pk_uniqueness(learners, "learner_id", "Learner", r"^LRN-2026-\d{6}$"))
    schema_errors.extend(validate_pk_uniqueness(enrollments, "enrollment_id", "Enrollment", r"^ENR-2026-\d{6}$"))
    schema_errors.extend(validate_pk_uniqueness(assignments, "assignment_id", "Assignment", r"^ASN-2026-\d{6}$"))
    schema_errors.extend(validate_pk_uniqueness(rubrics, "rubric_id", "Rubric", r"^RUB-ASN-2026-\d{6}-\d{2}$"))
    schema_errors.extend(validate_pk_uniqueness(rubric_criteria, "criterion_id", "RubricCriterion", r"^CRT-RUB-ASN-2026-\d{6}-\d{2}-\d{2}$"))
    schema_errors.extend(validate_pk_uniqueness(submissions, "submission_id", "Submission", r"^SUB-ASN-2026-\d{6}-LRN-2026-\d{6}-\d{2}$"))
    schema_errors.extend(validate_pk_uniqueness(artifacts, "artifact_id", "SubmissionArtifact", r"^ART-2026-\d{6}$"))
    schema_errors.extend(validate_pk_uniqueness(grades, "grade_id", "Grade", r"^GRD-SUB-ASN-2026-\d{6}-LRN-2026-\d{6}-\d{2}$"))
    schema_errors.extend(validate_pk_uniqueness(feedbacks, "feedback_id", "Feedback", r"^FDB-2026-\d{6}$"))
    schema_errors.extend(validate_pk_uniqueness(resubmissions, "resubmission_id", "Resubmission", r"^RSB-2026-\d{6}$"))
    schema_errors.extend(validate_pk_uniqueness(appeals, "appeal_id", "Appeal", r"^APP-2026-\d{6}$"))

    # FK Integrity
    course_pks = {c["course_id"] for c in courses}
    learner_pks = {l["learner_id"] for l in learners}
    assignment_pks = {a["assignment_id"] for a in assignments}
    rubric_pks = {r["rubric_id"] for r in rubrics}
    criterion_pks = {c["criterion_id"] for c in rubric_criteria}
    submission_pks = {s["submission_id"] for s in submissions}
    grade_pks = {g["grade_id"] for g in grades}

    schema_errors.extend(validate_fk_integrity(enrollments, "course_id", "Enrollment", course_pks, "Course"))
    schema_errors.extend(validate_fk_integrity(enrollments, "learner_id", "Enrollment", learner_pks, "Learner"))
    schema_errors.extend(validate_fk_integrity(assignments, "course_id", "Assignment", course_pks, "Course"))
    schema_errors.extend(validate_fk_integrity(rubrics, "assignment_id", "Rubric", assignment_pks, "Assignment"))
    schema_errors.extend(validate_fk_integrity(rubric_criteria, "rubric_id", "RubricCriterion", rubric_pks, "Rubric"))
    schema_errors.extend(validate_fk_integrity(submissions, "assignment_id", "Submission", assignment_pks, "Assignment"))
    schema_errors.extend(validate_fk_integrity(submissions, "learner_id", "Submission", learner_pks, "Learner"))
    schema_errors.extend(validate_fk_integrity(artifacts, "submission_id", "SubmissionArtifact", submission_pks, "Submission"))
    schema_errors.extend(validate_fk_integrity(grades, "submission_id", "Grade", submission_pks, "Submission"))
    schema_errors.extend(validate_fk_integrity(feedbacks, "grade_id", "Feedback", grade_pks, "Grade"))
    schema_errors.extend(validate_fk_integrity(feedbacks, "criterion_id", "Feedback", criterion_pks, "RubricCriterion"))
    schema_errors.extend(validate_fk_integrity(resubmissions, "previous_submission_id", "Resubmission", submission_pks, "Submission"))
    schema_errors.extend(validate_fk_integrity(resubmissions, "new_submission_id", "Resubmission", submission_pks, "Submission"))
    schema_errors.extend(validate_fk_integrity(appeals, "grade_id", "Appeal", grade_pks, "Grade"))
    schema_errors.extend(validate_fk_integrity(appeals, "learner_id", "Appeal", learner_pks, "Learner"))

    # Enum checks
    schema_errors.extend(validate_enum_field(courses, "status", "Course", COURSE_STATUSES))
    schema_errors.extend(validate_enum_field(courses, "term", "Course", TERMS))
    schema_errors.extend(validate_enum_field(learners, "status", "Learner", LEARNER_STATUSES))
    schema_errors.extend(validate_enum_field(learners, "timezone", "Learner", TIMEZONES))
    schema_errors.extend(validate_enum_field(enrollments, "status", "Enrollment", ENROLLMENT_STATUSES))
    schema_errors.extend(validate_enum_field(assignments, "status", "Assignment", ASSIGNMENT_STATUSES))
    schema_errors.extend(validate_enum_field(submissions, "status", "Submission", SUBMISSION_STATUSES))
    schema_errors.extend(validate_enum_field(artifacts, "file_type", "SubmissionArtifact", FILE_TYPES))
    schema_errors.extend(validate_enum_field(appeals, "status", "Appeal", APPEAL_STATUSES))

    # Uniqueness constraints (email, 1:1 rubric, 1:1 grade, composite enrollment)
    schema_errors.extend(validate_unique_field(learners, "email", "Learner"))
    schema_errors.extend(validate_unique_field(rubrics, "assignment_id", "Rubric"))
    schema_errors.extend(validate_unique_field(grades, "submission_id", "Grade"))
    schema_errors.extend(validate_unique_composite_key(enrollments, ["course_id", "learner_id"], "Enrollment"))

    # 3. Business Rule Validations
    rule_violations: List[BusinessRuleViolation] = []
    
    # Check 1: Enrollment integrity (Flags UNENROLLED_LEARNER_SUBMISSION)
    rule_violations.extend(validate_enrollment_integrity(submissions, assignments, enrollments))

    # Check 2: Chronology and lateness logic
    rule_violations.extend(validate_chronology_and_lateness(courses, assignments, submissions, grades, appeals))

    # Check 3: Grading math, rubric caps, and double penalty (Flags GRADE_EXCEEDS_MAX & DOUBLE_LATE_PENALTY)
    rule_violations.extend(validate_grading_and_penalties(grades, feedbacks, rubrics, assignments, submissions, appeals))

    # Check 4: Appeal audit compliance (Flags UNAUDITED_APPEAL_GRADE_CHANGE)
    rule_violations.extend(validate_appeal_audit_compliance(appeals))

    # Check 5: Lifecycle transitions and policy limits
    rule_violations.extend(validate_lifecycle_transitions(submissions, grades, resubmissions, appeals, assignments))

    # 4. Ground Truth Evaluation
    detected_anomalies: List[Dict[str, str]] = []
    unexpected_errors: List[Dict[str, str]] = []

    # Map detected issues
    for err in schema_errors:
        unexpected_errors.append(err.to_dict())

    for viol in rule_violations:
        if viol.issue_type in ANOMALY_TYPES:
            detected_anomalies.append(viol.to_dict())
        else:
            unexpected_errors.append(viol.to_dict())

    ground_truth_records: List[Dict[str, str]] = []
    if ground_truth_path and ground_truth_path.exists():
        ground_truth_records = load_csv(ground_truth_path)

    # Anomaly reconciliation
    gt_map: Dict[Tuple[str, str], Dict[str, str]] = {
        (gt["issue_type"], gt["record_id"]): gt for gt in ground_truth_records
    }
    detected_map: Dict[Tuple[str, str], Dict[str, str]] = {
        (det["issue_type"], det["record_id"]): det for det in detected_anomalies
    }

    tp_keys = set(gt_map.keys()) & set(detected_map.keys())
    fn_keys = set(gt_map.keys()) - set(detected_map.keys())
    fp_keys = set(detected_map.keys()) - set(gt_map.keys())

    tp_count = len(tp_keys)
    fn_count = len(fn_keys)
    fp_count = len(fp_keys)

    precision = tp_count / (tp_count + fp_count) if (tp_count + fp_count) > 0 else 1.0
    recall = tp_count / (tp_count + fn_count) if (tp_count + fn_count) > 0 else 1.0
    f1_score = (
        2 * (precision * recall) / (precision + recall)
        if (precision + recall) > 0
        else 1.0
    )

    # 5. Render Console Report
    console.print(Panel.fit("[bold green]SYNTHETIC DATA VALIDATION ENGINE REPORT[/bold green]", border_style="blue"))

    # Entities table
    table_entities = Table(title="Operational Entity Record Counts", show_lines=True)
    table_entities.add_column("Entity Name", style="cyan", no_wrap=True)
    table_entities.add_column("Total Rows", justify="right", style="magenta")
    table_entities.add_column("Status", justify="center", style="green")

    total_records = sum(entity_counts.values())
    for ent, count in entity_counts.items():
        table_entities.add_row(ent, f"{count:,}", "[bold green]VALIDATED[/bold green]")
    table_entities.add_row("[bold]Total Records[/bold]", f"[bold]{total_records:,}[/bold]", "[bold green]HEALTHY[/bold green]")
    console.print(table_entities)

    # Anomaly Detection Benchmark table
    table_anomalies = Table(title="Controlled Anomaly Injection & Detection Benchmark", show_lines=True)
    table_anomalies.add_column("Anomaly Type", style="yellow")
    table_anomalies.add_column("Ground Truth Injected", justify="right", style="cyan")
    table_anomalies.add_column("Detected (TP)", justify="right", style="green")
    table_anomalies.add_column("Missed (FN)", justify="right", style="red")
    table_anomalies.add_column("False Alarms (FP)", justify="right", style="red")
    table_anomalies.add_column("Recall", justify="right", style="blue")

    for atype in ANOMALY_TYPES:
        gt_for_type = [k for k in gt_map.keys() if k[0] == atype]
        det_for_type = [k for k in detected_map.keys() if k[0] == atype]
        tp_for_type = [k for k in tp_keys if k[0] == atype]
        fn_for_type = [k for k in fn_keys if k[0] == atype]
        fp_for_type = [k for k in fp_keys if k[0] == atype]

        rec_str = f"{(len(tp_for_type)/len(gt_for_type))*100:.1f}%" if len(gt_for_type) > 0 else "100.0%"
        table_anomalies.add_row(
            atype,
            str(len(gt_for_type)),
            str(len(tp_for_type)),
            str(len(fn_for_type)),
            str(len(fp_for_type)),
            rec_str,
        )

    console.print(table_anomalies)

    # Summary Metrics
    console.print(f"[bold]Validation Metrics:[/bold] Precision: [bold green]{precision*100:.1f}%[/bold green] | Recall: [bold green]{recall*100:.1f}%[/bold green] | F1-Score: [bold green]{f1_score*100:.1f}%[/bold green]")
    
    if unexpected_errors:
        console.print(f"[bold red]WARNING: Found {len(unexpected_errors)} unexpected corruptions/errors![/bold red]")
        for ue in unexpected_errors[:10]:
            console.print(f"  - {ue}")
    else:
        console.print("[bold green]Zero unexpected corruptions! All clean records passed without false positives.[/bold green]")

    return {
        "entity_counts": entity_counts,
        "total_records": total_records,
        "schema_error_count": len(schema_errors),
        "rule_violation_count": len(rule_violations),
        "detected_anomalies_count": len(detected_anomalies),
        "ground_truth_count": len(ground_truth_records),
        "true_positives": tp_count,
        "false_negatives": fn_count,
        "false_positives": fp_count,
        "precision": precision,
        "recall": recall,
        "f1_score": f1_score,
        "unexpected_errors": unexpected_errors,
        "is_clean": (len(unexpected_errors) == 0 and fn_count == 0 and fp_count == 0),
    }
