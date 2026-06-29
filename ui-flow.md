# UI Flow

## Purpose

This document defines the first version of the NTCIR-19 ModelRetrieval submission system interface.

The UI should be simple, operational, and fast to scan. It is not a marketing site. The first screen should help users sign in and submit or administer runs.

## Current Implementation Checkpoint

Implemented through Sprint 2:

- Login/logout.
- Team dashboard with registered subtask upload links.
- Organizer dashboard.
- Organizer team management.
- Organizer user management.
- Organizer password change.
- Organizer ground-truth upload, validation, activation, and history.
- Organizer submission-period controls.
- Participant upload form for registered subtasks.
- Immediate validation error display.

Sprint 3 has added participant score display after accepted uploads and latest team-dashboard score summaries.

## Roles

The system has two user-facing roles:

- Participant team.
- Organizer/admin.

Each role has a separate dashboard after login.

## Shared Pages

### Login

URL:

- `/login`

Purpose:

- Allow teams and organizers to sign in.

Fields:

- User ID.
- Password.

Behavior:

- If the user ID belongs to a team, redirect to the team dashboard.
- If the user ID belongs to an organizer, redirect to the organizer dashboard.
- If credentials are invalid, show a generic login error.

Required states:

- Empty form.
- Invalid credentials.
- Signed-out confirmation.
- Session expired.

### Change Password

URL:

- `/account/password`

Purpose:

- Allow signed-in organizers to change their password.
- Optional for teams in v1 unless implementation is simple.

Fields:

- Current password.
- New password.
- Confirm new password.

Required states:

- Success.
- Current password incorrect.
- New password confirmation mismatch.

## Participant Team Flow

### Team Dashboard

URL:

- `/team`

Purpose:

- Show the team's allowed subtasks, submission status, deadlines, and scores.

Content:

- Team ID.
- Registered subtasks.
- Normal submission deadline: August 1, 2026 at 15:00 JST.
- Late submission deadline: October 15, 2026 at 23:59 JST.
- Submission status for each registered subtask and period.
- Link to upload page for open periods without a successful submission.
- Links to score pages for successful submissions.

Status labels:

- Not submitted.
- Validation failed.
- Submitted and evaluated.
- Closed.
- Reopened by organizer.

Actions:

- Upload Subtask A submission.
- Upload Subtask B submission.
- View results.
- Logout.

### Upload Submission

URL:

- `/team/submissions/new`

Purpose:

- Let a team upload one `.txt` submission file for one registered subtask and one active submission period.

Inputs:

- Subtask selector: A or B, limited to registered subtasks.
- Submission period selector: normal or late, limited to currently open periods.
- File input accepting `.txt`.

Rules shown near the form:

- One `.txt` file only.
- Maximum file size: 10 MB.
- Up to 5 `RunID` values.
- TREC_EVAL format: `topicID Q0 docID Rank Score RunID`.
- Every run must include all test queries.
- Every query must include all candidate models.
- After a successful submission, no re-upload is allowed for that subtask and period.

Submit behavior:

- Upload file.
- Validate immediately.
- If validation passes, evaluate immediately.
- Redirect to results page.
- If validation fails, show validation errors.

Required states:

- Upload form.
- File too large.
- Wrong file type.
- Submission period closed.
- Team not registered for selected subtask.
- Already successfully submitted.
- Validation failed.
- Evaluation succeeded.
- Evaluation failed due to organizer/system configuration.

### Validation Error Result

URL:

- `/team/submissions/{submission_id}/errors`

Purpose:

- Show why the upload was rejected.

Content:

- Submission timestamp in JST.
- Selected subtask.
- Submission period.
- Uploaded filename.
- Overall error summary.
- Error table.

Error table columns:

- Line.
- Field.
- Code.
- Message.

Behavior:

- Show the first set of detailed errors if there are many.
- Show total error count.
- Make clear that failed validation attempts do not count as successful submissions.
- Provide a link back to upload again if the period is still open.

### Participant Results

URL:

- `/team/submissions/{submission_id}`

Purpose:

- Show the team's successful submission and scores.

Content:

- Team ID.
- Subtask.
- Submission period: normal or late.
- Submitted timestamp in JST.
- Uploaded filename.
- File checksum.
- Run-level score table.

Subtask A score columns:

- RunID.
- nDCG@1.
- nDCG@3.
- nDCG@5.

Subtask B score columns:

- RunID.
- MRR.

Behavior:

- Participants can only view their own submissions.
- Scores remain visible after evaluation.
- No re-upload action appears after successful submission.

## Organizer Flow

### Organizer Dashboard

URL:

- `/admin`

Purpose:

- Provide a compact overview of task operations.

Content:

- Number of active teams.
- Number of successful submissions by subtask and period.
- Number of validation failures.
- Active ground-truth version for each subtask.
- Deadline status for normal and late periods.

Actions:

- Manage teams.
- Manage organizer users.
- Upload ground truth.
- View submissions.
- View leaderboard.
- Export CSV.
- Download submission bundle.
- Configure periods.

### Team Management

URL:

- `/admin/teams`

Purpose:

- Add and manage registered teams.

Content:

- Team list.
- Team ID.
- Display name.
- Registered subtasks.
- Active status.
- Created timestamp.
- Last login timestamp.

Actions:

- Add team.
- Generate password.
- Enable or disable team.
- Edit registered subtasks.

Add team fields:

- Team ID.
- Display name.
- Registered subtasks: A, B, or both.

Generated password behavior:

- Password may be displayed to organizers.
- Only password hash is stored.
- Regenerating a password invalidates the previous one.

### Organizer User Management

URL:

- `/admin/users`

Purpose:

- Add and manage organizer accounts.

Content:

- Organizer list.
- Username.
- Display name.
- Active status.
- Created timestamp.
- Last login timestamp.

Actions:

- Add organizer.
- Generate password.
- Disable organizer.

Fields:

- Username.
- Display name.

### Submission Period Management

URL:

- `/admin/periods`

Purpose:

- Configure normal and late submission windows.

Content:

- Period name.
- Deadline in JST.
- Current status.
- Reopen override.

Actions:

- Edit deadline.
- Reopen closed period.
- Close reopened period.

Required states:

- Open.
- Closed by deadline.
- Reopened by organizer.

### Ground Truth Management

URL:

- `/admin/ground-truth`

Purpose:

- Upload, validate, activate, and inspect ground-truth versions.

Inputs:

- Subtask selector.
- Ground-truth file upload.
- Version label.
- Notes.

Content:

- Active ground-truth version per subtask.
- Ground-truth version history.
- Upload timestamp in JST.
- Uploaded by.
- File checksum.
- Validation status.

Actions:

- Upload ground truth.
- Activate version.
- View validation summary.
- Trigger re-evaluation if supported.

Required states:

- No ground truth uploaded.
- Upload validation failed.
- Uploaded but inactive.
- Active.

### Submissions Table

URL:

- `/admin/submissions`

Purpose:

- Inspect all successful and failed submission attempts.

Filters:

- Team ID.
- Subtask.
- Submission period.
- Status.
- Date range.

Columns:

- Submitted timestamp in JST.
- Team ID.
- Subtask.
- Period.
- Status.
- Filename.
- File size.
- Run count.
- Ground-truth version.

Actions:

- View details.
- Download original file.
- View validation errors.
- View scores.

### Submission Detail

URL:

- `/admin/submissions/{submission_id}`

Purpose:

- Show all metadata for one submission attempt.

Content:

- Team ID.
- Subtask.
- Period.
- Status.
- Uploaded filename.
- Stored file path.
- File checksum.
- Submitted timestamp in JST.
- Validation summary.
- Run IDs.
- Scores, if evaluated.
- Ground-truth version used.

Actions:

- Download original file.
- View validation errors.
- Re-run evaluation if allowed.

### Private Leaderboard

URL:

- `/admin/leaderboard`

Purpose:

- Show organizer-only rankings across teams and runs.

Filters:

- Subtask.
- Submission period: normal, late, or all.
- Ground-truth version.

Subtask A columns:

- Rank.
- Team ID.
- RunID.
- Period.
- nDCG@1.
- nDCG@3.
- nDCG@5.
- Submitted timestamp in JST.

Subtask B columns:

- Rank.
- Team ID.
- RunID.
- Period.
- MRR.
- Submitted timestamp in JST.

Sorting:

- Subtask A: nDCG@5, then nDCG@3, then nDCG@1.
- Subtask B: MRR.

Actions:

- Export CSV.
- Download submission bundle for current filters.

Visibility:

- Organizer/admin only.
- Participants must not see this page.

### Export and Bundle Download

URL:

- `/admin/exports`

Purpose:

- Create downloadable task records.

Export types:

- Leaderboard CSV.
- Submission metadata CSV.
- Submission files bundle.
- Validation failures CSV.

Filters:

- Subtask.
- Submission period.
- Team ID.
- Status.

Behavior:

- Generated files are stored on the server local filesystem.
- Downloads require organizer login.
- Export and bundle actions are recorded in audit events.

## Error Pages

### Forbidden

Purpose:

- Show when a team or organizer attempts to access an unauthorized page.

Examples:

- Team tries to access admin page.
- Team tries to view another team's submission.
- Organizer-only export accessed by a participant.

### Not Found

Purpose:

- Show when a requested submission, team, or file does not exist or is not visible to the current user.

### System Configuration Error

Purpose:

- Show when a participant uploads a valid file but evaluation cannot run because organizer setup is incomplete.

Examples:

- No active ground truth for the selected subtask.
- Missing query or model metadata configuration.

## Navigation

Participant navigation:

- Dashboard.
- Submissions/results.
- Change password, if enabled.
- Logout.

Organizer navigation:

- Dashboard.
- Teams.
- Organizer users.
- Periods.
- Ground truth.
- Submissions.
- Leaderboard.
- Exports.
- Change password.
- Logout.

## MVP Screen Set

The first coding milestone should include:

- Login.
- Team dashboard.
- Upload submission.
- Validation error result.
- Participant results.
- Organizer dashboard.
- Team management.
- Ground-truth upload.
- Submissions table.
- Private leaderboard.

The second milestone can add:

- Organizer user management.
- Submission period editing.
- Export center.
- Bundle download.
- Re-evaluation controls.
