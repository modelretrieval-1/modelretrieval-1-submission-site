# Sakura VPS Setup Guide

## Purpose

This guide describes the first-time Sakura VPS setup for the NTCIR-19 ModelRetrieval submission system.

It assumes:

- Staging and production run on the same Sakura VPS.
- Nginx runs on the host.
- App environments run with Docker Compose.
- DNS is managed in Muumuu Domain.
- GitHub Actions deploys by SSH.

Commands may need small package-manager adjustments depending on the VPS operating system.

## Target Layout

```text
/opt/modelretrieval/
  staging/
    compose.yml
    .env
    data/
  production/
    compose.yml
    .env
    data/
    backup.sh
  backups/
```

Nginx routes:

```text
staging.<domain> -> 127.0.0.1:8001
submit.<domain>  -> 127.0.0.1:8002
```

Current project routes:

```text
submission-staging.modelretrieval-1.happysocial.net -> 127.0.0.1:8001
submission.modelretrieval-1.happysocial.net         -> 127.0.0.1:8002
```

## 1. DNS

In Muumuu Domain, create A records pointing to the Sakura VPS public IP.

```text
staging.<domain>  A  <sakura-vps-ip>
submit.<domain>   A  <sakura-vps-ip>
```

For this project:

```text
submission-staging.modelretrieval-1.happysocial.net  A  <sakura-vps-ip>
submission.modelretrieval-1.happysocial.net          A  <sakura-vps-ip>
```

Wait for DNS propagation before issuing certificates.

## 2. System Packages

Install the required host services:

- Docker Engine.
- Docker Compose plugin.
- Nginx.
- Certbot with Nginx integration.
- SQLite CLI.
- Git.

Ubuntu-style package example:

```bash
sudo apt update
sudo apt install -y ca-certificates curl git nginx certbot python3-certbot-nginx sqlite3
```

Install Docker from Docker's official repository for the VPS OS, then verify:

```bash
docker --version
docker compose version
```

## 3. Deploy User

Create a non-root deploy user without a password:

```bash
sudo adduser --disabled-password --gecos "" deploy
sudo usermod -aG docker deploy
```

The deploy user should use SSH keys only. It does not need broad passwordless `sudo` for normal deployments.

Install the GitHub Actions public SSH key for this user:

```bash
sudo mkdir -p /home/deploy/.ssh
sudo editor /home/deploy/.ssh/authorized_keys
sudo chown -R deploy:deploy /home/deploy/.ssh
sudo chmod 700 /home/deploy/.ssh
sudo chmod 600 /home/deploy/.ssh/authorized_keys
```

The matching private key is stored in GitHub as `STAGING_SSH_KEY` and `PRODUCTION_SSH_KEY`, or as separate keys if desired.

Optional hardening:

```bash
sudo passwd -l deploy
```

If the VPS SSH policy allows it, disable SSH password authentication globally:

```text
PasswordAuthentication no
PubkeyAuthentication yes
```

This is usually configured in:

```text
/etc/ssh/sshd_config
```

Then reload SSH:

```bash
sudo systemctl reload ssh
```

Some distributions use `sshd` instead:

```bash
sudo systemctl reload sshd
```

Before disabling password authentication, confirm key-based SSH login works from your admin machine and from GitHub Actions.

## 4. Firewall

Allow only required public ports:

- SSH.
- HTTP.
- HTTPS.

Example with UFW:

```bash
sudo ufw allow OpenSSH
sudo ufw allow "Nginx Full"
sudo ufw enable
sudo ufw status
```

Do not expose Uvicorn or Docker app ports publicly. Compose binds app ports to `127.0.0.1`.

## 5. Directory Setup

Create directories:

```bash
sudo mkdir -p /opt/modelretrieval/staging/data
sudo mkdir -p /opt/modelretrieval/production/data
sudo mkdir -p /opt/modelretrieval/backups
sudo chown -R deploy:deploy /opt/modelretrieval
```

## 6. Copy Deployment Files

Copy these files from the repository to the VPS:

```text
compose.staging.yml
compose.production.yml
deployment/staging.env.example
deployment/production.env.example
deployment/scripts/backup.sh
deployment/nginx/*.conf.example
```

Install Compose files:

```bash
cp compose.staging.yml /opt/modelretrieval/staging/compose.yml
cp compose.production.yml /opt/modelretrieval/production/compose.yml
```

Install env files:

```bash
cp deployment/staging.env.example /opt/modelretrieval/staging/.env
cp deployment/production.env.example /opt/modelretrieval/production/.env
chmod 600 /opt/modelretrieval/staging/.env
chmod 600 /opt/modelretrieval/production/.env
```

Edit both `.env` files:

- Replace `SECRET_KEY`.
- Set `APP_IMAGE`.
- Confirm `APP_ENV`.
- Confirm `DATABASE_PATH=/data/app.sqlite3`.
- Confirm `STORAGE_ROOT=/data/storage`.

### APP_IMAGE

`APP_IMAGE` is the container image that Docker Compose pulls and runs.

After GitHub Actions publishes an image, check it in:

```text
GitHub repository -> Packages
```

Expected image tags:

```text
ghcr.io/<owner>/<repo>:latest-staging
ghcr.io/<owner>/<repo>:main-<short-sha>
ghcr.io/<owner>/<repo>:vYYYY.MM.DD
```

Recommended staging value:

```text
APP_IMAGE=ghcr.io/<owner>/<repo>:latest-staging
```

Recommended production value:

```text
APP_IMAGE=ghcr.io/<owner>/<repo>:vYYYY.MM.DD
```

Production should use an immutable `v*` tag, not `latest-staging`.

Check the current value on the VPS:

```bash
grep APP_IMAGE /opt/modelretrieval/staging/.env
grep APP_IMAGE /opt/modelretrieval/production/.env
```

If GHCR returns `unauthorized`, log in as the same user that runs Docker Compose:

```bash
su - deploy
echo "<github_pat>" | docker login ghcr.io -u "<github_username>" --password-stdin
```

The GitHub personal access token needs `read:packages`. If the package or repository is private, it may also need `repo`.

Install production backup script:

```bash
cp deployment/scripts/backup.sh /opt/modelretrieval/production/backup.sh
chmod 700 /opt/modelretrieval/production/backup.sh
```

### Data Directory Ownership

The app container runs as a non-root `app` user. The host bind-mounted `data/` directories must be writable by that container user.

If the app fails with:

```text
PermissionError: [Errno 13] Permission denied: '/data/storage'
```

the host data directory has the wrong owner.

The app may exit before `docker compose exec app id` works. Use a one-off container instead:

```bash
cd /opt/modelretrieval/staging
docker compose run --rm --no-deps --entrypoint id app
```

Example output:

```text
uid=999(app) gid=999(app) groups=999(app)
```

Then fix staging ownership:

```bash
sudo chown -R 999:999 /opt/modelretrieval/staging/data
```

Replace `999:999` with the UID/GID shown by `id`.

For production:

```bash
cd /opt/modelretrieval/production
docker compose run --rm --no-deps --entrypoint id app
sudo chown -R <uid>:<gid> /opt/modelretrieval/production/data
```

Avoid `chmod 777`; set ownership instead.

## 7. Nginx And HTTPS

Start with bootstrap HTTP configs:

```bash
sudo cp deployment/nginx/staging.bootstrap.conf.example /etc/nginx/sites-available/modelretrieval-staging
sudo cp deployment/nginx/production.bootstrap.conf.example /etc/nginx/sites-available/modelretrieval-production
```

Edit hostnames:

- Replace `staging.example.jp`.
- Replace `submit.example.jp`.

Enable sites:

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

Replace bootstrap configs with final HTTPS configs:

```bash
sudo cp deployment/nginx/staging.conf.example /etc/nginx/sites-available/modelretrieval-staging
sudo cp deployment/nginx/production.conf.example /etc/nginx/sites-available/modelretrieval-production
```

Edit hostnames and certificate paths, then reload:

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

Then test and reload:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

If needed, increase the value to `256`.

## 8. First Manual Staging Deploy

Set `APP_IMAGE` in `/opt/modelretrieval/staging/.env`.

Then:

```bash
cd /opt/modelretrieval/staging
docker compose pull
docker compose up -d
```

If startup fails with a `/data/storage` permission error, run the data directory ownership fix from step 6.

Smoke check:

```bash
curl -fsS https://staging.<domain>/health
```

For this project:

```bash
curl -fsS https://submission-staging.modelretrieval-1.happysocial.net/health
```

Create first staging organizer if needed:

```bash
docker compose exec app python -m app.cli create-admin --username admin --display-name "Admin User"
```

## 9. First Manual Production Deploy

Set immutable `APP_IMAGE` in `/opt/modelretrieval/production/.env`.

Then:

```bash
cd /opt/modelretrieval/production
./backup.sh
docker compose pull
docker compose up -d
```

If startup fails with a `/data/storage` permission error, run the data directory ownership fix from step 6.

Smoke check:

```bash
curl -fsS https://submit.<domain>/health
```

For this project:

```bash
curl -fsS https://submission.modelretrieval-1.happysocial.net/health
```

Create first production organizer:

```bash
docker compose exec app python -m app.cli create-admin --username admin --display-name "Admin User"
```

Store the generated password securely.

## 10. Enable GitHub Actions Deployment

After manual staging works:

1. Add GitHub Actions secrets from `deployment/github-secrets.md`.
2. Push to `main` or `master`.
3. Confirm staging deploys.
4. Verify staging manually.
5. Create and push a `v*` tag.
6. Confirm production backup and deployment.

Do not enable production automation before a manual staging deployment succeeds.
