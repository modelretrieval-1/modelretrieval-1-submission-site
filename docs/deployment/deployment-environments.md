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
MAX_UPLOAD_BYTES=524288000
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
MAX_UPLOAD_BYTES=524288000
```

Template:

- `deployment/staging.env.example`

Recommended public hostname:

```text
staging.<domain>
```

Current project value:

```text
submission-staging.modelretrieval-1.happysocial.net
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
MAX_UPLOAD_BYTES=524288000
```

Template:

- `deployment/production.env.example`

Recommended public hostname:

```text
submit.<domain>
```

Current project value:

```text
submission.modelretrieval-1.happysocial.net
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
| `MAX_UPLOAD_BYTES` | No | Upload size limit. Default is 500 MB. |

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

Current project values:

```text
submission-staging.modelretrieval-1.happysocial.net  A  <sakura-vps-ip>
submission.modelretrieval-1.happysocial.net          A  <sakura-vps-ip>
```

Nginx should route requests by hostname to the correct local upstream.

## Container Port Rules

Bind app ports only to localhost on the VPS:

```text
127.0.0.1:8001:8000
127.0.0.1:8002:8000
```

Do not expose Uvicorn directly to the public internet.

## Compose Files

The repository includes two image-based Compose files:

- `compose.staging.yml`: staging stack, localhost port `8001`.
- `compose.production.yml`: production stack, localhost port `8002`, requires an immutable `APP_IMAGE`.

Expected VPS file placement:

```text
/opt/modelretrieval/staging/compose.yml
/opt/modelretrieval/staging/.env
/opt/modelretrieval/staging/data/

/opt/modelretrieval/production/compose.yml
/opt/modelretrieval/production/.env
/opt/modelretrieval/production/data/
```

The deployed `compose.yml` files may be copied from the repository's environment-specific Compose files.

## APP_IMAGE

`APP_IMAGE` tells Docker Compose which image to pull.

Staging commonly uses:

```text
APP_IMAGE=ghcr.io/<owner>/<repo>:latest-staging
```

Production should use an immutable version tag:

```text
APP_IMAGE=ghcr.io/<owner>/<repo>:vYYYY.MM.DD
```

Check the current value:

```bash
grep APP_IMAGE /opt/modelretrieval/staging/.env
grep APP_IMAGE /opt/modelretrieval/production/.env
```

If Docker cannot pull with `unauthorized`, log in to GHCR as the same user that runs Docker Compose:

```bash
echo "<github_pat>" | docker login ghcr.io -u "<github_username>" --password-stdin
```

The token needs `read:packages`. Private repositories or packages may also require `repo`.

## Data Directory Ownership

The container writes to `/data`, which is a host bind mount.

If startup fails with:

```text
PermissionError: [Errno 13] Permission denied: '/data/storage'
```

find the container UID/GID:

```bash
docker compose run --rm --no-deps --entrypoint id app
```

Then apply ownership on the host data directory:

```bash
sudo chown -R <uid>:<gid> /opt/modelretrieval/staging/data
sudo chown -R <uid>:<gid> /opt/modelretrieval/production/data
```

Run the command for the environment you are fixing. Do not use `chmod 777`.

## First Admin Creation

After each environment is deployed, create the first organizer account inside that environment.

Example:

```bash
docker compose exec app python -m app.cli create-admin --username admin --display-name "Admin User"
```

Store the generated password securely and change it after first login if desired.
