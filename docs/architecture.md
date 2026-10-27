# System Architecture & Technical Design

This document details the architecture, relational data model, lifecycle event flows, deterministic random generation strategy, anomaly injection mechanics, and validation engine designed for the **Assignment Lifecycle & Synthetic Grading System**.

---

## 1. High-Level Architecture

The system operates across three decoupled layers: **Generator Pipeline**, **Persistence / Export Layer**, and **Validation & Anomaly Benchmark Engine**.

```mermaid
flowchart TD
    subgraph Core Configuration
        CFG["Config & Seeds<br/>Seed: 20261022<br/>Scales: starter | full"]
    end

    subgraph Generation Engine
        M["Master Generator<br/>Courses, Learners,<br/>Enrollments, Assignments, Rubrics"]
        T["Transactional Generator<br/>Submissions, Artifacts,<br/>Grades, Feedback"]
        L["Lifecycle Engine<br/>Resubmissions, Appeals,<br/>Grade Updates"]
        A["Anomaly Injection<br/>~1-2% Negative Scenarios<br/>(4 distinct flaws)"]
    end

    subgraph Persistence Layer
        CSV["Operational CSVs<br/>(12 Clean Entities)"]
        GT["Ground Truth CSV<br/>(Exclusively Isolated Anomalies)"]
        SQL["SQLite Database<br/>(Indexed & Relational Schema)"]
    end

    subgraph Validation Engine
        SV["Schema Validator<br/>PK Unique, FK Integrity, Enums"]
        BV["Business Rule Validator<br/>Chronology, Lateness, Scoring Math"]
        RPT["Benchmark Runner<br/>Precision, Recall, F1 & Confusion Matrix"]
    end

    CFG --> M
    M --> T
    T --> L
    L --> A
    A --> CSV
    A --> GT
    CSV --> SQL
    CSV --> SV
    CSV --> BV
    GT --> RPT
    SV --> RPT
    BV --> RPT
```

---

## 2. Entity-Relationship Diagram (ERD)

The relational schema comprises 12 operational entities organized into master records, submission transactions, rubric assessments, and post-grading lifecycle events.

```mermaid
erDiagram
    Course ||--o{ Enrollment : "has"
    Learner ||--o{ Enrollment : "participates in"
    Course ||--o{ Assignment : "offers"
    Assignment ||--|| Rubric : "defined by (1:1)"
    Rubric ||--|{ RubricCriterion : "contains (1:N)"
    
    Assignment ||--o{ Submission : "receives"
    Learner ||--o{ Submission : "submits"
    Submission ||--|{ SubmissionArtifact : "attaches (1:N)"
    Submission ||--|| Grade : "evaluated with (1:1)"
    
    Grade ||--|{ Feedback : "breaks down into"
    RubricCriterion ||--o{ Feedback : "applied on"
    
    Submission ||--o{ Resubmission : "previous draft"
    Submission ||--o{ Resubmission : "new draft"
    
    Grade ||--o{ Appeal : "contests"
    Learner ||--o{ Appeal : "submits"

    Course {
        string course_id PK
        string title
        string department
        string term
        string start_date_utc
        string end_date_utc
        string status
    }
    Learner {
        string learner_id PK
        string full_name
        string email UK
        string timezone
        string enrolled_date_utc
        string status
    }
    Enrollment {
        string enrollment_id PK
        string course_id FK
        string learner_id FK
        string enrolled_at_utc
        string status
    }
    Assignment {
        string assignment_id PK
        string course_id FK
        string title
        int max_resubmissions
        string due_date_utc
        float late_penalty_percent
        string status
    }
    Rubric {
        string rubric_id PK
        string assignment_id FK
        string title
        float total_points
        int version
    }
    RubricCriterion {
        string criterion_id PK
        string rubric_id FK
        string title
        string description
        float max_points
        float weight
    }
    Submission {
        string submission_id PK
        string assignment_id FK
        string learner_id FK
        int version_number
        string submitted_at_utc
        bool is_late
        float hours_late
        string status
    }
    SubmissionArtifact {
        string artifact_id PK
        string submission_id FK
        string file_name
        string file_type
        int file_size_kb
        string file_sha256
    }
    Grade {
        string grade_id PK
        string submission_id FK
        float raw_score
        float late_penalty_applied
        float final_score
        string graded_by
        string graded_at_utc
    }
    Feedback {
        string feedback_id PK
        string grade_id FK
        string criterion_id FK
        float points_awarded
        string instructor_comment
    }
    Resubmission {
        string resubmission_id PK
        string previous_submission_id FK
        string new_submission_id FK
        string requested_at_utc
        string reason
        bool is_allowed_by_policy
    }
    Appeal {
        string appeal_id PK
        string grade_id FK
        string learner_id FK
        string submitted_at_utc
        string reason
        string status
        float original_score
        float updated_score
        bool audit_logged
    }
```

---

## 3. Lifecycle State Machine & Chronological Event Flow

All events enforce strict chronological progression:

$$\text{Course.start\_date} \le \text{Assignment.due\_date} \le \text{Submission.submitted\_at} \le \text{Grade.graded\_at} \le \text{Appeal.submitted\_at}$$

```mermaid
stateDiagram-v2
    [*] --> SUBMITTED : Learner submits draft (v1)
    SUBMITTED --> GRADED : Evaluator reviews work & records feedback
    GRADED --> RESUBMITTED : Learner requests resubmission (policy permitted)
    RESUBMITTED --> SUBMITTED : New draft version (v2) submitted
    GRADED --> APPEALED : Learner appeals score
    APPEALED --> PENDING : Under committee review
    PENDING --> APPROVED : Score updated & audit logged
    PENDING --> REJECTED : Score retained
```

---

## 4. Deterministic Reproducibility Strategy

To guarantee that running generation twice with seed `20261022` produces **bit-for-bit identical row counts and SHA-256 checksums**:
1. **Isolated PRNG Instance**: Rather than relying on global mutable PRNG state, an isolated `random.Random(seed)` instance is passed explicitly through all generation modules.
2. **Fixed Baseline Epochs**: All timestamps are calculated deterministically as integer offsets from fixed term epoch baselines (`2026-01-15T00:00:00Z` and `2026-08-25T00:00:00Z`).
3. **Canonical Float Rounding & Formatting**: All scores and penalties are strictly rounded to 2 decimal places (`round(x, 2)`) prior to serialization.
4. **Primary Key Sorting**: Prior to writing CSV artifacts, all rows are deterministically sorted by their canonical primary keys.
5. **Standardized Line Separators**: The CSV export engine enforces strict UNIX line terminators (`\n`) and explicit UTF-8 encoding across Windows, Linux, and macOS.

---

## 5. Anomaly Injection & Ground Truth Isolation

The framework injects 4 deliberate negative scenarios across a controlled subset (~1.5% to 2% of records):

1. **`UNENROLLED_LEARNER_SUBMISSION`**: A submission record is attributed to an assignment in a course where the learner has no active enrollment record in `Enrollment`.
2. **`GRADE_EXCEEDS_MAX`**: A `Grade.raw_score` and corresponding feedback points are artificially inflated above the `Rubric.total_points` (100.0).
3. **`DOUBLE_LATE_PENALTY`**: `Grade.late_penalty_applied` is deducted twice from the raw score, corrupting `final_score`.
4. **`UNAUDITED_APPEAL_GRADE_CHANGE`**: An appeal status is `APPROVED` and modifies `Grade.final_score`, but `Appeal.audit_logged` is set to `False`.

### Zero Ground Truth Leakage
- Operational CSV tables (`submissions.csv`, `grades.csv`, `appeals.csv`) contain **only** standard production fields.
- Anomaly metadata, flaw labels, and root causes are written exclusively to `data/ground_truth.csv`.

---

## 6. Validation Engine Architecture

The validator analyzes datasets without knowledge of the ground truth labels, executing:
- **Schema Validation Layer**: Checks primary key uniqueness, ID scheme regex, orphan foreign keys, non-null values, and enum sets.
- **Business Rule Layer**: Validates chronology, lateness math, feedback reconciliation ($\sum \text{feedback} == \text{raw}$), penalty calculations, and security audit log integrity.
- **Evaluation Runner**: Matches validator findings against `ground_truth.csv`, calculating:
  $$\text{Precision} = \frac{TP}{TP + FP}, \quad \text{Recall} = \frac{TP}{TP + FN}, \quad F_1 = 2 \times \frac{\text{Precision} \times \text{Recall}}{\text{Precision} + \text{Recall}}$$
