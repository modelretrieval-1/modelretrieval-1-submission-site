# NTCIR-19 ModelRetrieval Submission System User Stories

## Current Implementation Checkpoint

Implemented through the latest Sprint 4 slice:

- Team and organizer login.
- Organizer team and organizer-user management.
- Organizer ground-truth upload, validation, activation, and history.
- Participant upload UI for registered subtasks.
- Participant-selected normal/late upload period.
- Immediate validation errors and persisted rejected attempts.
- Accepted submission/run persistence.
- Accepted submission evaluation and participant score display.
- Organizer submissions table and detail view.
- Organizer private leaderboard view.
- Leaderboard CSV export.

Next story: submission bundle download.

## Participant Team Stories

### Team Access

As a participant team, I want to access the submission system using my registered team identity so that only official NTCIR-19 ModelRetrieval teams can submit runs.

Acceptance criteria:

- The system recognizes teams by `team_id`.
- Each team uses one shared account.
- The system blocks unknown or unregistered teams.
- The system knows which subtasks the team is registered for.

### Select Subtask

As a participant team, I want to choose Subtask A or Subtask B before uploading a submission so that the system validates and evaluates the file against the correct rules.

Acceptance criteria:

- Only registered subtasks are selectable.
- The selected subtask is recorded with the submission.
- Files are validated against the selected subtask's query IDs and model IDs.

### Submit Runs During Normal Period

As a participant team, I want to upload my normal-period run file so that I can receive official evaluation scores.

Acceptance criteria:

- The team explicitly selects the normal period when uploading.
- Upload is allowed before the normal submission deadline in JST.
- The default normal submission deadline is August 1, 2026 at 15:00 JST.
- Invalid files are rejected immediately.
- Failed validation attempts do not count as successful submissions.
- Once a file succeeds, the team cannot submit another successful file for the same subtask and normal period.

### Submit Runs During Late Period

As a participant team, I want to upload my late-period run file so that I can participate in late submission evaluation.

Acceptance criteria:

- The team explicitly selects the late period when uploading.
- Upload is allowed before the late submission deadline in JST.
- The default late submission deadline is October 15, 2026 at 23:59 JST.
- The late period is tracked separately from the normal period.
- One successful submission is allowed per team, subtask, and late period.

### Choose Submission Period

As a participant team, I want to choose normal or late submission during upload so that the submission is recorded under the intended turn.

Acceptance criteria:

- The upload form includes a submission-period selector.
- The system records the selected period with the submission.
- The system rejects a selected period if it is closed and no organizer override is active.
- The system does not automatically switch a selected normal submission into late, or a selected late submission into normal.
- If both periods are open because of organizer override, the participant's selected period is used.

### Understand Validation Errors

As a participant team, I want line-level validation errors so that I can quickly fix my submission file.

Acceptance criteria:

- The system rejects invalid files immediately.
- Errors include line numbers when applicable.
- Errors explain invalid field counts, invalid `Q0`, invalid IDs, invalid ranks, invalid scores, too many runs, missing queries, missing candidate models, or ranking/score-order mismatches.

### See My Scores

As a participant team, I want to see my evaluation score immediately after a successful submission so that I can confirm my result.

Acceptance criteria:

- Subtask A submissions show nDCG@1, nDCG@3, and nDCG@5.
- Subtask B submissions show MRR.
- The system shows the submission timestamp and run IDs.
- Participants can only see their own scores.

## Organizer/Admin Stories

### Manage Registered Teams

As an organizer, I want to configure registered teams and their eligible subtasks so that only valid participants can submit.

Acceptance criteria:

- Organizers can add, update, or disable registered teams.
- Organizers can generate a password for each shared team account.
- Generated passwords may be shown to organizers.
- Each team can be associated with Subtask A, Subtask B, or both.
- Disabled or unregistered teams cannot submit.
- No additional manual approval is required after team creation.

### Manage Organizer Accounts

As an organizer, I want to manage organizer accounts so that multiple admins can operate the submission system.

Acceptance criteria:

- Organizers sign in with password login.
- Organizer accounts can change their own password.
- Authorized organizers can add another organizer account.
- New organizer accounts can be created with a generated password.
- Multi-factor authentication is not required.

### Configure Deadlines

As an organizer, I want to configure normal and late submission deadlines in JST so that the system enforces the official schedule automatically.

Acceptance criteria:

- Deadline configuration stores timezone explicitly as JST.
- The server enforces deadlines.
- Participants receive clear errors when submissions are closed.
- Organizers can reopen a closed submission period.

### Upload Ground Truth

As an organizer, I want to upload or configure ground-truth files so that the system can evaluate submissions internally.

Acceptance criteria:

- Ground truth can be uploaded per subtask.
- The system validates the ground-truth file before activation.
- Ground-truth versions are tracked.
- Participants cannot access ground-truth data.
- Ground-truth files are stored on the server local filesystem.

### Review Submissions

As an organizer, I want to review all submissions and validation failures so that I can monitor participation and support teams.

Acceptance criteria:

- Organizers can filter by team, subtask, period, status, and submission time.
- Organizers can inspect validation errors.
- Organizers can download submitted files.

### View Private Leaderboard

As an organizer, I want a private leaderboard so that I can compare team performance without exposing rankings to participants.

Acceptance criteria:

- The leaderboard is visible only to organizers/admins.
- It supports Subtask A and Subtask B.
- It supports normal and late submission periods.
- It clearly indicates whether each row is from the normal or late period.
- It shows team, run ID, metrics, and submission timestamp.
- It can be exported as CSV.

### Verify Evaluation Results

As an organizer, I want to inspect evaluation results from the system so that I can confirm scores before using them in official reporting.

Acceptance criteria:

- Organizers can view metric values per run.
- Organizers can see which ground-truth version was used.
- Organizers can rerun evaluation if ground truth is replaced or corrected.

### Download Submission Bundle

As an organizer, I want to download all submitted files as a bundle so that I can archive and inspect official submissions outside the system.

Acceptance criteria:

- Organizers can download submissions filtered by subtask and submission period.
- The bundle includes submission files and metadata.
- Both normal and late submissions can be included or separated.

### Retain Records

As an organizer, I want submissions and validation failures to be retained indefinitely so that the task has a complete audit record.

Acceptance criteria:

- Successful submissions are retained forever.
- Failed validation attempts are retained forever.
- Evaluation records are retained forever.
- Ground-truth version records are retained forever.
