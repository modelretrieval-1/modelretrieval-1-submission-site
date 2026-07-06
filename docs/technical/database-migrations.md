# Database Migration Plan

## Purpose

This document defines the plan for adopting Alembic as the database migration tool for the NTCIR-19 ModelRetrieval submission system.

The goal is to make schema changes explicit, reviewable, repeatable, and safe for staging and production data.

## Decision

Use Alembic for versioned SQLite schema migrations.

Reasons:

- The project is a Python/FastAPI application, and Alembic is the standard Python migration tool.
- Staging and production will contain persistent SQLite data that must survive application upgrades.
- Production deployment already uses immutable images and pre-deploy backups, so explicit migrations fit the release flow.
- Future maintainers are more likely to understand Alembic than a project-specific migration format.

Atlas is not selected for the current phase because it would add a separate schema-management ecosystem to an otherwise small Python stack.

## Current State

The app currently initializes the SQLite schema from `app/db.py` at application startup:

- `initialize_database()` runs `CREATE TABLE IF NOT EXISTS` statements.
- Default submission periods are inserted with `INSERT OR IGNORE`.
- Tests and local development rely on this bootstrap behavior.
- Staging and production currently start the app with `docker compose up -d`, which causes startup initialization to run inside the app process.

This is simple, but it is not enough once existing databases need ordered schema changes.

## Target State

Alembic owns schema versioning.

Target behavior:

- Schema changes are represented as Alembic revision files under `migrations/versions/`.
- The current schema becomes the baseline Alembic revision.
- Staging and production deployments run `alembic upgrade head` before the app serves traffic.
- The app no longer relies on startup-time `CREATE TABLE IF NOT EXISTS` for deployed environments.
- Local tests and development remain easy to bootstrap.
- Default reference data, such as normal and late submission periods, remains deterministic and idempotent.

## Scope

Initial adoption should include:

- Add Alembic as an application dependency.
- Add `alembic.ini`.
- Add a `migrations/` directory with Alembic environment configuration.
- Add an initial revision that creates the current schema.
- Add the partial unique index for one successful submission per team, subtask, and period.
- Add idempotent insertion of default submission periods.
- Add a small CLI or documented command for applying migrations.
- Update tests to create databases through migrations or through a migration-aware helper.
- Update Docker image contents so migration files are included.
- Update deployment docs and CI/CD flow to run migrations before app startup.

Out of scope for the initial adoption:

- Replacing raw `sqlite3` data access with SQLAlchemy ORM.
- Adding async database access.
- Adding online schema-diff automation.
- Adding a web UI for migration status.

## Alembic Mode

Use Alembic with explicit Python revision scripts and SQLAlchemy Core operations.

The application can continue using `sqlite3` for runtime queries. Alembic requires SQLAlchemy for migrations, but this does not require adopting the ORM for app code.

Recommended dependency shape:

```toml
dependencies = [
  "alembic>=1.13.0",
  ...
]
```

Alembic should read the SQLite path from the same application configuration used by the app, especially `DATABASE_PATH`.

## Baseline Strategy

Because production is not yet launched with user data, the preferred path is:

1. Create an initial Alembic revision containing the current schema.
2. For new databases, run `alembic upgrade head`.
3. For any existing local or staging database created by `initialize_database()`, either recreate it if disposable or stamp it to the baseline revision after confirming the schema matches.

If non-disposable data exists before the migration plan is implemented:

1. Back up the database.
2. Compare the live schema with the initial revision.
3. If equivalent, run `alembic stamp head`.
4. If not equivalent, create a transitional revision or manual repair plan before stamping.

## Application Startup Policy

Production and staging should not perform schema migrations implicitly inside web app startup.

Recommended policy:

- `initialize_database()` may remain for tests during the transition, but should not be the production schema authority after Alembic adoption.
- App startup may verify that the database is at the expected Alembic head and fail clearly if it is not.
- Deploy scripts should run migrations explicitly before starting or replacing the app container.

This keeps failed migrations visible as deployment failures rather than hidden inside runtime startup.

## Deployment Flow

Staging deployment should become:

```text
docker compose pull
docker compose run --rm app alembic upgrade head
docker compose up -d
deployment/scripts/smoke-check.sh
```

Production deployment should become:

```text
ENVIRONMENT=production ./backup.sh
docker compose pull
docker compose run --rm app alembic upgrade head
docker compose up -d
deployment/scripts/smoke-check.sh
```

The production backup must happen before migration.

If a migration fails:

- Do not start the new app version.
- Inspect logs and the backup.
- Fix forward when possible.
- Restore only if the database was partially changed or the data is damaged.

## SQLite Migration Constraints

SQLite supports the current schema well, but migrations should stay conservative.

Safe operations:

- Create tables.
- Create indexes.
- Add nullable columns.
- Add columns with safe defaults.
- Insert or update reference rows idempotently.

Riskier operations:

- Dropping columns.
- Renaming columns.
- Changing constraints.
- Rebuilding tables with foreign keys.

For risky operations, write migrations as explicit table-copy migrations and test them against a copied production-like database.

## Rollback Policy

Do not rely on Alembic downgrades as the primary production rollback strategy.

Production rollback remains:

- restore from the pre-deploy backup if data or schema is damaged;
- otherwise deploy a forward fix or previous compatible image.

Alembic downgrade functions may be implemented for local development convenience, but production runbooks should treat backups as the reliable rollback boundary.

## Testing Plan

Add or update tests for:

- Migration from an empty SQLite database to head.
- Presence of all expected tables and the partial unique index.
- Idempotent default submission-period rows.
- Existing app integration tests using migrated databases.
- A deployment smoke path that runs migrations before app startup.

The existing test suite must continue to pass with:

```bash
uv run --extra dev pytest
uv run --extra dev ruff check .
```

## Implementation Steps

1. Add Alembic dependency and lockfile update.
2. Add Alembic config and migration environment.
3. Create initial schema revision.
4. Add migration application helper or CLI command.
5. Adjust `app/db.py` so schema creation is no longer duplicated as the long-term source of truth.
6. Update tests to use migration-aware database setup.
7. Update Dockerfile to copy migration files and Alembic config.
8. Update CI/CD deployment commands to run migrations before `docker compose up -d`.
9. Update deployment runbook, checklist, and handoff.
10. Run full tests, lint, and local smoke verification.

## Acceptance Criteria

- A fresh database can be created with `alembic upgrade head`.
- Existing tests pass against the migrated schema.
- Staging and production deployment docs run migrations before starting the app.
- The initial Alembic revision faithfully matches the current schema.
- Default normal and late submission periods are present after migration.
- The app behavior, routes, permissions, and UI are unchanged by the migration adoption.
