# UI/UX Improvement Plan

Document role: prioritized implementation plan for improving the participant
and organizer experience while preserving the current FastAPI/Jinja2/
Bootstrap architecture.

Status: **P2 IMPLEMENTED**. The current application shell and responsive UI remain
the baseline. P1 organizer attention, replacement-workflow, and P2 review-table
improvements are implemented; this plan continues to track later refinements.

Source documents:

- `../ui/ui-flow.md` — active screen and workflow specification.
- `../../HANDOFF.md` — current implementation status.
- `../product/requirements.md` — stable product and policy requirements.

## Priority Summary

| Priority | Improvement | Primary users | Reason |
|---|---|---|---|
| P0 | Submission lifecycle and status clarity | Participants | Reduces uncertainty after upload and distinguishes validation from evaluation. |
| P0 | Upload guidance and validation-error redesign | Participants | Prevents avoidable failures and makes rejected files actionable. |
| P1 | Organizer attention dashboard | Organizers | Surfaces operational problems without requiring table-by-table inspection. |
| P1 | Replacement-upload warnings and history | Participants and organizers | Makes the highest-risk workflow understandable and auditable. |
| P1 | Accessibility and responsive interaction refinements | All users | Improves reliability on mobile and for keyboard/screen-reader users. |
| P2 | Leaderboard and review-table improvements | Organizers | Makes comparison, filtering, and export workflows faster. |

## Prioritized Work Items

### P0-1: Make submission lifecycle explicit

Goal: help participants understand exactly what happened after a valid upload.

Scope:

- Show a consistent lifecycle: `Uploaded → Validating → Queued → Evaluating → Evaluated`.
- Display the current state, submission timestamp, and latest status message.
- Distinguish validation failure, evaluation failure, and successful evaluation.
- Keep polling feedback visible while a submission is queued or processing.
- Provide clear `View details` and `Back to dashboard` actions.
- Add an accessible live region for status changes.

Acceptance criteria:

- A participant can identify the current state without reading implementation terms.
- Validation failure is visibly different from evaluation failure.
- Queued and processing states explain that no further participant action is required.
- Terminal states do not continue polling.
- Existing ownership checks and status behavior remain unchanged.

Likely files: `app/templates/team_submission_status.html`,
`app/templates/team_dashboard.html`, `app/static/app.css`, and related UI tests.

### P0-2: Improve upload guidance and validation errors

Goal: reduce preventable upload failures and make rejected submissions fixable.

Scope:

- Add a compact checklist beside or above the upload form:
  subtask, period, maximum five runs, TREC_EVAL format, and
  completeness requirements.
- Show selected subtask and period context prominently.
- Group validation messages into structure, field errors, completeness,
  ordering, and run-limit categories.
- Preserve line numbers and field names where available.
- Add a concise error summary at the top of the form.
- Keep a no-JavaScript path fully usable.

Acceptance criteria:

- A participant can understand the basic file requirements before uploading.
- Multiple errors are grouped and scannable rather than presented as one long list.
- Error messages remain actionable and retain precise line/field information.
- Invalid uploads never appear as queued or evaluated submissions.

Likely files: `app/templates/team_submission_upload.html`, validation error
context in `app/routes/team.py`, shared CSS, and submission UI tests.

### P1-1: Add an organizer attention dashboard

Goal: answer “Does anything need my attention?” immediately after organizer login.

Scope:

- Add summary cards for queued evaluations, evaluation failures, recent
  submissions, open/closed periods, and active ground-truth version.
- Add a recent validation-failure panel with links to relevant submission details.
- Add an incomplete-submission or pending-action panel where the existing data
  model can support it without introducing speculative policy.
- Make each summary actionable and link to a filtered page.

Acceptance criteria:

- The dashboard shows current operational state, not hardcoded examples.
- Every warning/metric has a useful destination page.
- Empty states explicitly say when no action is required.
- Dashboard queries do not expose participant-only or hidden ground-truth data.

Likely files: `app/routes/admin.py`, `app/templates/admin_dashboard.html`,
domain query helpers, and organizer integration tests.

Implementation status: **Complete**. The dashboard now exposes live queued,
processing, evaluation-failure, and validation-failure counts, each linking to
the corresponding filtered submission view, alongside the existing recent
failure panel.

### P1-2: Clarify replacement uploads and submission history

Goal: prevent accidental misunderstanding of the one-time replacement policy.

Scope:

- Add a prominent warning before a replacement upload.
- Explain that participant-visible previous metrics are hidden while replacement
  permission is pending and after a replacement succeeds.
- Show current, superseded, rejected, queued, and failed states consistently.
- Add an organizer-facing replacement timeline linking old and new submissions.
- Add confirmation for granting permission and for the replacement upload action.

Acceptance criteria:

- Participants understand that replacement changes which result is visible to them.
- Failed replacement validation does not appear to consume permission.
- Organizers can distinguish current and superseded submissions at a glance.
- Existing audit/history and leaderboard rules remain intact.

Likely files: upload/dashboard/status templates, organizer submission detail
templates, and resubmission-related tests.

Implementation status: **Complete**. Participant and organizer pages now explain
the one-time replacement policy, hide the previous participant-visible result
while permission is pending, provide a confirmation before granting permission,
and expose current/superseded history and permission usage to organizers.

### P1-3: Accessibility and responsive interaction refinements

Goal: make core workflows reliable for keyboard users, screen readers, and small screens.

Scope:

- Add `aria-live` status announcements for upload and evaluation changes.
- Verify visible labels, focus states, button names, and keyboard navigation.
- Add text or icons alongside color-based statuses.
- Keep primary upload/status actions full-width or easy to reach on mobile.
- Ensure tables provide a useful compact/mobile representation.
- Ensure the mobile navigation closes after route selection.

Acceptance criteria:

- Core participant and organizer flows are usable without a mouse.
- Status meaning does not depend on color alone.
- No critical action is hidden by horizontal overflow on mobile.
- Automated responsive/accessibility checks cover the new behavior.

Likely files: shared templates, `app/static/app.css`, minimal JavaScript,
and browser/E2E tests.

### P2-1: Improve leaderboard and organizer review tables

Goal: make high-volume organizer inspection faster.

Scope:

- Freeze identifying columns on wide tables where practical.
- Add rank numbers and visually emphasize official metric columns.
- Preserve active filters in links and CSV export.
- Add explicit current/superseded state filters.
- Add a visible “last updated” timestamp.
- Ensure metric tables use the planned pivoted layout with metric names as columns.

Acceptance criteria:

- Organizers can filter, compare, and export the same result set.
- Current versus historical submissions are visually unambiguous.
- Tables remain usable at the supported desktop and mobile widths.
- Existing privacy rules for leaderboards and per-query metrics remain unchanged.

Likely files: organizer list/detail/leaderboard templates, route query/filter
helpers, CSS, and organizer integration tests.

Implementation status: **Complete**. Organizer review tables now support current
and superseded state filters, preserve active filters in bundle links, keep
identifying columns visible during horizontal scrolling, emphasize primary
metrics, show leaderboard ranks, and display the leaderboard refresh timestamp.
The leaderboard also supports team filtering and client-side sorting by every
displayed column. Participant metric tables use a consistent background across
all metric columns, and the evaluated lifecycle is visually muted as a terminal
state.

## Recommended Delivery Sequence

1. P0-1: submission lifecycle and status clarity.
2. P0-2: upload guidance and validation-error redesign.
3. P1-1: organizer attention dashboard.
4. P1-2: replacement-upload warnings and history.
5. P1-3: accessibility and responsive refinements.
6. P2-1: leaderboard and review-table improvements.

The first two items should be delivered together because they cover the full
participant upload journey. P1-1 and P1-2 can then use the same status language
and visual conventions. P1-3 should be applied incrementally during each slice,
with a final cross-screen audit afterward.

## Testing and Quality Gates

Each work item is complete only when:

- Template and route behavior is covered by existing or new tests.
- Participant ownership and organizer access-control tests remain green.
- Mobile layout checks cover the affected screens.
- Keyboard and semantic-label checks cover new controls.
- `uv run --extra dev pytest` passes.
- `uv run --extra dev ruff check .` passes.
- Visual browser smoke verification is performed when browser automation is available.
- `docs/ui/ui-flow.md` and `HANDOFF.md` are updated when behavior or status wording changes.

## Out of Scope

- React, Vue, or a separate frontend build pipeline.
- A visual rebrand or marketing-style public site.
- Changes to submission policy, metric calculations, permissions, or retention.
- New external services solely for UI behavior.
