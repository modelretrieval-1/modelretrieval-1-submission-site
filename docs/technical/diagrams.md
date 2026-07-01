# Diagrams

## Purpose

This document defines the diagrams needed to explain, review, and operate the NTCIR-19 ModelRetrieval submission system.

The goal is to keep diagrams practical and version-controlled. Use Mermaid diagrams in Markdown first. Mermaid keeps diagrams easy to review in pull requests, update alongside code, and render on GitHub or compatible documentation tools.

## Existing Documents Reused

The diagrams should support the existing documents rather than replace them.

- `../product/requirements.md`: source for roles, product rules, and security expectations.
- `../product/user-stories.md`: source for use cases and actor goals.
- `architecture.md`: source for system and deployment architecture.
- `../deployment/deployment-strategy.md`: source for environment and release-flow diagrams.
- `../deployment/deployment-environments.md`: source for staging and production configuration boundaries.
- `../deployment/deployment-runbook.md`: source for operational flow diagrams.
- `data-model.md`: source for the ER diagram.
- `submission-spec.md`: source for the submission validation sequence.
- `evaluation-spec.md`: source for evaluation and leaderboard behavior.
- `../ui/ui-flow.md`: source for user-facing workflows.

## Diagram Format

Use Mermaid fenced code blocks inside Markdown files.

Recommended conventions:

- Keep each diagram small enough to understand without zooming.
- Prefer plain operational names over UML-heavy notation.
- Keep labels aligned with code and database terms, such as `submissions`, `runs`, `evaluation_results`, `normal`, and `late`.
- Use separate diagrams for deployment, data, and workflow concerns.
- Store the diagram source in this repository so it changes with the system.

## Required Diagrams

### 1. Deployment Diagram

Priority: highest. Initial version: `../deployment/deployment-strategy.md`.

Purpose:

- Explain how development, staging, and production are separated.
- Show how staging and production share the Sakura VPS without sharing data.

Should show:

- Developer laptop.
- GitHub or source repository.
- Sakura VPS.
- Host Nginx.
- Staging Docker Compose app.
- Production Docker Compose app.
- Staging SQLite and storage directory.
- Production SQLite and storage directory.
- Muumuu Domain DNS.
- Staging and production hostnames.
- Localhost upstream ports, currently `8001` for staging and `8002` for production.

Best home:

- `../deployment/deployment-strategy.md`
- Optionally duplicated or summarized in `architecture.md`

### 2. CI/CD Flow Diagram

Priority: high. Initial version: `../deployment/deployment-strategy.md`.

Purpose:

- Explain the automatic deployment strategy.
- Make the production promotion path explicit.

Should show:

- Commit and push to `main`.
- Test and lint job.
- Docker image build.
- Container registry publish.
- Automatic staging deploy.
- Manual staging verification.
- Version tag creation.
- Production backup.
- Production deploy.
- Smoke check.
- Rollback path to previous image tag.

Best home:

- `../deployment/deployment-strategy.md`
- `../deployment/deployment-runbook.md`

### 3. System Context Diagram

Priority: high.

Purpose:

- Explain the system boundary to non-developers and operators.

Should show:

- Participant teams.
- Organizers.
- Browser.
- FastAPI/Jinja2 application.
- SQLite database.
- Local file storage.
- Nginx.
- Muumuu Domain DNS.
- Sakura VPS.

Best home:

- `architecture.md`

### 4. Use Case Diagram

Priority: medium-high.

Purpose:

- Explain product scope by actor.

Actors:

- Participant Team.
- Organizer/Admin.

Participant use cases:

- Log in.
- View dashboard.
- Upload submission.
- Choose normal or late period.
- View validation errors.
- View own scores.

Organizer use cases:

- Log in.
- Manage teams.
- Manage organizer users.
- Change password.
- Configure submission periods.
- Upload ground truth.
- Activate ground truth.
- Review submissions.
- View private leaderboard.
- Export leaderboard CSV.
- Download submission bundle.

Best home:

- `../product/user-stories.md`
- `../ui/ui-flow.md`

### 5. Submission Sequence Diagram

Priority: high. Initial version: `submission-spec.md`.

Purpose:

- Explain the most important participant workflow and validation/evaluation path.

Should show:

- Team browser.
- FastAPI route.
- Session/auth check.
- Team subtask eligibility check.
- Submission period lookup.
- File type and size validation.
- TREC_EVAL parser.
- Active ground-truth requirement lookup.
- Query/model completeness validation.
- Duplicate and rank/score-order validation.
- Rejected submission persistence.
- Accepted submission and run persistence.
- Evaluation.
- Metric result persistence.
- Participant score response.

Important branches:

- Invalid file creates a `rejected` submission and `validation_errors`.
- Valid file becomes `accepted` transiently, then `evaluated` or `evaluation_failed`.
- Existing successful submission blocks a second successful upload for the same team/subtask/period.

Best home:

- `submission-spec.md`
- `evaluation-spec.md`

### 6. Ground Truth Activation Sequence Diagram

Priority: medium.

Purpose:

- Explain how organizers prepare evaluation data.

Should show:

- Organizer browser.
- Ground-truth upload route.
- CSV validation.
- File storage.
- SHA-256 calculation.
- `ground_truth_versions` row creation.
- Activation request.
- Deactivation of previous active version for the same subtask.
- Future submissions using the active version.

Best home:

- `evaluation-spec.md`
- `../ui/ui-flow.md`

### 7. Data Model / ER Diagram

Priority: high. Initial version: `data-model.md`.

Purpose:

- Explain the SQLite schema and core relationships.

Should include:

- `organizers`
- `teams`
- `team_subtasks`
- `submission_periods`
- `ground_truth_versions`
- `submissions`
- `runs`
- `validation_errors`
- `evaluation_results`
- `audit_events`

Important relationships:

- Teams have many registered subtasks.
- Teams have many submissions.
- Submissions belong to one selected submission period.
- Successful submissions have runs.
- Rejected submissions have validation errors.
- Evaluated submissions have evaluation results.
- Evaluation results reference the ground-truth version used.

Best home:

- `data-model.md`

### 8. Submission Status State Diagram

Priority: medium.

Purpose:

- Explain submission lifecycle and persistence states.

States:

- Upload attempt.
- `rejected`.
- `accepted`.
- `evaluated`.
- `evaluation_failed`.

Important notes:

- `accepted` is mostly transient before evaluation persistence.
- `rejected` attempts are retained forever and do not count as successful submissions.
- `accepted`, `evaluated`, and `evaluation_failed` count as successful for the one-successful-submission rule.

Best home:

- `data-model.md`
- `submission-spec.md`

## Recommended Drawing Order

1. Deployment Diagram.
2. CI/CD Flow Diagram.
3. Submission Sequence Diagram.
4. Data Model / ER Diagram.
5. Use Case Diagram.
6. System Context Diagram.
7. Ground Truth Activation Sequence Diagram.
8. Submission Status State Diagram.

This order supports the current Sprint 6 deployment work first, then fills in product and implementation diagrams.

## Mermaid Diagram Types

Recommended Mermaid types:

- Deployment and system context: `flowchart`.
- CI/CD flow: `flowchart`.
- Use cases: `flowchart` with actor and use-case nodes.
- Submission workflow: `sequenceDiagram`.
- Ground-truth workflow: `sequenceDiagram`.
- Data model: `erDiagram`.
- Submission status: `stateDiagram-v2`.

## Acceptance Criteria

A diagram is ready when:

- It is stored in Markdown as Mermaid source.
- It uses current repo terminology.
- It is linked from the relevant source document.
- It is small enough to review in one screen or section.
- It avoids secrets, real passwords, or private infrastructure details.
- It distinguishes staging and production data stores where relevant.
- It reflects the current implementation or clearly labels future/planned behavior.
