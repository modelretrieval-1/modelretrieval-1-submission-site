# Refactor Plan

## Purpose

This document defines a small, document-driven refactor plan for the NTCIR-19 ModelRetrieval submission system.

The goal is to reduce repository bulk and make future Sprint 6 UI work easier without changing product behavior, routes, permissions, templates, database schema, or deployment shape.

## Implementation Checkpoint

Initial implementation is complete.

Implemented:

- `app/web.py` contains shared web helpers.
- `app/routes/auth.py` contains login, logout, and password-change routes.
- `app/routes/team.py` contains team dashboard and participant upload routes.
- `app/routes/admin.py` contains organizer routes and download helpers.
- `app/main.py` is now focused on app assembly, health/home routes, and router registration.

Deferred:

- `app/routes/downloads.py` was not created because the download helpers are still small enough to live with the admin workflow.
- Domain modules remain unchanged.

Verified:

```text
uv run --extra dev pytest
142 passed

uv run --extra dev ruff check .
All checks passed
```

## Current Problem

The codebase is still healthy, but before this refactor `app/main.py` had become the main growth point.

It owned too many responsibilities:

- FastAPI app construction and startup.
- Session lookup and role redirects.
- Login and logout routes.
- Team dashboard and upload routes.
- Organizer dashboard and management routes.
- Ground-truth routes.
- Submission-period routes.
- Submission review/detail routes.
- Leaderboard routes.
- CSV and ZIP response helpers.
- Template rendering helpers.

The domain modules are larger than tiny modules, but their boundaries are clearer:

- `app/accounts.py`: account and password operations.
- `app/submissions.py`: upload validation, period logic, submission persistence, admin queries, bundle queries.
- `app/evaluation.py`: metrics, evaluation persistence, team summaries, leaderboard rows.
- `app/ground_truth.py`: ground-truth storage, validation, versioning, activation, active requirements.

For now, the refactor should focus on route and web-layer structure, not on splitting domain logic.

## Refactor Principles

- Preserve all existing URLs.
- Preserve all current permissions and redirects.
- Preserve server-rendered FastAPI/Jinja2 architecture.
- Preserve the SQLite schema.
- Preserve template names and template variables unless a later UI story changes them.
- Avoid mixing refactor work with the application-shell redesign.
- Avoid broad renames unless they directly reduce risk or confusion.
- Keep each slice small enough to review and test independently.
- Run the existing test suite after each slice.

## Target Shape

Recommended eventual structure:

```text
app/
  main.py
  web.py
  routes/
    __init__.py
    auth.py
    team.py
    admin.py
    downloads.py
```

Intended responsibilities:

- `app/main.py`: app factory, lifespan, static mounting, router registration, health/home routes if still small.
- `app/web.py`: shared web helpers such as `templates`, `redirect`, session account lookup, role guards, and common template context.
- `app/routes/auth.py`: login, logout, password-change routes.
- `app/routes/team.py`: team dashboard and participant upload flow.
- `app/routes/admin.py`: organizer dashboard, teams, users, ground truth, periods, submissions, submission detail, leaderboard.
- `app/routes/downloads.py`: leaderboard CSV and submission bundle downloads if these helpers make `admin.py` too large.

This is a target, not a mandate to create every file in the first slice.

## Recommended Slices

### Slice 1: Extract Shared Web Helpers

Move low-risk helper code out of `app/main.py` into `app/web.py`.

Candidates:

- `templates`
- `redirect`
- `get_session_account`
- `require_organizer`
- `require_team`
- common render helpers only if they are reused across route modules

Acceptance criteria:

- No route behavior changes.
- No template changes.
- Tests still pass.

### Slice 2: Extract Auth Routes

Create `app/routes/auth.py` for:

- `/login`
- `/logout`
- `/account/password`

Keep the existing route paths and response behavior.

Acceptance criteria:

- Team and organizer login tests still pass.
- Password-change tests still pass.
- Access-control redirects are unchanged.

### Slice 3: Extract Team Routes

Create `app/routes/team.py` for:

- `/team`
- `/team/submissions/new`
- participant upload handling and result rendering

Acceptance criteria:

- Team dashboard behavior is unchanged.
- Upload validation, accepted submission, rejected attempt, period, and one-success tests still pass.
- Participant score display is unchanged.

### Slice 4: Extract Admin Routes

Create `app/routes/admin.py` for:

- `/admin`
- `/admin/teams`
- `/admin/users`
- `/admin/ground-truth`
- `/admin/periods`
- `/admin/submissions`
- `/admin/submissions/{submission_id}`
- `/admin/leaderboard`

Acceptance criteria:

- Organizer dashboard and admin management behavior are unchanged.
- Team accounts still cannot access organizer routes.
- Existing admin tests still pass.

### Slice 5: Extract Download Helpers If Needed

If `admin.py` becomes too large, create `app/routes/downloads.py` or `app/downloads.py` for:

- leaderboard CSV content generation
- submission bundle ZIP generation
- submission bundle metadata CSV generation

Acceptance criteria:

- CSV export content is unchanged.
- Bundle archive structure and metadata are unchanged.
- Existing download tests still pass.

## What Not To Refactor Yet

Do not split these modules unless a later change creates a concrete need:

- `app/accounts.py`
- `app/submissions.py`
- `app/evaluation.py`
- `app/ground_truth.py`
- `app/db.py`

Do not introduce:

- React, Vue, or a frontend build pipeline.
- SQLAlchemy or a migration framework.
- New deployment topology.
- New database schema.
- New auth/session model.

## Testing Plan

For every slice:

```bash
uv run --extra dev pytest
uv run --extra dev ruff check .
```

If time is tight, run the focused tests first, then the full suite before merging:

- Auth slice: `tests/test_login_flow.py`, `tests/test_password_change.py`
- Team slice: `tests/test_team_submissions.py`, `tests/test_submissions.py`
- Admin slice: `tests/test_admin_*.py`, `tests/test_ground_truth.py`
- Download slice: `tests/test_admin_submissions.py`, `tests/test_admin_leaderboard.py`

## Definition Of Done

The refactor is done when:

- `app/main.py` is mostly app assembly.
- Route modules own route handlers for their workflow area.
- Shared web helpers have one obvious home.
- All current routes still exist.
- All current tests pass.
- Ruff passes.
- Documentation links point to this plan.
