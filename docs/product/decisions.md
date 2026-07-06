# Product Decisions

## Purpose

This document records resolved product and implementation decisions for the NTCIR-19 ModelRetrieval submission system.

For the latest implementation status, use `../../HANDOFF.md`. This document should stay focused on stable decisions, not sprint progress.

## Authentication And Team Data

- Organizers add teams directly to the system.
- Teams are identified by `team_id`.
- Each team has one shared account.
- Organizers generate the team password.
- No separate manual approval step is required after team creation.

## Submission Packaging

- Participants upload one file containing up to 5 runs.
- Subtask A and Subtask B are uploaded separately.
- Filename extensions are not used to accept or reject submissions; validation is based on file content.
- Maximum upload size is 10 MB.

## Format Strictness

- Every run must include all test queries.
- Every query must include all candidate models.
- Duplicate ranks within a query are allowed.
- Ties are resolved by line order.
- Missing relevant documents are rejected during validation because all candidate models are required.
- `Rank` is not blindly trusted; the system recomputes order from `Score` and compares it with submitted ranks.

## Deadlines

- Normal submission deadline: August 1, 2026 at 15:00 JST.
- Late submission deadline: October 15, 2026 at 23:59 JST.
- Organizers can reopen a closed submission period.
- Late submissions use the same ground truth and appear in the same private admin leaderboard with a period filter.
- Leaderboard rows indicate normal or late period.
- Participants explicitly choose normal or late during upload; the system does not automatically choose the period.

## Evaluation

- Subtask A official primary metrics are nDCG@3 and nDCG@5.
- Subtask A nDCG is macro-averaged equally across queries.
- Subtask B submissions must include all models; missing correct models are validation errors.
- Tied scores are allowed and resolved by line order.
- Participant-visible scores remain run-level aggregate metrics only.
- Per-query metrics are stored and shown only to organizers for diagnostics.
- Private leaderboard sorting and CSV export continue to use aggregate run-level metrics, not per-query rows.

## Organizer Workflow

- Organizers can download all submissions as a bundle.
- Organizers can export leaderboard results as CSV.
- All 5 runs are official; organizers do not mark one official run per team.
- The system does not send email notifications. Organizers send messages manually.

## Security And Privacy

- Uploaded ground-truth files are stored on the server local filesystem.
- Submission files are not encrypted at rest.
- Submissions and validation failures are retained forever.
- Participant-visible scores are not hidden after correction or re-evaluation.
- Participants cannot re-upload after a successful submission for the same team, subtask, and submission period unless an organizer grants one-time replacement-upload permission.
- When replacement-upload permission is granted, previous metrics for that team, subtask, and period are hidden from the participant.
- A successful replacement submission becomes current and supersedes the previous successful submission.
- Organizers can inspect current and superseded metric history.
- Private leaderboard and leaderboard CSV use current evaluated submissions only.

## Implementation Direction

- Use a lightweight server-rendered web stack.
- Use FastAPI with Jinja2 templates for the web app.
- Use Bootstrap 5 and local CSS for the UI.
- Do not introduce React, Vue, or a frontend build pipeline for the current phase.
- Use SQLite for persistent data.
- Use the server local filesystem for submissions, ground truth, exports, and bundles.
- Deploy on Sakura VPS with Docker Compose app containers behind host Nginx.
- Use GitHub Actions and GHCR for automated staging and tagged production deployment.
- Organizer accounts use password login only.
- Organizers can change their password.
- Organizers can add users with generated passwords.
- Generated team and organizer passwords may be visible to organizers when created or regenerated.
