# Synthetic Data Generator & Validation Engine

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/pytest-Passing-brightgreen.svg)]()
[![Reproducibility](https://img.shields.io/badge/SHA--256-Deterministic-success.svg)]()

> **Enterprise-Grade Synthetic Data Generator & Validation Engine** in Python modeling complete academic lifecycle events: courses, learners, enrollments, assignments, rubric-based grading, feedback, multi-version resubmissions, and appeals.

---

## Highlights

- **100% Deterministic Reproducibility**: Running generation twice with seed `20261022` produces identical row counts and identical file **SHA-256 checksums** across all operational CSVs and ground truth labels.
- **Relational Integrity Across 12 Entities**: Rigorous Primary Key and Foreign Key constraints spanning courses, learners, enrollments, assignments, rubrics, criteria, submissions, artifacts, grades, feedback, resubmissions, and appeals.
- **Strict Chronological Consistency**:
  $$\text{Course.start\_date} \le \text{Assignment.due\_date} \le \text{Submission.submitted\_at} \le \text{Grade.graded\_at} \le \text{Appeal.submitted\_at}$$
- **Controlled Negative Scenario Injection**: Systematically injects 4 deliberate negative edge cases into ~1-2% of records without leaking anomaly tags into operational datasets.
- **Precision Validation Engine**: Automated validator achieving **100.0% Precision**, **100.0% Recall**, and **100.0% F1-score** on anomaly detection while guaranteeing zero false alarms on clean records.
- **Scalable Performance**: Sub-second execution for starter workloads (4,800+ records) and ~10 seconds for the full enterprise benchmark (**280,000+ records**).
- **Relational Database Export**: High-performance SQLite database export (`database.sqlite`) with foreign keys and index optimizations.

---

## Table of Contents

- [Entity Data Model](#entity-data-model)
- [Deliberate Edge Cases & Ground Truth](#deliberate-edge-cases--ground-truth)
- [Repository Structure](#repository-structure)
- [Installation & Setup](#installation--setup)
- [Command-Line Interface (CLI)](#command-line-interface-cli)
- [Running the Test Suite](#running-the-test-suite)
- [Benchmark Results](#benchmark-results)
- [Documentation Links](#documentation-links)

---

## Entity Data Model

The platform models 12 relational entities conforming to standardized, deterministic zero-padded ID schemes:

| Entity | PK Format | Example PK | Description |
| :--- | :--- | :--- | :--- |
| **Course** | `CRS-2026-XXXXXX` | `CRS-2026-000001` | Academic course offering with term boundaries |
| **Learner** | `LRN-2026-XXXXXX` | `LRN-2026-000001` | Platform student profile with unique institutional email |
| **Enrollment** | `ENR-2026-XXXXXX` | `ENR-2026-000001` | Bridge table with composite uniqueness on `(course_id, learner_id)` |
| **Assignment** | `ASN-2026-XXXXXX` | `ASN-2026-000001` | Evaluative task with due date, resubmission policy, and late penalty |
| **Rubric** | `RUB-<asn_id>-01` | `RUB-ASN-2026-000001-01` | 1:1 assignment grading rubric totaling 100.0 points |
| **RubricCriterion** | `CRT-<rubric_id>-XX` | `CRT-RUB-ASN-2026-000001-01-01` | Dimension assessment item with weights summing to 1.0 |
| **Submission** | `SUB-<asn_id>-<lrn_id>-<ver>` | `SUB-ASN-2026-000001-LRN-2026-000005-01` | Student submission draft with lateness timestamp auditing |
| **SubmissionArtifact**| `ART-2026-XXXXXX` | `ART-2026-000001` | Uploaded digital artifacts with SHA-256 file hashes |
| **Grade** | `GRD-<submission_id>` | `GRD-SUB-ASN-2026-000001-LRN-2026-000005-01` | 1:1 evaluation record with raw score, late penalty, and final score |
| **Feedback** | `FDB-2026-XXXXXX` | `FDB-2026-000001` | Criterion-level points and qualitative evaluator feedback |
| **Resubmission** | `RSB-2026-XXXXXX` | `RSB-2026-000001` | Policy-governed link between successive submission drafts |
| **Appeal** | `APP-2026-XXXXXX` | `APP-2026-000001` | Formal regrade petition with audit logging and score updates |

---

## Deliberate Edge Cases & Ground Truth

To benchmark validation and anomaly detection capabilities, 4 negative scenarios are injected into a controlled subset (~1.5% to 2% of records):

1. **`UNENROLLED_LEARNER_SUBMISSION`**: A submission draft is recorded for an assignment where the learner has no active enrollment in that course.
2. **`GRADE_EXCEEDS_MAX`**: A grade's `raw_score` and criterion feedback points exceed the rubric's maximum total points (`100.0`).
3. **`DOUBLE_LATE_PENALTY`**: The late penalty is calculated and deducted twice on a late submission, corrupting `final_score`.
4. **`UNAUDITED_APPEAL_GRADE_CHANGE`**: An appeal is `APPROVED` and modifies `Grade.final_score`, but `Appeal.audit_logged` is set to `False`.

### Zero Ground Truth Leakage
All injected anomalies are cataloged exclusively in `data/ground_truth.csv` with the schema:
```text
issue_id, issue_type, entity_name, record_id, field_name, expected_value, actual_value, description
```
Operational CSV tables contain **no anomaly labels, tags, or indicator flags**.

---

## Repository Structure

```text
├── data/
│   ├── raw/                 # Generated operational CSVs for all 12 entities
│   ├── ground_truth.csv     # Isolated ground truth labels
│   └── database.sqlite      # SQLite database with loaded tables & indexes
├── src/
│   ├── __init__.py
│   ├── config.py            # Global deterministic seed, scales, domain constants
│   ├── models.py            # Typed dataclasses for entities and ground truth
│   ├── exporter.py          # Deterministic CSV and SQLite export engine
│   ├── generator/
│   │   ├── __init__.py
│   │   ├── master.py        # Courses, Learners, Enrollments, Assignments, Rubrics
│   │   ├── transactions.py  # Submissions, Artifacts, Grades, Feedback
│   │   ├── lifecycle.py     # Resubmissions, Appeals, Grade adjustments
│   │   ├── anomalies.py     # Controlled negative scenario injection
│   │   └── orchestrator.py  # End-to-end pipeline coordination
│   ├── validator/
│   │   ├── __init__.py
│   │   ├── schema.py        # PK uniqueness, FK referential integrity, Enum validation
│   │   ├── business_rules.py# Chronology, lateness logic, score reconciliation, audits
│   │   └── runner.py        # Benchmark evaluator and Rich console reporter
│   └── cli.py               # Unified CLI interface
├── tests/
│   ├── __init__.py
│   ├── test_reproducibility.py # Generates twice with seed 20261022, asserts hash equality
│   └── test_validation.py      # Validates clean data, catches anomalies, tests schemas
├── docs/
│   ├── data_dictionary.md   # Schema reference and data types for all entities
│   └── architecture.md      # System architecture, Mermaid ERD, and state diagrams
├── requirements.txt
└── README.md
```

---

## Installation & Setup

### Prerequisites
- Python 3.10+ (Tested on Python 3.10, 3.11, 3.12, 3.14)
- Git

### Setup
```bash
# Clone the repository
git clone https://github.com/<your-username>/assignment-lifecycle-engine.git
cd assignment-lifecycle-engine

# Install dependencies
pip install -r requirements.txt
```

---

## Command-Line Interface (CLI)

The CLI supports data generation, validation benchmarking, and SQL exporting:

### 1. Generate Synthetic Datasets
Generates all operational CSVs, injects controlled anomalies, writes isolated `ground_truth.csv`, and builds `database.sqlite`:

```bash
# Starter scale (50 courses, 500 learners, 100 assignments, ~300 submissions)
python -m src.cli generate --scale starter --seed 20261022 --out data/raw

# Full benchmark scale (200 courses, 10,000 learners, 1,000 assignments, ~30,000 submissions)
python -m src.cli generate --scale full --seed 20261022 --out data/raw
```

### 2. Validate Operational Data & Benchmark Anomalies
Runs all schema checks, referential integrity tests, and business rules; reconciles detected anomalies against `ground_truth.csv`:

```bash
python -m src.cli validate --data-dir data/raw --ground-truth data/ground_truth.csv
```

### 3. Export to SQLite
Seeds the relational SQLite database with indexed tables directly from operational CSVs:

```bash
python -m src.cli export-sql --data-dir data/raw --db-path data/database.sqlite
```

---

## Running the Test Suite

Run the full automated test suite using `pytest`:

```bash
pytest tests/ -v
```

### Key Tests Included
- `tests/test_reproducibility.py`: Generates the dataset twice in isolated temporary directories using seed `20261022` and asserts that every single CSV file produces an **identical SHA-256 checksum** and row count.
- `tests/test_validation.py`: Asserts that `validate` achieves **100% Precision**, **100% Recall**, and **100% F1-score**, verifies zero anomaly leakage into operational headers, confirms chronological ordering, and tests arithmetic reconciliation.

---

## Benchmark Results

### Record Counts by Scale Profile

| Operational Entity | Starter Scale | Full Benchmark Scale |
| :--- | :--- | :--- |
| **Courses** | 50 | 200 |
| **Learners** | 500 | 10,000 |
| **Enrollments** | 1,268 | 23,991 |
| **Assignments** | 100 | 1,000 |
| **Rubrics** | 100 | 1,000 |
| **Rubric Criteria** | 400 | 4,000 |
| **Submissions** | 323 | 32,365 |
| **Submission Artifacts** | 436 | 41,347 |
| **Grades** | 323 | 32,365 |
| **Feedback** | 1,292 | 129,460 |
| **Resubmissions** | 23 | 2,365 |
| **Appeals** | 22 | 2,239 |
| **Total Operational Records** | **4,837** | **280,332** |
| **Execution Time** | **< 1.0 s** | **~10.0 s** |

### Anomaly Detection Benchmark (Full Scale: 280,332 Records)

| Anomaly Type | Injected | Detected (TP) | Missed (FN) | False Alarms (FP) | Recall |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `UNENROLLED_LEARNER_SUBMISSION` | 212 | 212 | 0 | 0 | **100.0%** |
| `GRADE_EXCEEDS_MAX` | 242 | 242 | 0 | 0 | **100.0%** |
| `DOUBLE_LATE_PENALTY` | 71 | 71 | 0 | 0 | **100.0%** |
| `UNAUDITED_APPEAL_GRADE_CHANGE` | 13 | 13 | 0 | 0 | **100.0%** |
| **Overall Summary** | **538** | **538** | **0** | **0** | **Precision: 100.0%<br/>Recall: 100.0%<br/>F1: 100.0%** |

---

## Documentation Links

- [Complete Data Dictionary](docs/data_dictionary.md): Comprehensive schema specifications, data types, constraints, and descriptions for all 12 entities and ground truth.
- [System Architecture & Design](docs/architecture.md): Architectural design, Mermaid ERD diagrams, lifecycle event flows, and determinism proofs.
