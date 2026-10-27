"""Systematic injection of deliberate edge cases into operational records and logging to ground_truth.csv."""

import random
from collections import defaultdict
from typing import Dict, List, Set, Tuple

from src.config import (
    ANOMALY_DOUBLE_LATE_PENALTY,
    ANOMALY_GRADE_EXCEEDS_MAX,
    ANOMALY_UNAUDITED_APPEAL,
    ANOMALY_UNENROLLED_SUBMISSION,
    ScaleConfig,
)
from src.models import (
    AnomalyGroundTruth,
    Appeal,
    Assignment,
    Enrollment,
    Feedback,
    Grade,
    Learner,
    Rubric,
    Submission,
    SubmissionArtifact,
)


def inject_anomalies(
    config: ScaleConfig,
    assignments: List[Assignment],
    enrollments: List[Enrollment],
    learners: List[Learner],
    submissions: List[Submission],
    grades: List[Grade],
    feedbacks: List[Feedback],
    appeals: List[Appeal],
    rubrics: List[Rubric],
    rng: random.Random,
    artifacts: List[SubmissionArtifact] = None,
    resubmissions: List[Resubmission] = None,
) -> Tuple[
    List[Submission],
    List[Grade],
    List[Feedback],
    List[Appeal],
    List[AnomalyGroundTruth],
]:
    """Injects 4 controlled negative scenarios (~1-2% of relevant records) and generates ground_truth.csv entries."""

    ground_truth: List[AnomalyGroundTruth] = []
    issue_counter = 1

    asn_by_id: Dict[str, Assignment] = {a.assignment_id: a for a in assignments}
    grade_by_id: Dict[str, Grade] = {g.grade_id: g for g in grades}
    feedbacks_by_grade: Dict[str, List[Feedback]] = defaultdict(list)
    for f in feedbacks:
        feedbacks_by_grade[f.grade_id].append(f)

    # Active enrollments by (course_id, learner_id)
    active_enr_pairs: Set[Tuple[str, str]] = {
        (e.course_id, e.learner_id) for e in enrollments if e.status == "ACTIVE"
    }

    all_learner_ids = [l.learner_id for l in learners]

    # -------------------------------------------------------------------------
    # 1. UNENROLLED_LEARNER_SUBMISSION
    # A submission is created for an assignment where the learner has NO active enrollment in that course.
    # -------------------------------------------------------------------------
    # Pick submissions that are NOT resubmitted to keep versioning clean
    eligible_subs = [s for s in submissions if s.version_number == 1 and s.status != "RESUBMITTED"]
    count_unenrolled = max(2, int(len(eligible_subs) * (config.anomaly_rate * 0.5)))
    unenrolled_sample_subs = eligible_subs[:count_unenrolled]

    for sub in unenrolled_sample_subs:
        asn = asn_by_id[sub.assignment_id]
        orig_learner = sub.learner_id

        # Find a learner not enrolled in asn.course_id
        target_learner = None
        for candidate in all_learner_ids:
            if (asn.course_id, candidate) not in active_enr_pairs and candidate != orig_learner:
                target_learner = candidate
                break

        if target_learner:
            old_sub_id = sub.submission_id
            new_sub_id = f"SUB-{asn.assignment_id}-{target_learner}-{sub.version_number:02d}"
            
            sub.learner_id = target_learner
            sub.submission_id = new_sub_id

            # Cascade update to child artifacts
            if artifacts:
                for art in artifacts:
                    if art.submission_id == old_sub_id:
                        art.submission_id = new_sub_id

            # Cascade update to resubmissions
            if resubmissions:
                for rsb in resubmissions:
                    if rsb.previous_submission_id == old_sub_id:
                        rsb.previous_submission_id = new_sub_id
                    if rsb.new_submission_id == old_sub_id:
                        rsb.new_submission_id = new_sub_id

            # Cascade update to child grade & feedback & appeals
            for gr in grades:
                if gr.submission_id == old_sub_id:
                    old_grade_id = gr.grade_id
                    new_grade_id = f"GRD-{new_sub_id}"
                    gr.submission_id = new_sub_id
                    gr.grade_id = new_grade_id

                    # Cascade to feedback
                    for fb in feedbacks:
                        if fb.grade_id == old_grade_id:
                            fb.grade_id = new_grade_id

                    # Cascade to appeals
                    for app in appeals:
                        if app.grade_id == old_grade_id:
                            app.grade_id = new_grade_id
                            app.learner_id = target_learner

            issue_id = f"ISSUE-2026-{issue_counter:06d}"
            issue_counter += 1

            ground_truth.append(
                AnomalyGroundTruth(
                    issue_id=issue_id,
                    issue_type=ANOMALY_UNENROLLED_SUBMISSION,
                    entity_name="Submission",
                    record_id=new_sub_id,
                    field_name="learner_id",
                    expected_value="ACTIVE_ENROLLMENT_REQUIRED",
                    actual_value=target_learner,
                    description=(
                        f"Submission {new_sub_id} submitted for assignment {asn.assignment_id} "
                        f"in course {asn.course_id}, but learner {target_learner} has no active enrollment."
                    ),
                )
            )

    # -------------------------------------------------------------------------
    # 2. GRADE_EXCEEDS_MAX
    # Grade.raw_score (and corresponding feedback points) exceeds Rubric.total_points (100.0)
    # -------------------------------------------------------------------------
    # Re-index feedbacks by grade after cascade
    feedbacks_by_grade = defaultdict(list)
    for f in feedbacks:
        feedbacks_by_grade[f.grade_id].append(f)

    eligible_grades = [g for g in grades if g.raw_score < 100.0 and len(feedbacks_by_grade[g.grade_id]) > 0]
    count_exceeds = max(2, int(len(eligible_grades) * (config.anomaly_rate * 0.5)))
    exceeds_sample_grades = eligible_grades[:count_exceeds]

    for grade in exceeds_sample_grades:
        orig_raw = grade.raw_score
        excess_points = round(rng.uniform(12.0, 25.0), 2)
        new_raw = round(100.0 + excess_points, 2)
        grade.raw_score = new_raw

        # Distribute excess into the first feedback record so sum(points_awarded) == raw_score
        f_list = feedbacks_by_grade[grade.grade_id]
        if f_list:
            delta = round(new_raw - orig_raw, 2)
            f_list[0].points_awarded = round(f_list[0].points_awarded + delta, 2)

        # Recalculate final score based on new raw score
        grade.final_score = round(max(0.0, new_raw - grade.late_penalty_applied), 2)

        issue_id = f"ISSUE-2026-{issue_counter:06d}"
        issue_counter += 1

        ground_truth.append(
            AnomalyGroundTruth(
                issue_id=issue_id,
                issue_type=ANOMALY_GRADE_EXCEEDS_MAX,
                entity_name="Grade",
                record_id=grade.grade_id,
                field_name="raw_score",
                expected_value="<= 100.0",
                actual_value=str(new_raw),
                description=(
                    f"Grade {grade.grade_id} raw_score ({new_raw}) and feedback points exceed "
                    f"rubric maximum total_points (100.0)."
                ),
            )
        )

    # -------------------------------------------------------------------------
    # 3. DOUBLE_LATE_PENALTY
    # Grade.late_penalty_applied is calculated and deducted twice, miscalculating final_score.
    # -------------------------------------------------------------------------
    sub_by_id = {s.submission_id: s for s in submissions}
    late_grades = [
        g for g in grades
        if sub_by_id.get(g.submission_id) and sub_by_id[g.submission_id].is_late and g.late_penalty_applied > 0.0
    ]
    count_double_penalty = max(2, int(len(late_grades) * (config.anomaly_rate * 0.6)))
    double_penalty_sample = late_grades[:count_double_penalty]

    for grade in double_penalty_sample:
        sub = sub_by_id[grade.submission_id]
        asn = asn_by_id[sub.assignment_id]
        expected_penalty = round(grade.raw_score * (asn.late_penalty_percent / 100.0), 2)
        doubled_penalty = round(expected_penalty * 2.0, 2)

        grade.late_penalty_applied = doubled_penalty
        grade.final_score = round(max(0.0, grade.raw_score - doubled_penalty), 2)

        issue_id = f"ISSUE-2026-{issue_counter:06d}"
        issue_counter += 1

        ground_truth.append(
            AnomalyGroundTruth(
                issue_id=issue_id,
                issue_type=ANOMALY_DOUBLE_LATE_PENALTY,
                entity_name="Grade",
                record_id=grade.grade_id,
                field_name="late_penalty_applied",
                expected_value=f"{expected_penalty:.2f}",
                actual_value=f"{doubled_penalty:.2f}",
                description=(
                    f"Grade {grade.grade_id} for late submission {sub.submission_id} had late penalty "
                    f"deducted twice ({doubled_penalty:.2f} instead of {expected_penalty:.2f}), "
                    f"corrupting final_score to {grade.final_score}."
                ),
            )
        )

    # -------------------------------------------------------------------------
    # 4. UNAUDITED_APPEAL_GRADE_CHANGE
    # An appeal is APPROVED and changes Grade.final_score, but Appeal.audit_logged is False.
    # -------------------------------------------------------------------------
    approved_appeals = [a for a in appeals if a.status == "APPROVED" and a.updated_score is not None]
    count_unaudited = max(1, int(len(approved_appeals) * (config.anomaly_rate * 0.8)))
    unaudited_sample = approved_appeals[:count_unaudited]

    for appeal in unaudited_sample:
        appeal.audit_logged = False
        issue_id = f"ISSUE-2026-{issue_counter:06d}"
        issue_counter += 1

        ground_truth.append(
            AnomalyGroundTruth(
                issue_id=issue_id,
                issue_type=ANOMALY_UNAUDITED_APPEAL,
                entity_name="Appeal",
                record_id=appeal.appeal_id,
                field_name="audit_logged",
                expected_value="True",
                actual_value="False",
                description=(
                    f"Appeal {appeal.appeal_id} was APPROVED with score change from {appeal.original_score} "
                    f"to {appeal.updated_score}, but audit_logged was set to False."
                ),
            )
        )

    return submissions, grades, feedbacks, appeals, ground_truth
