# Documentation Cleanup Plan

## Purpose

This document plans a document-driven cleanup of the NTCIR-19 ModelRetrieval submission-system documentation before any implementation changes are made.

The goal is to reduce duplicated status text, clarify which document owns which kind of information, and make future maintenance safer during staging and production hardening.

This plan is intentionally conservative. It does not delete or rewrite existing documents by itself.

## Implementation Status

The initial cleanup has been implemented:

- Added document role notes to the main entry points.
- Added `../product/decisions.md`.
- Replaced `../product/open-questions.md` with a compatibility pointer.
- Archived the completed route/web-layer refactor plan under `../archive/refactor-plan.md`.
- Replaced `../technical/refactor-plan.md` with a pointer to the archived record.
- Trimmed repeated current-status sections from stable product, UI, and technical docs.
- Kept `../../HANDOFF.md` as the detailed current-status owner.

## Current Problem

The documentation is thorough, but several files repeat the same implementation status and sprint-progress summaries.

Repeated status appears in:

- `HANDOFF.md`
- `README.md`
- `docs/product/requirements.md`
- `docs/product/user-stories.md`
- `docs/product/open-questions.md`
- `docs/planning/implementation-plan.md`
- `docs/ui/ui-flow.md`
- `docs/ui/app-ui-redesign.md`
- `docs/technical/submission-spec.md`
- `docs/technical/evaluation-spec.md`
- `docs/technical/architecture.md`

This creates two risks:

- Future updates may change one document but leave stale status in another.
- New contributors may not know which document is the source of truth.

## Cleanup Principles

- Keep documentation useful for real project work, not merely tidy.
- Preserve important project history unless it is actively confusing.
- Prefer trimming and linking over large rewrites.
- Keep one clear owner for each category of information.
- Avoid deleting operational deployment docs during production hardening.
- Do not change product requirements, routes, permissions, deployment behavior, or implementation from this cleanup.

## Proposed Source Of Truth Rules

| Information type | Primary owner | Notes |
|---|---|---|
| Current continuation state | `HANDOFF.md` | Most detailed current-status document for future Codex/developer sessions. |
| Project overview and quick start | `README.md` | Short status, setup commands, test commands, and links. |
| Documentation map | `docs/index.md` | Table of contents only. Avoid progress details. |
| Product rules and decisions | `docs/product/requirements.md` | Stable product behavior and policy decisions. |
| Historical or resolved questions | `docs/product/decisions.md` or archived `open-questions.md` | Prefer stable decisions over an "open questions" file when questions are resolved. |
| User-facing workflows | `docs/ui/ui-flow.md` | Screen inventory, states, and flows. |
| Visual/application-shell direction | `docs/ui/app-ui-redesign.md` | UI layout and interaction direction. |
| Sprint plan and history | `docs/planning/implementation-plan.md` | Sprint structure and milestone history, not detailed latest status. |
| Data model | `docs/technical/data-model.md` | Schema and persistence rules. |
| Submission contract | `docs/technical/submission-spec.md` | Upload format, validation rules, and submission workflow. |
| Evaluation contract | `docs/technical/evaluation-spec.md` | Metrics, ground-truth usage, leaderboard behavior. |
| Deployment operations | `docs/deployment/deployment-runbook.md` | Main operational guide. |
| Deployment references | Other `docs/deployment/*.md` files | Keep focused references for environments, VPS setup, secrets, restore, and checklist. |

## Proposed Changes

### Phase 1: Mark Document Roles

Add short "Document Role" notes to the most important docs so readers know where to update information.

Recommended targets:

- `HANDOFF.md`
- `README.md`
- `docs/index.md`
- `docs/product/requirements.md`
- `docs/planning/implementation-plan.md`
- `docs/deployment/deployment-runbook.md`

Acceptance criteria:

- Each role note is short.
- No product behavior changes.
- No large rewrites.

### Phase 2: Reduce Repeated Current Status

Trim duplicated "Current Implementation Checkpoint" sections from stable product, UI, and technical docs.

Recommended approach:

- Keep one short checkpoint sentence when it helps orient the reader.
- Link to `HANDOFF.md` for latest implementation state.
- Keep stable rules in place.

Candidate docs:

- `docs/product/requirements.md`
- `docs/product/user-stories.md`
- `docs/ui/ui-flow.md`
- `docs/ui/app-ui-redesign.md`
- `docs/technical/submission-spec.md`
- `docs/technical/evaluation-spec.md`
- `docs/technical/architecture.md`

Acceptance criteria:

- Requirements and specifications remain complete.
- Repeated sprint status is removed or shortened.
- `HANDOFF.md` remains the detailed current-status source.

### Phase 3: Convert Resolved Questions Into Decisions

`docs/product/open-questions.md` currently says all product policy questions are resolved.

Recommended action:

- Create `docs/product/decisions.md` from the resolved decisions.
- Update `docs/index.md` to point to `decisions.md`.
- Either archive `open-questions.md` under `docs/archive/` or replace it with a short pointer to `decisions.md`.

Acceptance criteria:

- No resolved decision is lost.
- The docs no longer present resolved policy as "open questions."
- Links are updated.

### Phase 4: Archive Completed Implementation Plans

Some documents are now more historical than operational.

Candidates:

- `docs/technical/refactor-plan.md`

Recommended action:

- Move completed historical plans to `docs/archive/` only after confirming they are not needed for active work.
- Keep links from `docs/index.md` if the archived docs remain useful.

Acceptance criteria:

- Active docs do not send readers to completed plans as if they are current work.
- Historical implementation context remains available.

### Phase 5: Normalize Deployment Docs

Deployment docs are many, but the split is mostly justified because production operations are sensitive.

Recommended action:

- Keep the current deployment docs.
- Make `docs/deployment/deployment-runbook.md` the clear start-here document.
- Ensure other deployment docs are focused references:
  - `deployment-strategy.md`: architecture and release model.
  - `deployment-environments.md`: environment boundaries and variables.
  - `vps-setup.md`: one-time host setup.
  - `github-secrets.md`: CI/CD secret setup.
  - `restore.md`: restore procedure.
  - `deployment-checklist.md`: launch/release checklist.

Acceptance criteria:

- No deployment instructions are lost.
- The runbook links to focused references instead of duplicating too much detail.

## Proposed Target Layout

```text
README.md
HANDOFF.md
docs/
  index.md
  archive/
    refactor-plan.md
  product/
    requirements.md
    decisions.md
    open-questions.md              # compatibility pointer to decisions.md
    user-stories.md                # optional active planning reference
  ui/
    ui-flow.md
    app-ui-redesign.md
  technical/
    architecture.md
    data-model.md
    submission-spec.md
    evaluation-spec.md
    diagrams.md
  planning/
    implementation-plan.md
    documentation-cleanup-plan.md
  deployment/
    deployment-runbook.md
    deployment-strategy.md
    deployment-environments.md
    deployment-checklist.md
    vps-setup.md
    github-secrets.md
    restore.md
```

## Recommended Order Of Work

1. Review and approve this cleanup plan.
2. Add document role notes.
3. Create `docs/product/decisions.md`.
4. Update `docs/index.md`.
5. Trim repeated current-status sections from stable docs.
6. Archive or replace `open-questions.md`.
7. Archive completed `refactor-plan.md` if desired.
8. Do a final link and wording pass.

## Non-Goals

- Do not rewrite product requirements.
- Do not change application behavior.
- Do not change deployment behavior.
- Do not remove deployment safety instructions.
- Do not delete historical context without an archive or pointer.

## Open Cleanup Decisions

- `docs/product/user-stories.md` remains active for now because it still provides acceptance-criteria framing.
- `docs/technical/refactor-plan.md` now points to the archived historical record.
- `docs/product/open-questions.md` remains in place as a compatibility pointer to `decisions.md`.
- `docs/planning/implementation-plan.md` still keeps sprint history, while `../../HANDOFF.md` owns detailed current implementation status.
