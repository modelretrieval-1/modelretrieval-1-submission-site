# Deployment Runbook

## Purpose

This runbook describes the operational flow for deploying and maintaining staging and production.

The repository includes the first Docker deployment files:

- `Dockerfile`
- `.dockerignore`
- `compose.staging.yml`
- `compose.production.yml`
- `deployment/staging.env.example`
- `deployment/production.env.example`

Nginx and CI/CD files will be added separately.

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

## DNS Setup

In Muumuu Domain DNS, point staging and production hostnames to the Sakura VPS public IP.

Example:

```text
staging.<domain>  A  <sakura-vps-ip>
submit.<domain>   A  <sakura-vps-ip>
```

Wait for DNS propagation before issuing HTTPS certificates.

## Nginx Setup

Configure two Nginx server blocks:

- `staging.<domain>` proxies to `http://127.0.0.1:8001`.
- `submit.<domain>` proxies to `http://127.0.0.1:8002`.

Enable HTTPS using Certbot after the HTTP server blocks are reachable.

## Staging Deployment

Staging should deploy automatically after CI passes on `main`.

Deployment command shape:

```bash
cd /opt/modelretrieval/staging
docker compose pull
docker compose up -d
docker compose exec app python -m app.cli create-admin --username admin --display-name "Admin User"
```

Only run `create-admin` when the environment does not yet have an organizer account.

## Production Deployment

Production should deploy only from an explicit version tag.

Before deployment:

```bash
cd /opt/modelretrieval/production
./backup.sh
```

Deploy:

```bash
docker compose pull
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
