# NTCIR-19 ModelRetrieval Submission System Requirements

Document role: this file is the source of truth for stable product requirements and policy rules. Use `../../HANDOFF.md` for detailed current implementation status.

## Purpose

The submission system accepts official NTCIR-19 ModelRetrieval run files from registered teams, validates them immediately, evaluates successful submissions internally, and gives organizers a private view of scores and leaderboards.

The system supports:

- Subtask A: Language Model Retrieval, evaluated with nDCG@1, nDCG@3, and nDCG@5.
- Subtask B: Image Style Transfer Model Retrieval, evaluated with MRR.

## Implementation Status

The main product scope is implemented and the current work is production hardening. Use `../../HANDOFF.md` for the detailed current implementation checkpoint.

## Users and Roles

### Participant Team

Participants submit runs as a team. A team can submit to one or both subtasks if registered for them.

Participant teams can:

- Sign in using a shared team account.
- Change their shared team account password after signing in.
- Upload run files for registered subtasks.
- See validation results immediately.
- See evaluation state after a valid upload and scores after asynchronous evaluation completes.
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
- Participants can change the shared team account password after signing in by entering the current password and confirming the new password.
- Organizer password regeneration remains available and invalidates the previous team password.
- No additional manual approval step is required after the organizer creates the team account.

## Submission Periods

The system supports two submission turns:

- Normal submission period.
- Late submission period.

All deadline enforcement must use Japan Standard Time (JST, UTC+09:00).

Default deadlines:

- Normal submission: August 1, 2026 at 15:00 JST.
- Late submission: October 15, 2026 at 23:59 JST.

Participants can submit until they have one current successful submission per subtask per submission turn. Failed validation attempts do not count as successful submissions.

For each team, subtask, and submission turn:

- The participant must explicitly choose the submission turn, `normal` or `late`, when uploading.
- The system must not automatically choose normal or late based only on the current time.
- The selected submission turn must be open at upload time, or reopened by organizer override.
- A team may continue retrying while submissions fail validation.
- Once a submission succeeds, the system must prevent another successful submission for that same team, subtask, and turn unless an organizer grants one-time replacement-upload permission.
- If a team attempts to submit again after a successful submission without organizer permission, the system must show an error.
- If an organizer grants replacement-upload permission, the participant can upload again while the selected period is open or reopened.
- Previous metrics for that team, subtask, and period must not be participant-visible while replacement-upload permission is pending or after a replacement succeeds.
- A successful replacement submission becomes the current participant-visible submission and supersedes the previous successful submission.
- Failed replacement validation attempts do not consume replacement-upload permission.
- Organizers can reopen a submission period after it closes.
- Participant-facing dashboard and upload pages must display the currently configured period deadlines and reopen state, not hardcoded default deadline text.

## Run Limits

Each subtask has its own run limit.

- A team may submit up to 5 runs for Subtask A in a successful submission.
- A team may submit up to 5 runs for Subtask B in a successful submission.
- If a submitted file or submission package contains more than 5 distinct runs for the selected subtask, the system must reject it immediately.
- Each subtask must be uploaded separately.
- Each upload is a single file.
- Filename extensions are not used to accept or reject submissions.
- The system must validate the uploaded file by reading its content as TREC_EVAL text.
- Files with any extension, or no extension, are accepted when their content satisfies the submission format.
- Maximum upload size is 500 MB. This limit is enforced server-side and is not displayed as participant-facing upload guidance.

## Submission File Format

Submissions must use TREC_EVAL format:

```text
topicID Q0 docID Rank Score RunID
```

Required validation:

- Each non-empty line must contain exactly 6 whitespace-separated fields.
- `topicID` must identify a valid query for the selected subtask and split.
- For Subtask B, `topicID` is the query `image_id` and matches ground truth with or without a trailing `.png` suffix on either side.
- For Subtask B, `docID` is the candidate `model_id` and numeric values match ground truth with or without left zero-padding on either side.
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
- Query image IDs match ground truth with an optional `.png` suffix ignored on either side.
- Numeric model IDs match ground truth with left zero-padding ignored on either side.

Participants should see the submission state after a valid upload and their scores
as soon as asynchronous evaluation completes.
Participant-visible scores must remain run-level aggregate scores only.

The system should also retain per-query metric details for organizer diagnostics:

- Subtask A: per-query nDCG@1, nDCG@3, and nDCG@5 for each RunID and query.
- Subtask B: per-query reciprocal rank for each RunID and query.
- Per-query metric details are organizer-only and must not be visible to participant teams.
- The private leaderboard and leaderboard CSV export should continue to use aggregate run-level metrics unless a later requirement explicitly changes them.
- UI score tables should present metric names as columns where practical, rather than repeating one row per metric.

## Ground Truth Management

Organizers must be able to upload or configure ground-truth data in the system.

Organizers must be able to download the preserved original file for each stored
ground-truth version. Ground-truth downloads must require organizer authentication
and must not be available through participant or public static-file routes.

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

- Filtering by team.
- Filtering by subtask.
- Filtering by submission turn.
- Indicating whether each result is normal or late.
- Sorting by official metric.
- Sorting interactively by any displayed column.
- Viewing team, run ID, submission time, and metric values.
- CSV export.

Participants must not see the global leaderboard.
Participants must not see organizer-only per-query metric details.

All 5 runs in a successful submission are official runs; organizers do not need to select a single official run.

## Audit and Traceability

The system should retain:

- All successful submissions.
- Failed validation attempts and validation errors.
- Evaluation results.
- Organizer-only per-query evaluation results.
- Ground-truth versions.
- Submission timestamps in JST.
- User/team identity for each action.

The MVP audit trail records authentication, account changes, submission lifecycle
transitions, replacement permissions, submission-period changes, ground-truth
uploads/activation/downloads, and organizer exports/bundle downloads. Audit events
are append-only and use the `audit_events` table; passwords, session cookies, and
uploaded file contents must not be included in event metadata.

Organizers must be able to browse the audit trail through a protected, read-only
admin page with event-type, actor, entity, date-range, and paginated filtering.
Participant teams must not be able to access audit events.

## Non-Functional Requirements

- Deadline checks must be deterministic and based on server-side time.
- Evaluation must be reproducible for a given submission and ground-truth version.
- Participants must never be able to access hidden ground-truth files.
- Error messages should be clear enough for participants to fix format issues without organizer support.
- Organizer pages should prioritize fast inspection of submissions, scores, and validation failures.
- The system does not send automatic email notifications for successful or failed submissions; organizers contact participants manually when needed.
- Submission files and validation failures are retained forever unless organizers delete them manually in a future maintenance workflow.
- Submission files do not need encryption at rest.
- Participant-visible scores stay visible after evaluation unless an organizer grants replacement-upload permission for that team, subtask, and period. Superseded scores are organizer-only.

## UI and Frontend Requirements

The application remains a server-rendered FastAPI/Jinja2 app. The completed UI modernization improves clarity and usability without introducing a single-page application framework or frontend build pipeline.

The active UI flow is documented in `../ui/ui-flow.md`. The product should feel more like an application console than a collection of standalone web pages.

Implemented UI direction:

- Use Bootstrap 5 for the core CSS/component foundation.
- Use a small local stylesheet for project-specific spacing, density, status colors, and task branding.
- Use Bootstrap components for navigation, forms, tables, alerts, badges, button groups, dropdowns, and responsive layout.
- Keep pages operational and scan-friendly, especially organizer pages that contain filters, submissions, validation errors, and leaderboard data.
- Avoid marketing-style layouts, decorative hero sections, and visual noise.
- Prefer accessible semantic HTML, visible labels, clear focus states, and readable validation messages.
- Use consistent status badges for submission states, period states, subtasks, and evaluation states.
- Keep JavaScript minimal and optional. Use Bootstrap's bundled JavaScript only where needed for navigation or simple components.
- Do not introduce React, Vue, or a separate frontend build step for this phase.

Planned application UI direction:

- Add a shared authenticated app shell.
- Use persistent role-aware navigation.
- Use a desktop sidebar and compact top bar.
- Use a collapsed mobile navigation menu.
- Make `/admin` a richer organizer operations dashboard.
- Make `/team` a clearer participant submission-status dashboard.
- Normalize page headers, filters, actions, status badges, and tables.
- Preserve all existing backend behavior, permissions, routes, and server-rendered architecture unless a later document explicitly changes them.

## Recommended Technical Stack

Use a lightweight server-rendered web application:

- Backend/web framework: FastAPI with Jinja2 templates.
- UI/component foundation: Bootstrap 5 with local project CSS.
- Database: SQLite.
- File storage: server local filesystem for submissions, ground truth, and exported bundles.
- Public deployment: VPS-hosted application with a reverse proxy and HTTPS.

This keeps the system simple while still supporting server-side validation, internal evaluation, local file storage, and password-based accounts.
