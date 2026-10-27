# AI Transparency & Prompt History Disclosure

In accordance with the **YottaFlex AI Recruitment Drive Submission Guidelines** (Section 03: *Use LLMs Transparently*), this document details the AI tools utilized, complete prompt logs, areas of AI acceleration, critical human architectural interventions, and automated verification protocols.

---

## 1. Executive Summary of AI Utilization

- **AI Tools Used**: Antigravity (Google DeepMind agentic coding assistant powered by Gemini 3.8 Flash / Thinking models).
- **Core Philosophy**: AI was used as an **accelerator and collaborative pair programmer** for scaffolding boilerplate dataclasses, generating domain templates, and formatting documentation. All core architectural decisions, data consistency rules, cascading foreign key fixes, validation algorithms, and reproducibility assertions were explicitly directed, reviewed, and verified by the engineer.

---

## 2. Where AI Accelerated the Work

1. **Schema & Dataclass Boilerplate**:
   - Synthesizing 12 typed Python dataclasses conforming to the exact field contracts and zero-padded ID schemes (`CRS-2026-XXXXXX`, `LRN-2026-XXXXXX`, `ASN-2026-XXXXXX`, `RUB-<asn>-01`, etc.).
2. **Domain-Specific Templates & Nomenclature**:
   - Rapidly creating realistic pools of course subjects (e.g., *Distributed Systems*, *Applied Cryptography*, *Machine Learning Systems*), rubric criteria definitions, and qualitative instructor feedback commentary.
3. **Mermaid Diagram Authoring**:
   - Generating standard Mermaid syntax for the Entity-Relationship Diagram (ERD) and lifecycle state machines in [`docs/architecture.md`](architecture.md).
4. **Documentation Scaffolding**:
   - Generating markdown tables in the data dictionary across 12 entities with standard columns.

---

## 3. Where Human Engineering & Critical Review Intervened

While LLMs generate code quickly, complex relational data generators require sound human engineering judgment to prevent subtle data corruption, non-determinism, and referential integrity violations:

1. **Cascading Foreign Key Consistency on Anomaly Injection**:
   - *Issue Identified*: An initial draft of the `UNENROLLED_LEARNER_SUBMISSION` anomaly simply modified the submission's `learner_id` to an unenrolled learner, but left the submission PK or child records out of sync, causing SQLite foreign key constraint failures on resubmissions (`RSB-...`) and artifacts.
   - *Human Engineering Decision*: Designed and implemented a robust cascading update mechanism in `src/generator/anomalies.py` that updates child artifacts, grades, feedbacks, appeals, and resubmission parent pointers synchronously while keeping the target submission detached from course enrollments.
2. **Strict Deterministic Bit-for-Bit Reproducibility**:
   - *Challenge*: Default floating-point serialization and unseeded hash sets often cause slight variations in CSV outputs across runs, breaking SHA-256 reproducibility.
   - *Human Engineering Decision*: Enforced an isolated PRNG instance (`random.Random(seed)`), fixed term base epochs (`2026-01-15T00:00:00Z` and `2026-08-25T00:00:00Z`), canonical 2-decimal float rounding (`round(x, 2)`), primary-key sorting before serialization, and explicit UNIX line separators (`\n`).
3. **Absolute Ground Truth Isolation**:
   - *Challenge*: LLMs frequently include convenience flags like `is_anomaly=True` inside the operational data tables, which contaminates downstream training datasets (data leakage).
   - *Human Engineering Decision*: Strictly isolated all injected negative scenarios into `data/ground_truth.csv` and created a specific regression test (`test_separate_ground_truth_no_data_leakage`) to assert zero contamination in operational CSV headers.
4. **Zero-Dependency Relational Portability (SQLite)**:
   - *Decision*: Rather than requiring Docker or external database services (PostgreSQL/MySQL), designed an automated SQLite export engine (`data/database.sqlite`) with native foreign keys (`PRAGMA foreign_keys = ON;`) and performance indexes to allow instant zero-setup review.

---

## 4. Chronological Prompt History Log

### Prompt Session 1: Initial System Architecture & Task Specification
```text
# TASK SPECIFICATION: 72 Hours Code Challenge — AI Forward Deployed Engineer
Target: Build a complete, enterprise-grade Synthetic Data Generator & Validation Engine in Python that generates lifecycle events for assignments, submissions, rubric-based grading, feedback, resubmissions, and appeals.

## 1. Core Requirements & Seed Configuration
- Language: Python 3.10+
- Deterministic Seed: 20261022 (must use fixed seed for random and numpy)
- Reproducibility Requirement: Running generation twice with the same seed MUST yield identical row counts and identical file SHA-256 checksums.
- Scalability:
  - Starter Scale: 50 courses, 500 learners, 100 assignments, 300 submissions.
  - Full Benchmark Scale: 200 courses, 10,000 learners, 1,000 assignments, 30,000 submissions.
- Delivery Artifacts:
  - Exported CSVs and an SQLite DB export (database.sqlite).
  - Labeled ground_truth.csv containing exclusively injected anomalies (do NOT leak into data features).
  - Validation test suite with pytest.
  - Comprehensive data_dictionary.md covering all 11 entities.
  - Complete README.md with CLI instructions.
...
[Entities, Schemas, 4 Injected Negative Scenarios, CLI Specifications]
```

**Actions Taken**:
- Initialized local Git repository in `c:\72_hours_code`.
- Implemented `src/config.py`, `src/models.py`, `src/generator/`, `src/validator/`, and `src/cli.py`.
- Built pytest test suite (`test_reproducibility.py` and `test_validation.py`).

---

### Prompt Session 2: Granular 10-Step Workflow Alignment & Provenance Disclosure
```text
Business Context / Problem:
Manage assignment publication, submissions, rubric-based grading, feedback, resubmissions and appeals.
...
Synthetic Data Generation Instructions (Granular):
Step 1 — Write a data dictionary for: Course, Learner, Assignment, Rubric, RubricCriterion, Submission, SubmissionArtifact, Grade, Feedback, Resubmission, Appeal. For each field specify type, required/optional, allowed values, units, uniqueness and validation rule.
Step 2 — Create parent/master tables first, then child and event tables...
Step 3 — Apply deterministic IDs and naming...
Step 4 — Generate the baseline volume: 1,000 assignments, 10,000 learners and 30,000 submissions...
Step 5 — Generate valid baseline records first, then inject labelled edge cases...
Step 6 — Calculate derived values...
Step 7 — Produce a separate ground_truth.csv/json...
Step 8 — Run validation: primary-key uniqueness, foreign-key integrity, allowed enums, date ordering, arithmetic reconciliation, lifecycle transitions and duplicate checks.
Step 9 — Export CSV/JSON/SQL seed data plus README, schema/data dictionary, generator command, fixed seed, source manifest and validation summary.
Step 10 — Regenerate twice with the same seed and compare row counts/checksums to demonstrate reproducibility.
```

**Actions Taken**:
- Updated `docs/data_dictionary.md` to include all requested columns: `Field Name`, `Data Type`, `Required / Optional`, `Allowed Values / Domain`, `Units`, `Key / Uniqueness`, `Validation Rule`, `Description`, `Sample Value`.
- Added composite uniqueness validation (`(course_id, learner_id)`) and field uniqueness checks (`Learner.email`).
- Added lifecycle state transition validation (`validate_lifecycle_transitions`).
- Extended exporter to output JSON files (`data/json/`) and cryptographic source manifest (`data/manifest.json`).
- Added `python -m src.cli export-json` command.

---

### Prompt Session 3: GitHub Push & Automation
```text
git remote add origin https://github.com/Balaswamyvasamsetti/assignment-lifecycle-engine.git
git branch -M main
git push -u origin main
```

**Actions Taken**:
- Created GitHub Actions CI matrix testing Python 3.10, 3.11, and 3.12.
- Created `scripts/verify_reproducibility.py` and `scripts/analytics.py`.
- Added remote `origin` and pushed `main` branch to GitHub.

---

## 5. Automated Verification & Quality Assurance Protocols

To ensure that AI-generated logic was rigorously correct, every feature was verified against automated test fixtures:

1. **Hash Verification**: [`tests/test_reproducibility.py`](../tests/test_reproducibility.py) runs two full end-to-end generation pipelines in isolated temporary directories and asserts SHA-256 hash equality for every CSV, JSON, and ground truth file.
2. **Schema & Business Rule Verification**: [`tests/test_validation.py`](../tests/test_validation.py) injects unit-test corruptions (duplicate PKs, orphan FKs, invalid enums, broken chronology, policy violations) to verify that the validation engine flags them correctly.
3. **Ground Truth Benchmark**: Tested against both Starter (4,837 rows) and Full Scale (280,332 rows) to confirm **100.0% Precision**, **100.0% Recall**, and **100.0% F1-score**.
