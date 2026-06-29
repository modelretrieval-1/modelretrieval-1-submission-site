# NTCIR-19 ModelRetrieval Submission System Requirements

## Purpose

The submission system accepts official NTCIR-19 ModelRetrieval run files from registered teams, validates them immediately, evaluates successful submissions internally, and gives organizers a private view of scores and leaderboards.

The system supports:

- Subtask A: Language Model Retrieval, evaluated with nDCG@1, nDCG@3, and nDCG@5.
- Subtask B: Image Style Transfer Model Retrieval, evaluated with MRR.

## Current Implementation Checkpoint

The project is entering Sprint 3.

Completed implementation:

- Sprint 0 foundation.
- Sprint 1 accounts and team setup.
- Sprint 2 ground-truth management, TREC_EVAL validation, participant upload UI, validation-failure persistence, and accepted submission/run persistence.

Current sprint target:

- Sprint 3 evaluation metrics and participant score display.

## Users and Roles

### Participant Team

Participants submit runs as a team. A team can submit to one or both subtasks if registered for them.

Participant teams can:

- Sign in using a shared team account.
- Upload run files for registered subtasks.
- See validation results immediately.
- See evaluation scores immediately after a successful submission.
- View their own successful submissions and scores.

### Organizer/Admin

Organizers administer the task and evaluation data.

Organizers can:

- Manage or import registered teams.
- Generate passwords for team accounts.
- Configure submission periods and deadlines in JST.
- Reopen a closed submission period when needed.
- Upload or configure ground-truth files.
- View all submissions and validation failures.
- View all scores.
- View a private leaderboard.
- Download all submissions as a bundle.
- Export leaderboard results as CSV.

## Registration Requirements

- The system must only accept submissions from teams already registered for NTCIR-19 ModelRetrieval.
- The system must know which subtasks each team is registered for.
- A team must not submit to a subtask unless registered for that subtask.
- Teams are identified by `team_id`.
- Each team has one shared account.
- Organizers add teams to the system and generate passwords.
- No additional manual approval step is required after the organizer creates the team account.

## Submission Periods

The system supports two submission turns:

- Normal submission period.
- Late submission period.

All deadline enforcement must use Japan Standard Time (JST, UTC+09:00).

Default deadlines:

- Normal submission: August 1, 2026 at 15:00 JST.
- Late submission: October 15, 2026 at 23:59 JST.

Participants can submit until they have one successful submission per subtask per submission turn. Failed validation attempts do not count as successful submissions.

For each team, subtask, and submission turn:

- A team may continue retrying while submissions fail validation.
- Once a submission succeeds, the system must prevent another successful submission for that same team, subtask, and turn.
- If a team attempts to submit again after a successful submission, the system must show an error.
- Organizers can reopen a submission period after it closes.

## Run Limits

Each subtask has its own run limit.

- A team may submit up to 5 runs for Subtask A in a successful submission.
- A team may submit up to 5 runs for Subtask B in a successful submission.
- If a submitted file or submission package contains more than 5 distinct runs for the selected subtask, the system must reject it immediately.
- Each subtask must be uploaded separately.
- Each upload is a single `.txt` file.
- Compressed files are not accepted.
- Maximum upload size is 10 MB.

## Submission File Format

Submissions must use TREC_EVAL format:

```text
topicID Q0 docID Rank Score RunID
```

Required validation:

- Each non-empty line must contain exactly 6 whitespace-separated fields.
- `topicID` must identify a valid query for the selected subtask and split.
- The second field must be exactly `Q0`.
- `docID` must identify a valid candidate model for the selected subtask.
- `Rank` must be a positive integer.
- `Score` must be numeric.
- `RunID` must be present and non-empty.
- The number of distinct `RunID` values must not exceed 5.
- The file must not include data for an unregistered or mismatched subtask.
- Every run must include all required test queries.
- Every query must include all candidate models for the selected subtask.
- Duplicate ranks within a query are allowed; ties are resolved by line order.
- Tied scores are allowed; ties are resolved by line order.
- The system must recompute ordering from `Score` and compare it with the submitted `Rank`.
- If ranking and score order disagree, the system should reject the submission with a warning-style validation message.

## Validation Behavior

The system must reject invalid submissions immediately.

When rejecting a file, the system should show actionable errors, including:

- Error type.
- Line number when applicable.
- Field name when applicable.
- Human-readable explanation.

Invalid submissions must not be evaluated and must not count as successful submissions.

## Evaluation Requirements

Evaluation must be implemented internally by the system.

Subtask A:

- Compute nDCG@1, nDCG@3, and nDCG@5.
- Use organizer-provided ground truth for hidden test queries.
- Ground truth relevance is derived from relative F1 according to the task specification.
- Macro-average nDCG equally across queries.
- Treat nDCG@3 and nDCG@5 as official primary metrics.

Subtask B:

- Compute MRR.
- Use organizer-provided ground truth for hidden test queries.
- Each query has one relevant model.

Participants should see their scores immediately after a successful submission.

## Ground Truth Management

Organizers must be able to upload or configure ground-truth data in the system.

Ground-truth data must be protected from participant access.

Ground-truth files are stored on the server local filesystem.

The system should record:

- Who uploaded or configured the ground truth.
- Upload/configuration time.
- Subtask.
- Submission turn or evaluation phase, if applicable.
- File checksum or version identifier.

## Leaderboard Requirements

The leaderboard is private and visible only to organizers/admins.

The leaderboard should support:

- Filtering by subtask.
- Filtering by submission turn.
- Indicating whether each result is normal or late.
- Sorting by official metric.
- Viewing team, run ID, submission time, and metric values.
- CSV export.

Participants must not see the global leaderboard.

All 5 runs in a successful submission are official runs; organizers do not need to select a single official run.

## Audit and Traceability

The system should retain:

- All successful submissions.
- Failed validation attempts and validation errors.
- Evaluation results.
- Ground-truth versions.
- Submission timestamps in JST.
- User/team identity for each action.

## Non-Functional Requirements

- Deadline checks must be deterministic and based on server-side time.
- Evaluation must be reproducible for a given submission and ground-truth version.
- Participants must never be able to access hidden ground-truth files.
- Error messages should be clear enough for participants to fix format issues without organizer support.
- Organizer pages should prioritize fast inspection of submissions, scores, and validation failures.
- The system does not send automatic email notifications for successful or failed submissions; organizers contact participants manually when needed.
- Submission files and validation failures are retained forever unless organizers delete them manually in a future maintenance workflow.
- Submission files do not need encryption at rest.
- Participant-visible scores stay visible after evaluation. The system does not support participant re-upload after a successful submission.

## Recommended Technical Stack

Use a lightweight server-rendered web application:

- Backend/web framework: FastAPI with Jinja2 templates.
- Database: SQLite.
- File storage: server local filesystem for submissions, ground truth, and exported bundles.
- Public deployment: VPS-hosted application with a reverse proxy and HTTPS.

This keeps the system simple while still supporting server-side validation, internal evaluation, local file storage, and password-based accounts.
