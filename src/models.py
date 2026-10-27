"""Typed data models for the 12 core entities and ground truth anomaly records."""

from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional


@dataclass
class Course:
    course_id: str
    title: str
    department: str
    term: str
    start_date_utc: str
    end_date_utc: str
    status: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Learner:
    learner_id: str
    full_name: str
    email: str
    timezone: str
    enrolled_date_utc: str
    status: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Enrollment:
    enrollment_id: str
    course_id: str
    learner_id: str
    enrolled_at_utc: str
    status: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Assignment:
    assignment_id: str
    course_id: str
    title: str
    max_resubmissions: int
    due_date_utc: str
    late_penalty_percent: float
    status: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Rubric:
    rubric_id: str
    assignment_id: str
    title: str
    total_points: float
    version: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RubricCriterion:
    criterion_id: str
    rubric_id: str
    title: str
    description: str
    max_points: float
    weight: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Submission:
    submission_id: str
    assignment_id: str
    learner_id: str
    version_number: int
    submitted_at_utc: str
    is_late: bool
    hours_late: float
    status: str

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["is_late"] = str(self.is_late)
        return d


@dataclass
class SubmissionArtifact:
    artifact_id: str
    submission_id: str
    file_name: str
    file_type: str
    file_size_kb: int
    file_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Grade:
    grade_id: str
    submission_id: str
    raw_score: float
    late_penalty_applied: float
    final_score: float
    graded_by: str
    graded_at_utc: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Feedback:
    feedback_id: str
    grade_id: str
    criterion_id: str
    points_awarded: float
    instructor_comment: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Resubmission:
    resubmission_id: str
    previous_submission_id: str
    new_submission_id: str
    requested_at_utc: str
    reason: str
    is_allowed_by_policy: bool

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["is_allowed_by_policy"] = str(self.is_allowed_by_policy)
        return d


@dataclass
class Appeal:
    appeal_id: str
    grade_id: str
    learner_id: str
    submitted_at_utc: str
    reason: str
    status: str
    original_score: float
    updated_score: Optional[float]
    audit_logged: bool

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["audit_logged"] = str(self.audit_logged)
        if d["updated_score"] is None:
            d["updated_score"] = ""
        return d


@dataclass
class AnomalyGroundTruth:
    issue_id: str
    issue_type: str
    entity_name: str
    record_id: str
    field_name: str
    expected_value: str
    actual_value: str
    description: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
