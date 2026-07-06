# Organizer-Approved Resubmission Plan

Document role: this is a proposed feature plan. It is not implemented yet and should not be treated as a resolved product decision until the open questions are answered.

## Feature Goal

Allow an organizer to let a team upload a new successful submission for a team, subtask, and submission period after that team already has a successful upload.

The requested policy is:

- Organizers can grant a team permission to upload again.
- The team can upload again for the same subtask and period.
- The team cannot see previous metrics after a replacement upload is allowed.
- Organizers can see the full metric history.

## Current Behavior

The current system intentionally enforces one successful submission per team, subtask, and submission period.

Current enforcement points:

- Participant upload checks for an existing successful submission before accepting a new valid file.
- The database has a partial unique index that prevents multiple successful submissions for the same team, subtask, and period.
- Participant dashboard shows latest submission summaries and metrics.
- Organizer submission pages show all submission attempts.
- Organizer leaderboard shows evaluated run-level metrics.

Successful statuses currently include:

- `accepted`
- `evaluated`
- `evaluation_failed`

Rejected validation attempts do not count as successful submissions and are already retained as history.

## Product Interpretation

The safest interpretation is to introduce the idea of a current official submission.

For each team, subtask, and period:

- At most one successful submission should be current.
- Older successful submissions should remain stored as history.
- Participant pages should show only the current participant-visible state.
- Organizer pages should expose both current and historical submissions.
- Leaderboard and CSV export should default to current submissions only unless the organizer explicitly asks for history.

This avoids deleting data and keeps auditability intact.

## Recommended Data Model

Add current/history fields to `submissions`:

- `is_current`: boolean-like integer, default `0`.
- `superseded_at_jst`: nullable timestamp.
- `superseded_by_submission_id`: nullable foreign key to `submissions.id`.
- `superseded_reason`: nullable text.
- `superseded_by_organizer_id`: nullable foreign key to `organizers.id`.

Change the successful-submission uniqueness rule:

- Current rule: one successful submission ever per team, subtask, and period.
- Proposed rule: one current successful submission per team, subtask, and period.

Replace the current partial unique index with a new partial unique index over:

- `team_id`
- `subtask`
- `submission_period_id`

where:

- `status IN ('accepted', 'evaluated', 'evaluation_failed')`
- `is_current = 1`

Add a separate table for organizer-granted resubmission permission:

```text
resubmission_permissions
  id
  team_id
  subtask
  submission_period_id
  granted_by_organizer_id
  granted_at_jst
  reason
  used_by_submission_id
  used_at_jst
  is_used
```

This permission table makes organizer intent explicit and auditable. It also prevents accidental unlimited re-uploads.

## Recommended Workflow

### Organizer Grants Permission

1. Organizer opens an evaluated submission detail page or a team/subtask/period history page.
2. Organizer clicks an action such as `Allow replacement upload`.
3. Organizer enters an optional reason.
4. System records a one-time resubmission permission.
5. Participant upload becomes available for that team, subtask, and period.

### Participant Uploads Replacement

1. Team sees the slot as available because an organizer granted permission.
2. Team uploads a new file using the same validation and evaluation flow.
3. If validation fails:
   - The failed attempt is stored as `rejected`.
   - The permission remains unused.
   - The previous successful submission remains current.
4. If validation and evaluation succeed:
   - The new submission becomes current.
   - The previous current successful submission is marked superseded.
   - The permission is marked used.
   - Participant sees only the new current metrics.
   - Organizer can still inspect old and new metrics.
5. If validation succeeds but evaluation fails:
   - Policy decision needed. See open questions.

## Participant Visibility Rules

Recommended participant rules:

- Before organizer grants permission, the participant sees current successful metrics as today.
- After organizer grants permission but before replacement succeeds, hide previous metrics for that team/subtask/period if the requested policy means previous metrics must no longer be visible once re-upload is allowed.
- After replacement succeeds, show only the current replacement metrics.
- Never show superseded metrics on participant pages.

Alternative rule:

- Keep old metrics visible until a replacement succeeds, then hide superseded metrics.

The first rule matches the user request more strictly. The second rule is less surprising for participants because their existing accepted result remains visible until it is actually replaced.

## Organizer Visibility Rules

Organizer pages should distinguish:

- Current successful submission.
- Superseded successful submission.
- Rejected validation attempt.
- Evaluation failed attempt.
- Pending unused resubmission permission.

Recommended organizer views:

- Submission list: add current/superseded indicator and filter.
- Submission detail: show replacement history and links between old and new submissions.
- Team detail or team row action: show resubmission permission status.
- Leaderboard: default current only.
- Leaderboard CSV: default current only, with possible `include_history=1` later.

## Leaderboard Policy

Recommended default:

- Private leaderboard includes only current evaluated submissions.
- Superseded submissions are excluded from ranking by default.
- Organizer can inspect superseded metrics from submission detail/history pages.

Possible future extension:

- Add an organizer-only leaderboard filter: `current only` or `include history`.
- Add CSV column `submission_state` with values such as `current` and `superseded`.

## Submission Bundle Policy

Recommended default:

- Submission bundle continues to include all stored successful and failed attempts, because it is an archive/export tool.
- Add metadata in filenames or a manifest later to identify current vs superseded submissions.

Alternative:

- Provide two bundle modes: current-only and all-history.

## Migration Plan

Implement as a new Alembic revision.

Recommended migration steps:

1. Add new columns to `submissions`.
2. Backfill `is_current = 1` for existing successful submissions.
3. Backfill `is_current = 0` for rejected submissions.
4. Create `resubmission_permissions`.
5. Drop the existing `idx_one_successful_submission` partial unique index.
6. Create a new partial unique index for current successful submissions.

Because production data may exist by the time this is implemented, test the migration against a copy of staging or production data before deployment.

## Application Change Plan

### Domain Logic

Add helper behavior for:

- Finding the current successful submission for a team/subtask/period.
- Checking whether an unused resubmission permission exists.
- Granting resubmission permission.
- Marking the old current submission superseded after replacement succeeds.
- Marking a permission used by the replacement submission.
- Listing submission history for organizers.

### Participant Upload

Change the upload guard:

- If no current successful submission exists, allow upload as today.
- If a current successful submission exists and no unused permission exists, reject as today.
- If a current successful submission exists and an unused permission exists, allow validation/evaluation.
- If replacement succeeds, supersede old current submission.

### Participant Dashboard

Change participant summaries to:

- Load current participant-visible submissions only.
- Hide metrics from superseded submissions.
- Show an upload action when a resubmission permission exists and the period is open or reopened.

### Organizer Admin

Add organizer controls to:

- Grant resubmission permission.
- View permission status.
- View current and superseded submission history.

Recommended initial location:

- Add the grant action on the organizer submission detail page.

Reason:

- The organizer is already looking at the specific team/subtask/period/submission that should be replaced.

### Evaluation And Leaderboard

Change leaderboard queries to:

- Include only `submissions.status = 'evaluated'`.
- Include only `submissions.is_current = 1`.

Organizer history pages can continue to query all evaluated submissions.

## Testing Plan

Add or update tests for:

- Existing duplicate successful upload is still blocked without organizer permission.
- Organizer can grant one-time resubmission permission.
- Team can upload again after permission.
- Failed replacement validation does not consume permission.
- Successful replacement consumes permission.
- Successful replacement marks old submission superseded.
- Participant dashboard hides superseded metrics.
- Participant dashboard shows current replacement metrics only.
- Organizer submission detail/history shows old and new metrics.
- Leaderboard excludes superseded submissions.
- Leaderboard CSV excludes superseded submissions.
- Database unique index allows multiple historical successes but only one current success.
- Team users cannot grant or inspect resubmission permissions.

## Documentation Updates Needed If Implemented

Update:

- `docs/product/requirements.md`
- `docs/product/decisions.md`
- `docs/product/user-stories.md`
- `docs/ui/ui-flow.md`
- `docs/technical/data-model.md`
- `docs/technical/submission-spec.md`
- `docs/technical/evaluation-spec.md`
- `docs/technical/database-migrations.md`
- `HANDOFF.md`

The stable product docs should be updated only after the policy questions below are resolved.

## Open Questions

1. Does the participant lose access to previous metrics immediately when permission is granted, or only after the replacement upload succeeds?
2. Is organizer permission one-time, or can an organizer allow unlimited replacement uploads until revoked?
3. Should a replacement upload be allowed after the selected submission period is closed, or must the period also be open/reopened?
4. If replacement validation succeeds but evaluation fails, should the old submission remain current?
5. Should leaderboard and CSV always use current submissions only, or should organizers be able to include superseded history?
6. Should submission bundles include all history by default, or current submissions only?
7. Should participants see that a previous submission was superseded, without seeing the old metrics?
8. Should organizer grant actions require a reason before saving?

## Recommended First Slice

Implement the smallest safe version after policy approval:

1. Add current/superseded schema fields and resubmission permission table.
2. Add organizer grant action on submission detail.
3. Allow one replacement upload when permission exists.
4. Hide superseded metrics from participants.
5. Keep organizer detail/history visibility.
6. Filter leaderboard and CSV to current submissions only.
7. Add focused tests for the replacement workflow.

This slice keeps the behavior auditable and avoids broad UI redesign work.
