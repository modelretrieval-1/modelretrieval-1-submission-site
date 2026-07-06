# Restore Guide

## Purpose

This guide describes how to restore a database and storage backup created by `deployment/scripts/backup.sh`.

Restore the SQLite database and storage directory from the same backup timestamp. Do not mix a database from one backup with storage files from another backup.

## Backup Layout

Expected backup directory:

```text
/opt/modelretrieval/backups/production-YYYYMMDD-HHMMSS/
  app.sqlite3
  storage.tar.gz
  env.snapshot
  manifest.txt
```

`env.snapshot` exists only if the `.env` file was available when the backup ran. Treat it as sensitive.

## Production Restore

Stop the app container:

```bash
cd /opt/modelretrieval/production
docker compose stop app
```

Set the backup directory:

```bash
BACKUP_DIR=/opt/modelretrieval/backups/production-YYYYMMDD-HHMMSS
```

Move the current data aside before restoring:

```bash
mv data/app.sqlite3 data/app.sqlite3.before-restore
mv data/storage data/storage.before-restore
```

Restore database and storage:

```bash
cp "${BACKUP_DIR}/app.sqlite3" data/app.sqlite3
tar -C data -xzf "${BACKUP_DIR}/storage.tar.gz"
```

Start the app:

```bash
docker compose up -d
```

Run smoke checks:

```bash
curl -fsS https://submit.<domain>/health
```

Then verify:

- Organizer login.
- Team login.
- Ground-truth history.
- Recent submissions.
- Evaluation results, including organizer-only per-query evaluation results when present.
- Private leaderboard.

## Staging Restore Test

Before relying on production restore, test the process on staging.

Recommended approach:

1. Copy a production backup to a safe staging-only location.
2. Stop the staging app.
3. Restore the backup into `/opt/modelretrieval/staging/data`.
4. Start staging.
5. Run the staging smoke checks.
6. Confirm no production `.env` or production `SECRET_KEY` remains in staging.

Do not expose production participant data in staging unless the organizers explicitly approve that operational test.
