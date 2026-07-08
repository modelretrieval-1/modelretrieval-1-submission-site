# Implementation History

This archive preserves completed story details that were previously kept in `../../HANDOFF.md`.

Use `../../HANDOFF.md` for the current continuation state and next work.

## Completed Story

Implement organizer team management.

Route targets:

- `GET /admin/teams`
- `POST /admin/teams`
- `POST /admin/teams/{team_id}/password`

Minimum behavior:

- Organizer-only access.
- List teams with team ID, display name, active status, registered subtasks, created time, last login.
- Add team with team ID, display name, and subtasks A/B.
- Show generated password after team creation.
- Regenerate a team password and display the new password.
- Team users must not access these pages.

Suggested tests:

- Organizer can view teams page.
- Team cannot view teams page.
- Organizer can add a team with Subtask A.
- Organizer can add a team with both subtasks.
- Duplicate team ID is handled cleanly.
- Generated password can authenticate the new team.
- Regenerated password invalidates the old password.

Status:

- Complete.
- Implemented routes: `GET /admin/teams`, `POST /admin/teams`, `POST /admin/teams/{team_id}/password`.
- Implemented tests in `tests/test_admin_teams.py`.

## Completed Story

Implement organizer user management.

Route targets:

- `GET /admin/users`
- `POST /admin/users`
- `POST /admin/users/{username}/password`

Minimum behavior:

- Organizer-only access.
- List organizer users with username, display name, active status, created time, last login.
- Add organizer with username and display name.
- Show generated password after organizer creation.
- Regenerate an organizer password and display the new password.
- Team users must not access these pages.

Suggested tests:

- Organizer can view users page.
- Team cannot view users page.
- Organizer can add a new organizer.
- Duplicate username is handled cleanly.
- Generated password can authenticate the new organizer.
- Regenerated password invalidates the old password.

Status:

- Complete.
- Implemented routes: `GET /admin/users`, `POST /admin/users`, `POST /admin/users/{username}/password`.
- Implemented tests in `tests/test_admin_users.py`.

## Completed Story

Implement ground-truth upload scaffolding.

Route targets:

- `GET /admin/ground-truth`
- `POST /admin/ground-truth`

Minimum behavior:

- Organizer-only access.
- Upload ground-truth file for Subtask A or B.
- Store file on local filesystem under the configured storage root.
- Compute and store file SHA-256.
- Create a `ground_truth_versions` row.
- Show upload history.
- Do not expose uploaded ground-truth files to participants.

Suggested tests:

- Organizer can view ground-truth page.
- Team cannot view ground-truth page.
- Organizer can upload Subtask A ground truth.
- Organizer can upload Subtask B ground truth.
- Upload stores a file under `storage/ground-truth`.
- Upload creates a database row with checksum.
- Participant cannot access the page or file.

Status:

- Complete.
- Implemented routes: `GET /admin/ground-truth`, `POST /admin/ground-truth`.
- Implemented tests in `tests/test_ground_truth.py`.

## Completed Story

Implement ground-truth file format validation.

Target behavior:

- Subtask A ground-truth upload must include `task_id`, `model_id`, and `relevance_score`.
- Subtask B ground-truth upload must include `image_id` and `model_id`.
- Invalid ground-truth files are rejected before storage and database row creation.
- Validation errors should be shown to organizers.
- Valid files should receive `validation_status = validated` or similar.

Suggested tests:

- Valid Subtask A CSV is accepted.
- Subtask A CSV missing `relevance_score` is rejected.
- Valid Subtask B CSV is accepted.
- Subtask B CSV missing `image_id` is rejected.
- Empty file is rejected.
- Validation status is persisted.

Status:

- Complete.
- Subtask A requires `task_id`, `model_id`, and `relevance_score`.
- Subtask B requires `image_id` and `model_id`.
- Header-only files are rejected.
- Invalid uploads are rejected before file storage and database row creation.
- Valid uploads are stored with `validation_status = validated`.

## Completed Story

Implement ground-truth version activation.

Target behavior:

- Organizer can activate one ground-truth version per subtask.
- Activating a version marks other versions for the same subtask inactive.
- Only validated versions can be activated.
- The ground-truth history shows the active version.

Suggested tests:

- Organizer can activate a validated Subtask A version.
- Organizer can activate a validated Subtask B version.
- Activating a second version deactivates the previous version for the same subtask.
- Activating Subtask A does not affect active Subtask B.
- Team cannot activate ground truth.

Status:

- Complete.
- Implemented route: `POST /admin/ground-truth/{version_id}/activate`.
- One active ground-truth version is allowed per subtask.
- Activating one subtask does not affect the other subtask.
- Only validated versions can be activated.

## Completed Story

Implement TREC_EVAL parser and participant submission validation core.

Target behavior:

- Parse lines shaped as `topicID Q0 docID Rank Score RunID`.
- Reject lines with the wrong number of fields.
- Enforce `Q0`.
- Parse positive integer rank.
- Parse numeric score.
- Track distinct `RunID` values.
- Reject more than 5 runs.
- Prepare data structures for later query/model completeness validation.

Suggested tests:

- Valid TREC_EVAL lines parse successfully.
- Wrong field count is rejected with line number.
- Non-`Q0` token is rejected.
- Non-integer rank is rejected.
- Non-positive rank is rejected.
- Non-numeric score is rejected.
- More than 5 distinct runs is rejected.

Status:

- Complete.
- Implemented parser in `app/submissions.py`.
- Blank lines are ignored.
- Wrong field counts are rejected.
- Non-`Q0` values are rejected.
- Invalid rank values are rejected.
- Invalid score values are rejected.
- More than 5 distinct runs is rejected.
- Query/model completeness was implemented in a later validation slice.

## Completed Story

Implement duplicate row validation and score-vs-rank order validation.

Target behavior:

- Reject duplicate `(RunID, topicID, docID)` rows.
- Allow duplicate ranks within a query.
- Allow tied scores.
- Use line order as tie-breaker.
- Recompute expected ordering from score descending plus line order.
- Reject if submitted rank order disagrees with score-derived order.

Suggested tests:

- Duplicate `(RunID, topicID, docID)` is rejected.
- Duplicate ranks are allowed when ordering still matches score order.
- Tied scores are allowed and use line order.
- Higher score listed below a lower score is rejected.
- Rank values that disagree with score-derived order are rejected.

Status:

- Complete.
- Duplicate `(RunID, topicID, docID)` rows are rejected.
- Duplicate ranks are allowed when ordering still matches score order.
- Tied scores are allowed and use line order.
- Score-derived ordering is checked per `RunID` and `topicID`.
- Rank/order mismatches are rejected with warning severity.

## Completed Story

Implement query/model completeness validation.

Target behavior:

- Given required query IDs and candidate model IDs, every run must include every query.
- Every query must include every candidate model.
- Missing required queries are rejected.
- Missing candidate models are rejected.
- Unknown query IDs are rejected.
- Unknown model IDs are rejected.

Suggested tests:

- Complete run passes.
- Missing query is rejected.
- Missing model for one query is rejected.
- Unknown query ID is rejected.
- Unknown model ID is rejected.
- Completeness is checked independently for each `RunID`.

Status:

- Complete.
- Implemented `validate_query_model_completeness`.
- Complete runs pass.
- Missing topics are rejected.
- Missing models per query are rejected.
- Unknown topic IDs are rejected.
- Unknown model IDs are rejected.
- Completeness is checked independently per `RunID`.

## Completed Story

Derive required query/model IDs from active ground truth and wire participant upload validation.

Target behavior:

- For Subtask A, active ground truth provides required topic IDs from `task_id` and candidate model IDs from `model_id`.
- For Subtask B, active ground truth provides required topic IDs from `image_id` and candidate model IDs from `model_id`.
- If no active ground truth exists for a subtask, participant upload validation cannot proceed.
- Participant upload validation should combine parser errors, order errors, and completeness errors.

Suggested tests:

- Active Subtask A ground truth produces required topic/model ID sets.
- Active Subtask B ground truth produces required topic/model ID sets.
- Missing active ground truth returns a clear configuration error.
- A complete parsed submission validates against active ground truth.
- An incomplete parsed submission returns completeness errors.

Status:

- Complete.
- Implemented `GroundTruthRequirements`.
- Implemented active ground-truth lookup by subtask.
- Implemented extraction of required topic/model IDs from active Subtask A and Subtask B ground-truth versions.
- Implemented `validate_submission_against_requirements`.
- Missing active ground truth now returns a clear `missing_active_ground_truth` validation error.
- Implemented tests in `tests/test_ground_truth.py` and `tests/test_submissions.py`.

## Completed Story

Build participant submission upload UI and persist validation failures.

Target behavior:

- Team dashboard links to a submission form for each eligible subtask.
- Team uploads one TREC_EVAL-format file for one subtask at a time.
- Accept any filename extension and reject files larger than 50 MB.
- Use active ground-truth requirements for validation.
- Show validation errors immediately.
- Persist failed validation attempts for audit/debugging.
- Do not count failed attempts as successful submissions.

Suggested tests:

- Team can open the upload page for an eligible subtask.
- Team cannot open the upload page for an ineligible subtask.
- Files with non-TREC_EVAL content are rejected regardless of filename extension.
- Upload larger than 50 MB is rejected.
- Missing active ground truth shows a clear error.
- Invalid TREC_EVAL content shows validation errors and persists a failed attempt.
- Organizer-only pages remain inaccessible to teams.

Status:

- Complete.
- Team dashboard links to upload pages for registered subtasks.
- Implemented route: `GET /team/submissions/{subtask}/new`.
- Implemented route: `POST /team/submissions/{subtask}/new`.
- Team users cannot access upload pages for unregistered subtasks.
- Files with non-TREC_EVAL content are rejected and persisted as rejected attempts.
- Files larger than the configured maximum are rejected and persisted as rejected attempts.
- Missing active ground truth is rejected and persisted as a validation error.
- Invalid TREC_EVAL content is rejected, stored, and persisted with validation errors.
- Valid submissions are stored as `accepted` and run metadata is written to `runs`.
- Implemented tests in `tests/test_team_submissions.py`.

## Completed Story

Implement evaluation metric calculation core.

Target behavior:

- Compute official Subtask A nDCG@3 and nDCG@5.
- Evaluate each RunID independently.
- Compute Subtask B MRR.
- Keep the functions pure and covered by known expected values.

Suggested tests:

- nDCG@3 and nDCG@5 match known expected values.
- MRR matches known expected values.
- Macro nDCG is averaged across queries.
- Multi-run submissions are scored independently.

Status:

- Complete.
- Implemented `app/evaluation.py`.
- Implemented `dcg`, `ndcg_at`, `mean_reciprocal_rank`, `evaluate_subtask_a`, and `evaluate_subtask_b`.
- Implemented tests in `tests/test_evaluation.py`.

## Completed Story

Evaluate accepted submissions and persist metric results.

Target behavior:

- Load active ground truth into Subtask A relevance maps and Subtask B relevant-model maps.
- Evaluate each accepted submission after validation.
- Store metric rows in `evaluation_results`.
- Store organizer-only per-query metric rows separately from aggregate `evaluation_results`.
- Update submission status from `accepted` to `evaluated` or `evaluation_failed`.
- Keep participant score display ready for the following UI slice.

Suggested tests:

- Accepted submission creates evaluation result rows.
- Subtask A accepted submission stores `ndcg@1`, `ndcg@3`, and `ndcg@5`.
- Subtask B accepted submission stores `mrr`.
- Evaluation failure leaves a clear status and does not lose the submission file.

Status:

- Complete.
- Active Subtask A ground truth is loaded into relevance maps.
- Active Subtask B ground truth is loaded into relevant-model maps.
- Valid uploads are evaluated immediately after run metadata is persisted.
- Metric rows are written to `evaluation_results`.
- Per-query metric rows are written to `evaluation_query_results` for organizer-only visibility.
- Successful evaluation updates submissions to `evaluated`.
- Missing evaluation setup can mark submissions as `evaluation_failed`.
- Implemented integration tests in `tests/test_team_submissions.py`.

## Completed Story

Show participant scores after evaluated submissions.

Target behavior:

- After a successful upload, show each submitted RunID and its metrics.
- Keep participant-visible metrics aggregate-only; do not show per-query diagnostics to teams.
- Team dashboard should show the latest evaluated submission status per registered subtask.
- Participants should only see their own scores.
- Keep private leaderboard work for Sprint 4.

Suggested tests:

- Successful Subtask A upload response shows `ndcg@1`, `ndcg@3`, and `ndcg@5`.
- Successful Subtask B upload response shows `mrr`.
- Team dashboard links to or summarizes the team's evaluated submission.
- Team users cannot access another team's results.

Status:

- Complete.
- Successful upload responses show submitted run metrics.
- Team dashboard shows latest submission status and scores per subtask.
- Team-visible result queries only use the signed-in team's submissions.
- Implemented integration tests in `tests/test_team_submissions.py`.

## Completed Story

Enforce one successful submission per team/subtask/period.

Target behavior:

- If a team already has an `accepted`, `evaluated`, or `evaluation_failed` submission for a subtask and period, a new successful upload is blocked.
- Failed validation attempts remain retryable.
- Team dashboard should clearly show that the subtask already has a successful submission.
- The database partial unique index already protects this rule; the UI should show a friendly error instead of surfacing an integrity exception.

Suggested tests:

- A second valid upload for the same team/subtask/period is rejected with a clear message.
- A rejected upload followed by a valid upload still succeeds.
- Different subtasks are tracked independently.
- Different teams are tracked independently.

Status:

- Complete.
- Implemented `has_successful_submission`.
- Valid duplicate uploads now receive a friendly `successful_submission_exists` validation error.
- Rejected attempts remain retryable.
- The database partial unique index remains the backstop for this rule.
- Implemented integration tests in `tests/test_team_submissions.py`.

## Completed Story

Enforce submission periods and JST deadlines.

Target behavior:

- Determine whether normal or late period is currently open using server-side JST time.
- Block uploads when no period is open unless organizer override is enabled.
- Keep the current normal-period behavior as the default path for tests.
- Show clear participant errors when submissions are closed.

Suggested tests:

- Upload before the normal deadline uses the normal period.
- Upload after the normal deadline and before the late deadline uses the late period.
- Upload after the late deadline is rejected when no override is enabled.
- `is_open_override` permits upload after a closed deadline.

Status:

- Complete, but the upload route now uses the participant-selected period behavior below.
- Implemented JST deadline parsing and open-period selection.
- `get_open_submission_period` remains available, but participant uploads no longer auto-switch periods.
- `is_open_override` permits a period to be used after its deadline.
- Closed-period uploads are blocked before storing the submitted file.
- Implemented tests in `tests/test_submissions.py` and `tests/test_team_submissions.py`.

## Completed Story

Add organizer submission-period controls.

Target behavior:

- Organizer can view normal and late period deadlines.
- Organizer can edit period deadlines.
- Organizer can toggle `is_open_override`.
- Team dashboard and upload flow should reflect changed period availability.

Suggested tests:

- Organizer can view submission periods.
- Organizer can update normal and late deadlines.
- Organizer can toggle reopen override.
- Team users cannot access period controls.

Status:

- Complete.
- Implemented route: `GET /admin/periods`.
- Implemented route: `POST /admin/periods/{period_name}`.
- Organizer can edit start timestamps, deadlines, and reopen override.
- Invalid timestamps are rejected with a clear error.
- Team users are redirected away from period controls.
- Implemented tests in `tests/test_admin_periods.py`.

## Completed Story

Let participants choose normal or late submission during upload.

Context:

- Product decision changed after `caf77ef` and `083c3a4`.
- Previous implementation automatically selected the first open period from server-side JST time.
- Current behavior is participant-selected period: the team explicitly chooses `normal` or `late`, and the system validates that selected period is open or reopened.
- The system must not auto-switch a selected normal upload to late, or selected late upload to normal.

Target behavior:

- Team upload form includes a submission-period selector.
- GET upload page shows normal and late periods with deadline/override status.
- POST upload route accepts a selected period.
- Selected period is validated against its JST deadline and `is_open_override`.
- Successful submissions are recorded under the selected period.
- Existing one-successful-submission rule applies to the selected period.

Suggested tests:

- Team can submit to selected normal period when normal is open.
- Team can submit to selected late period when late is open.
- Selecting closed normal is rejected even if late is open.
- Selecting closed late is rejected even if normal is open.
- If both periods are open via override, the selected period is used.
- Missing/invalid period selection is rejected with a clear message.

Status:

- Complete.
- Upload form now includes a normal/late submission-period selector.
- GET upload page shows configured period deadlines and reopen status.
- POST upload route accepts the selected period.
- Missing and invalid period selections are rejected before storing a submission attempt.
- Closed selected periods are rejected even when the other period is open.
- Successful and rejected attempts are recorded under the selected period.
- Implemented integration tests in `tests/test_team_submissions.py`.

## Completed Story

Add organizer submissions table and detail view.

Target behavior:

- Organizer can view all submission attempts.
- Organizer can filter by team, subtask, period, and status.
- Organizer can inspect validation errors for rejected submissions.
- Organizer can inspect run-level metrics for evaluated submissions.
- Organizer can inspect per-query metric diagnostics for evaluated submissions.
- Team users cannot access organizer submission views.

Suggested tests:

- Organizer can view submissions table.
- Organizer can filter submissions by status and subtask.
- Organizer can open rejected submission detail and see validation errors.
- Organizer can open evaluated submission detail and see run metrics.
- Team users cannot access organizer submission views.

Status:

- Complete.
- Implemented route: `GET /admin/submissions`.
- Implemented route: `GET /admin/submissions/{submission_id}`.
- Organizer submissions table can filter by team ID, subtask, period, and status.
- Rejected submission details show persisted validation errors.
- Evaluated submission details show run metadata and metric rows.
- Team users are redirected away from organizer submission views.
- Implemented integration tests in `tests/test_admin_submissions.py`.

## Completed Story

Add organizer private leaderboard view.

Target behavior:

- Organizer can view private leaderboard rows for Subtask A and Subtask B.
- Leaderboard can filter by subtask and submission period.
- Rows show team, run ID, metrics, submission period, and submission timestamp.
- Team users cannot access the leaderboard.

Suggested tests:

- Organizer can view leaderboard page.
- Team cannot view leaderboard page.
- Organizer can filter leaderboard by subtask and period.
- Subtask A rows show nDCG metrics.
- Subtask B rows show MRR.

Status:

- Complete.
- Implemented route: `GET /admin/leaderboard`.
- Leaderboard is organizer-only.
- Leaderboard shows evaluated run rows with team, subtask, period, RunID, metrics, and submitted time.
- Leaderboard can filter by subtask and period.
- Subtask A rows show `ndcg@1`, `ndcg@3`, and `ndcg@5`.
- Subtask B rows show `mrr`.
- Implemented integration tests in `tests/test_admin_leaderboard.py`.

## Completed Story

Add leaderboard CSV export.

Target behavior:

- Organizer can export leaderboard rows as CSV.
- CSV export respects the current subtask and submission-period filters.
- Export includes team, subtask, period, RunID, metrics, and submitted timestamp.
- Team users cannot access the CSV export.

Suggested tests:

- Organizer can download leaderboard CSV.
- CSV export includes Subtask A nDCG metrics.
- CSV export includes Subtask B MRR.
- CSV export respects subtask and period filters.
- Team users cannot download leaderboard CSV.

Status:

- Complete.
- Implemented route: `GET /admin/leaderboard.csv`.
- Leaderboard page includes an export link that preserves current filters.
- CSV export includes team, subtask, period, RunID, metrics, and submitted timestamp.
- CSV export respects subtask and period filters.
- Team users are redirected away from the CSV export.
- Implemented integration tests in `tests/test_admin_leaderboard.py`.

## Completed Story

Add submission bundle download.

Target behavior:

- Organizer can download submitted files as a bundle.
- Bundle can filter by subtask and submission period.
- Bundle includes stored submission files and metadata.
- Team users cannot access bundle downloads.

Suggested tests:

- Organizer can download a submission bundle.
- Bundle includes submitted files.
- Bundle includes metadata.
- Bundle respects subtask and period filters.
- Team users cannot download submission bundles.

Status:

- Complete.
- Implemented route: `GET /admin/submissions/bundle.zip`.
- Submissions page includes a download link that preserves current subtask and period filters.
- Bundle includes `metadata.csv`.
- Bundle includes stored submission files when the file exists on disk.
- Bundle metadata includes all matching attempts, including attempts without stored files.
- Team users are redirected away from bundle downloads.
- Implemented integration tests in `tests/test_admin_submissions.py`.

## Completed Story

Modernize the server-rendered UI with Bootstrap 5 and project-specific CSS.

Target behavior:

- Improve global navigation with role-aware links and active page state.
- Improve form layout, labels, help text, validation messages, and action placement.
- Improve organizer tables, filters, and status badges.
- Improve participant dashboard, upload form, validation-error display, and score display.
- Keep FastAPI/Jinja2 as the frontend architecture.
- Avoid a single-page app framework or build pipeline.

Suggested tests:

- Keep existing integration tests green.
- Add focused HTML/response assertions only where navigation or page structure changes affect behavior.
- Run a manual browser smoke check for login, team upload, admin teams, ground truth, periods, submissions, and leaderboard.

Status:

- Complete.
- Added Bootstrap 5 to the shared base template.
- Added role-aware top navigation with active page state.
- Improved login, password, team dashboard, team upload, organizer dashboard, teams, users, ground truth, periods, submissions, submission detail, and leaderboard templates.
- Added Bootstrap form controls, tables, alerts, badges, filter panels, and responsive layout polish.
- Kept generated-password markup compatible with existing tests.
- Browser plugin backend was unavailable in the latest session, so visual smoke verification remains pending; local server availability plus automated HTML/integration tests passed.

## Completed Story

Strengthen the local UI quality gate for Sprint 6A.

Target behavior:

- Keep the authenticated app shell responsive and role-aware.
- Preserve mobile offcanvas navigation controls.
- Keep public pages outside the authenticated app shell.
- Ensure key tables remain inside horizontal-scroll wrappers.
- Ensure key forms keep visible labels.
- Add small CSS guards for compact rows and action areas so text does not force awkward overflow.

Status:

- Complete.
- Added CSS guards for top-bar buttons, public brand text, header action buttons, period rows, and participant slot rows in `app/static/app.css`.
- Expanded `tests/test_app_shell.py` to cover mobile navigation controls, public/authenticated shell separation, responsive table wrappers, and visible labels on organizer and participant form pages.
- Verified `uv run --extra dev pytest` with 146 passing tests.
- Verified `uv run --extra dev ruff check .`.
- Verified local server startup plus `/health` and `/login` responses.
- In-app browser backend was unavailable, so true visual browser smoke verification remains pending.
