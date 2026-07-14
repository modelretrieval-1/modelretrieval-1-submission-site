# Evaluation Specification

## Evaluation Overview

The system evaluates successful submissions internally after validation.

Participants see their own current aggregate run-level scores after asynchronous
evaluation completes. Organizers see current and superseded aggregate scores,
organizer-only per-query diagnostics, and a private leaderboard.

Ground truth is uploaded or configured by organizers and must not be accessible to participants.

Ground-truth files are stored on the server local filesystem.

## Implementation Status

Aggregate run-level evaluation is implemented for valid participant uploads. Organizer-only per-query metric persistence and organizer submission-detail display are also implemented. Use `../../HANDOFF.md` for the detailed current implementation checkpoint.

Evaluation runs asynchronously. After synchronous validation, a valid upload is stored as `queued`; an in-process worker thread claims it (`processing`), re-reads and re-parses the preserved file, computes metrics, and persists results (`evaluated`) or records a failure (`evaluation_failed`). Re-parsing from the stored file keeps evaluation reproducible from the exact bytes that were preserved. Interrupted `processing` submissions are re-queued on startup, and a synchronous `eager` mode drains the queue inline for tests and single-shot runs.

## Subtask A: Language Model Retrieval

### Metric

Subtask A uses:

- nDCG@1
- nDCG@3
- nDCG@5

The official primary metrics are nDCG@3 and nDCG@5.

### Inputs

Evaluation requires:

- A valid TREC_EVAL submission.
- A ground-truth relevance table for hidden test tasks.

Expected ground-truth fields:

- `task_id`
- `model_id`
- `relevance_score`

The ground truth may also include supporting fields such as F1, normalized F1, or model rank.

### Relevance

The official task defines relevance from normalized F1:

| Normalized F1 condition | Relevance |
|---|---:|
| `relative_f1 <= 0.90` | 0 |
| `0.90 < relative_f1 <= 0.95` | 1 |
| `0.95 < relative_f1 <= 0.99` | 2 |
| `relative_f1 > 0.99` | 3 |

The evaluation system may either ingest precomputed relevance scores or compute them during ground-truth upload.

### nDCG Calculation

For each query and cutoff `k`, compute:

```text
DCG@k = sum((2^rel_i - 1) / log2(i + 1))
nDCG@k = DCG@k / IDCG@k
```

The final score is the macro-average nDCG across evaluated queries, with each query weighted equally.

The system should retain the underlying per-query nDCG@k values for organizer diagnostics. These per-query values are not participant-visible scores.

## Subtask B: Image Style Transfer Model Retrieval

### Metric

Subtask B uses MRR.

### Inputs

Evaluation requires:

- A valid TREC_EVAL submission.
- A ground-truth mapping from query image ID to the correct model ID.

Expected ground-truth fields:

- `image_id`
- `model_id`

Image IDs are matched between the submission and ground truth with an optional
trailing `.png` suffix ignored on either side, so `test-0001-0011` and
`test-0001-0011.png` refer to the same query image. Numeric model IDs are matched with
left zero-padding ignored on either side, so `0001` and `1`, or `0111` and `111`, refer
to the same model. Both validation and MRR scoring apply these normalizations.

### MRR Calculation

For each query, find the rank of the first relevant model.

```text
MRR = mean(1 / rank_q)
```

Every submitted run must include all candidate models for every query. If the correct model is omitted, the submission is rejected during validation rather than scored as `0`.

The system should retain the underlying per-query reciprocal-rank values for organizer diagnostics. These per-query values are not participant-visible scores.

## Multi-Run Evaluation

Each distinct `RunID` is evaluated independently.

For a successful submission containing multiple run IDs:

- Compute metrics for each run.
- Store all run-level scores.
- Show participants their own run-level results.
- Include all 5 submitted runs from current evaluated submissions as official runs in the private leaderboard.
- Store per-query metric details for each run and query.
- Show per-query metric details only to organizers, such as on the organizer submission detail page.
- Keep participant pages, private leaderboard sorting, and leaderboard CSV export based on aggregate run-level scores unless a later policy changes that behavior.

## Metric Display Shape

Metric persistence remains normalized:

- `evaluation_results` stores one aggregate metric row per submission, run, and metric.
- `evaluation_query_results` stores one per-query metric row per submission, run, query, and metric.

Organizer and participant UI tables should pivot these rows for readability:

- Aggregate score tables should use one row per `RunID`, with metric names as columns.
- Per-query diagnostic tables should use one row per `RunID` and query/topic ID, with metric names as columns.
- Subtask A columns should be `nDCG@1`, `nDCG@3`, and `nDCG@5`.
- Subtask B columns should be `MRR` for aggregate scores and `Reciprocal Rank` for per-query diagnostics.
- Dense UI tables may display values with 4 decimal places; CSV exports may retain 6 decimal places.

This is a presentation concern only. It does not require changing the normalized metric storage tables.

## Ground Truth Versioning

Each ground-truth upload or configuration should create a version.

Store:

- Subtask.
- Version ID.
- Upload/configuration timestamp.
- Organizer/admin user.
- File checksum.
- Active/inactive status.

Each evaluation result must reference the ground-truth version used.
Each per-query evaluation result must also reference the same ground-truth version used for the aggregate score.

## Re-Evaluation

Organizers should be able to rerun evaluation after replacing or correcting ground truth.

Re-evaluation should:

- Preserve the original submitted file.
- Create new evaluation results tied to the new ground-truth version.
- Create new per-query evaluation results tied to the new ground-truth version.
- Keep prior evaluation results for audit unless explicitly superseded.
- Keep participant-visible scores available; the system does not hide scores after correction.
- Allow participant replacement upload only when an organizer grants one-time permission for the same team, subtask, and period.

## Private Leaderboard

Leaderboard visibility is restricted to organizers/admins.

Suggested sorting:

- Subtask A: primary sort by nDCG@5, then nDCG@3, then nDCG@1.
- Subtask B: primary sort by MRR.

Leaderboard rows must indicate whether the submission belongs to the normal or late period. Late submissions use the same ground truth as normal submissions and appear in the same private admin leaderboard with a submission-period filter. Superseded submissions remain visible in organizer submission history, but the private leaderboard and leaderboard CSV use current evaluated submissions only.
