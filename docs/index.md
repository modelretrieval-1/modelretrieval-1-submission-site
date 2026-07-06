# Documentation Index

This directory contains project documentation grouped by topic. Keep `../README.md` and `../HANDOFF.md` at the repository root for quick orientation.

Document role: this file is only the documentation map. Keep current implementation status in `../HANDOFF.md`.

## Product

- [Requirements](product/requirements.md): product requirements and policy decisions.
- [Decisions](product/decisions.md): resolved product and implementation decisions.
- [User Stories](product/user-stories.md): participant and organizer stories.
- [Open Questions](product/open-questions.md): legacy pointer to resolved decisions.

## UI

- [UI Flow](ui/ui-flow.md): screen and workflow definitions.
- [Application UI Redesign](ui/app-ui-redesign.md): pointer to the archived completed app-shell redesign plan.

## Technical

- [Architecture](technical/architecture.md): recommended application and VPS architecture.
- [Data Model](technical/data-model.md): database/entity design.
- [Database Migrations](technical/database-migrations.md): Alembic adoption plan and migration policy.
- [Submission Specification](technical/submission-spec.md): participant upload format and validation rules.
- [Evaluation Specification](technical/evaluation-spec.md): metric definitions and evaluation behavior.
- [Diagrams](technical/diagrams.md): diagram inventory and Mermaid conventions.
- [Refactor Plan](technical/refactor-plan.md): pointer to the archived route/web-layer refactor record.

## Planning

- [Implementation Plan](planning/implementation-plan.md): Scrum plan, epics, testing strategy, and sprint plan.
- [Organizer-Approved Resubmission Plan](planning/resubmission-plan.md): proposed plan for allowing organizer-approved replacement submissions while preserving organizer-only metric history.
- [Documentation Cleanup Plan](planning/documentation-cleanup-plan.md): pointer to the archived completed cleanup plan.

## Archive

- [Archived Refactor Plan](archive/refactor-plan.md): completed route/web-layer refactor plan and implementation record.
- [Archived Implementation History](archive/implementation-history.md): completed story details moved out of the current handoff.
- [Archived Application UI Redesign](archive/app-ui-redesign.md): completed app-shell redesign plan and acceptance criteria.
- [Archived Documentation Cleanup Plan](archive/documentation-cleanup-plan.md): completed documentation cleanup plan and implementation record.
- [Archived Open Questions](archive/open-questions.md): historical pointer for resolved product questions.

## Deployment

- [Deployment Strategy](deployment/deployment-strategy.md): environment model and deployment approach.
- [Deployment Environments](deployment/deployment-environments.md): development, staging, and production configuration.
- [Deployment Runbook](deployment/deployment-runbook.md): setup, deploy, promote, rollback, backup, and restore operations.
- [Deployment Checklist](deployment/deployment-checklist.md): launch and release verification checklist.
- [VPS Setup](deployment/vps-setup.md): Sakura VPS setup procedure.
- [GitHub Secrets](deployment/github-secrets.md): GitHub Actions secret configuration.
- [Restore](deployment/restore.md): restore procedure.

## Runtime Deployment Assets

The repository-level `deployment/` directory is reserved for files used by the deployment itself, such as Nginx examples, environment examples, and shell scripts.
