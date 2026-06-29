# Open Questions

All product policy questions are now resolved. Remaining work is implementation.

Current implementation checkpoint:

- Sprint 0 is complete.
- Sprint 1 account/team setup is complete for v1.
- Sprint 2 validation-core scope is complete.
- Sprint 3 evaluation and participant score display is next/current.

## Authentication and Team Data

Resolved:

- Organizers add teams directly to the system.
- Teams are identified by `team_id`.
- Each team has one shared account.
- Organizers generate the team password.
- No separate manual approval step is required after team creation.

## Submission Packaging

Resolved:

- Participants upload one `.txt` file containing up to 5 runs.
- Subtask A and Subtask B are uploaded separately.
- Compressed files are not accepted.
- Maximum upload size is 10 MB.

## Format Strictness

Resolved:

- Every run must include all test queries.
- Every query must include all candidate models.
- Duplicate ranks within a query are allowed.
- Ties are resolved by line order.
- Missing relevant documents are rejected during validation because all candidate models are required.
- `Rank` is not blindly trusted; the system recomputes order from `Score` and compares it with submitted ranks.

## Deadlines

Resolved:

- Normal submission deadline: August 1, 2026 at 15:00 JST.
- Late submission deadline: October 15, 2026 at 23:59 JST.
- Organizers can reopen a closed submission period.
- Late submissions use the same ground truth and appear in the same private admin leaderboard with a period filter.
- Leaderboard rows should indicate normal or late.
- Participants explicitly choose normal or late during upload; the system should not automatically choose the period.

## Evaluation

Resolved:

- Subtask A official primary metrics are nDCG@3 and nDCG@5.
- Subtask A nDCG is macro-averaged equally across queries.
- Subtask B submissions must include all models; missing correct models are validation errors.
- Tied scores are allowed and resolved by line order.

## Organizer Workflow

Resolved:

- Organizers can download all submissions as a bundle.
- Organizers can export leaderboard results as CSV.
- All 5 runs are official; organizers do not mark one official run per team.
- The system does not send email notifications. Organizers send messages manually.

## Security and Privacy

Resolved:

- Uploaded ground-truth files are stored on the server local filesystem.
- Submission files are not encrypted at rest.
- Submissions and validation failures are retained forever.
- Participant-visible scores are not hidden after correction or re-evaluation.
- Participants cannot re-upload after a successful submission.

## Implementation Details

Resolved:

- Use a light web stack.
- SQLite is preferred for the database.
- VPS deployment is preferred.
- Organizer accounts use password login only.
- Organizers can change their password.
- Organizers can add users with generated passwords.
- Generated team passwords may be visible to organizers.

Recommendation:

- Use FastAPI with Jinja2 templates for the web app.
- Use SQLite for persistent data.
- Use the server local filesystem for submissions, ground truth, exports, and bundles.
- Deploy on a VPS behind a reverse proxy such as Nginx or Caddy.
- Run the application as a managed service, for example with systemd.

Note:

- VPS deployment is a good fit because the system needs local ground-truth files, local submission archives, SQLite, and internal evaluation code.
