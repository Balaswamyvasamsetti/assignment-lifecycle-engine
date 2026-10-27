"""Configuration settings, deterministic seeds, scales, and domain constants."""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

DEFAULT_SEED: int = 20261022

# Default Paths
BASE_DIR: Path = Path(__file__).resolve().parent.parent
DATA_DIR: Path = BASE_DIR / "data"
RAW_DATA_DIR: Path = DATA_DIR / "raw"
GROUND_TRUTH_PATH: Path = DATA_DIR / "ground_truth.csv"
SQLITE_DB_PATH: Path = DATA_DIR / "database.sqlite"


@dataclass(frozen=True)
class ScaleConfig:
    name: str
    num_courses: int
    num_learners: int
    num_assignments: int
    num_submissions: int
    avg_enrollments_per_course: int
    anomaly_rate: float = 0.02


SCALES: Dict[str, ScaleConfig] = {
    "starter": ScaleConfig(
        name="starter",
        num_courses=50,
        num_learners=500,
        num_assignments=100,
        num_submissions=300,
        avg_enrollments_per_course=25,
        anomaly_rate=0.02,
    ),
    "full": ScaleConfig(
        name="full",
        num_courses=200,
        num_learners=10000,
        num_assignments=1000,
        num_submissions=30000,
        avg_enrollments_per_course=120,
        anomaly_rate=0.015,
    ),
}

# Domain Constants
TERMS: List[str] = ["Fall 2026", "Spring 2026"]

DEPARTMENTS: List[str] = [
    "Computer Science",
    "Data Science",
    "Electrical Engineering",
    "Mathematics",
    "Mechanical Engineering",
    "Information Systems",
    "Bioinformatics",
    "Economics",
]

COURSE_STATUSES: List[str] = ["ACTIVE", "ARCHIVED"]
LEARNER_STATUSES: List[str] = ["ACTIVE", "SUSPENDED"]
ENROLLMENT_STATUSES: List[str] = ["ACTIVE", "DROPPED"]
ASSIGNMENT_STATUSES: List[str] = ["PUBLISHED", "CLOSED"]
SUBMISSION_STATUSES: List[str] = ["SUBMITTED", "GRADED", "APPEALED", "RESUBMITTED"]
APPEAL_STATUSES: List[str] = ["PENDING", "APPROVED", "REJECTED"]

TIMEZONES: List[str] = [
    "UTC",
    "America/New_York",
    "Europe/London",
    "Asia/Kolkata",
]

FILE_TYPES: List[str] = ["pdf", "zip", "py", "docx"]

# Anomaly Identifiers
ANOMALY_UNENROLLED_SUBMISSION = "UNENROLLED_LEARNER_SUBMISSION"
ANOMALY_GRADE_EXCEEDS_MAX = "GRADE_EXCEEDS_MAX"
ANOMALY_DOUBLE_LATE_PENALTY = "DOUBLE_LATE_PENALTY"
ANOMALY_UNAUDITED_APPEAL = "UNAUDITED_APPEAL_GRADE_CHANGE"

ANOMALY_TYPES = [
    ANOMALY_UNENROLLED_SUBMISSION,
    ANOMALY_GRADE_EXCEEDS_MAX,
    ANOMALY_DOUBLE_LATE_PENALTY,
    ANOMALY_UNAUDITED_APPEAL,
]
