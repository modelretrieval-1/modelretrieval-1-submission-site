# Project Handoff

## Project

NTCIR-19 ModelRetrieval submission and evaluation system.

The app accepts registered team submissions, validates TREC_EVAL `.txt` files, evaluates internally, shows participant scores immediately, and gives organizers private administration and leaderboard views.

## Current Phase

Scrum implementation is underway.

- Sprint 0: complete.
- Sprint 1: complete for the planned v1 account scope.
- Sprint 2: complete for the planned validation-core scope.
- Sprint 3: next/current sprint, focused on evaluation metrics and participant score display.

## Current Stack

- Python 3.12+
- uv
- FastAPI
- Jinja2
- SQLite
- Local filesystem storage
- Pytest
- Ruff
- Playwright planned for E2E tests
- VPS deployment planned with Nginx or Caddy, HTTPS, and systemd

## Setup Commands

Install dependencies:

```bash
uv sync --extra dev
```

Run tests:

```bash
uv run --extra dev pytest
```

Run lint:

```bash
uv run --extra dev ruff check .
```

Run the app:

```bash
uv run uvicorn app.main:app --reload
```

## Verified State

Latest verified commands:

```text
uv run --extra dev pytest
99 passed

uv run --extra dev ruff check .
All checks passed
```

## Implemented Code

Foundation:

- `app/config.py`: settings and environment loading.
- `app/storage.py`: local storage directory bootstrap.
- `app/db.py`: SQLite schema and default submission periods.
- `app/main.py`: FastAPI app, lifespan startup, health page, login/logout, dashboards.
- `app/main.py`: also includes organizer team management routes.
- `app/main.py`: also includes organizer user management routes.
- `app/main.py`: also includes organizer password change routes.
- `app/main.py`: also includes ground-truth upload routes.
- `app/main.py`: also includes team submission upload routes.
- `app/ground_truth.py`: ground-truth file storage, SHA-256 calculation, CSV format validation, version metadata helpers, activation helpers, active ground-truth requirement extraction.
- `app/submissions.py`: TREC_EVAL parser, field-level submission validation, duplicate row validation, score-vs-rank order validation, query/model completeness validation, combined validation against active ground truth, submission file guards, submission storage, submission attempt persistence helpers.
- `app/evaluation.py`: pure nDCG, MRR, Subtask A evaluation, Subtask B evaluation, ground-truth metric loading, evaluation result persistence, and evaluation status helpers.

Accounts and sessions:

- `app/auth.py`: password generation, PBKDF2 hashing, password verification.
- `app/accounts.py`: organizer/team creation, authentication, subtask eligibility, password reset/change helpers.
- `app/accounts.py`: also includes team listing and reset by public team ID.
- `app/accounts.py`: also includes organizer listing and reset by username.
- `app/sessions.py`: signed cookie session creation and parsing.

Templates:

- `app/templates/base.html`
- `app/templates/home.html`
- `app/templates/login.html`
- `app/templates/team_dashboard.html`
- `app/templates/admin_dashboard.html`
- `app/templates/admin_teams.html`
- `app/templates/admin_users.html`
- `app/templates/password_change.html`
- `app/templates/admin_ground_truth.html`
- `app/templates/team_submission_upload.html`

Tests:

- `tests/test_config.py`
- `tests/test_storage.py`
- `tests/test_db.py`
- `tests/test_app.py`
- `tests/test_auth.py`
- `tests/test_accounts.py`
- `tests/test_sessions.py`
- `tests/test_login_flow.py`
- `tests/test_admin_teams.py`
- `tests/test_admin_users.py`
- `tests/test_password_change.py`
- `tests/test_ground_truth.py`
- `tests/test_submissions.py`
- `tests/test_team_submissions.py`
- `tests/test_evaluation.py`

## Product Decisions

Key decisions already made:

- Users are participant teams and organizers.
- Teams are identified by `team_id`.
- Each team has one shared account.
- Organizers add teams and generate visible passwords.
- Only registered teams can submit.
- Subtask A and Subtask B submissions are uploaded separately.
- Upload format is one `.txt` file, no zip, maximum 10 MB.
- Each subtask allows up to 5 runs.
- One successful submission per team/subtask/period.
- Failed validation attempts do not count.
- Normal deadline: August 1, 2026 at 15:00 JST.
- Late deadline: October 15, 2026 at 23:59 JST.
- Organizers can reopen periods.
- Participants see scores immediately.
- Leaderboard is organizer-only.
- Ground truth is uploaded/configured by organizers and stored on the server local filesystem.
- Evaluation is internal.
- Records are retained forever.
- No email notifications.
- VPS deployment.

## Completed Latest Story

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

## Completed Latest Story

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

## Completed Latest Story

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

## Completed Latest Story

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

## Completed Latest Story

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

## Completed Latest Story

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

## Completed Latest Story

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

## Completed Latest Story

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

## Completed Latest Story

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

## Completed Latest Story

Build participant submission upload UI and persist validation failures.

Target behavior:

- Team dashboard links to a submission form for each eligible subtask.
- Team uploads one `.txt` file for one subtask at a time.
- Reject non-`.txt` files and files larger than 10 MB.
- Use active ground-truth requirements for validation.
- Show validation errors immediately.
- Persist failed validation attempts for audit/debugging.
- Do not count failed attempts as successful submissions.

Suggested tests:

- Team can open the upload page for an eligible subtask.
- Team cannot open the upload page for an ineligible subtask.
- Non-`.txt` upload is rejected.
- Upload larger than 10 MB is rejected.
- Missing active ground truth shows a clear error.
- Invalid TREC_EVAL content shows validation errors and persists a failed attempt.
- Organizer-only pages remain inaccessible to teams.

Status:

- Complete.
- Team dashboard links to upload pages for registered subtasks.
- Implemented route: `GET /team/submissions/{subtask}/new`.
- Implemented route: `POST /team/submissions/{subtask}/new`.
- Team users cannot access upload pages for unregistered subtasks.
- Non-`.txt` files are rejected and persisted as rejected attempts.
- Files larger than the configured maximum are rejected and persisted as rejected attempts.
- Missing active ground truth is rejected and persisted as a validation error.
- Invalid TREC_EVAL content is rejected, stored, and persisted with validation errors.
- Valid submissions are stored as `accepted` and run metadata is written to `runs`.
- Implemented tests in `tests/test_team_submissions.py`.

## Completed Latest Story

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

## Completed Latest Story

Evaluate accepted submissions and persist metric results.

Target behavior:

- Load active ground truth into Subtask A relevance maps and Subtask B relevant-model maps.
- Evaluate each accepted submission after validation.
- Store metric rows in `evaluation_results`.
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
- Successful evaluation updates submissions to `evaluated`.
- Missing evaluation setup can mark submissions as `evaluation_failed`.
- Implemented integration tests in `tests/test_team_submissions.py`.

## Next Recommended Story

Show participant scores after evaluated submissions.

Target behavior:

- After a successful upload, show each submitted RunID and its metrics.
- Team dashboard should show the latest evaluated submission status per registered subtask.
- Participants should only see their own scores.
- Keep private leaderboard work for Sprint 4.

Suggested tests:

- Successful Subtask A upload response shows `ndcg@1`, `ndcg@3`, and `ndcg@5`.
- Successful Subtask B upload response shows `mrr`.
- Team dashboard links to or summarizes the team's evaluated submission.
- Team users cannot access another team's results.

## Docs To Read First In A New Session

1. `HANDOFF.md`
2. `README.md`
3. `implementation-plan.md`
4. `ui-flow.md`
5. `data-model.md`
6. `submission-spec.md`
7. `evaluation-spec.md`
8. `requirements.md`
9. `user-stories.md`
10. `architecture.md`
11. `open-questions.md`
