# Deployment Environments

## Purpose

This document defines the configuration boundaries for development, staging, and production.

The application must behave consistently across environments while keeping data, secrets, and domains separated.

## Environment Summary

| Environment | Location | Purpose | Deployment |
|---|---|---|---|
| Development | Developer laptop | Local coding and tests | Manual local commands |
| Staging | Sakura VPS | Production-like verification | Automatic from `main` |
| Production | Sakura VPS | Official participant system | Explicit version tag |

## Development

Development runs locally.

Recommended command:

```bash
uv run uvicorn app.main:app --reload
```

Recommended local values:

```text
APP_ENV=development
DATABASE_PATH=var/app.sqlite3
STORAGE_ROOT=var/storage
SECRET_KEY=change-me-before-production
MAX_UPLOAD_BYTES=10485760
```

Development can use the default paths from `app/config.py`.

## Staging

Staging should use production-like infrastructure but non-production data.

Recommended host path:

```text
/opt/modelretrieval/staging
```

Recommended app data:

```text
/opt/modelretrieval/staging/data/app.sqlite3
/opt/modelretrieval/staging/data/storage
```

Recommended `.env`:

```text
APP_NAME=NTCIR-19 ModelRetrieval Submissions Staging
APP_ENV=staging
DATABASE_PATH=/data/app.sqlite3
STORAGE_ROOT=/data/storage
SECRET_KEY=<unique-staging-secret>
MAX_UPLOAD_BYTES=10485760
```

Recommended public hostname:

```text
staging.<domain>
```

Recommended local upstream:

```text
127.0.0.1:8001
```

## Production

Production is the official system used by organizers and participant teams.

Recommended host path:

```text
/opt/modelretrieval/production
```

Recommended app data:

```text
/opt/modelretrieval/production/data/app.sqlite3
/opt/modelretrieval/production/data/storage
```

Recommended `.env`:

```text
APP_NAME=NTCIR-19 ModelRetrieval Submissions
APP_ENV=production
DATABASE_PATH=/data/app.sqlite3
STORAGE_ROOT=/data/storage
SECRET_KEY=<unique-production-secret>
MAX_UPLOAD_BYTES=10485760
```

Recommended public hostname:

```text
submit.<domain>
```

Recommended local upstream:

```text
127.0.0.1:8002
```

## Required Environment Variables

| Name | Required | Description |
|---|---:|---|
| `APP_NAME` | No | Display name shown in the UI. |
| `APP_ENV` | Yes | `development`, `staging`, or `production`. |
| `DATABASE_PATH` | Yes outside local dev | SQLite database path inside the app container or local process. |
| `STORAGE_ROOT` | Yes outside local dev | Directory for submissions, ground truth, bundles, and exports. |
| `SECRET_KEY` | Yes | Session signing secret. Must be unique per environment. |
| `MAX_UPLOAD_BYTES` | No | Upload size limit. Default is 10 MB. |

## Secret Rules

- Do not commit `.env` files.
- Use different `SECRET_KEY` values for staging and production.
- Treat production `.env` as sensitive.
- Rotating `SECRET_KEY` signs out existing sessions.
- Generated team and organizer passwords are shown once but only hashes are stored.

## Data Separation Rules

Staging and production must never share:

- SQLite database files.
- Storage directories.
- `.env` files.
- `SECRET_KEY` values.
- Compose project names.

The same Docker image can be used in staging and production because environment-specific behavior comes from runtime configuration.

## Domain Rules

Muumuu Domain DNS should point each hostname to the Sakura VPS public IP.

Example:

```text
staging.<domain>  A  <sakura-vps-ip>
submit.<domain>   A  <sakura-vps-ip>
```

Nginx should route requests by hostname to the correct local upstream.

## Container Port Rules

Bind app ports only to localhost on the VPS:

```text
127.0.0.1:8001:8000
127.0.0.1:8002:8000
```

Do not expose Uvicorn directly to the public internet.

## First Admin Creation

After each environment is deployed, create the first organizer account inside that environment.

Example:

```bash
docker compose exec app python -m app.cli create-admin --username admin --display-name "Admin User"
```

Store the generated password securely and change it after first login if desired.
