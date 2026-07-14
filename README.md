# NTCIR-19 ModelRetrieval Submission System

This repository contains the submission and evaluation system for the NTCIR-19 ModelRetrieval task.

Document role: this file is the short project overview and quick-start guide. Use [HANDOFF.md](HANDOFF.md) for detailed current implementation status.

## Current Status

The project is in **Sprint 6: Production Hardening**.

The planned core app scope is implemented: participant upload, validation, evaluation, score display, organizer review, private leaderboard, exports, submission bundles, audit logging with an organizer-only audit viewer, server-rendered Bootstrap UI, and the Sprint 6A application-shell redesign.

Staging has been tested successfully, and production was deployed successfully from immutable tag `v2026.07.14.0` with Nginx/Certbot HTTPS. The remaining focus is post-deploy operational verification, backup/restore readiness, and final browser/E2E regression coverage.

Use [HANDOFF.md](HANDOFF.md) for the detailed implementation inventory and latest continuation notes.

Current test status:

```text
uv run --extra dev pytest
172 passed

uv run --extra dev ruff check .
All checks passed
```

## UI Direction

The app remains a FastAPI/Jinja2 server-rendered system. The UI now uses Bootstrap 5 for navigation, forms, tables, alerts, badges, and responsive layout, with `app/static/app.css` reserved for project-specific polish. React, Vue, and a separate frontend build pipeline are intentionally not part of this phase.

The current UI slice includes the implemented Sprint 6A application-shell redesign and completed P0–P2 UX improvements: persistent role-aware navigation, participant lifecycle and upload guidance, organizer attention tools, replacement history, and faster leaderboard/review tables. Automated responsive/accessibility-oriented regression checks are in place; remaining UI work is visual browser smoke verification tracked in `HANDOFF.md`.

The public home page is intentionally lightweight: it introduces the NTCIR-19 ModelRetrieval submission portal and directs registered users to sign in. The `/health` endpoint remains an operational check and is not presented as a normal user action.

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
- [docs/product/requirements.md](docs/product/requirements.md): product requirements.
- [docs/product/decisions.md](docs/product/decisions.md): resolved product and implementation decisions.
- [docs/ui/ui-flow.md](docs/ui/ui-flow.md): active screen and workflow specification.
- [docs/technical/data-model.md](docs/technical/data-model.md): database/entity design.
- [docs/technical/database-migrations.md](docs/technical/database-migrations.md): Alembic migration adoption plan.
- [docs/technical/submission-spec.md](docs/technical/submission-spec.md): participant upload format and validation rules.
- [docs/deployment/deployment-runbook.md](docs/deployment/deployment-runbook.md): operational deployment, rollback, backup, and restore guide.
- [docs/planning/implementation-plan.md](docs/planning/implementation-plan.md): Scrum plan, epics, testing strategy, sprint plan.
- [docs/planning/documentation-cleanup-plan.md](docs/planning/documentation-cleanup-plan.md): pointer to the archived documentation cleanup plan.
- [HANDOFF.md](HANDOFF.md): concise continuation guide for a new Codex session.
