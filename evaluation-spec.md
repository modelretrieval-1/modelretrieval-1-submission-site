# Evaluation Specification

## Evaluation Overview

The system evaluates successful submissions internally after validation.

Participants see their own scores immediately. Organizers see all scores and a private leaderboard.

Ground truth is uploaded or configured by organizers and must not be accessible to participants.

Ground-truth files are stored on the server local filesystem.

## Current Implementation Checkpoint

Evaluation is implemented for accepted participant uploads.

Implemented behavior:

- Valid submissions can be accepted and stored.
- Ground-truth versions can be uploaded, validated, and activated.
- Accepted submissions store `RunID` metadata in `runs`.
- `evaluation_results` exists in the database schema.
- Pure metric helpers for nDCG and MRR are implemented and unit tested.
- Accepted submissions are evaluated immediately and metric rows are persisted.
- Participant upload responses and the team dashboard show the team's own metric results.
- One successful submission is enforced per team, subtask, and selected submission period.
- Organizer submission-period controls and participant-selected normal/late uploads are implemented.
- Organizer submission detail views show run-level metric rows for evaluated submissions.
- Organizer private leaderboard view shows evaluated run rows with metrics and period filters.
- Organizer leaderboard rows can be exported as CSV with the current filters.

Next implementation focus: UI modernization using Bootstrap 5 and project-specific CSS.

Follow-on focus: production deployment documentation.

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

### MRR Calculation

For each query, find the rank of the first relevant model.

```text
MRR = mean(1 / rank_q)
```

Every submitted run must include all candidate models for every query. If the correct model is omitted, the submission is rejected during validation rather than scored as `0`.

## Multi-Run Evaluation

Each distinct `RunID` is evaluated independently.

For a successful submission containing multiple run IDs:

- Compute metrics for each run.
- Store all run-level scores.
- Show participants their own run-level results.
- Include all 5 submitted runs as official runs in the private leaderboard.

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

## Re-Evaluation

Organizers should be able to rerun evaluation after replacing or correcting ground truth.

Re-evaluation should:

- Preserve the original submitted file.
- Create new evaluation results tied to the new ground-truth version.
- Keep prior evaluation results for audit unless explicitly superseded.
- Keep participant-visible scores available; the system does not hide scores after correction.
- Not allow participant re-upload after a successful submission.

## Private Leaderboard

Leaderboard visibility is restricted to organizers/admins.

Suggested sorting:

- Subtask A: primary sort by nDCG@5, then nDCG@3, then nDCG@1.
- Subtask B: primary sort by MRR.

Leaderboard rows must indicate whether the submission belongs to the normal or late period. Late submissions use the same ground truth as normal submissions and appear in the same private admin leaderboard with a submission-period filter.
