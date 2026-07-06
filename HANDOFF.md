# Project Handoff

Document role: this is the primary current-state handoff for future Codex or developer sessions. Keep detailed implementation status here instead of duplicating it across stable product and technical docs.

## Project

NTCIR-19 ModelRetrieval submission and evaluation system.

The app accepts registered team submissions, validates uploaded files by TREC_EVAL content, evaluates internally, shows participant scores immediately, and gives organizers private administration and leaderboard views.

## Current Phase

Scrum implementation is underway.

- Sprint 0: complete.
- Sprint 1: complete for the planned v1 account scope.
- Sprint 2: complete for the planned validation-core scope.
- Sprint 3: complete for the planned evaluation and participant-result scope.
- Sprint 4: complete for the planned organizer-operations scope.
- Sprint 5: complete for the planned UI modernization scope.
- Sprint 6: current sprint, focused on visual browser smoke verification, staging end-to-end operations verification, production promotion rehearsal, and production hardening.
- Sprint 6A: core application-shell, dashboard, page-normalization, and automated local UI regression slices are implemented; remaining UI work is visual browser smoke verification when browser automation is available.

## Current Stack

- Python 3.12+
- uv
- FastAPI
- Jinja2
- Bootstrap 5
- SQLite
- Local filesystem storage
- Pytest
- Ruff
- Playwright planned for E2E tests
- VPS deployment planned with Docker Compose app containers, host Nginx, HTTPS, GHCR images, GitHub Actions, and separate staging/production data directories

## Current UI Direction

The current requested product direction is to make the interface feel more like an application than a collection of web pages.

Active screen and workflow spec:

- `docs/ui/ui-flow.md`

Historical redesign plan:

- `docs/archive/app-ui-redesign.md`

Key points:

- Keep FastAPI, Jinja2, Bootstrap 5, and local CSS.
- Add a shared authenticated app shell.
- Use persistent role-aware navigation with a desktop sidebar and compact top bar.
- Use mobile collapsed navigation.
- Make `/admin` a richer organizer operations dashboard.
- Make `/team` a clearer participant submission-status dashboard.
- Preserve current backend behavior, routes, permissions, and server-rendered architecture.

Implemented Sprint 6A UI slices:

- Shared authenticated app shell with role-aware sidebar/topbar navigation.
- Participant upload navigation entry at `/team/submissions/new`.
- Participant dashboard submission availability by subtask and period.
- Organizer-approved one-time replacement uploads with participant-hidden superseded metrics and organizer-visible metric history.
- Organizer dashboard period open/closed/reopened state.
- Organizer dashboard recent validation-failure panel.
- Upload page period open/closed/reopened state beside normal/late choices.
- Normalized organizer review pages for submissions, submission details, and leaderboard.
- Planned metric-table display improvement: show aggregate and per-query metrics as pivoted tables with metric names as columns.
- Normalized organizer account pages for teams and users.
- Normalized organizer operations pages for ground-truth versions and submission periods.
- Normalized participant form pages for submission upload and password change.
- Responsive app-shell guards for mobile navigation, visible labels, table wrappers, and compact row overflow.

## Current Refactor State

The initial small, document-driven route/web-layer refactor is implemented. `docs/technical/refactor-plan.md` now points to the archived implementation record in `docs/archive/refactor-plan.md`.

Key points:

- Routes, permissions, templates, database schema, and deployment behavior were kept unchanged.
- `app/main.py` now focuses on app assembly, lifespan startup, static mounting, health/home routes, and router registration.
- Shared web helpers live in `app/web.py`.
- Auth/password routes live in `app/routes/auth.py`.
- Team dashboard and participant upload routes live in `app/routes/team.py`.
- Organizer routes and download helpers live in `app/routes/admin.py`.
- Domain modules such as `app/submissions.py`, `app/evaluation.py`, `app/accounts.py`, and `app/ground_truth.py` remain intact.

## Current Documentation Layout

Project documentation is organized under `docs/`, with `README.md` and `HANDOFF.md` kept at the repository root for quick orientation.

Key groups:

- `docs/product/`: requirements, user stories, and resolved questions.
- `docs/ui/`: UI flow and application-shell redesign.
- `docs/technical/`: architecture, data model, submission/evaluation specs, diagrams, and refactor plan.
- `docs/planning/`: Scrum implementation plan.
- `docs/deployment/`: deployment strategy, environments, runbook, checklist, restore, VPS setup, and GitHub secrets.

The repository-level `deployment/` directory is reserved for runtime deployment assets such as Nginx templates, environment examples, and shell scripts.

## Current Deployment Plan

- Development runs on the developer laptop with `uv run uvicorn app.main:app --reload`.
- Staging and production run on the same Sakura VPS.
- Host Nginx terminates HTTPS and routes by hostname.
- Staging domain: `submission-staging.modelretrieval-1.happysocial.net`.
- Production domain: `submission.modelretrieval-1.happysocial.net`.
- Staging upstream: `127.0.0.1:8001`.
- Production upstream: `127.0.0.1:8002`.
- Docker images are published to GHCR.
- Staging deploys automatically from `main`.
- Production deploys from immutable `v*` tags.
- The VPS deploy user should be passwordless and use SSH key authentication.
- Staging and production may use the same SSH deploy key, but they must not share `.env`, `SECRET_KEY`, database, storage directory, or Compose project name.
- If GHCR pull returns unauthorized, log in on the VPS with a GitHub PAT that has `read:packages`.
- If the container cannot create `/data/storage`, fix ownership of `/opt/modelretrieval/<env>/data` to match the app container UID/GID.
- If Nginx cannot build `server_names_hash`, set `server_names_hash_bucket_size 128;` in the `http { ... }` block.

## Database Migration Work

Alembic is implemented as the database migration tool.

Source of truth:

- `docs/technical/database-migrations.md`

Implementation state:

- Keep the runtime app on raw `sqlite3` for now.
- Alembic is used only for versioned schema management.
- The current schema is captured in baseline revision `20260706_0001`.
- `python -m app.cli migrate` applies migrations using the app settings.
- Run `alembic upgrade head` explicitly during staging and production deployment before app startup.
- Development and test startup use migration-backed `initialize_database()`.
- Staging and production app startup verifies that the database is already at the Alembic head revision.
- Keep production rollback based on pre-deploy backups rather than relying on Alembic downgrades.

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
146 passed

uv run --extra dev ruff check .
All checks passed

uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
Application startup complete

curl -fsS http://127.0.0.1:8000/health
{"status":"ok","environment":"development"}

curl -fsS http://127.0.0.1:8000/login
Rendered public login shell with sign-in form

In-app browser backend was unavailable during the latest verification, so visual browser smoke verification remains pending.
```

## Implemented Code

Foundation:

- `app/config.py`: settings and environment loading.
- `app/storage.py`: local storage directory bootstrap.
- `app/db.py`: SQLite schema and default submission periods.
- `app/main.py`: FastAPI app assembly, lifespan startup, static mounting, health page, home page, and router registration.
- `app/web.py`: shared Jinja templates, redirects, session account lookup, and role guards.
- `app/routes/auth.py`: login, logout, and password-change routes.
- `app/routes/team.py`: team dashboard and participant submission upload routes.
- `app/routes/admin.py`: organizer dashboard, team/user management, ground-truth upload/activation, submission-period controls, submission review/detail, private leaderboard, CSV export, and submission bundle download routes.
- `app/ground_truth.py`: ground-truth file storage, SHA-256 calculation, CSV format validation, version metadata helpers, activation helpers, active ground-truth requirement extraction.
- `app/submissions.py`: TREC_EVAL parser, field-level submission validation, duplicate row validation, score-vs-rank order validation, query/model completeness validation, combined validation against active ground truth, submission file guards, submission storage, submission attempt persistence helpers.
- `app/submissions.py`: also includes submission-period lookup and open/closed deadline helpers.
- `app/submissions.py`: also includes organizer submission list/detail query helpers.
- `app/submissions.py`: also includes submission bundle query helpers.
- `app/evaluation.py`: pure nDCG, MRR, Subtask A evaluation, Subtask B evaluation, ground-truth metric loading, evaluation result persistence, leaderboard query helpers, and evaluation status helpers.

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
- `app/templates/admin_periods.html`
- `app/templates/admin_submissions.html`
- `app/templates/admin_submission_detail.html`
- `app/templates/admin_leaderboard.html`
- `app/static/app.css`: Bootstrap companion styling for layout, navigation, badges, tables, forms, and responsive polish.

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
- `tests/test_admin_periods.py`
- `tests/test_admin_submissions.py`
- `tests/test_admin_leaderboard.py`

## Product Decisions

Key decisions already made:

- Users are participant teams and organizers.
- Teams are identified by `team_id`.
- Each team has one shared account.
- Organizers add teams and generate visible passwords.
- Participant team self-service password change is implemented at `/account/password`.
- Only registered teams can submit.
- Subtask A and Subtask B submissions are uploaded separately.
- Upload format is one TREC_EVAL-format file, any filename extension, maximum 10 MB.
- Each subtask allows up to 5 runs.
- One current successful submission per team/subtask/period, with organizer-approved one-time replacement upload support.
- Failed validation attempts do not count.
- Normal deadline: August 1, 2026 at 15:00 JST.
- Late deadline: October 15, 2026 at 23:59 JST.
- Organizers can reopen periods.
- Participants see scores immediately.
- Leaderboard is organizer-only.
- Ground truth is uploaded/configured by organizers and stored on the server local filesystem.
- Evaluation is internal.
- Participant-visible scores are aggregate run-level metrics only.
- Per-query metric details are implemented as organizer-only diagnostics.
- Records are retained forever.
- No email notifications.
- VPS deployment.
- Three environments: local development, staging on Sakura VPS, and production on the same Sakura VPS.
- Use Muumuu Domain DNS with separate staging and production hostnames.
- Use host Nginx as reverse proxy.
- Use Docker Compose for staging and production app stacks.
- Deploy staging automatically from `main`; deploy production from explicit version tags.
- Keep the frontend server-rendered with FastAPI/Jinja2.
- Use Bootstrap 5 plus a small local CSS layer for UI.
- Do not introduce React, Vue, or a frontend build pipeline for this phase.
- Make the next UI slice feel like an application shell rather than standalone pages.

## Sprint 6 Deployment Documents

Deployment planning documents:

- `docs/deployment/deployment-strategy.md`: environment model, release flow, Docker Compose recommendation, DNS/Nginx shape, backup and rollback strategy.
- `docs/deployment/deployment-environments.md`: development, staging, and production domains, data paths, environment variables, and secret rules.
- `docs/deployment/deployment-runbook.md`: setup, deploy, promote, rollback, backup, restore, logs, and smoke-test operations.
- `docs/deployment/deployment-checklist.md`: confirmed inputs, one-time VPS, staging, production, backup, and launch-readiness checklist.

## Diagram Documents

Created `docs/technical/diagrams.md` to define the diagram set and drawing order.

Initial Mermaid diagrams added:

- Deployment diagram in `docs/deployment/deployment-strategy.md`.
- CI/CD flow diagram in `docs/deployment/deployment-strategy.md`.
- Submission sequence diagram in `docs/technical/submission-spec.md`.
- Data model / ER diagram in `docs/technical/data-model.md`.

Use Mermaid in Markdown for the first version of diagrams.

## Docker Deployment Files

Docker deployment files added:

- `Dockerfile`
- `.dockerignore`
- `compose.staging.yml`
- `compose.production.yml`
- `deployment/staging.env.example`
- `deployment/production.env.example`

Staging binds the app to `127.0.0.1:8001`. Production binds the app to `127.0.0.1:8002` and requires `APP_IMAGE` to reference an immutable image tag.

## Nginx Deployment Files

Nginx templates added:

- `deployment/nginx/staging.conf.example`
- `deployment/nginx/production.conf.example`

The templates include HTTP-to-HTTPS redirect blocks, Let's Encrypt certificate paths, `client_max_body_size 12m`, proxy timeouts, forwarded headers, and localhost upstreams for staging and production.

## Backup Deployment Files

Backup and restore files added:

- `deployment/scripts/backup.sh`
- `deployment/scripts/smoke-check.sh`
- `docs/deployment/restore.md`

The backup script creates timestamped backups containing `app.sqlite3`, `storage.tar.gz`, optional `env.snapshot`, and `manifest.txt`.

## CI/CD Deployment Files

GitHub Actions workflow added:

- `.github/workflows/ci-cd.yml`

The workflow runs tests and lint, builds and pushes GHCR images, deploys staging from branch pushes, deploys production from `v*` tags, runs production backup before deploy, and runs smoke checks after deploy.

## Operator Setup Documents

Added operator-facing setup docs:

- `docs/deployment/vps-setup.md`: Sakura VPS, Docker, Nginx, Certbot, directories, first manual deploy, and first admin setup.
- `docs/deployment/github-secrets.md`: GitHub Actions secrets, SSH key expectations, remote paths, image behavior, and environment protection.

Current deployment notes captured in docs:

- `APP_IMAGE` is the GHCR image reference used by Compose.
- VPS GHCR pulls may require `docker login ghcr.io` with a GitHub PAT that has `read:packages`.
- `SECRET_KEY` should be generated with a high-entropy command such as `openssl rand -hex 32`, and staging/production must use different values.
- A passwordless deploy user can be created with `sudo adduser --disabled-password --gecos "" deploy`.
- The same SSH key may be used for staging and production, although separate keys give cleaner rotation.
- Bind-mounted `data/` ownership must match the app container UID/GID to avoid `/data/storage` permission errors.
- Long hostnames may require `server_names_hash_bucket_size 128;` in Nginx.
- Home page startup copy was changed from the old Sprint 0 placeholder to task-specific NTCIR-19 ModelRetrieval copy.

## Completed Implementation History

Detailed completed story notes are archived at `docs/archive/implementation-history.md`. Keep `HANDOFF.md` focused on current continuation state, verification status, and next work.


## Next Recommended Work

Run the visual browser smoke check when a browser backend is available, then complete the staging end-to-end operations workflow and prepare production promotion.

Target behavior:

- Complete organizer/team workflow checks on staging.
- Upload and activate staging ground truth.
- Upload invalid and valid team submissions on staging.
- Confirm participant scores, organizer leaderboard, CSV export, and bundle download on staging.
- Take a production backup before each production update.
- Promote production only from an immutable `v*` tag after staging passes.

Completed deployment checks:

- GitHub Actions staging deployment from `main` has been verified.
- CI tests and lint passed in GitHub Actions.
- GHCR image publish completed.
- Staging `APP_IMAGE` was updated remotely.
- Staging `/health` and `/login` checks passed over HTTPS.

Suggested remaining checks:

- Staging organizer login and team creation.
- Staging team login and access-control check.
- Staging ground-truth upload/activation.
- Staging valid and invalid submission uploads.
- Staging leaderboard, CSV export, and submission bundle download.
- Production backup script before production deploy.

## Docs To Read First In A New Session

1. `HANDOFF.md`
2. `README.md`
3. `docs/index.md`
4. `docs/planning/implementation-plan.md`
5. `docs/ui/ui-flow.md`
6. `docs/technical/data-model.md`
7. `docs/deployment/deployment-strategy.md`
8. `docs/deployment/deployment-environments.md`
9. `docs/deployment/deployment-runbook.md`
10. `docs/deployment/deployment-checklist.md`
11. `docs/deployment/vps-setup.md`
12. `docs/deployment/github-secrets.md`
13. `docs/technical/submission-spec.md`
14. `docs/technical/evaluation-spec.md`
15. `docs/product/requirements.md`
16. `docs/product/decisions.md`
17. `docs/product/user-stories.md`
18. `docs/technical/architecture.md`
