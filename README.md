# NTCIR-19 ModelRetrieval Submission System

This repository contains the submission and evaluation system for the NTCIR-19 ModelRetrieval task.

## Current Status

The project is entering **Sprint 4: Organizer Operations**.

Participant upload, validation, evaluation, score display, period controls, and selected normal/late upload period are complete for the planned scope.

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
- Tests for settings, storage, database initialization, app startup, accounts, sessions, and login flow.

Current test status:

```text
uv run --extra dev pytest
115 passed

uv run --extra dev ruff check .
All checks passed
```

Next recommended story:

- Add organizer submissions table and detail view.

## Development Setup

Create the virtual environment and install dependencies with `uv`:

```bash
uv sync --extra dev
```

Run the app:

```bash
uv run uvicorn app.main:app --reload
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

- [requirements.md](requirements.md): product requirements and decisions.
- [user-stories.md](user-stories.md): participant and organizer stories.
- [ui-flow.md](ui-flow.md): screen and workflow definitions.
- [data-model.md](data-model.md): database/entity design.
- [submission-spec.md](submission-spec.md): participant upload format and validation rules.
- [evaluation-spec.md](evaluation-spec.md): metric definitions and evaluation behavior.
- [architecture.md](architecture.md): VPS deployment architecture.
- [open-questions.md](open-questions.md): resolved product and implementation decisions.
- [implementation-plan.md](implementation-plan.md): Scrum plan, epics, testing strategy, sprint plan.
- [HANDOFF.md](HANDOFF.md): concise continuation guide for a new Codex session.
