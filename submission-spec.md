# Submission Specification

## Supported Subtasks

The system supports two independent subtasks:

- Subtask A: Pre-trained BERT Model Retrieval.
- Subtask B: Image Style Transfer LoRA Model Retrieval.

Each subtask has its own submission limit of up to 5 runs per team per submission turn.

Each upload must be a single `.txt` file. Zip files and other compressed formats are not accepted.

Maximum upload size: 10 MB.

## Current Implementation Checkpoint

Current upload behavior is implemented:

- Team upload pages exist for registered subtasks.
- Participants explicitly choose normal or late submission during upload.
- Uploads are limited to one `.txt` file.
- Non-`.txt` files and oversized files are rejected immediately.
- TREC_EVAL parser and validation rules are implemented.
- Active ground truth supplies required query and candidate model IDs.
- Failed validation attempts are persisted as `rejected` submissions with `validation_errors`.
- Valid submissions are persisted with run metadata, evaluated immediately, and shown to the participant with scores.
- One successful submission is enforced per team, subtask, and selected submission turn.
- Organizers can review submitted attempts and inspect validation errors or run metrics.
- Organizers can view a private leaderboard of evaluated run metrics.
- Organizers can export leaderboard rows as CSV.
- Organizers can download submission bundles with metadata and stored files.

Next implementation focus: production deployment documentation.

## Submission Turns

The system supports:

- Normal submission.
- Late submission.

All submission windows and deadlines are enforced in JST.

For each team, subtask, and submission turn, only one successful submission is allowed. Participants may retry until validation succeeds.

Participants choose the submission turn explicitly during upload. The system validates the selected turn against its JST deadline and organizer reopen override. The system must not automatically assign normal or late based only on server time.

Default deadlines in JST:

- Normal submission: August 1, 2026 at 15:00.
- Late submission: October 15, 2026 at 23:59.

## File Format

Every run must use TREC_EVAL format:

```text
topicID Q0 docID Rank Score RunID
```

Example:

```text
1 Q0 1 1 0.99 Run01
1 Q0 7 2 0.95 Run01
```

## Field Rules

| Field | Rule |
|---|---|
| `topicID` | Must be a valid query/task ID for the selected subtask. |
| `Q0` | Must be exactly `Q0`. |
| `docID` | Must be a valid candidate model ID for the selected subtask. |
| `Rank` | Must be a positive integer where `1` is the highest rank. |
| `Score` | Must be a numeric predicted score. |
| `RunID` | Must identify the submitted run. |

## Run Count Rule

A submission may contain at most 5 distinct `RunID` values for the selected subtask.

If more than 5 distinct run IDs are present, the system rejects the submission immediately.

## Recommended Additional Validation Rules

Required validation rules:

- A `(RunID, topicID, docID)` combination must not appear more than once.
- A run must include every required test query.
- Every query must include all candidate models for the selected subtask.
- Missing required queries or candidate models must reject the submission.
- Duplicate ranks within a query are allowed.
- Tied scores are allowed.
- When ranks or scores are tied, line order is used as the tie-breaker.
- The system recomputes the expected ordering from `Score`, using line order for ties, and compares it with the submitted `Rank`.
- If submitted ranks disagree with score-derived ordering, the submission is rejected with a warning-style validation message.
- Lines with only whitespace should be ignored.

## Rejection Behavior

Invalid submissions are rejected immediately and are not evaluated.

The system should report:

- File-level errors.
- Line-level errors.
- The first several errors plus a total error count if the file has many issues.

Examples:

- `Line 12: expected 6 fields, found 5.`
- `Line 20: field 2 must be Q0.`
- `Line 41: docID 999 is not a valid Subtask A model ID.`
- `Submission contains 6 run IDs; maximum is 5.`
- `Run01 is missing topicID 48.`
- `Run02 topicID 14 is missing model ID 20.`
- `Run03 topicID 5 rank order does not match score order.`

## Successful Submission Record

For each successful submission, store:

- Team ID.
- Subtask.
- Submission turn.
- Uploaded filename.
- Submission timestamp in JST.
- Run IDs.
- File checksum.
- Validation status.
- Evaluation status.
- Evaluation score summary.
