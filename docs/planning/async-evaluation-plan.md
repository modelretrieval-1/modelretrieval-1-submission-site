# Asynchronous Submission Evaluation Plan

Document role: implemented design record for asynchronous evaluation and its
participant-checkable status. Keep current implementation status in
`../../HANDOFF.md`.

Status: **IMPLEMENTED (2026-07-08).** The async evaluation worker, `queued`/
`processing` statuses, migration `20260708_0003`, the participant status page and
status JSON endpoint, and the `EVALUATION_MODE` setting are all in place. See
`../../HANDOFF.md` for the current implementation checkpoint.

## Context

Before this feature was implemented, evaluation (nDCG / MRR over many queries ×
runs) ran **inside** the upload POST (`app/routes/team.py`, `upload_submission`):
the request validated, stored, evaluated, and only then responded. On a slow
evaluation the participant's browser could hang, and a very long request risked
proxy/gateway timeouts.

Goal (confirmed with the product owner): make **evaluation asynchronous** while
keeping **validation synchronous** so format errors still appear immediately. After a
valid upload the participant is sent to the **participant dashboard**, where the
latest submission state (`queued` → `processing` → `evaluated` /
`evaluation_failed`) is shown. An ownership-checked status page and JSON endpoint
remain available for detailed progress checks.

## Confirmed decisions

- **Async scope: evaluation only.** Validation stays inside the upload request so
  participants still get immediate format/validation errors. Only the slow scoring is
  deferred. The submission slot is reserved at upload time.
- **Worker model: in-process worker thread + SQLite-backed queue.** No new services
  (no Redis/Celery). Fits the single-process uvicorn container (`Dockerfile`, no
  `--workers`). Interrupted jobs are recovered on startup. Processes one at a time.
- **Progress granularity: state-level only** (`queued`/`processing`/`evaluated`/
  `evaluation_failed`) — no "percent of queries evaluated".

This supersedes the shipped "UI-only spinner" upload progress only in emphasis: the
two-phase upload bar stays, while evaluation continues after the redirect to the
dashboard.

## Status model

Submission `status` (free-text TEXT column) gains two in-flight values:

| status | meaning | `is_current` | occupies slot |
|---|---|---|---|
| `rejected` | validation failed (synchronous) | 0 | no |
| `queued` | validation passed, file stored, awaiting evaluation | 1 | yes |
| `processing` | worker is evaluating | 1 | yes |
| `evaluated` | done, metrics available | 1 | yes |
| `evaluation_failed` | evaluation errored | 1 | yes |

`queued`/`processing` must occupy the "one current successful submission per
(team, subtask, period)" slot so a team cannot queue several files at once.

## Changes

### Migration — new Alembic revision under `migrations/versions/`
- Drop & recreate the partial unique index `idx_one_current_successful_submission`
  to include the new states:
  `... WHERE status IN ('accepted','queued','processing','evaluated','evaluation_failed') AND is_current = 1`.
- No new columns; reuse `validation_summary` for human notes (e.g. "Queued for
  evaluation.", "Evaluation failed: …"). Mirror the index change in the `SCHEMA`
  string in `app/db.py` for documentation parity.

### `app/submissions.py`
- Add `'queued','processing'` to `SUCCESSFUL_SUBMISSION_STATUSES` and
  `SUCCESSFUL_SUBMISSION_STATUS_SQL`.
- New helpers (reuse the existing connection/commit patterns):
  - `mark_submission_status(connection, submission_id, status, validation_summary=None)`.
  - `claim_next_queued_submission(connection) -> int | None` — atomic claim:
    `UPDATE submissions SET status='processing' WHERE id=(SELECT id FROM submissions WHERE status='queued' ORDER BY id LIMIT 1) AND status='queued'`, then return the claimed id.
  - `requeue_processing_submissions(connection) -> int` — startup recovery (`processing`→`queued`).
  - `get_team_submission_status(connection, submission_id, internal_team_id)` — ownership-scoped status/summary for the JSON endpoint.
- Reuse as-is: `create_submission_attempt`, `persist_submission_runs`,
  `activate_current_submission`, `get_current_successful_submission_id`,
  `get_unused_resubmission_permission_id`, `get_resubmission_permission`.

### New module `app/processing.py`
- `process_submission(app_settings, submission_id)` — the evaluation job. Opens its
  own connection, loads the submission, sets `processing`, **re-reads the stored file
  and re-parses** with `parse_trec_eval` (the in-memory parse from validation is gone
  by the time the worker runs; re-parsing keeps evaluation reproducible from the
  preserved file), loads the stored `ground_truth_version_id` via
  `get_ground_truth_version`, runs `evaluate_submission` +
  `evaluate_submission_query_metrics`, then `persist_evaluation_results` (which
  already flips status to `evaluated`). Any exception → `mark_evaluation_failed` + a
  summary note.
- `EvaluationWorker(threading.Thread)` — loop guarded by a stop `threading.Event`:
  claim next queued → `process_submission` → repeat; wait ~1s when idle.
- `recover_orphaned_submissions(app_settings)` — `requeue_processing_submissions` at startup.
- `run_pending_evaluations(app_settings)` — drain the queue synchronously (eager mode + tests).
- `start_evaluation_worker(app)` / `stop_evaluation_worker(app)` — manage the thread on `app.state`.

### `app/config.py`
- Add `evaluation_mode: str` (env `EVALUATION_MODE`, default `"worker"`). `"eager"`
  processes inline in the request and skips the worker thread — used by tests for
  determinism.

### `app/main.py` lifespan
- On startup, when `evaluation_mode == "worker"`: after DB init/verify, call
  `recover_orphaned_submissions(settings)` then `start_evaluation_worker(app)`.
- On shutdown: `stop_evaluation_worker(app)`.

### `app/routes/team.py`
- In `upload_submission`: after validation passes and slot/permission checks, create
  the submission as `status="queued"`, store the file, persist runs, and
  `activate_current_submission` (reserve the slot / supersede + consume replacement
  permission at enqueue time). Then: if eager, call `process_submission` inline.
  Finally **redirect (303) to `/team`** (Post/Redirect/Get). The
  validation-failure path re-renders the upload page with errors —
  immediate feedback).
- Move the current inline evaluation block into `process_submission`.
- New routes:
  - `GET /team/submissions/{submission_id}` — ownership-checked status/results page.
  - `GET /team/submissions/{submission_id}/status` — ownership-checked JSON `{status, summary}` for polling.

### Templates
- New `app/templates/team_submission_status.html` — state badge; when `evaluated`,
  render the metric table (reuse `pivot_evaluation_results`); when `queued`/`processing`,
  show a `.spinner-border` and a `{% block scripts %}` that polls the `/status` JSON
  every ~2s and reloads on a terminal state.
- `app/templates/team_submission_upload.html` — relabel the existing processing phase
  to "Validating…"; the XHR follows the 303 and renders the dashboard (the existing
  `document.write` path is unchanged).
- `app/templates/team_dashboard.html` — extend the status-badge mapping to color
  `queued`/`processing`.

## Tests

- Tests set `evaluation_mode="eager"` in `make_settings` so upload→metrics flows stay
  deterministic. Upload now 303-redirects to the dashboard; `TestClient` follows
  redirects by default, so assertions use the dashboard and its metric markers in
  `tests/test_team_submissions.py`. Admin/leaderboard tests
  still see `evaluated` rows because eager completes inline.
- New tests: worker mode leaves status `queued`, then `run_pending_evaluations` yields
  `evaluated` + metrics; `/status` JSON returns the transitions; recovery re-queues a
  `processing` row; status page/endpoint reject another team (ownership).

## Documentation synchronized during implementation

- `HANDOFF.md` — stack (background worker), async flow, product decisions, and
  implemented status.
- `docs/technical/architecture.md` — in-process evaluation worker.
- `docs/technical/submission-spec.md` — async submit behavior + status values; update
  the submission sequence diagram.
- `docs/technical/evaluation-spec.md` — evaluation runs asynchronously via the worker;
  reproducible re-parse from the stored file.
- `docs/ui/ui-flow.md` — submission status page and its states, plus the asynchronous
  worker flow and dashboard redirect.
- `docs/technical/data-model.md` — enumerate the new `status` values.

## Verification

1. `uv run --extra dev pytest` and `uv run --extra dev ruff check .` — all green.
2. Run the app (`uv run uvicorn app.main:app --reload`, worker mode): upload a valid
   file → land on the participant dashboard showing the latest queued/processing
   state; reload later to confirm **Evaluated** with scores. Upload an invalid file →
   **immediate** validation errors on the upload page. The detailed status page may
   also be opened directly to verify its polling behavior.
3. Restart the app while a submission is `processing` → it is re-queued on startup and
   completes. Hit `GET /team/submissions/{id}/status` and observe the JSON state.

## Out of scope / non-goals

- No external queue/broker (Redis/Celery), no multi-process worker pool.
- Validation stays synchronous; no change to metric math, storage layout, or the
  supersession/replacement rules beyond reserving the slot at enqueue time.
- No fine-grained "percent of queries evaluated" progress — state-level only.
