# NTCIR-19 ModelRetrieval Submission System

This repository contains the submission and evaluation system for the NTCIR-19 ModelRetrieval task.

## Current Status

The project is in **Sprint 6: Production Hardening**.

Participant upload, validation, evaluation, score display, period controls, selected normal/late upload period, organizer submission review, private leaderboard, leaderboard CSV export, submission bundle download, Bootstrap-based UI modernization, and the Sprint 6A application-shell/page-normalization redesign are complete for the planned scope so far.

Completed foundation:

- FastAPI project skeleton.
- SQLite schema bootstrap.
- Local storage directory bootstrap.
- Basic health page and health endpoint.
- uv dependency workflow and lockfile.
- Account/password helpers.
- Organizer and team account creation primitives.
- Signed cookie session helpers.
- Minimal login/logout flow.
- Minimal team and organizer dashboards.
- Organizer team management page.
- Team creation with visible generated passwords.
- Team password regeneration.
- Participant team self-service password change.
- Organizer user management page.
- Organizer creation with visible generated passwords.
- Organizer password regeneration.
- Organizer password change page.
- Ground-truth upload page.
- Ground-truth file storage with SHA-256 metadata.
- Ground-truth CSV format validation for Subtask A and Subtask B.
- Ground-truth version activation.
- TREC_EVAL parser with field-level validation.
- Duplicate submission row and score-vs-rank order validation.
- Query/model completeness validation.
- Active ground-truth requirement extraction for Subtask A and Subtask B.
- Combined participant submission validation against active ground truth.
- Team submission upload page for registered subtasks.
- `.txt` and maximum upload-size guards.
- Rejected submission attempt persistence with validation errors.
- Accepted submission persistence with run metadata.
- Evaluation metric core for nDCG and MRR.
- Accepted submission evaluation with persisted metric results.
- Participant score display after evaluated submissions.
- One successful submission per team/subtask/period enforcement.
- Submission period and JST deadline enforcement.
- Organizer submission-period controls.
- Participant-selected normal/late submission period during upload.
- Organizer submissions table and detail view.
- Organizer private leaderboard view.
- Leaderboard CSV export.
- Submission bundle download.
- Shared authenticated app shell with role-aware sidebar/topbar navigation.
- Participant upload navigation entry.
- Participant dashboard submission availability by subtask and period.
- Organizer dashboard period open/closed/reopened state.
- Organizer dashboard recent validation-failure panel.
- Upload page period open/closed/reopened state.
- Normalized organizer review pages for submissions, submission details, and leaderboard.
- Normalized organizer account pages for teams and users.
- Normalized organizer operations pages for ground-truth versions and submission periods.
- Normalized participant form pages for submission upload and password change.
- Docker image and Docker Compose deployment foundation.
- Host Nginx reverse-proxy templates for staging and production.
- VPS setup, GitHub Actions deployment, backup, restore, and smoke-check documentation.
- Backup, restore, and deployment smoke-check scripts.
- Tests for settings, storage, database initialization, app startup, accounts, sessions, and login flow.

Current test status:

```text
uv run --extra dev pytest
142 passed

uv run --extra dev ruff check .
All checks passed
```

Next recommended work:

- Run the final local/browser UI quality gate, then rehearse the staging deployment on Sakura VPS, verify GitHub Actions staging deployment, and promote production with an immutable `v*` tag after staging passes.

## UI Direction

The app remains a FastAPI/Jinja2 server-rendered system. The UI now uses Bootstrap 5 for navigation, forms, tables, alerts, badges, and responsive layout, with `app/static/app.css` reserved for project-specific polish. React, Vue, and a separate frontend build pipeline are intentionally not part of this phase.

The current UI slice is the Sprint 6A application-shell redesign: persistent role-aware navigation, a richer organizer operations dashboard, a clearer participant submission dashboard, and normalized organizer/participant workflow pages. Remaining work should continue from `docs/ui/app-ui-redesign.md` with final responsive, accessibility, and browser smoke verification.

## Development Setup

Create the virtual environment and install dependencies with `uv`:

```bash
uv sync --extra dev
```

Run the app:

```bash
uv run uvicorn app.main:app --reload
```

Build the deployment image locally:

```bash
docker build -t modelretrieval-submissions:local .
```

Create the first organizer account:

```bash
uv run python -m app.cli create-admin --username admin --display-name "Admin User"
```

Run tests:

```bash
uv run --extra dev pytest
```

Run the standard-library Sprint 0 tests without installing dependencies:

```bash
uv run python -m unittest discover -s tests
```

Lock dependencies:

```bash
uv lock
```

## Important Documents

- [docs/index.md](docs/index.md): organized documentation index.
- [docs/product/requirements.md](docs/product/requirements.md): product requirements and decisions.
- [docs/ui/app-ui-redesign.md](docs/ui/app-ui-redesign.md): application-shell and dashboard redesign plan and acceptance criteria.
- [docs/technical/data-model.md](docs/technical/data-model.md): database/entity design.
- [docs/technical/submission-spec.md](docs/technical/submission-spec.md): participant upload format and validation rules.
- [docs/deployment/deployment-runbook.md](docs/deployment/deployment-runbook.md): operational deployment, rollback, backup, and restore guide.
- [docs/planning/implementation-plan.md](docs/planning/implementation-plan.md): Scrum plan, epics, testing strategy, sprint plan.
- [HANDOFF.md](HANDOFF.md): concise continuation guide for a new Codex session.
