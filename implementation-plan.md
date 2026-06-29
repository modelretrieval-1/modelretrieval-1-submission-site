# Implementation Plan

## Approach

Build the NTCIR-19 ModelRetrieval submission system using Scrum-style increments.

Each sprint should produce a working, testable slice of the system. Testing is not a final phase; unit, integration, and E2E tests are part of the definition of done for each story.

Recommended stack:

- FastAPI.
- Jinja2 server-rendered templates.
- SQLite.
- Local filesystem storage.
- uv for Python dependency and virtual environment management.
- Pytest for unit and integration tests.
- Playwright for E2E browser tests.
- Ruff or similar linting.

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

- FastAPI app served by Uvicorn.
- Reverse proxy using Nginx or Caddy.
- HTTPS.
- systemd service.
- Dependencies installed from `uv.lock`.
- SQLite and uploaded files on persistent disk.
- Backup script.

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
- Organizer creates team with generated password.
- Organizer creates organizer user with generated password.

Required tests:

- Unit tests for password helpers.
- Integration tests for login and session behavior.
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
- Add systemd service file template.
- Add Nginx or Caddy reverse proxy example.
- Add backup script or backup instructions.
- Add deployment checklist.
- Add first-admin creation command.

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
- Sprint 3 has started with metric calculation, evaluation persistence, and participant score display complete.
- Next item: enforce one successful submission per team/subtask/period.

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
- Completed: account primitives, password generation/hashing, authentication, signed sessions, login/logout, minimal role dashboards, `/admin/teams`, team creation form, generated password display, subtask assignment UI, team password regeneration, `/admin/users`, organizer creation form, organizer generated password display, organizer password regeneration, `/account/password`, organizer password change flow.
- Remaining account polish can be handled later if needed.

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

- In progress.
- Completed: pure metric calculation helpers for nDCG, macro nDCG by run, MRR, Subtask A evaluation, Subtask B evaluation, unit tests with known expected values, active ground-truth metric loading, accepted submission evaluation, `evaluation_results` persistence, `evaluated` status updates, upload-page score display, and team-dashboard latest score summaries.
- Next: enforce one successful submission per team/subtask/period.

### Sprint 4: Organizer Operations

Deliverables:

- Submissions table.
- Submission detail.
- Private leaderboard.
- CSV export.
- Bundle download.

Demo:

- Organizer reviews all submissions and exports leaderboard.

### Sprint 5: Production Hardening

Deliverables:

- VPS deployment docs.
- Reverse proxy config.
- systemd service.
- Backup plan.
- Final E2E regression suite.

Demo:

- Run app in production-like mode.
- Complete team and organizer workflows.

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
