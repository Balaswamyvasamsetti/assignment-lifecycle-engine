"""Business rule validation: chronology, lateness reconciliation, scoring math, and audit controls."""

from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Set, Tuple

from src.config import (
    ANOMALY_DOUBLE_LATE_PENALTY,
    ANOMALY_GRADE_EXCEEDS_MAX,
    ANOMALY_UNAUDITED_APPEAL,
    ANOMALY_UNENROLLED_SUBMISSION,
)


class BusinessRuleViolation:
    def __init__(
        self,
        issue_type: str,
        entity_name: str,
        record_id: str,
        field_name: str,
        expected_value: str,
        actual_value: str,
        description: str,
    ):
        self.issue_type = issue_type
        self.entity_name = entity_name
        self.record_id = record_id
        self.field_name = field_name
        self.expected_value = expected_value
        self.actual_value = actual_value
        self.description = description

    def to_dict(self) -> Dict[str, str]:
        return {
            "issue_type": self.issue_type,
            "entity_name": self.entity_name,
            "record_id": self.record_id,
            "field_name": self.field_name,
            "expected_value": self.expected_value,
            "actual_value": self.actual_value,
            "description": self.description,
        }


def parse_iso(dt_str: str) -> datetime:
    """Helper to parse ISO-8601 strings into datetime objects."""
    clean_str = dt_str.replace("Z", "+00:00")
    return datetime.fromisoformat(clean_str)


def validate_enrollment_integrity(
    submissions: List[Dict[str, str]],
    assignments: List[Dict[str, str]],
    enrollments: List[Dict[str, str]],
) -> List[BusinessRuleViolation]:
    """Validates that submissions only come from actively enrolled learners in the course."""
    violations: List[BusinessRuleViolation] = []

    asn_course_map = {a["assignment_id"]: a["course_id"] for a in assignments}
    active_enrolled_pairs: Set[Tuple[str, str]] = {
        (e["course_id"], e["learner_id"])
        for e in enrollments
        if e.get("status") == "ACTIVE"
    }

    for sub in submissions:
        sub_id = sub["submission_id"]
        asn_id = sub["assignment_id"]
        l_id = sub["learner_id"]
        course_id = asn_course_map.get(asn_id, "")

        if (course_id, l_id) not in active_enrolled_pairs:
            violations.append(
                BusinessRuleViolation(
                    issue_type=ANOMALY_UNENROLLED_SUBMISSION,
                    entity_name="Submission",
                    record_id=sub_id,
                    field_name="learner_id",
                    expected_value="ACTIVE_ENROLLMENT_REQUIRED",
                    actual_value=l_id,
                    description=(
                        f"Learner {l_id} submitted for assignment {asn_id} in course {course_id} "
                        f"without an active enrollment record."
                    ),
                )
            )

    return violations


def validate_chronology_and_lateness(
    courses: List[Dict[str, str]],
    assignments: List[Dict[str, str]],
    submissions: List[Dict[str, str]],
    grades: List[Dict[str, str]],
    appeals: List[Dict[str, str]],
) -> List[BusinessRuleViolation]:
    """Validates chronological ordering and lateness calculation logic."""
    violations: List[BusinessRuleViolation] = []

    course_dates = {
        c["course_id"]: (parse_iso(c["start_date_utc"]), parse_iso(c["end_date_utc"]))
        for c in courses
    }
    asn_map = {a["assignment_id"]: a for a in assignments}
    sub_map = {s["submission_id"]: s for s in submissions}
    grade_map = {g["grade_id"]: g for g in grades}

    # 1. Assignment due date vs Course dates
    for a in assignments:
        c_dates = course_dates.get(a["course_id"])
        if c_dates:
            c_start, c_end = c_dates
            due_dt = parse_iso(a["due_date_utc"])
            if not (c_start <= due_dt <= c_end):
                violations.append(
                    BusinessRuleViolation(
                        issue_type="CHRONOLOGY_VIOLATION_ASSIGNMENT",
                        entity_name="Assignment",
                        record_id=a["assignment_id"],
                        field_name="due_date_utc",
                        expected_value=f"Between {c_start} and {c_end}",
                        actual_value=str(due_dt),
                        description="Assignment due date falls outside course term boundaries.",
                    )
                )

    # 2. Submission lateness and submission date
    for sub in submissions:
        sub_id = sub["submission_id"]
        asn = asn_map.get(sub["assignment_id"])
        if not asn:
            continue

        sub_dt = parse_iso(sub["submitted_at_utc"])
        due_dt = parse_iso(asn["due_date_utc"])
        is_late_flag = sub["is_late"].strip().lower() in ("true", "1")
        hours_late = float(sub["hours_late"])

        expected_is_late = sub_dt > due_dt
        if is_late_flag != expected_is_late:
            violations.append(
                BusinessRuleViolation(
                    issue_type="LATENESS_FLAG_MISMATCH",
                    entity_name="Submission",
                    record_id=sub_id,
                    field_name="is_late",
                    expected_value=str(expected_is_late),
                    actual_value=str(is_late_flag),
                    description=f"Submission lateness flag does not match due date comparison.",
                )
            )

        if expected_is_late:
            expected_hours = round((sub_dt - due_dt).total_seconds() / 3600.0, 2)
            if abs(hours_late - expected_hours) > 0.1:
                violations.append(
                    BusinessRuleViolation(
                        issue_type="HOURS_LATE_MISCALCULATION",
                        entity_name="Submission",
                        record_id=sub_id,
                        field_name="hours_late",
                        expected_value=f"{expected_hours:.2f}",
                        actual_value=f"{hours_late:.2f}",
                        description="Reported hours_late differs from timestamp difference.",
                    )
                )
        else:
            if hours_late > 0.0:
                violations.append(
                    BusinessRuleViolation(
                        issue_type="ON_TIME_POSITIVE_HOURS_LATE",
                        entity_name="Submission",
                        record_id=sub_id,
                        field_name="hours_late",
                        expected_value="0.0",
                        actual_value=str(hours_late),
                        description="On-time submission must have hours_late == 0.0.",
                    )
                )

    # 3. Grade date vs Submission date
    for g in grades:
        sub = sub_map.get(g["submission_id"])
        if sub:
            sub_dt = parse_iso(sub["submitted_at_utc"])
            graded_dt = parse_iso(g["graded_at_utc"])
            if graded_dt < sub_dt:
                violations.append(
                    BusinessRuleViolation(
                        issue_type="CHRONOLOGY_VIOLATION_GRADE",
                        entity_name="Grade",
                        record_id=g["grade_id"],
                        field_name="graded_at_utc",
                        expected_value=f">= {sub_dt}",
                        actual_value=str(graded_dt),
                        description="Grade timestamp precedes submission timestamp.",
                    )
                )

    # 4. Appeal date vs Grade date
    for app in appeals:
        grd = grade_map.get(app["grade_id"])
        if grd:
            grd_dt = parse_iso(grd["graded_at_utc"])
            app_dt = parse_iso(app["submitted_at_utc"])
            if app_dt < grd_dt:
                violations.append(
                    BusinessRuleViolation(
                        issue_type="CHRONOLOGY_VIOLATION_APPEAL",
                        entity_name="Appeal",
                        record_id=app["appeal_id"],
                        field_name="submitted_at_utc",
                        expected_value=f">= {grd_dt}",
                        actual_value=str(app_dt),
                        description="Appeal timestamp precedes grade timestamp.",
                    )
                )

    return violations


def validate_grading_and_penalties(
    grades: List[Dict[str, str]],
    feedbacks: List[Dict[str, str]],
    rubrics: List[Dict[str, str]],
    assignments: List[Dict[str, str]],
    submissions: List[Dict[str, str]],
    appeals: List[Dict[str, str]],
) -> List[BusinessRuleViolation]:
    """Validates rubric score reconciliation, max point boundaries, and late penalty calculations."""
    violations: List[BusinessRuleViolation] = []

    asn_map = {a["assignment_id"]: a for a in assignments}
    sub_map = {s["submission_id"]: s for s in submissions}
    rubric_map = {r["assignment_id"]: r for r in rubrics}

    # Group feedback points by grade_id
    fdb_sum_by_grade: Dict[str, float] = defaultdict(float)
    for f in feedbacks:
        fdb_sum_by_grade[f["grade_id"]] += float(f["points_awarded"])

    # Approved appeals mapping to ignore normal final_score discrepancy if updated
    approved_appeal_grades: Set[str] = {
        app["grade_id"]
        for app in appeals
        if app["status"] == "APPROVED" and app.get("updated_score") not in ("", None)
    }

    for g in grades:
        g_id = g["grade_id"]
        sub = sub_map.get(g["submission_id"])
        if not sub:
            continue

        asn = asn_map.get(sub["assignment_id"])
        if not asn:
            continue

        rubric = rubric_map.get(asn["assignment_id"])
        total_rubric_points = float(rubric["total_points"]) if rubric else 100.0

        raw_score = float(g["raw_score"])
        late_penalty_applied = float(g["late_penalty_applied"])
        final_score = float(g["final_score"])
        is_late = sub["is_late"].strip().lower() in ("true", "1")
        late_rate = float(asn["late_penalty_percent"]) / 100.0

        # Check 1: Feedback reconciliation: raw_score == sum(criterion_scores)
        fb_sum = round(fdb_sum_by_grade.get(g_id, 0.0), 2)
        if abs(raw_score - fb_sum) > 0.05:
            violations.append(
                BusinessRuleViolation(
                    issue_type="FEEDBACK_SCORE_RECONCILIATION_ERROR",
                    entity_name="Grade",
                    record_id=g_id,
                    field_name="raw_score",
                    expected_value=f"{fb_sum:.2f}",
                    actual_value=f"{raw_score:.2f}",
                    description=f"Raw score does not match sum of rubric criterion feedback points.",
                )
            )

        # Check 2: Raw score exceeds rubric max points (GRADE_EXCEEDS_MAX)
        if raw_score > total_rubric_points:
            violations.append(
                BusinessRuleViolation(
                    issue_type=ANOMALY_GRADE_EXCEEDS_MAX,
                    entity_name="Grade",
                    record_id=g_id,
                    field_name="raw_score",
                    expected_value=f"<= {total_rubric_points:.1f}",
                    actual_value=f"{raw_score:.2f}",
                    description=f"Grade raw_score ({raw_score:.2f}) exceeds rubric max ({total_rubric_points:.1f}).",
                )
            )

        # Check 3: Late penalty applied correctness (DOUBLE_LATE_PENALTY)
        expected_penalty = round(raw_score * late_rate, 2) if is_late else 0.0
        
        # If penalty differs significantly from expected
        if abs(late_penalty_applied - expected_penalty) > 0.05:
            if abs(late_penalty_applied - round(expected_penalty * 2.0, 2)) < 0.1 and late_penalty_applied > 0.0:
                violations.append(
                    BusinessRuleViolation(
                        issue_type=ANOMALY_DOUBLE_LATE_PENALTY,
                        entity_name="Grade",
                        record_id=g_id,
                        field_name="late_penalty_applied",
                        expected_value=f"{expected_penalty:.2f}",
                        actual_value=f"{late_penalty_applied:.2f}",
                        description=f"Late penalty applied was deducted twice on late submission.",
                    )
                )
            else:
                violations.append(
                    BusinessRuleViolation(
                        issue_type="INVALID_LATE_PENALTY_APPLIED",
                        entity_name="Grade",
                        record_id=g_id,
                        field_name="late_penalty_applied",
                        expected_value=f"{expected_penalty:.2f}",
                        actual_value=f"{late_penalty_applied:.2f}",
                        description=f"Late penalty applied does not match penalty policy.",
                    )
                )

        # Check 4: Final score reconciliation (for grades not updated by approved appeal)
        if g_id not in approved_appeal_grades:
            expected_final = round(max(0.0, raw_score - late_penalty_applied), 2)
            if abs(final_score - expected_final) > 0.05:
                violations.append(
                    BusinessRuleViolation(
                        issue_type="FINAL_SCORE_RECONCILIATION_ERROR",
                        entity_name="Grade",
                        record_id=g_id,
                        field_name="final_score",
                        expected_value=f"{expected_final:.2f}",
                        actual_value=f"{final_score:.2f}",
                        description=f"Final score does not match raw_score minus late_penalty_applied.",
                    )
                )

    return violations


def validate_appeal_audit_compliance(
    appeals: List[Dict[str, str]],
) -> List[BusinessRuleViolation]:
    """Validates that any approved appeal altering grades must have audit_logged == True."""
    violations: List[BusinessRuleViolation] = []

    for app in appeals:
        app_id = app["appeal_id"]
        status = app.get("status", "").strip()
        updated_score_str = app.get("updated_score", "").strip()
        audit_logged_str = app.get("audit_logged", "").strip().lower()
        audit_logged = audit_logged_str in ("true", "1")

        if status == "APPROVED" and updated_score_str != "":
            if not audit_logged:
                violations.append(
                    BusinessRuleViolation(
                        issue_type=ANOMALY_UNAUDITED_APPEAL,
                        entity_name="Appeal",
                        record_id=app_id,
                        field_name="audit_logged",
                        expected_value="True",
                        actual_value="False",
                        description=f"Appeal {app_id} was APPROVED and modified score but audit_logged is False.",
                    )
                )

    return violations
