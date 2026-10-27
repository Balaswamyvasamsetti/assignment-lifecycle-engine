"""Lifecycle event generator for Resubmissions and Appeals."""

import hashlib
import random
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from src.config import FILE_TYPES, ScaleConfig
from src.models import (
    Appeal,
    Assignment,
    Feedback,
    Grade,
    Resubmission,
    RubricCriterion,
    Submission,
    SubmissionArtifact,
)

RESUBMISSION_REASONS = [
    "Incorporated instructor feedback on architecture and refactored core classes.",
    "Corrected edge case bug identified in criterion 1 feedback.",
    "Added additional integration test suites to address test coverage remarks.",
    "Fixed memory leak in concurrency worker thread.",
    "Resolved linting warnings and updated README API documentation.",
]

APPEAL_REASONS = [
    "Submitted passing unit test logs demonstrating that the edge case was indeed handled.",
    "Clarified architecture documentation in section 4.2 which addresses criterion 2 deductions.",
    "Requested re-evaluation of late penalty due to university LMS outage.",
    "Pointed out that automated test runner timed out due to environment lag, manual run succeeds.",
    "Submitted clarification regarding algorithmic complexity in the analysis write-up.",
]


def generate_lifecycle_data(
    config: ScaleConfig,
    assignments: List[Assignment],
    submissions: List[Submission],
    artifacts: List[SubmissionArtifact],
    grades: List[Grade],
    feedbacks: List[Feedback],
    rubric_criteria: List[RubricCriterion],
    rng: random.Random,
) -> Tuple[
    List[Resubmission],
    List[Appeal],
    List[Submission],
    List[SubmissionArtifact],
    List[Grade],
    List[Feedback],
]:
    """Generates Resubmission and Appeal lifecycle records, appending new submissions/grades as needed."""

    asn_by_id: Dict[str, Assignment] = {a.assignment_id: a for a in assignments}
    grade_by_sub_id: Dict[str, Grade] = {g.submission_id: g for g in grades}
    criteria_by_rubric: Dict[str, List[RubricCriterion]] = {}
    for crit in rubric_criteria:
        criteria_by_rubric.setdefault(crit.rubric_id, []).append(crit)

    resubmissions: List[Resubmission] = []
    appeals: List[Appeal] = []

    resubmission_counter = 1
    appeal_counter = 1
    artifact_counter = len(artifacts) + 1
    feedback_counter = len(feedbacks) + 1

    # 1. Generate Resubmissions (for version 1 submissions where assignment allows resubmissions)
    candidates_for_resubmission = [
        s for s in submissions
        if s.version_number == 1 and asn_by_id[s.assignment_id].max_resubmissions >= 1
    ]

    # Target ~10-15% resubmission rate
    target_resubmissions = max(2, int(len(candidates_for_resubmission) * 0.12))
    selected_for_resub = candidates_for_resubmission[:target_resubmissions]

    for prev_sub in selected_for_resub:
        asn = asn_by_id[prev_sub.assignment_id]
        prev_grade = grade_by_sub_id.get(prev_sub.submission_id)
        if not prev_grade:
            continue

        prev_sub.status = "RESUBMITTED"
        prev_graded_dt = datetime.fromisoformat(prev_grade.graded_at_utc.replace("Z", "+00:00"))
        
        # Resubmission requested 6 to 36 hours after previous grade
        req_dt = prev_graded_dt + timedelta(hours=rng.uniform(6.0, 36.0))
        new_version = 2
        new_sub_id = f"SUB-{asn.assignment_id}-{prev_sub.learner_id}-{new_version:02d}"

        # Resubmission submitted shortly after request (e.g. 2 to 24 hours later)
        new_sub_dt = req_dt + timedelta(hours=rng.uniform(2.0, 24.0))
        
        # Resubmission timing relative to due date
        due_dt = datetime.fromisoformat(asn.due_date_utc.replace("Z", "+00:00"))
        is_late = new_sub_dt > due_dt
        hours_late = round((new_sub_dt - due_dt).total_seconds() / 3600.0, 2) if is_late else 0.0

        new_sub = Submission(
            submission_id=new_sub_id,
            assignment_id=asn.assignment_id,
            learner_id=prev_sub.learner_id,
            version_number=new_version,
            submitted_at_utc=new_sub_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            is_late=is_late,
            hours_late=hours_late,
            status="GRADED",
        )
        submissions.append(new_sub)

        # Resubmission artifact
        art_id = f"ART-2026-{artifact_counter:06d}"
        artifact_counter += 1
        f_type = rng.choice(FILE_TYPES)
        f_name = f"solution_v2_final.{f_type}"
        f_size = rng.randint(50, 15000)
        f_hash = hashlib.sha256(f"{art_id}-{new_sub_id}-{f_name}".encode("utf-8")).hexdigest()
        artifacts.append(
            SubmissionArtifact(
                artifact_id=art_id,
                submission_id=new_sub_id,
                file_name=f_name,
                file_type=f_type,
                file_size_kb=f_size,
                file_sha256=f_hash,
            )
        )

        # Resubmission Grade & Feedback (improved score)
        new_grade_id = f"GRD-{new_sub_id}"
        new_graded_dt = new_sub_dt + timedelta(hours=rng.uniform(4.0, 24.0))
        rubric_id = f"RUB-{asn.assignment_id}-01"
        crit_list = criteria_by_rubric.get(rubric_id, [])

        total_raw_score = 0.0
        for crit in crit_list:
            fdb_id = f"FDB-2026-{feedback_counter:06d}"
            feedback_counter += 1
            # Higher score on resubmission
            pct = rng.uniform(0.85, 1.0)
            pts = round(min(crit.max_points, crit.max_points * pct), 2)
            total_raw_score += pts

            feedbacks.append(
                Feedback(
                    feedback_id=fdb_id,
                    grade_id=new_grade_id,
                    criterion_id=crit.criterion_id,
                    points_awarded=pts,
                    instructor_comment=f"Resubmission reviewed: improvements verified on {crit.title}.",
                )
            )

        total_raw_score = round(total_raw_score, 2)
        late_penalty_applied = (
            round(total_raw_score * (asn.late_penalty_percent / 100.0), 2) if is_late else 0.0
        )
        final_score = round(max(0.0, total_raw_score - late_penalty_applied), 2)

        new_grade = Grade(
            grade_id=new_grade_id,
            submission_id=new_sub_id,
            raw_score=total_raw_score,
            late_penalty_applied=late_penalty_applied,
            final_score=final_score,
            graded_by=prev_grade.graded_by,
            graded_at_utc=new_graded_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        )
        grades.append(new_grade)
        grade_by_sub_id[new_sub_id] = new_grade

        # Policy allowed check: version <= max_resubmissions + 1
        is_allowed = new_version <= (asn.max_resubmissions + 1)
        rsb_id = f"RSB-2026-{resubmission_counter:06d}"
        resubmission_counter += 1

        resubmissions.append(
            Resubmission(
                resubmission_id=rsb_id,
                previous_submission_id=prev_sub.submission_id,
                new_submission_id=new_sub_id,
                requested_at_utc=req_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                reason=rng.choice(RESUBMISSION_REASONS),
                is_allowed_by_policy=is_allowed,
            )
        )

    # 2. Generate Appeals
    # Target ~6-8% of graded submissions
    sub_by_id: Dict[str, Submission] = {s.submission_id: s for s in submissions}
    eligible_grades = [g for g in grades if g.final_score < 95.0]
    target_appeals = max(3, int(len(eligible_grades) * 0.07))
    selected_for_appeal = eligible_grades[:target_appeals]

    for grade in selected_for_appeal:
        sub = sub_by_id.get(grade.submission_id)
        if not sub:
            continue

        appeal_id = f"APP-2026-{appeal_counter:06d}"
        appeal_counter += 1

        grade_dt = datetime.fromisoformat(grade.graded_at_utc.replace("Z", "+00:00"))
        # Appeal submitted between 6 hours and 5 days after grading
        appeal_dt = grade_dt + timedelta(hours=rng.uniform(6.0, 120.0))

        # Status distribution: APPROVED (50%), REJECTED (35%), PENDING (15%)
        r_val = rng.random()
        if r_val < 0.50:
            status = "APPROVED"
            # Score improved by 4 to 12 points
            bump = round(rng.uniform(4.0, 12.0), 2)
            updated_score = min(100.0, round(grade.final_score + bump, 2))
            # Update Grade.final_score
            grade.final_score = updated_score
            sub.status = "APPEALED"
            audit_logged = True
        elif r_val < 0.85:
            status = "REJECTED"
            updated_score = None
            audit_logged = True
        else:
            status = "PENDING"
            updated_score = None
            audit_logged = True

        appeals.append(
            Appeal(
                appeal_id=appeal_id,
                grade_id=grade.grade_id,
                learner_id=sub.learner_id,
                submitted_at_utc=appeal_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                reason=rng.choice(APPEAL_REASONS),
                status=status,
                original_score=grade.final_score if status != "APPROVED" else round(grade.final_score - bump, 2),
                updated_score=updated_score,
                audit_logged=audit_logged,
            )
        )

    return resubmissions, appeals, submissions, artifacts, grades, feedbacks
