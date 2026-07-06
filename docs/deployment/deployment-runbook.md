# Deployment Runbook

Document role: this is the start-here operational guide for deployment, backup, rollback, logs, smoke checks, and restore flow. Use the neighboring deployment docs for focused reference details.

## Purpose

This runbook describes the operational flow for deploying and maintaining staging and production.

The repository includes the first Docker deployment files:

- `Dockerfile`
- `.dockerignore`
- `compose.staging.yml`
- `compose.production.yml`
- `deployment/staging.env.example`
- `deployment/production.env.example`
- `deployment/nginx/staging.bootstrap.conf.example`
- `deployment/nginx/production.bootstrap.conf.example`
- `deployment/nginx/staging.conf.example`
- `deployment/nginx/production.conf.example`
- `deployment/scripts/backup.sh`
- `deployment/scripts/smoke-check.sh`
- `restore.md`
- `vps-setup.md`
- `github-secrets.md`
- `.github/workflows/ci-cd.yml`

The GitHub Actions workflow runs tests, linting, image publishing, staging deployment, production backup, production deployment, and smoke checks.

Database schema changes should be managed with Alembic after the migration plan is implemented. See `../technical/database-migrations.md`.

For first-time VPS setup, start with `vps-setup.md`.

For GitHub Actions secret configuration, use `github-secrets.md`.

The VPS deploy user should be passwordless and use SSH key authentication only.

## One-Time VPS Setup

Install host-level services on the Sakura VPS:

- Docker Engine.
- Docker Compose plugin.
- Nginx.
- Certbot for Let's Encrypt.
- SQLite CLI for backup and inspection.

Create the application directory:

```bash
sudo mkdir -p /opt/modelretrieval/staging/data
sudo mkdir -p /opt/modelretrieval/production/data
sudo mkdir -p /opt/modelretrieval/backups
```

Create separate `.env` files:

```text
/opt/modelretrieval/staging/.env
/opt/modelretrieval/production/.env
```

Set restrictive permissions:

```bash
sudo chmod 600 /opt/modelretrieval/staging/.env
sudo chmod 600 /opt/modelretrieval/production/.env
```

Copy Compose files into each environment directory:

```bash
sudo cp compose.staging.yml /opt/modelretrieval/staging/compose.yml
sudo cp compose.production.yml /opt/modelretrieval/production/compose.yml
```

Create environment files from templates and replace secrets:

```bash
sudo cp deployment/staging.env.example /opt/modelretrieval/staging/.env
sudo cp deployment/production.env.example /opt/modelretrieval/production/.env
```

Set `APP_IMAGE` in each `.env`.

Staging can use:

```text
APP_IMAGE=ghcr.io/<owner>/<repo>:latest-staging
```

Production should use an immutable version tag:

```text
APP_IMAGE=ghcr.io/<owner>/<repo>:vYYYY.MM.DD
```

Check the current values:

```bash
grep APP_IMAGE /opt/modelretrieval/staging/.env
grep APP_IMAGE /opt/modelretrieval/production/.env
```

If GHCR returns `unauthorized`, log in as the Docker Compose user:

```bash
su - deploy
echo "<github_pat>" | docker login ghcr.io -u "<github_username>" --password-stdin
```

The token needs `read:packages`. Private repositories or packages may also require `repo`.

Copy deployment scripts to the VPS environment directories:

```bash
sudo cp deployment/scripts/backup.sh /opt/modelretrieval/production/backup.sh
sudo chmod 700 /opt/modelretrieval/production/backup.sh
```

Fix bind-mounted data directory ownership if needed. The app container runs as a non-root `app` user, so host `data/` directories must be writable by that container UID/GID.

If the app cannot start and logs show:

```text
PermissionError: [Errno 13] Permission denied: '/data/storage'
```

use a one-off container to check the app UID/GID:

```bash
cd /opt/modelretrieval/staging
docker compose run --rm --no-deps --entrypoint id app
```

Then set ownership using the returned UID/GID:

```bash
sudo chown -R <uid>:<gid> /opt/modelretrieval/staging/data
```

Repeat for production when needed:

```bash
cd /opt/modelretrieval/production
docker compose run --rm --no-deps --entrypoint id app
sudo chown -R <uid>:<gid> /opt/modelretrieval/production/data
```

Do not use `chmod 777`.

## DNS Setup

In Muumuu Domain DNS, point staging and production hostnames to the Sakura VPS public IP.

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

Wait for DNS propagation before issuing HTTPS certificates.

## Nginx Setup

Configure two Nginx server blocks:

- `staging.<domain>` proxies to `http://127.0.0.1:8001`.
- `submit.<domain>` proxies to `http://127.0.0.1:8002`.

Current project hostnames:

- `submission-staging.modelretrieval-1.happysocial.net` proxies to `http://127.0.0.1:8001`.
- `submission.modelretrieval-1.happysocial.net` proxies to `http://127.0.0.1:8002`.

For first-time certificate issuance, start with the temporary HTTP-only bootstrap configs:

```bash
sudo cp deployment/nginx/staging.bootstrap.conf.example /etc/nginx/sites-available/modelretrieval-staging
sudo cp deployment/nginx/production.bootstrap.conf.example /etc/nginx/sites-available/modelretrieval-production
```

Edit the copied files:

- Replace `staging.example.jp` with the real staging hostname.
- Replace `submit.example.jp` with the real production hostname.
- Keep staging proxying to `127.0.0.1:8001`.
- Keep production proxying to `127.0.0.1:8002`.

Enable the sites:

```bash
sudo ln -s /etc/nginx/sites-available/modelretrieval-staging /etc/nginx/sites-enabled/modelretrieval-staging
sudo ln -s /etc/nginx/sites-available/modelretrieval-production /etc/nginx/sites-enabled/modelretrieval-production
sudo nginx -t
sudo systemctl reload nginx
```

Issue certificates:

```bash
sudo certbot --nginx -d staging.<domain>
sudo certbot --nginx -d submit.<domain>
```

For this project:

```bash
sudo certbot --nginx -d submission-staging.modelretrieval-1.happysocial.net
sudo certbot --nginx -d submission.modelretrieval-1.happysocial.net
```

After Certbot succeeds, replace the bootstrap configs with the HTTPS examples:

```bash
sudo cp deployment/nginx/staging.conf.example /etc/nginx/sites-available/modelretrieval-staging
sudo cp deployment/nginx/production.conf.example /etc/nginx/sites-available/modelretrieval-production
```

Edit the copied files again with the real hostnames. The HTTPS examples assume Certbot's Nginx SSL snippets exist:

```text
/etc/letsencrypt/options-ssl-nginx.conf
/etc/letsencrypt/ssl-dhparams.pem
```

After installing the HTTPS examples, verify and reload:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

If `sudo nginx -t` fails with:

```text
nginx: [emerg] could not build server_names_hash, you should increase server_names_hash_bucket_size: 64
```

add this inside the `http { ... }` block in `/etc/nginx/nginx.conf`:

```nginx
server_names_hash_bucket_size 128;
```

Then test again:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

If `128` is still too small, use `256`.

Keep these settings in both final configs:

- `client_max_body_size 12m`
- proxy headers
- proxy timeouts
- upstream ports `8001` and `8002`

## Staging Deployment

Staging should deploy automatically after CI passes on `main` or `master`.

Deployment command shape:

```bash
cd /opt/modelretrieval/staging
docker compose pull
docker compose run --rm app alembic upgrade head
docker compose up -d
docker compose exec app python -m app.cli create-admin --username admin --display-name "Admin User"
```

Only run `create-admin` when the environment does not yet have an organizer account.

If the app exits before `docker compose exec` works, check `docker compose logs app`. For `/data/storage` permission errors, apply the data directory ownership fix from the one-time setup section.

## Production Deployment

Production should deploy only from an explicit version tag.

Before deployment:

```bash
cd /opt/modelretrieval/production
ENVIRONMENT=production deployment/scripts/backup.sh
```

Deploy:

```bash
docker compose pull
docker compose run --rm app alembic upgrade head
docker compose up -d
```

After deployment, run smoke checks:

```bash
curl -fsS https://submit.<domain>/health
```

Then verify:

- Login page loads.
- Organizer login works.
- Team dashboard loads for a test team if available.
- Admin pages are still protected from participant accounts.

The production backup must run before `alembic upgrade head`. If a migration fails, do not start the new app version until the migration issue is understood.

## Promotion Flow

Recommended flow:

```text
push to main
  -> CI test and lint
  -> deploy staging
  -> verify staging manually
  -> create version tag
  -> deploy production
```

Example tag:

```bash
git tag v2026.07.01
git push origin v2026.07.01
```

## GitHub Actions Setup

The workflow is defined in `.github/workflows/ci-cd.yml`.

Required GitHub environment or repository secrets:

```text
STAGING_HOST
STAGING_USER
STAGING_SSH_KEY
STAGING_PATH
STAGING_URL

PRODUCTION_HOST
PRODUCTION_USER
PRODUCTION_SSH_KEY
PRODUCTION_PATH
PRODUCTION_URL
```

Recommended values:

```text
STAGING_PATH=/opt/modelretrieval/staging
STAGING_URL=https://submission-staging.modelretrieval-1.happysocial.net
PRODUCTION_PATH=/opt/modelretrieval/production
PRODUCTION_URL=https://submission.modelretrieval-1.happysocial.net
```

After the Alembic migration plan is implemented, the staging deploy job should update `APP_IMAGE` in the remote staging `.env`, pull the image, run `alembic upgrade head`, start the Compose stack, and run `deployment/scripts/smoke-check.sh`.

After the Alembic migration plan is implemented, the production deploy job should run `./backup.sh` in the remote production directory before updating `APP_IMAGE`, pulling the image, running `alembic upgrade head`, starting the Compose stack, and running the smoke check.

The workflow publishes images to GitHub Container Registry using the repository's `GITHUB_TOKEN`.

Image tags:

- Branch pushes: `ghcr.io/<owner>/<repo>:main-<short-sha>`
- Staging convenience tag: `ghcr.io/<owner>/<repo>:latest-staging`
- Version tags: `ghcr.io/<owner>/<repo>:vYYYY.MM.DD`

## Rollback

Rollback the application by redeploying the previous known-good image tag.

Recommended process:

```bash
cd /opt/modelretrieval/production
edit .env or compose image tag to previous version
docker compose pull
docker compose up -d
curl -fsS https://submit.<domain>/health
```

Do not restore an older database unless the data itself is damaged or a schema migration requires it.

## Backup

Production backups should include:

- SQLite database.
- Storage directory.
- Environment configuration, handled securely.

Recommended backup moments:

- Daily during active submission periods.
- Immediately before each production deploy.
- Before ground-truth replacement.
- Before future re-evaluation workflows.

Recommended backup output:

```text
/opt/modelretrieval/backups/production-YYYYMMDD-HHMMSS/
  app.sqlite3
  storage.tar.gz
  manifest.txt
```

Run the backup script from the repository or copy it to the VPS:

```bash
ENVIRONMENT=production deployment/scripts/backup.sh
```

Useful overrides:

```bash
APP_ROOT=/opt/modelretrieval
ENVIRONMENT=production
BACKUP_ROOT=/opt/modelretrieval/backups
DATABASE_PATH=/opt/modelretrieval/production/data/app.sqlite3
STORAGE_ROOT=/opt/modelretrieval/production/data/storage
ENV_FILE=/opt/modelretrieval/production/.env
```

The script writes:

- `app.sqlite3`
- `storage.tar.gz`
- `env.snapshot` when an env file is present
- `manifest.txt`

`env.snapshot` contains secrets and must be protected like the original `.env` file.

## Smoke Checks

Run smoke checks with:

```bash
deployment/scripts/smoke-check.sh https://staging.<domain>
deployment/scripts/smoke-check.sh https://submit.<domain>
```

For this project:

```bash
deployment/scripts/smoke-check.sh https://submission-staging.modelretrieval-1.happysocial.net
deployment/scripts/smoke-check.sh https://submission.modelretrieval-1.happysocial.net
```

The script checks:

- `/health`
- `/login`

## Restore

Restore database and storage from the same backup timestamp.

Recommended process:

```bash
cd /opt/modelretrieval/production
docker compose stop app
restore app.sqlite3 into data/app.sqlite3
restore storage archive into data/storage
docker compose up -d
curl -fsS https://submit.<domain>/health
```

See `restore.md` for a full restore guide.

After restore, verify organizer login, team login, ground-truth history, and recent submissions.

## Logs

Application logs:

```bash
docker compose logs -f app
```

Nginx logs are host-level logs and depend on the VPS OS package defaults.

Common locations:

```text
/var/log/nginx/access.log
/var/log/nginx/error.log
```

## First-Deploy Smoke Test

For each environment:

1. Open `/health`.
2. Open `/login`.
3. Create the first organizer.
4. Log in as organizer.
5. Create a test team.
6. Log out and log in as that team.
7. Confirm admin pages redirect away from the team account.
8. Upload and activate minimal test ground truth in staging.
9. Upload a valid sample submission in staging.
10. Confirm participant scores and organizer leaderboard.
