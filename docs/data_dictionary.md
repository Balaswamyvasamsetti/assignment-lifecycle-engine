# Comprehensive Data Dictionary: Assignment Lifecycle & Grading Engine

This data dictionary formally documents all 12 operational entities and the ground truth anomaly catalog. For each attribute, it details data type, nullability (required/optional), domain of allowable values, physical units, key constraints, automated validation rules, operational description, and sample representations.

---

## 1. Course (`courses.csv`)
Represents an academic course offering within a specified department, term, and calendar window.

- **Primary Key**: `course_id`
- **Foreign Keys**: None
- **Cardinality**: 1:N with Enrollment, 1:N with Assignment

| Field Name | Data Type | Required / Optional | Allowed Values / Domain | Units | Key / Uniqueness | Validation Rule | Description | Sample Value |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `course_id` | `TEXT` | Required | `CRS-2026-000001` .. `CRS-2026-999999` | N/A | Primary Key, Unique | Regex: `^CRS-2026-\d{6}$` | Unique zero-padded course identifier | `CRS-2026-000001` |
| `title` | `TEXT` | Required | Non-empty alphanumeric string | N/A | Non-unique | Length $\ge 5$ characters | Official course title with section indicator | `Distributed Systems (Sec 01)` |
| `department` | `TEXT` | Required | `Computer Science`, `Data Science`, `Electrical Engineering`, `Mathematics`, `Mechanical Engineering`, `Information Systems`, `Bioinformatics`, `Economics` | N/A | Non-unique | Valid department enum | Department administering the course offering | `Computer Science` |
| `term` | `TEXT` | Required | `Fall 2026`, `Spring 2026` | N/A | Non-unique | Valid academic term enum | Academic semester / term session | `Fall 2026` |
| `start_date_utc`| `TEXT` | Required | ISO 8601 UTC timestamp | UTC Timestamp | Non-unique | Valid ISO 8601, $\le \text{end\_date\_utc}$ | Official opening date of course offering | `2026-08-25T00:00:00Z` |
| `end_date_utc` | `TEXT` | Required | ISO 8601 UTC timestamp | UTC Timestamp | Non-unique | Valid ISO 8601, $> \text{start\_date\_utc}$ | Official closing date of course offering | `2026-12-20T23:59:59Z` |
| `status` | `TEXT` | Required | `ACTIVE`, `ARCHIVED` | N/A | Non-unique | Valid status enum | Current administrative status of the course | `ACTIVE` |

---

## 2. Learner (`learners.csv`)
Represents an enrolled student matriculating across courses.

- **Primary Key**: `learner_id`
- **Foreign Keys**: None
- **Cardinality**: 1:N with Enrollment, 1:N with Submission, 1:N with Appeal

| Field Name | Data Type | Required / Optional | Allowed Values / Domain | Units | Key / Uniqueness | Validation Rule | Description | Sample Value |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `learner_id` | `TEXT` | Required | `LRN-2026-000001` .. `LRN-2026-999999` | N/A | Primary Key, Unique | Regex: `^LRN-2026-\d{6}$` | Unique zero-padded student identifier | `LRN-2026-000042` |
| `full_name` | `TEXT` | Required | Non-empty string | N/A | Non-unique | Standard name pattern | Student's given name and surname | `Amara Chen` |
| `email` | `TEXT` | Required | RFC 5322 compliant institutional email | N/A | Unique | Email regex, unique across system | Student institutional email address | `amara.chen.000042@university.edu` |
| `timezone` | `TEXT` | Required | `UTC`, `America/New_York`, `Europe/London`, `Asia/Kolkata` | IANA Timezone | Non-unique | Valid IANA timezone string | Student's primary configured timezone | `America/New_York` |
| `enrolled_date_utc`| `TEXT` | Required | ISO 8601 UTC timestamp | UTC Timestamp | Non-unique | Valid ISO 8601 | Platform account registration timestamp | `2025-11-14T16:22:00Z` |
| `status` | `TEXT` | Required | `ACTIVE`, `SUSPENDED` | N/A | Non-unique | Valid status enum | Standing of student account | `ACTIVE` |

---

## 3. Enrollment (`enrollments.csv`)
Bridge table managing the Many-to-Many association between Learners and Courses.

- **Primary Key**: `enrollment_id`
- **Foreign Keys**:
  - `course_id` $\rightarrow$ `Course.course_id`
  - `learner_id` $\rightarrow$ `Learner.learner_id`
- **Cardinality**: N:M junction table, Composite Unique on `(course_id, learner_id)`

| Field Name | Data Type | Required / Optional | Allowed Values / Domain | Units | Key / Uniqueness | Validation Rule | Description | Sample Value |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `enrollment_id` | `TEXT` | Required | `ENR-2026-000001` .. `ENR-2026-999999` | N/A | Primary Key, Unique | Regex: `^ENR-2026-\d{6}$` | Unique enrollment record identifier | `ENR-2026-000105` |
| `course_id` | `TEXT` | Required | Valid `Course.course_id` | N/A | Foreign Key | Exists in `courses.csv` | Reference to enrolled course | `CRS-2026-000001` |
| `learner_id` | `TEXT` | Required | Valid `Learner.learner_id` | N/A | Foreign Key | Exists in `learners.csv` | Reference to matriculated student | `LRN-2026-000042` |
| `enrolled_at_utc` | `TEXT` | Required | ISO 8601 UTC timestamp | UTC Timestamp | Non-unique | Valid ISO 8601 | Timestamp student enrolled in course | `2026-08-10T14:30:00Z` |
| `status` | `TEXT` | Required | `ACTIVE`, `DROPPED` | N/A | Non-unique | Valid enrollment enum | Status of learner in this course offering | `ACTIVE` |

---

## 4. Assignment (`assignments.csv`)
Academic task or assessment published within a course offering.

- **Primary Key**: `assignment_id`
- **Foreign Keys**:
  - `course_id` $\rightarrow$ `Course.course_id`
- **Cardinality**: N:1 with Course, 1:1 with Rubric, 1:N with Submission

| Field Name | Data Type | Required / Optional | Allowed Values / Domain | Units | Key / Uniqueness | Validation Rule | Description | Sample Value |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `assignment_id` | `TEXT` | Required | `ASN-2026-000001` .. `ASN-2026-999999` | N/A | Primary Key, Unique | Regex: `^ASN-2026-\d{6}$` | Unique assignment identifier | `ASN-2026-000001` |
| `course_id` | `TEXT` | Required | Valid `Course.course_id` | N/A | Foreign Key | Exists in `courses.csv` | Course offering this assessment | `CRS-2026-000001` |
| `title` | `TEXT` | Required | Non-empty alphanumeric string | N/A | Non-unique | Length $\ge 5$ characters | Name of assignment deliverable | `Assignment 1: Distributed Consensus` |
| `max_resubmissions`| `INTEGER` | Required | `0`, `1`, `2` | Iteration Count | Non-unique | $0 \le x \le 2$ | Maximum drafts allowed after initial submission | `1` |
| `due_date_utc` | `TEXT` | Required | ISO 8601 UTC timestamp | UTC Timestamp | Non-unique | Course start $\le \text{due} \le$ course end | Official submission deadline | `2026-10-15T23:59:00Z` |
| `late_penalty_percent`| `REAL` | Required | `5.0`, `10.0`, `15.0`, `20.0` | Percentage (%) | Non-unique | $0.0 \le x \le 100.0$ | Daily or total penalty rate for late arrival | `10.0` |
| `status` | `TEXT` | Required | `PUBLISHED`, `CLOSED` | N/A | Non-unique | Valid status enum | Lifecycle state of assignment availability | `PUBLISHED` |

---

## 5. Rubric (`rubrics.csv`)
Evaluation framework defining grading criteria and scale for an assignment (1:1 with Assignment).

- **Primary Key**: `rubric_id`
- **Foreign Keys**:
  - `assignment_id` $\rightarrow$ `Assignment.assignment_id` (Unique 1:1)
- **Cardinality**: 1:1 with Assignment, 1:N with RubricCriterion

| Field Name | Data Type | Required / Optional | Allowed Values / Domain | Units | Key / Uniqueness | Validation Rule | Description | Sample Value |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `rubric_id` | `TEXT` | Required | `RUB-<asn_id>-01` | N/A | Primary Key, Unique | Regex: `^RUB-ASN-2026-\d{6}-\d{2}$` | Unique rubric identifier | `RUB-ASN-2026-000001-01` |
| `assignment_id` | `TEXT` | Required | Valid `Assignment.assignment_id` | N/A | Foreign Key, Unique | Exists in `assignments.csv`, 1:1 | Parent assignment identifier | `ASN-2026-000001` |
| `title` | `TEXT` | Required | Non-empty string | N/A | Non-unique | Descriptive title string | Name of evaluation rubric | `Rubric: Assignment 1: Distributed Consensus` |
| `total_points` | `REAL` | Required | `100.0` | Points | Non-unique | $> 0.0$, equals sum of criterion max points | Maximum possible score for the assignment | `100.0` |
| `version` | `INTEGER` | Required | `1` | Version Number | Non-unique | $\ge 1$ | Rubric version schema iteration | `1` |

---

## 6. RubricCriterion (`rubric_criteria.csv`)
Individual assessment component belonging to a rubric.

- **Primary Key**: `criterion_id`
- **Foreign Keys**:
  - `rubric_id` $\rightarrow$ `Rubric.rubric_id`
- **Cardinality**: N:1 with Rubric, 1:N with Feedback

| Field Name | Data Type | Required / Optional | Allowed Values / Domain | Units | Key / Uniqueness | Validation Rule | Description | Sample Value |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `criterion_id` | `TEXT` | Required | `CRT-<rubric_id>-XX` | N/A | Primary Key, Unique | Regex: `^CRT-RUB-ASN-2026-\d{6}-\d{2}-\d{2}$`| Unique criterion identifier | `CRT-RUB-ASN-2026-000001-01-01` |
| `rubric_id` | `TEXT` | Required | Valid `Rubric.rubric_id` | N/A | Foreign Key | Exists in `rubrics.csv` | Reference to parent rubric | `RUB-ASN-2026-000001-01` |
| `title` | `TEXT` | Required | Non-empty string | N/A | Non-unique | Criterion title | Title of grading dimension | `Code Correctness & Functional Requirements` |
| `description` | `TEXT` | Required | Non-empty string | N/A | Non-unique | Explanatory text | Detailed expectations and grading criteria | `Verifies algorithmic accuracy & edge cases.` |
| `max_points` | `REAL` | Required | $0.0 < x \le 100.0$ | Points | Non-unique | $\sum \text{max\_points} = \text{total\_points}$ | Maximum score achievable in this criterion | `40.0` |
| `weight` | `REAL` | Required | $0.0 < x \le 1.0$ | Fraction | Non-unique | $\sum \text{weight} = 1.0$ per rubric | Proportional weighting of criterion | `0.40` |

---

## 7. Submission (`submissions.csv`)
A student's submitted solution draft for an assignment.

- **Primary Key**: `submission_id`
- **Foreign Keys**:
  - `assignment_id` $\rightarrow$ `Assignment.assignment_id`
  - `learner_id` $\rightarrow$ `Learner.learner_id`
- **Cardinality**: N:1 with Assignment, N:1 with Learner, 1:1 with Grade, 1:N with Artifact

| Field Name | Data Type | Required / Optional | Allowed Values / Domain | Units | Key / Uniqueness | Validation Rule | Description | Sample Value |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `submission_id` | `TEXT` | Required | `SUB-<asn_id>-<lrn_id>-<ver>` | N/A | Primary Key, Unique | Regex: `^SUB-ASN-2026-\d{6}-LRN-2026-\d{6}-\d{2}$`| Unique submission draft identifier | `SUB-ASN-2026-000001-LRN-2026-000042-01` |
| `assignment_id` | `TEXT` | Required | Valid `Assignment.assignment_id` | N/A | Foreign Key | Exists in `assignments.csv` | Assignment submitted for | `ASN-2026-000001` |
| `learner_id` | `TEXT` | Required | Valid `Learner.learner_id` | N/A | Foreign Key | Exists in `learners.csv`, actively enrolled | Submitting learner | `LRN-2026-000042` |
| `version_number`| `INTEGER` | Required | `1`, `2`, `3` | Draft Version | Non-unique | $\ge 1$ | Version iteration of student draft | `1` |
| `submitted_at_utc`| `TEXT` | Required | ISO 8601 UTC timestamp | UTC Timestamp | Non-unique | Valid ISO 8601, $\ge \text{course start}$ | Submission upload timestamp | `2026-10-15T22:15:00Z` |
| `is_late` | `TEXT` | Required | `True`, `False` | Boolean | Non-unique | $\text{submitted\_at\_utc} > \text{due\_date\_utc}$ | Lateness determination flag | `False` |
| `hours_late` | `REAL` | Required | $\ge 0.0$ | Hours | Non-unique | If late: $(\text{sub} - \text{due})/3600$, else $0.0$ | Elapsed hours past due date | `0.0` |
| `status` | `TEXT` | Required | `SUBMITTED`, `GRADED`, `APPEALED`, `RESUBMITTED` | N/A | Non-unique | Valid submission status enum | Submission workflow lifecycle state | `GRADED` |

---

## 8. SubmissionArtifact (`submission_artifacts.csv`)
Digital code and report files uploaded within a submission bundle.

- **Primary Key**: `artifact_id`
- **Foreign Keys**:
  - `submission_id` $\rightarrow$ `Submission.submission_id`
- **Cardinality**: N:1 with Submission

| Field Name | Data Type | Required / Optional | Allowed Values / Domain | Units | Key / Uniqueness | Validation Rule | Description | Sample Value |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `artifact_id` | `TEXT` | Required | `ART-2026-000001` .. `ART-2026-999999` | N/A | Primary Key, Unique | Regex: `^ART-2026-\d{6}$` | Unique file artifact identifier | `ART-2026-000123` |
| `submission_id` | `TEXT` | Required | Valid `Submission.submission_id` | N/A | Foreign Key | Exists in `submissions.csv` | Reference to parent submission draft | `SUB-ASN-2026-000001-LRN-2026-000042-01` |
| `file_name` | `TEXT` | Required | Filename with valid extension | N/A | Non-unique | Length $\ge 3$ characters | Stored file name | `solution_v1_1.zip` |
| `file_type` | `TEXT` | Required | `pdf`, `zip`, `py`, `docx` | File Format | Non-unique | Valid extension enum | MIME category / extension | `zip` |
| `file_size_kb` | `INTEGER` | Required | $10 \le x \le 50000$ | Kilobytes (KB) | Non-unique | $> 0$ | File size on storage disk | `4520` |
| `file_sha256` | `TEXT` | Required | 64-char lowercase hexadecimal string | Hex Hash | Non-unique | Regex: `^[a-f0-9]{64}$` | Cryptographic SHA-256 integrity hash | `b3f4...e90a` |

---

## 9. Grade (`grades.csv`)
Evaluative outcome recorded for a student submission (1:1 with Submission).

- **Primary Key**: `grade_id`
- **Foreign Keys**:
  - `submission_id` $\rightarrow$ `Submission.submission_id` (Unique 1:1)
- **Cardinality**: 1:1 with Submission, 1:N with Feedback, 1:N with Appeal

| Field Name | Data Type | Required / Optional | Allowed Values / Domain | Units | Key / Uniqueness | Validation Rule | Description | Sample Value |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `grade_id` | `TEXT` | Required | `GRD-<submission_id>` | N/A | Primary Key, Unique | Regex: `^GRD-SUB-.*` | Unique grade record identifier | `GRD-SUB-ASN-2026-000001-LRN-2026-000042-01` |
| `submission_id` | `TEXT` | Required | Valid `Submission.submission_id` | N/A | Foreign Key, Unique | Exists in `submissions.csv`, 1:1 | Parent submission evaluated | `SUB-ASN-2026-000001-LRN-2026-000042-01` |
| `raw_score` | `REAL` | Required | $0.0 \le x \le \text{rubric.total}$ | Points | Non-unique | $\sum \text{feedback.points\_awarded}$ | Raw score before late deductions | `92.50` |
| `late_penalty_applied`| `REAL` | Required | $\ge 0.0$ | Points | Non-unique | If late: $\text{raw} \times \text{penalty}\%$, else $0.0$ | Deducted points due to late submission | `0.00` |
| `final_score` | `REAL` | Required | $\ge 0.0$ | Points | Non-unique | $\max(0.0, \text{raw} - \text{penalty})$ | Net earned score assigned to student | `92.50` |
| `graded_by` | `TEXT` | Required | `INST-2026-000001` .. `INST-2026-999999` | N/A | Non-unique | Regex: `^INST-2026-\d{6}$` | Evaluator / Instructor identifier | `INST-2026-000012` |
| `graded_at_utc` | `TEXT` | Required | ISO 8601 UTC timestamp | UTC Timestamp | Non-unique | Valid ISO 8601, $\ge \text{submitted\_at\_utc}$| Grading timestamp | `2026-10-17T11:45:00Z` |

---

## 10. Feedback (`feedback.csv`)
Criterion-specific feedback comment and point allocation.

- **Primary Key**: `feedback_id`
- **Foreign Keys**:
  - `grade_id` $\rightarrow$ `Grade.grade_id`
  - `criterion_id` $\rightarrow$ `RubricCriterion.criterion_id`
- **Cardinality**: N:1 with Grade, N:1 with RubricCriterion

| Field Name | Data Type | Required / Optional | Allowed Values / Domain | Units | Key / Uniqueness | Validation Rule | Description | Sample Value |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `feedback_id` | `TEXT` | Required | `FDB-2026-000001` .. `FDB-2026-999999` | N/A | Primary Key, Unique | Regex: `^FDB-2026-\d{6}$` | Unique feedback line item identifier | `FDB-2026-000481` |
| `grade_id` | `TEXT` | Required | Valid `Grade.grade_id` | N/A | Foreign Key | Exists in `grades.csv` | Reference to parent grade record | `GRD-SUB-ASN-2026-000001-LRN-2026-000042-01` |
| `criterion_id` | `TEXT` | Required | Valid `RubricCriterion.criterion_id` | N/A | Foreign Key | Exists in `rubric_criteria.csv` | Criterion evaluated | `CRT-RUB-ASN-2026-000001-01-01` |
| `points_awarded`| `REAL` | Required | $0.0 \le x \le \text{criterion.max}$ | Points | Non-unique | $\le \text{criterion.max\_points}$ | Points assigned for this dimension | `38.00` |
| `instructor_comment`| `TEXT` | Required | Non-empty narrative text | N/A | Non-unique | Length $\ge 5$ characters | Qualitative feedback commentary | `All edge cases passed; algorithm is optimal.` |

---

## 11. Resubmission (`resubmissions.csv`)
Event and policy tracking record connecting successive submission versions.

- **Primary Key**: `resubmission_id`
- **Foreign Keys**:
  - `previous_submission_id` $\rightarrow$ `Submission.submission_id`
  - `new_submission_id` $\rightarrow$ `Submission.submission_id`
- **Cardinality**: N:1 with preceding draft, N:1 with successive draft

| Field Name | Data Type | Required / Optional | Allowed Values / Domain | Units | Key / Uniqueness | Validation Rule | Description | Sample Value |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `resubmission_id`| `TEXT` | Required | `RSB-2026-000001` .. `RSB-2026-999999` | N/A | Primary Key, Unique | Regex: `^RSB-2026-\d{6}$` | Unique resubmission event identifier | `RSB-2026-000014` |
| `previous_submission_id`| `TEXT`| Required | Valid `Submission.submission_id` | N/A | Foreign Key | Exists in `submissions.csv` | Preceding draft identifier | `SUB-ASN-2026-000001-LRN-2026-000042-01` |
| `new_submission_id`| `TEXT` | Required | Valid `Submission.submission_id` | N/A | Foreign Key | Exists in `submissions.csv` | Successive draft identifier | `SUB-ASN-2026-000001-LRN-2026-000042-02` |
| `requested_at_utc`| `TEXT` | Required | ISO 8601 UTC timestamp | UTC Timestamp | Non-unique | Valid ISO 8601, $\ge \text{previous grade}$ | Timestamp student requested resubmission | `2026-10-18T09:20:00Z` |
| `reason` | `TEXT` | Required | Non-empty justification | N/A | Non-unique | Length $\ge 5$ characters | Student explanation for resubmitting | `Incorporated instructor feedback on architecture.` |
| `is_allowed_by_policy`| `TEXT`| Required | `True`, `False` | Boolean | Non-unique | $\text{new\_version} \le (\text{max\_resub} + 1)$ | Whether request conforms to policy limit | `True` |

---

## 12. Appeal (`appeals.csv`)
Formal regrade petition filed by a student regarding an assigned grade.

- **Primary Key**: `appeal_id`
- **Foreign Keys**:
  - `grade_id` $\rightarrow$ `Grade.grade_id`
  - `learner_id` $\rightarrow$ `Learner.learner_id`
- **Cardinality**: N:1 with Grade, N:1 with Learner

| Field Name | Data Type | Required / Optional | Allowed Values / Domain | Units | Key / Uniqueness | Validation Rule | Description | Sample Value |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `appeal_id` | `TEXT` | Required | `APP-2026-000001` .. `APP-2026-999999` | N/A | Primary Key, Unique | Regex: `^APP-2026-\d{6}$` | Unique appeal petition identifier | `APP-2026-000007` |
| `grade_id` | `TEXT` | Required | Valid `Grade.grade_id` | N/A | Foreign Key | Exists in `grades.csv` | Grade record being contested | `GRD-SUB-ASN-2026-000001-LRN-2026-000042-01` |
| `learner_id` | `TEXT` | Required | Valid `Learner.learner_id` | N/A | Foreign Key | Exists in `learners.csv` | Student filing petition | `LRN-2026-000042` |
| `submitted_at_utc`| `TEXT` | Required | ISO 8601 UTC timestamp | UTC Timestamp | Non-unique | Valid ISO 8601, $\ge \text{graded\_at\_utc}$| Appeal submission timestamp | `2026-10-19T14:10:00Z` |
| `reason` | `TEXT` | Required | Non-empty narrative justification | N/A | Non-unique | Length $\ge 5$ characters | Student argument for regrade review | `Submitted test logs demonstrating correct edge case.` |
| `status` | `TEXT` | Required | `PENDING`, `APPROVED`, `REJECTED` | N/A | Non-unique | Valid appeal status enum | Resolution decision status | `APPROVED` |
| `original_score`| `REAL` | Required | $\ge 0.0$ | Points | Non-unique | Equal to initial `Grade.final_score` | Original grade prior to appeal review | `78.50` |
| `updated_score` | `REAL` | Optional | $\ge 0.0$ | Points | Non-unique | Populated if `APPROVED`, empty if not | Revised score if petition granted | `86.00` |
| `audit_logged` | `TEXT` | Required | `True`, `False` | Boolean | Non-unique | Must be `True` if grade modified | Event audit compliance flag | `True` |

---

## 13. Ground Truth Labels (`ground_truth.csv`)
Exclusively isolated catalog of injected anomalies used for benchmark validation. **Never leaked into operational datasets.**

- **Primary Key**: `issue_id`

| Field Name | Data Type | Required / Optional | Allowed Values / Domain | Units | Key / Uniqueness | Validation Rule | Description | Sample Value |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `issue_id` | `TEXT` | Required | `ISSUE-2026-000001` .. `ISSUE-2026-999999` | N/A | Primary Key, Unique | Regex: `^ISSUE-2026-\d{6}$` | Unique issue label identifier | `ISSUE-2026-000001` |
| `issue_type` | `TEXT` | Required | `UNENROLLED_LEARNER_SUBMISSION`, `GRADE_EXCEEDS_MAX`, `DOUBLE_LATE_PENALTY`, `UNAUDITED_APPEAL_GRADE_CHANGE` | N/A | Non-unique | Valid anomaly enum | Anomaly category | `UNENROLLED_LEARNER_SUBMISSION` |
| `entity_name` | `TEXT` | Required | Operational entity name | N/A | Non-unique | Matches operational table | Name of entity containing flaw | `Submission` |
| `record_id` | `TEXT` | Required | Primary Key of target entity | N/A | Non-unique | Exists in operational CSV | Target record PK | `SUB-ASN-2026-000001-LRN-2026-000099-01` |
| `field_name` | `TEXT` | Required | Attribute name bearing anomaly | N/A | Non-unique | Exists in entity schema | Modified column name | `learner_id` |
| `expected_value`| `TEXT` | Required | Contractually expected value or rule | N/A | Non-unique | Text description / value | What rule requires | `ACTIVE_ENROLLMENT_REQUIRED` |
| `actual_value` | `TEXT` | Required | Injected corrupted value | N/A | Non-unique | Text description / value | Injected value observed | `LRN-2026-000099` |
| `description` | `TEXT` | Required | Human-readable explanation | N/A | Non-unique | Non-empty text | Root cause explanation | `Learner submitted for course without active enrollment.` |
