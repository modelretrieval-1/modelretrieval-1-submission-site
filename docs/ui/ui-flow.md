# UI Flow

## Purpose

This document defines the NTCIR-19 ModelRetrieval submission system interface.

The UI should be simple, operational, and fast to scan. It is not a marketing site. The first screen should help users sign in and submit or administer runs.

## Implementation Status

The main UI flow is implemented. Use `../../HANDOFF.md` for the detailed current implementation checkpoint and remaining production-hardening work.

## Application UI Redesign

The implemented UI slice makes the system feel like an application rather than a set of separate web pages.

Historical implementation record:

- `../archive/app-ui-redesign.md`

Current decisions:

- Keep FastAPI, Jinja2, Bootstrap 5, and local CSS.
- Continue the authenticated app shell with persistent role-aware navigation.
- Use a sidebar and compact top bar for organizer and participant workflows.
- Treat `/admin` as the organizer operations dashboard.
- Treat `/team` as the participant submission-status dashboard.
- Keep pages dense, operational, and scan-friendly.
- Do not add React, Vue, or a frontend build pipeline.
- Do not turn the app into a marketing-style site.

## UI Modernization Direction

The UI modernization slice improved the existing server-rendered pages rather than replacing the frontend architecture.

Decision:

- Keep FastAPI and Jinja2 templates.
- Use Bootstrap 5 as the primary CSS/component foundation.
- Keep a local `app/static/app.css` file for project-specific polish.
- Do not add React, Vue, or a separate JavaScript build pipeline in this phase.
- Use minimal JavaScript, limited to Bootstrap components or small progressive enhancements.

Design goals:

- Make the application feel like a reliable operations console for a research task.
- Improve navigation so teams and organizers always know where they are.
- Make upload, account, team, ground-truth, period, submission, and leaderboard forms easier to scan and submit.
- Make organizer tables denser, clearer, and easier to filter.
- Make validation errors and evaluation results visually distinct.
- Preserve accessibility through semantic HTML, form labels, focus states, and color-independent status text.

Current visual system:

- Top navigation with role-aware links and active page state.
- Constrained main content width with consistent vertical rhythm.
- Bootstrap forms, inputs, selects, file inputs, buttons, alerts, tables, badges, cards only where they frame a specific object or repeated item.
- Status badges for `rejected`, `accepted`, `evaluated`, `evaluation_failed`, `normal`, `late`, `open`, `closed`, and `reopened`.
- Compact filter toolbars for organizer submissions and leaderboard pages.
- Clear primary and secondary actions on every form.

Target visual system for the application redesign:

- Persistent left sidebar on desktop.
- Collapsed menu navigation on mobile.
- Compact top bar with signed-in identity and logout action.
- Main content workspace with consistent page headers, action placement, filters, and tables.
- Dashboard summary cards only for meaningful operational status.
- Role-aware navigation groups for organizer and participant tasks.

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

UI modernization notes:

- Use a compact centered login form.
- Keep the service name and task context visible.
- Use Bootstrap form controls and alert styling for invalid credentials or signed-out messages.

### Change Password

URL:

- `/account/password`

Purpose:

- Allow signed-in organizers to change their own password.
- Allow signed-in participant teams to change their shared team account password.

Fields:

- Current password.
- New password.
- Confirm new password.

Required states:

- Success.
- Current password incorrect.
- New password confirmation mismatch.
- Signed-in organizer changing organizer password.
- Signed-in team changing team password.

UI modernization notes:

- Use consistent form grouping, password fields, and success/error alerts.
- Place submit and cancel/navigation actions predictably at the bottom of the form.
- In the application shell, show the password page in both organizer and participant navigation.

## Participant Team Flow

### Team Dashboard

URL:

- `/team`

Purpose:

- Show the team's allowed subtasks, submission status, deadlines, and scores.

Content:

- Team ID.
- Registered subtasks.
- Current normal submission deadline from the configured submission-period row.
- Current late submission deadline from the configured submission-period row.
- Reopen status for each configured submission period.
- Submission status for each registered subtask and period.
- Link to upload page for open periods without a current successful submission, or when organizer-approved replacement permission is pending.
- Links to current score summaries for successful submissions.

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

UI modernization notes:

- Present registered subtasks and normal/late periods as compact status sections.
- Use badges for period and submission status.
- Make upload actions visually available only when the selected subtask/period can accept a successful submission or an organizer-approved replacement upload.

### Upload Submission

URL:

- `/team/submissions/new`

Purpose:

- Let a team upload one submission file for one registered subtask and one selected submission period.

Inputs:

- Subtask selector: A or B, limited to registered subtasks.
- Submission period selector: normal or late.
- File input accepting any filename extension.

Rules shown near the form:

- One file only.
- Maximum file size: 10 MB.
- Filename extension is not checked; the content must be valid TREC_EVAL text.
- Up to 5 `RunID` values.
- TREC_EVAL format: `topicID Q0 docID Rank Score RunID`.
- Every run must include all test queries.
- Every query must include all candidate models.
- After a successful submission, no re-upload is allowed for that subtask and period unless an organizer grants one-time replacement-upload permission.
- The selected period is used as submitted; the system does not auto-switch normal and late.
- Closed periods are rejected unless organizer reopen override is active.

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

UI modernization notes:

- Group subtask, period, and file inputs in one clear form.
- Show period deadlines and reopen status near the period selector.
- Use Bootstrap file input, helper text, and alert components.
- Keep the validation rules visible but compact.

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

UI modernization notes:

- Use an error summary alert followed by a readable table.
- Keep line number, field, code, and message columns easy to scan.
- Use status badges for severity and submission state.

### Participant Results

URL:

- `/team/submissions/{submission_id}`

Purpose:

- Show the team's current successful submission and scores.

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
- Participants see aggregate run-level metrics only.
- Participants do not see per-query metric details.
- No re-upload action appears after successful submission unless organizer-approved replacement permission is pending.

UI modernization notes:

- Use a concise metadata summary and a score table.
- Highlight official metric columns without hiding secondary metrics.
- Keep organizer-only per-query diagnostics out of participant views.

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
- Aggregate run-level scores, if evaluated.
- Organizer-only per-query metric diagnostics, if evaluated.
- Ground-truth version used.

Metric display:

- Display aggregate run-level scores as a pivoted table, not one row per metric.
- Use one row per `RunID`.
- Use metric names as columns.
- For Subtask A, aggregate metric columns should be `nDCG@1`, `nDCG@3`, and `nDCG@5`.
- For Subtask B, the aggregate metric column should be `MRR`.
- Right-align numeric metric values.
- Prefer compact precision such as 4 decimal places in dense UI tables, while CSV export can retain 6 decimal places.
- Highlight official primary metrics without hiding secondary metrics.

Example Subtask A aggregate layout:

```text
RunID | nDCG@1 | nDCG@3 | nDCG@5
Run01 | 0.4286 | 0.5627 | 0.5681
Run02 | 0.5714 | 0.6042 | 0.6219
```

Example Subtask B aggregate layout:

```text
RunID | MRR
Run01 | 0.8750
Run02 | 0.8125
```

Per-query diagnostics:

- Group or filter by RunID.
- Show query/topic ID.
- Display per-query metrics as a pivoted table, not one row per metric.
- Use one row per `RunID` and query/topic ID.
- Use metric names as columns.
- For Subtask A, per-query columns should be `nDCG@1`, `nDCG@3`, and `nDCG@5`.
- For Subtask B, the per-query column should be `Reciprocal Rank`.
- Keep this section organizer-only.
- Use compact tables or grouped sections so large query sets remain scannable.
- Put large per-query tables in a constrained scroll region with a sticky table header.
- Repeat or visually group `RunID` values so organizers can scan multi-run submissions.
- Add later filters when needed: RunID selector, metric selector, query search, and sort by lowest selected metric.

Example Subtask A per-query layout:

```text
RunID | Query | nDCG@1 | nDCG@3 | nDCG@5
Run01 | 1     | 0.0000 | 0.0532 | 0.0490
Run01 | 10    | 0.1429 | 0.4227 | 0.5329
Run01 | 11    | 1.0000 | 0.6967 | 0.6974
```

Example Subtask B per-query layout:

```text
RunID | Query  | Reciprocal Rank
Run01 | image1 | 1.0000
Run01 | image2 | 0.5000
```

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

## Implemented MVP Screen Set

The implemented MVP screen set includes:

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

Later or extended workflow screens include:

- Organizer user management.
- Submission period editing.
- Export center.
- Bundle download.
- Re-evaluation controls.
