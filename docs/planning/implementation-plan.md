# Implementation Plan

## Approach

Build the NTCIR-19 ModelRetrieval submission system using Scrum-style increments.

Each sprint should produce a working, testable slice of the system. Testing is not a final phase; unit, integration, and E2E tests are part of the definition of done for each story.

Recommended stack:

- FastAPI.
- Jinja2 server-rendered templates.
- Bootstrap 5 for UI components and layout.
- Local project CSS for task-specific visual polish.
- SQLite.
- Local filesystem storage.
- uv for Python dependency and virtual environment management.
- Pytest for unit and integration tests.
- Playwright for E2E browser tests.
- Ruff or similar linting.

Current UI direction:

- Continue using FastAPI, Jinja2, Bootstrap 5, and local CSS.
- Redesign authenticated pages around an application shell with role-aware navigation.
- Use `../ui/app-ui-redesign.md` as the source of truth before implementation.
- Keep the richer UI operational and dashboard-like, not marketing-style.

Current refactor state:

- The initial route/web-layer refactor from `../technical/refactor-plan.md` is implemented.
- `app/main.py` now focuses on app assembly and router registration.
- Shared helpers live in `app/web.py`, with auth, team, and admin routes under `app/routes/`.
- Domain modules, schema, routes, permissions, templates, and deployment behavior were left unchanged.

## Scrum Roles

Suggested roles:

- Product Owner: task organizer who decides requirements and priorities.
- Scrum Master: person who keeps sprint planning, review, and blockers clear.
- Developer: implements backend, frontend, tests, and deployment.
- Stakeholders: other organizers who review workflows and reports.

One person can hold multiple roles in a small project.

## Sprint Cadence

Recommended sprint length:

- 1 week if development time is limited and feedback is frequent.
- 2 weeks if development time is fragmented.

Each sprint should include:

- Sprint planning.
- Development.
- Testing.
- Sprint review/demo.
- Retrospective.
- Backlog refinement.

## Definition of Ready

A story is ready for sprint work when it has:

- Clear user role.
- Clear user goal.
- Acceptance criteria.
- Required validation rules.
- Required UI states.
- Required tests.
- Known dependencies.

## Definition of Done

A story is done only when:

- The feature works locally.
- Unit tests are added or updated.
- Integration tests are added or updated when database, file storage, auth, or evaluation behavior is involved.
- E2E tests are added or updated for user-facing flows.
- Error states are implemented.
- Access control is checked.
- Documentation is updated if behavior changes.
- The app passes linting and test suite.
- The feature is demo-ready.

## Testing Strategy

### Unit Tests

Use unit tests for pure logic.

Target areas:

- TREC_EVAL parsing.
- Field validation.
- Run count validation.
- Query/model completeness validation.
- Rank and score-order comparison.
- nDCG calculation.
- MRR calculation.
- Deadline status calculation in JST.
- Password generation helpers.
- File checksum helpers.

Unit tests should not require a running server.

### Integration Tests

Use integration tests for behavior across database, storage, and service layers.

Target areas:

- Team login with hashed passwords.
- Organizer login.
- Team creation and password generation.
- Subtask eligibility checks.
- Submission upload stored on local filesystem.
- Validation failure stored in database.
- Successful submission stored with run rows.
- One-successful-submission-per-team-subtask-period rule.
- Ground-truth upload and activation.
- Evaluation result persistence.
- Leaderboard query and sorting.
- CSV export generation.
- Bundle download generation.

Integration tests may use a temporary SQLite database and temporary storage directories.

### E2E Tests

Use Playwright for browser-level tests.

Target flows:

- Team logs in and sees dashboard.
- Team uploads invalid submission and sees validation errors.
- Team uploads valid Subtask A submission and sees nDCG scores.
- Team cannot upload again after success for the same subtask and period.
- Team cannot access another team's submission.
- Organizer logs in.
- Organizer creates team and generated password is shown.
- Organizer uploads ground truth.
- Organizer views submissions table.
- Organizer views private leaderboard.
- Participant cannot access organizer leaderboard.

E2E tests should use seeded test data and isolated test storage.

### Manual Acceptance Tests

At sprint review, manually verify:

- Main happy path.
- Main failure path.
- Permissions.
- Visual usability.
- Data displayed in JST.

## Environments

### Local Development

Purpose:

- Fast iteration and automated tests.

Expected setup:

- Dependencies installed with `uv sync --extra dev`.
- SQLite database under local project data directory.
- Local storage directories.
- Seed command for sample teams, ground truth, and submissions.

### Test Environment

Purpose:

- Run integration and E2E tests without touching development data.

Expected setup:

- Temporary SQLite database.
- Temporary storage root.
- Deterministic seed data.

### Production VPS

Purpose:

- Official participant submission system.

Expected setup:

- Docker Compose app container.
- Host Nginx reverse proxy with HTTPS.
- GitHub Container Registry image pulls.
- GitHub Actions CI/CD.
- SQLite and uploaded files on persistent bind-mounted disk.
- Backup and restore scripts or runbooks.

## Product Backlog

### Epic 1: Project Foundation

Goal:

- Create a maintainable app skeleton and development workflow.

Stories:

- Initialize FastAPI project structure.
- Add `uv` project workflow and lockfile.
- Add configuration management.
- Add SQLite database setup.
- Add local storage directory setup.
- Add base templates and layout.
- Add test framework.
- Add seed data command.

Required tests:

- Unit test for settings loading.
- Integration test for database initialization.
- Integration test for storage directory creation.

### Epic 2: Authentication and Accounts

Goal:

- Support team and organizer password login.

Stories:

- Organizer login.
- Team login.
- Logout.
- Password hashing.
- Organizer password change.
- Participant team password change.
- Organizer creates team with generated password.
- Organizer creates organizer user with generated password.

Required tests:

- Unit tests for password helpers.
- Integration tests for login and session behavior.
- Integration tests for organizer and team password changes.
- E2E tests for organizer login and team login.

### Epic 3: Team Dashboard and Submission Periods

Goal:

- Let teams see their eligible subtasks and submission status.

Stories:

- Show team dashboard.
- Store normal and late periods.
- Enforce JST deadlines.
- Allow organizer to reopen a period.
- Show upload links only when allowed.

Required tests:

- Unit tests for period status logic.
- Integration tests for eligibility and one-success rule.
- E2E test for dashboard status.

### Epic 4: Ground Truth Management

Goal:

- Let organizers upload and activate ground-truth files.

Stories:

- Upload Subtask A ground truth.
- Upload Subtask B ground truth.
- Validate ground-truth files.
- Activate ground-truth version.
- Store version metadata and checksum.

Required tests:

- Unit tests for ground-truth parsers.
- Integration tests for upload, validation, activation, and protection from participant access.
- E2E test for organizer upload.

### Epic 5: Submission Parsing and Validation

Goal:

- Reject invalid participant files immediately.

Stories:

- Parse TREC_EVAL `.txt` files.
- Enforce 10 MB limit.
- Enforce `.txt` upload only.
- Enforce up to 5 RunIDs.
- Enforce all queries and all candidate models.
- Allow ties by line order.
- Compare submitted rank with score-derived order.
- Store validation errors.

Required tests:

- Unit tests for parser and every validation rule.
- Integration tests for validation failure persistence.
- E2E test for invalid upload and error page.

### Epic 6: Evaluation

Goal:

- Evaluate accepted submissions internally.

Stories:

- Implement nDCG@1, nDCG@3, nDCG@5.
- Implement MRR.
- Evaluate each RunID independently.
- Store run-level scores.
- Show participant results.
- Reference active ground-truth version.

Required tests:

- Unit tests for nDCG and MRR with known expected values.
- Integration tests for accepted submission evaluation.
- E2E test for valid upload and score display.

### Epic 7: Organizer Review and Leaderboard

Goal:

- Let organizers inspect submissions and scores.

Stories:

- Admin dashboard.
- Submissions table with filters.
- Submission detail page.
- Private leaderboard.
- Normal/late period filter.
- CSV leaderboard export.
- Submission bundle download.

Required tests:

- Integration tests for leaderboard sorting and filters.
- Integration tests for CSV and bundle generation.
- E2E tests for organizer leaderboard and participant access denial.

### Epic 8: VPS Deployment

Goal:

- Prepare the system for production deployment.

Stories:

- Add production configuration guide.
- Add Dockerfile and environment-specific Docker Compose files.
- Add Nginx reverse proxy examples.
- Add GitHub Actions workflow for CI, image publishing, staging deploy, and tagged production deploy.
- Add backup script and restore instructions.
- Add deployment checklist.
- Add first-admin creation command.
- Add Sakura VPS setup and GitHub secrets guides.

Required tests:

- Smoke test app startup.
- Smoke test database migration/init.
- Manual VPS deployment checklist.

## Suggested Sprint Plan

Current implementation status:

- Sprint 0 is complete.
- Sprint 1 is complete for the planned v1 account scope.
- Implemented Sprint 1 items: password hashing, generated passwords, organizer/team account primitives, signed cookie sessions, login/logout, minimal team dashboard, minimal organizer dashboard, organizer team management UI, organizer user management UI, organizer password change page, and tests.
- Sprint 2 validation-core scope is complete.
- Implemented Sprint 2 items: organizer ground-truth upload page, local filesystem storage, SHA-256 metadata, upload history, organizer-only access, ground-truth CSV format validation, ground-truth version activation, TREC_EVAL parser with field-level validation, duplicate row validation, score-vs-rank order validation, query/model completeness validation, active ground-truth requirement extraction, combined validation against active ground truth, participant submission upload UI, validation failure persistence, accepted submission/run persistence, and tests.
- Sprint 3 is complete for the planned evaluation and participant-result scope.
- Implemented Sprint 3 items: pure metric calculation helpers, active ground-truth metric loading, accepted submission evaluation, `evaluation_results` persistence, participant score display, one-successful-submission enforcement, JST deadline/open-period enforcement, organizer submission-period controls, and tests.
- Participant-selected normal/late submission period is complete.
- Organizer submissions table and detail view is complete.
- Organizer private leaderboard view is complete.
- Leaderboard CSV export is complete.
- Submission bundle download is complete.
- Sprint 5 UI modernization is complete.
- Sprint 6A application-shell and page-normalization slices are complete for the core planned pages: role-aware sidebar/topbar navigation, participant upload navigation, participant submission availability, organizer period state, organizer validation-failure panel, upload-page period state, normalized organizer review/account/operations pages, and normalized participant form pages.
- Sprint 6 deployment documentation and tooling are implemented; next item is staging deployment rehearsal on Sakura VPS.

### Sprint 0: Planning and Scaffolding

Deliverables:

- Finalized requirements docs.
- FastAPI project skeleton.
- uv dependency workflow.
- Test framework.
- Database/storage initialization.

Demo:

- App starts locally.
- Test suite runs.

Status:

- Complete.
- Verified with `uv run --extra dev pytest`.

### Sprint 1: Accounts and Team Setup

Deliverables:

- Organizer login.
- Team login.
- Team creation by organizer.
- Generated passwords.
- Basic dashboards.

Demo:

- Organizer creates a team.
- Team logs in.

Status:

- Complete for the planned v1 account scope.
- Completed: account primitives, password generation/hashing, authentication, signed sessions, login/logout, minimal role dashboards, `/admin/teams`, team creation form, generated password display, subtask assignment UI, team password regeneration, `/admin/users`, organizer creation form, organizer generated password display, organizer password regeneration, `/account/password`, organizer password change flow, and participant team password change flow.

### Sprint 2: Ground Truth and Validation Core

Deliverables:

- Ground-truth upload.
- TREC_EVAL parser.
- Submission validation rules.
- Validation error persistence and UI.

Demo:

- Organizer uploads ground truth.
- Team uploads invalid file and sees errors.

Status:

- Complete for the planned validation-core scope.
- Completed: `/admin/ground-truth`, upload form, local file storage under `storage/ground-truth`, checksum calculation, `ground_truth_versions` row creation, upload history table, organizer-only access, Subtask A ground-truth column validation, Subtask B ground-truth column validation, activation of one ground-truth version per subtask, TREC_EVAL parser with field-level validation, duplicate row validation, score-vs-rank order validation, query/model completeness validation, active ground-truth requirement extraction, combined validation against active ground truth, participant upload UI, validation failure persistence, accepted submission persistence, run metadata persistence.
- Remaining validation-core polish can be handled later if period-reopen UI or deadline enforcement is prioritized before evaluation.

### Sprint 3: Evaluation and Participant Results

Deliverables:

- nDCG and MRR implementation.
- Successful submission evaluation.
- Participant score page.
- One-successful-submission rule.

Demo:

- Team uploads valid file and sees scores.
- Team cannot submit again for same subtask and period.

Status:

- Complete for the planned evaluation and participant-result scope.
- Completed: pure metric calculation helpers for nDCG, macro nDCG by run, MRR, Subtask A evaluation, Subtask B evaluation, unit tests with known expected values, active ground-truth metric loading, accepted submission evaluation, `evaluation_results` persistence, `evaluated` status updates, upload-page score display, team-dashboard latest score summaries, one-successful-submission enforcement with friendly errors, JST deadline/open-period enforcement, and organizer submission-period controls.

### Sprint 4: Organizer Operations

Deliverables:

- Submissions table.
- Submission detail.
- Private leaderboard.
- CSV export.
- Bundle download.

Status:

- Complete for the planned organizer-operations scope.
- Participant-selected submission period change request is complete.
- Organizer submissions table and detail view is complete.
- Organizer private leaderboard view is complete.
- Leaderboard CSV export is complete.
- Submission bundle download is complete.
- Next continue with staging deployment rehearsal and production promotion hardening.

Demo:

- Organizer reviews all submissions and exports leaderboard.

### Sprint 5: UI Modernization

Deliverables:

- Bootstrap 5 integration for server-rendered pages.
- Improved role-aware global navigation.
- Improved form layout, labels, helper text, validation messages, and action placement.
- Improved admin tables, filters, badges, and empty states.
- Improved participant dashboard, upload, validation-error, and result pages.
- Accessibility pass for labels, focus states, color-independent status text, and responsive layout.

Technical decisions:

- Keep FastAPI and Jinja2 templates.
- Use Bootstrap 5 as the component/layout foundation.
- Keep custom styling in `app/static/app.css`.
- Do not introduce React, Vue, or a frontend build pipeline in this phase.
- Use minimal JavaScript only where Bootstrap components require it or where progressive enhancement clearly improves usability.

Demo:

- Organizer can navigate between admin pages from a consistent navbar.
- Team can use the dashboard and upload flow with clearer forms and statuses.
- Organizer can scan submissions and leaderboard pages with improved filters and tables.

Status:

- Complete for the planned UI modernization scope.

### Sprint 6: Production Hardening

Deliverables:

- VPS deployment docs.
- Reverse proxy config.
- Docker Compose configuration.
- CI/CD deployment workflow.
- Backup plan.
- Final E2E regression suite.

Demo:

- Run app in production-like mode.
- Complete team and organizer workflows.

Status:

- Deployment planning documents have been added and updated:
  - `../deployment/deployment-strategy.md`
  - `../deployment/deployment-environments.md`
  - `../deployment/deployment-runbook.md`
  - `../deployment/deployment-checklist.md`
- Diagram planning is in `../technical/diagrams.md`, and Mermaid diagrams have been added for deployment, CI/CD, submission workflow, and the data model.
- Docker deployment files have been added: `Dockerfile`, `.dockerignore`, `compose.staging.yml`, `compose.production.yml`, and environment templates under `deployment/`.
- Nginx templates have been added under `deployment/nginx/` for staging and production reverse proxying.
- Backup and restore tooling has been added under `deployment/scripts/backup.sh` and `../deployment/restore.md`.
- CI/CD workflow has been added in `.github/workflows/ci-cd.yml` with smoke checks via `deployment/scripts/smoke-check.sh`.
- Operator setup docs have been added in `../deployment/vps-setup.md` and `../deployment/github-secrets.md`.
- Current deployment direction: local development, staging and production on one Sakura VPS, Muumuu Domain DNS, host Nginx, Docker Compose app stacks, automatic staging deployment from `main`, and production deployment from explicit version tags.
- Current project domains are `submission-staging.modelretrieval-1.happysocial.net` and `submission.modelretrieval-1.happysocial.net`.
- Deployment docs capture the GHCR login path, `APP_IMAGE` meaning, `SECRET_KEY` generation, passwordless deploy user, bind-mounted data ownership fix, and Nginx long-hostname hash bucket fix.
- Remaining Sprint 6 work is staging rehearsal, GitHub Actions deploy verification, production promotion rehearsal, and final E2E regression coverage.

### Sprint 6A: Application UI Redesign

Goal:

- Make the existing server-rendered system feel like a cohesive application rather than standalone pages.

Deliverables:

- App-shell UI design document.
- Shared authenticated layout with sidebar and top bar.
- Role-aware navigation for organizer and participant workflows.
- Richer organizer dashboard.
- Clearer participant dashboard.
- Normalized page headers, action bars, filters, tables, status badges, and detail panels.

Technical decisions:

- Keep FastAPI, Jinja2, Bootstrap 5, and local CSS.
- Do not introduce React, Vue, or a frontend build pipeline.
- Preserve route behavior and access control.

Status:

- Documentation exists in `../ui/app-ui-redesign.md`.
- Core implementation slices are complete: shared authenticated shell and role-aware navigation, participant upload navigation, participant dashboard submission availability by subtask and period, organizer dashboard period state, organizer dashboard recent validation failures, upload page period state, normalized organizer review/account/operations pages, and normalized participant form pages.
- Remaining implementation should focus on final responsive/accessibility/browser smoke verification, then staging deployment rehearsal and production hardening.

## Initial MVP

The MVP should include:

- Password login for teams and organizers.
- Organizer team creation.
- Ground-truth upload.
- Team upload of one `.txt` file per subtask/period.
- Immediate validation.
- Internal evaluation.
- Participant score display.
- Admin-only leaderboard.

The MVP can defer:

- Advanced export center.
- Re-evaluation UI.
- Detailed audit event browsing.
- Organizer user management polish.

## Quality Gates

Before production launch:

- All unit tests pass.
- All integration tests pass.
- E2E happy paths and key failure paths pass.
- No participant can access admin pages.
- No team can access another team's results.
- Ground-truth files are not publicly accessible.
- Backup and restore procedure is documented.
- Deadlines are verified in JST.
- Sample submissions produce expected scores.
