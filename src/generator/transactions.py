"""Transactional data generator for Submissions, Artifacts, Grades, and Feedback."""

import hashlib
import random
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Set, Tuple

from src.config import FILE_TYPES, ScaleConfig
from src.models import (
    Assignment,
    Course,
    Enrollment,
    Feedback,
    Grade,
    Rubric,
    RubricCriterion,
    Submission,
    SubmissionArtifact,
)

FEEDBACK_COMMENTS = {
    "Code Correctness & Functional Requirements": [
        "All edge cases passed; algorithm handles scale efficiently.",
        "Core unit tests passed with flying colors.",
        "Minor boundary condition failure in sorting logic, but core solution is solid.",
        "Well structured algorithmic solution with expected asymptotic complexity.",
    ],
    "Software Architecture & Engineering Quality": [
        "Clean modular design following SOLID principles.",
        "Excellent separation of concerns across service layers.",
        "Good idiomatic style, clear naming conventions and minimal technical debt.",
        "Refactored components are highly readable and easy to extend.",
    ],
    "Test Coverage & Robust Edge Case Handling": [
        "Comprehensive suite of regression and boundary tests included.",
        "Great parameterization on tricky edge cases.",
        "Test coverage exceeds 90% across core modules.",
        "Good integration tests, though concurrency tests could be deeper.",
    ],
    "Documentation & API Specifications": [
        "Clear documentation with complete setup instructions and reproducible benchmarks.",
        "Comprehensive docstrings with type annotations throughout.",
        "Architecture diagrams and data dictionaries are thoroughly detailed.",
        "README contains unambiguous CLI instructions and design rationale.",
    ],
}


def generate_transaction_data(
    config: ScaleConfig,
    courses: List[Course],
    enrollments: List[Enrollment],
    assignments: List[Assignment],
    rubrics: List[Rubric],
    rubric_criteria: List[RubricCriterion],
    rng: random.Random,
) -> Tuple[
    List[Submission],
    List[SubmissionArtifact],
    List[Grade],
    List[Feedback],
    Dict[str, List[Submission]],  # mapping learner_id -> submissions
]:
    """Generates initial Submissions, Artifacts, Grades, and Feedback."""
    
    # Pre-index data
    asn_by_id: Dict[str, Assignment] = {a.assignment_id: a for a in assignments}
    course_by_id: Dict[str, Course] = {c.course_id: c for c in courses}
    
    # Active enrollments by course
    active_enr_by_course: Dict[str, List[str]] = defaultdict(list)
    for enr in enrollments:
        if enr.status == "ACTIVE":
            active_enr_by_course[enr.course_id].append(enr.learner_id)

    # Rubric criteria by rubric_id
    criteria_by_rubric: Dict[str, List[RubricCriterion]] = defaultdict(list)
    for crit in rubric_criteria:
        criteria_by_rubric[crit.rubric_id].append(crit)

    submissions: List[Submission] = []
    artifacts: List[SubmissionArtifact] = []
    grades: List[Grade] = []
    feedbacks: List[Feedback] = []

    artifact_counter = 1
    feedback_counter = 1
    
    # We need to generate `config.num_submissions` submissions.
    # To maintain consistency, we pick assignment and an enrolled learner.
    # We will track (assignment_id, learner_id) to assign version 1.
    learner_submissions: Dict[str, List[Submission]] = defaultdict(list)
    pair_seen: Set[Tuple[str, str]] = set()

    # Pre-filter assignments that have at least one active learner enrolled
    eligible_assignments = [
        a for a in assignments if len(active_enr_by_course[a.course_id]) > 0
    ]
    if not eligible_assignments:
        eligible_assignments = assignments

    # Target number of initial submissions
    # Note: some submissions will later become resubmissions (version 2) in lifecycle.py
    num_initial_submissions = config.num_submissions

    for sub_idx in range(1, num_initial_submissions + 1):
        asn = eligible_assignments[(sub_idx - 1) % len(eligible_assignments)]
        course = course_by_id[asn.course_id]
        enrolled_learners = active_enr_by_course[asn.course_id]
        
        # Pick learner deterministically
        if enrolled_learners:
            l_idx = (sub_idx - 1) % len(enrolled_learners)
            learner_id = enrolled_learners[l_idx]
        else:
            # Fallback if no active learners in course
            learner_id = f"LRN-2026-{(sub_idx % config.num_learners) + 1:06d}"

        # If pair seen, increment section or pick another
        if (asn.assignment_id, learner_id) in pair_seen:
            # Pick next learner
            found = False
            for cand in enrolled_learners:
                if (asn.assignment_id, cand) not in pair_seen:
                    learner_id = cand
                    found = True
                    break
            if not found:
                # pick next assignment
                asn = eligible_assignments[sub_idx % len(eligible_assignments)]
                enrolled_learners = active_enr_by_course[asn.course_id]
                if enrolled_learners:
                    learner_id = enrolled_learners[0]

        pair_seen.add((asn.assignment_id, learner_id))
        version_number = 1
        sub_id = f"SUB-{asn.assignment_id}-{learner_id}-{version_number:02d}"

        # Timing: Course.start_date <= Assignment.due_date <= Submission.submitted_at (if late)
        # or Course.start_date <= Submission.submitted_at <= Assignment.due_date (if on time)
        due_dt = datetime.fromisoformat(asn.due_date_utc.replace("Z", "+00:00"))
        course_start_dt = datetime.fromisoformat(course.start_date_utc.replace("Z", "+00:00"))

        is_late = rng.random() < 0.20  # 20% late
        if not is_late:
            # Submitted between 1 and 72 hours before due date, but after course start
            hours_early = rng.uniform(0.5, 72.0)
            submitted_dt = due_dt - timedelta(hours=hours_early)
            if submitted_dt < course_start_dt + timedelta(days=1):
                submitted_dt = course_start_dt + timedelta(days=1, hours=rng.uniform(1.0, 10.0))
            hours_late = 0.0
        else:
            # Submitted between 0.5 and 48 hours after due date
            hours_late = round(rng.uniform(0.5, 48.0), 2)
            submitted_dt = due_dt + timedelta(hours=hours_late)

        # Status: Will be GRADED (unless pending)
        status = "GRADED"

        submission = Submission(
            submission_id=sub_id,
            assignment_id=asn.assignment_id,
            learner_id=learner_id,
            version_number=version_number,
            submitted_at_utc=submitted_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            is_late=is_late,
            hours_late=hours_late,
            status=status,
        )
        submissions.append(submission)
        learner_submissions[learner_id].append(submission)

        # Generate 1 or 2 artifacts
        num_artifacts = 1 if rng.random() < 0.70 else 2
        for art_i in range(1, num_artifacts + 1):
            art_id = f"ART-2026-{artifact_counter:06d}"
            artifact_counter += 1
            f_type = rng.choice(FILE_TYPES)
            f_name = f"solution_v{version_number}_{art_i}.{f_type}"
            f_size = rng.randint(45, 12500)  # KB
            f_hash = hashlib.sha256(f"{art_id}-{sub_id}-{f_name}".encode("utf-8")).hexdigest()

            artifacts.append(
                SubmissionArtifact(
                    artifact_id=art_id,
                    submission_id=sub_id,
                    file_name=f_name,
                    file_type=f_type,
                    file_size_kb=f_size,
                    file_sha256=f_hash,
                )
            )

        # Generate Grade & Feedback
        rubric_id = f"RUB-{asn.assignment_id}-01"
        crit_list = criteria_by_rubric.get(rubric_id, [])

        grade_id = f"GRD-{sub_id}"
        # Graded after submission: between 4 and 48 hours later
        graded_dt = submitted_dt + timedelta(hours=rng.uniform(4.0, 48.0))
        instructor_id = f"INST-2026-{rng.randint(1, 20):06d}"

        # Calculate criterion points
        total_raw_score = 0.0
        for crit in crit_list:
            fdb_id = f"FDB-2026-{feedback_counter:06d}"
            feedback_counter += 1
            
            # Award points: high performance distribution (e.g. 70% to 100% of max)
            pct = rng.uniform(0.70, 1.0)
            pts = round(crit.max_points * pct, 2)
            pts = min(pts, crit.max_points)
            total_raw_score += pts
            
            comment_pool = FEEDBACK_COMMENTS.get(crit.title, ["Good submission."])
            comment = rng.choice(comment_pool)

            feedbacks.append(
                Feedback(
                    feedback_id=fdb_id,
                    grade_id=grade_id,
                    criterion_id=crit.criterion_id,
                    points_awarded=pts,
                    instructor_comment=comment,
                )
            )

        total_raw_score = round(total_raw_score, 2)
        
        # Calculate late penalty
        if is_late:
            late_penalty_applied = round(total_raw_score * (asn.late_penalty_percent / 100.0), 2)
        else:
            late_penalty_applied = 0.0

        final_score = round(max(0.0, total_raw_score - late_penalty_applied), 2)

        grades.append(
            Grade(
                grade_id=grade_id,
                submission_id=sub_id,
                raw_score=total_raw_score,
                late_penalty_applied=late_penalty_applied,
                final_score=final_score,
                graded_by=instructor_id,
                graded_at_utc=graded_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            )
        )

    return submissions, artifacts, grades, feedbacks, learner_submissions
