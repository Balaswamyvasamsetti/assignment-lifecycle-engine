"""Master data generator for Courses, Learners, Enrollments, Assignments, and Rubrics."""

import random
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple

from src.config import (
    ASSIGNMENT_STATUSES,
    COURSE_STATUSES,
    DEPARTMENTS,
    ENROLLMENT_STATUSES,
    LEARNER_STATUSES,
    ScaleConfig,
    TERMS,
    TIMEZONES,
)
from src.models import (
    Assignment,
    Course,
    Enrollment,
    Learner,
    Rubric,
    RubricCriterion,
)

FIRST_NAMES = [
    "Alex", "Jordan", "Taylor", "Morgan", "Sam", "Chris", "Pat", "Riley",
    "Casey", "Jamie", "Avery", "Logan", "Parker", "Quinn", "Dakota", "Reese",
    "Skyler", "Cameron", "Jesse", "Kendall", "Hayden", "Rowan", "Harper", "Finley",
    "Peyton", "Emerson", "River", "Elliott", "Adrian", "Blake", "Kai", "Sloan",
    "Amara", "Arjun", "Elena", "Wei", "Fatima", "Dmitri", "Kenji", "Mateo",
    "Chioma", "Aarav", "Sofia", "Hassan", "Lina", "Tenzin", "Mei", "Santiago"
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas",
    "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson", "White",
    "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker", "Young",
    "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores",
    "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell",
    "Patel", "Sharma", "Kaur", "Singh", "Chen", "Wang", "Zhang", "Kim", "Tanaka"
]

COURSE_TOPICS = [
    ("Distributed Systems", "CS"),
    ("Machine Learning Systems", "CS"),
    ("Advanced Operating Systems", "CS"),
    ("Deep Learning Fundamentals", "DS"),
    ("Applied Cryptography & Network Security", "CS"),
    ("Database Management Systems Architecture", "CS"),
    ("Statistical Computing & Inference", "DS"),
    ("High Performance Parallel Computing", "CS"),
    ("Computer Vision & Pattern Recognition", "CS"),
    ("Natural Language Processing at Scale", "DS"),
    ("Digital Signal Processing", "EE"),
    ("Embedded Microcontroller Systems", "EE"),
    ("Linear Algebra & Numerical Optimization", "MATH"),
    ("Robotics & Autonomous Navigation", "ME"),
    ("Data Engineering & Pipeline Systems", "DS"),
    ("Cloud Computing Architecture & DevOps", "IS"),
    ("Bioinformatics & Computational Genomics", "BIO"),
    ("Econometrics & Quantitative Modeling", "ECON"),
    ("Software Architecture & Design Patterns", "CS"),
    ("Reinforcement Learning & Decision Making", "DS"),
    ("Quantum Computing Algorithms", "CS"),
    ("Cyber-Physical Systems Security", "EE"),
]

CRITERIA_TEMPLATES = [
    ("Code Correctness & Functional Requirements", "Verifies algorithmic accuracy, passing core test fixtures, and expected outputs.", 0.40, 40.0),
    ("Software Architecture & Engineering Quality", "Evaluates modularity, separation of concerns, clean code conventions, and maintainability.", 0.30, 30.0),
    ("Test Coverage & Robust Edge Case Handling", "Assesses unit and integration tests covering boundaries, invalid input handling, and stress conditions.", 0.20, 20.0),
    ("Documentation & API Specifications", "Reviews clarity of README, inline docstrings, schema contracts, and build reproducibility instructions.", 0.10, 10.0),
]


def generate_master_data(
    config: ScaleConfig,
    rng: random.Random,
) -> Tuple[
    List[Course],
    List[Learner],
    List[Enrollment],
    List[Assignment],
    List[Rubric],
    List[RubricCriterion],
]:
    """Generates deterministic Course, Learner, Enrollment, Assignment, Rubric, and Criterion records."""
    
    # 1. Generate Courses
    courses: List[Course] = []
    course_dates: Dict[str, Tuple[datetime, datetime]] = {}

    term_dates = {
        "Spring 2026": (
            datetime(2026, 1, 15, 0, 0, 0, tzinfo=timezone.utc),
            datetime(2026, 5, 15, 23, 59, 59, tzinfo=timezone.utc),
        ),
        "Fall 2026": (
            datetime(2026, 8, 25, 0, 0, 0, tzinfo=timezone.utc),
            datetime(2026, 12, 20, 23, 59, 59, tzinfo=timezone.utc),
        ),
    }

    for i in range(1, config.num_courses + 1):
        course_id = f"CRS-2026-{i:06d}"
        topic_idx = (i - 1) % len(COURSE_TOPICS)
        topic, _ = COURSE_TOPICS[topic_idx]
        section = (i - 1) // len(COURSE_TOPICS) + 1
        title = f"{topic} (Sec {section:02d})"
        dept = rng.choice(DEPARTMENTS)
        term = TERMS[(i - 1) % len(TERMS)]
        
        start_dt, end_dt = term_dates[term]
        course_dates[course_id] = (start_dt, end_dt)
        status = "ACTIVE" if rng.random() < 0.90 else "ARCHIVED"

        courses.append(
            Course(
                course_id=course_id,
                title=title,
                department=dept,
                term=term,
                start_date_utc=start_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                end_date_utc=end_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                status=status,
            )
        )

    # 2. Generate Learners
    learners: List[Learner] = []
    base_learner_date = datetime(2025, 11, 1, 10, 0, 0, tzinfo=timezone.utc)

    for i in range(1, config.num_learners + 1):
        learner_id = f"LRN-2026-{i:06d}"
        first_name = rng.choice(FIRST_NAMES)
        last_name = rng.choice(LAST_NAMES)
        full_name = f"{first_name} {last_name}"
        email = f"{first_name.lower()}.{last_name.lower()}.{i:06d}@university.edu"
        tz = rng.choice(TIMEZONES)
        enrolled_offset_days = rng.randint(0, 60)
        enrolled_offset_mins = rng.randint(0, 1439)
        learner_enrolled_dt = base_learner_date + timedelta(
            days=enrolled_offset_days, minutes=enrolled_offset_mins
        )
        status = "ACTIVE" if rng.random() < 0.96 else "SUSPENDED"

        learners.append(
            Learner(
                learner_id=learner_id,
                full_name=full_name,
                email=email,
                timezone=tz,
                enrolled_date_utc=learner_enrolled_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                status=status,
            )
        )

    # 3. Generate Enrollments (Composite Uniqueness on course_id, learner_id)
    enrollments: List[Enrollment] = []
    enrollment_id_counter = 1
    learner_ids = [l.learner_id for l in learners]

    for course in courses:
        c_start, _ = course_dates[course.course_id]
        # Target enrollments for this course
        pool_size = min(len(learners), max(10, config.avg_enrollments_per_course))
        # Deterministically sample learners without replacement
        sample_count = min(len(learners), rng.randint(max(5, pool_size - 10), pool_size + 10))
        course_learners = rng.sample(learner_ids, sample_count)

        for l_id in course_learners:
            enr_id = f"ENR-2026-{enrollment_id_counter:06d}"
            enrollment_id_counter += 1
            
            # Enrollment happens between 30 days prior and 7 days after course start
            day_offset = rng.randint(-30, 7)
            minute_offset = rng.randint(0, 1439)
            enr_dt = c_start + timedelta(days=day_offset, minutes=minute_offset)
            status = "ACTIVE" if rng.random() < 0.92 else "DROPPED"

            enrollments.append(
                Enrollment(
                    enrollment_id=enr_id,
                    course_id=course.course_id,
                    learner_id=l_id,
                    enrolled_at_utc=enr_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    status=status,
                )
            )

    # 4. Generate Assignments
    assignments: List[Assignment] = []
    rubrics: List[Rubric] = []
    rubric_criteria: List[RubricCriterion] = []

    # Distribute assignments across courses
    for i in range(1, config.num_assignments + 1):
        assignment_id = f"ASN-2026-{i:06d}"
        course = courses[(i - 1) % len(courses)]
        c_start, c_end = course_dates[course.course_id]
        
        # Due date is strictly between course start + 10 days and end - 10 days
        course_duration_days = (c_end - c_start).days
        due_day_offset = rng.randint(14, max(15, course_duration_days - 14))
        due_hour = rng.choice([17, 23])  # 5 PM or 11:59 PM
        due_minute = 59 if due_hour == 23 else 0
        due_dt = c_start + timedelta(days=due_day_offset, hours=due_hour, minutes=due_minute)

        asn_num = ((i - 1) // len(courses)) + 1
        title = f"Assignment {asn_num}: Implementation & Benchmark"
        max_resubmissions = rng.choice([0, 1, 2])
        late_penalty_percent = rng.choice([5.0, 10.0, 15.0, 20.0])
        status = rng.choice(ASSIGNMENT_STATUSES)

        assignments.append(
            Assignment(
                assignment_id=assignment_id,
                course_id=course.course_id,
                title=title,
                max_resubmissions=max_resubmissions,
                due_date_utc=due_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                late_penalty_percent=late_penalty_percent,
                status=status,
            )
        )

        # 5. Generate 1:1 Rubric
        rubric_id = f"RUB-{assignment_id}-01"
        rubrics.append(
            Rubric(
                rubric_id=rubric_id,
                assignment_id=assignment_id,
                title=f"Rubric: {title}",
                total_points=100.0,
                version=1,
            )
        )

        # 6. Generate Rubric Criteria for this Rubric
        for c_idx, (c_title, c_desc, c_weight, c_max) in enumerate(CRITERIA_TEMPLATES, 1):
            criterion_id = f"CRT-{rubric_id}-{c_idx:02d}"
            rubric_criteria.append(
                RubricCriterion(
                    criterion_id=criterion_id,
                    rubric_id=rubric_id,
                    title=c_title,
                    description=c_desc,
                    max_points=c_max,
                    weight=c_weight,
                )
            )

    return courses, learners, enrollments, assignments, rubrics, rubric_criteria
