# MVP Audit Logging Plan

Document role: implementation plan for the minimum viable audit trail. Keep
current implementation status in `../../HANDOFF.md`.

Status: **MVP IMPLEMENTED (2026-07-15)**.

## Goal

Record the small set of user and system activities needed to answer:

- Who accessed the system and when?
- Who changed account or submission configuration?
- What happened to a submission from upload through evaluation?
- Who changed or accessed protected ground truth and exported results?

This is an audit trail, not a request/access log. Do not record every page view.

## MVP Scope and Priority

Implement these events first, in this order:

### P0 — Authentication and account security

| Event | Actor | Entity | Required metadata |
|---|---|---|---|
| `login_succeeded` | organizer/team | account | username or team ID, IP/user-agent when available |
| `login_failed` | anonymous/account | account or none | submitted identifier, failure reason, IP/user-agent when available |
| `logout` | organizer/team | account | — |
| `password_changed` | organizer/team | account | actor account ID |
| `password_regenerated` | organizer | team/organizer account | target account ID |

These events provide the minimum security and account-change history. Never log
passwords, password hashes, session cookies, or submitted credentials.

### P0 — Submission lifecycle

| Event | Actor | Entity | Required metadata |
|---|---|---|---|
| `submission_accepted` | team | submission | team, subtask, period, run count, filename, checksum |
| `submission_validation_failed` | team | submission/attempt | subtask, period, error count, summarized failure reasons |
| `submission_evaluated` | system | submission | final status, run count, ground-truth version |
| `submission_evaluation_failed` | system | submission | failure category and safe summary |
| `replacement_permission_granted` | organizer | submission slot/team | team, subtask, period, permission ID |
| `submission_replaced` | team/system | submission | previous submission ID and replacement submission ID |

Do not put full submission contents in `metadata_json`; the submission record and
preserved file are the source of truth.

### P0 — Organizer configuration and protected data

| Event | Actor | Entity | Required metadata |
|---|---|---|---|
| `team_created` | organizer | team | team ID, registered subtasks |
| `organizer_created` | organizer | organizer | username |
| `submission_period_changed` | organizer | period | period, changed fields, old/new values |
| `submission_period_reopened` | organizer | period | period and reopen deadline/state |
| `ground_truth_uploaded` | organizer | ground-truth version | subtask, version ID, checksum |
| `ground_truth_activated` | organizer | ground-truth version | subtask, version ID |
| `ground_truth_downloaded` | organizer | ground-truth version | version ID |
| `leaderboard_exported` | organizer | leaderboard | filters and row count |
| `submission_bundle_downloaded` | organizer | bundle | filters and row count |

## Event Rules

- Write the event in the same database transaction as the state change whenever
  possible. A successful action without its audit event is not acceptable.
- Failed actions that matter for security or troubleshooting (`login_failed` and
  validation failures) should still create an event.
- Use `actor_type` values `organizer`, `team`, `system`, and `anonymous`.
- Use the existing `actor_id`, `entity_type`, `entity_id`, `metadata_json`, and
  `created_at_jst` columns in `audit_events`; no schema change is needed for the
  first slice.
- Metadata must be structured JSON with stable keys, not a formatted sentence.
- Store timestamps consistently in JST as the current schema specifies. If IP or
  user-agent capture is added, treat them as security metadata and protect access.
- Audit events are append-only. Do not update or delete individual events from
  the application.

## Implementation Plan

### Slice 1: Audit helper and tests

Add `record_audit_event(connection, *, actor_type, actor_id, event_type,
entity_type=None, entity_id=None, metadata=None)` in a small domain/helper module.
The helper should serialize JSON deterministically, use the project JST clock,
and accept `None` for anonymous actors.

Add unit tests for insertion, JSON serialization, anonymous actors, and timestamps.

### Slice 2: Authentication and account events

Instrument login success/failure, logout, password changes, and password
regeneration in `app/routes/auth.py` and account-management routes.

Add integration tests asserting event type, actor, target entity, and that secrets
are absent from metadata.

### Slice 3: Submission events

Instrument accepted uploads, validation failures, evaluation completion/failure,
and replacement permission/replacement actions in team/admin/processing flows.

Add tests covering both normal uploads and replacement uploads. Ensure rejected
validation attempts are logged without occupying a successful-submission slot.

### Slice 4: Organizer configuration and exports

Instrument team/organizer creation, period changes/reopens, ground-truth upload and
activation/download, leaderboard export, and bundle download.

Add tests confirming organizer-only actions have organizer actors and that export
filters/row counts are recorded without storing file contents.

### Slice 5: Organizer audit viewer (optional MVP+)

Add a paginated organizer-only `/admin/audit-events` page with filters for event
type, actor, entity, and date. This is useful operationally but is not required
for the first logging slice; database inspection/export is sufficient initially.

## Acceptance Criteria

- Every P0 event in this document is emitted on its success/failure path.
- Audit rows identify the actor, action, target entity, and timestamp.
- Authentication failures can be correlated without storing credentials.
- Submission audit history distinguishes validation failure, accepted, evaluated,
  and evaluation failure.
- Ground-truth access and leaderboard/bundle exports are attributable to an
  organizer.
- Existing tests remain green and new tests cover every P0 event family.
- Ruff passes and no sensitive values appear in audit metadata.

## Non-goals for MVP

- Logging ordinary page views or static asset requests.
- Full security analytics, alerting, or rate-limit dashboards.
- Audit-log editing/deletion UI.
- External log aggregation or a separate event-bus service.
- Capturing complete request bodies or uploaded file contents.

## Documentation Updates After Implementation

- Update `HANDOFF.md` with implementation status and event coverage.
- Update `docs/technical/data-model.md` with the concrete event vocabulary.
- Update `docs/product/requirements.md` under audit and traceability.
- Add audit checks to `docs/deployment/deployment-checklist.md`.
