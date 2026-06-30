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

## 1. DNS

In Muumuu Domain, create A records pointing to the Sakura VPS public IP.

```text
staging.<domain>  A  <sakura-vps-ip>
submit.<domain>   A  <sakura-vps-ip>
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

Create a non-root deploy user:

```bash
sudo adduser deploy
sudo usermod -aG docker deploy
```

Install the GitHub Actions public SSH key for this user:

```bash
sudo mkdir -p /home/deploy/.ssh
sudo editor /home/deploy/.ssh/authorized_keys
sudo chown -R deploy:deploy /home/deploy/.ssh
sudo chmod 700 /home/deploy/.ssh
sudo chmod 600 /home/deploy/.ssh/authorized_keys
```

The matching private key is stored in GitHub as `STAGING_SSH_KEY` and `PRODUCTION_SSH_KEY`, or as separate keys if desired.

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

Install production backup script:

```bash
cp deployment/scripts/backup.sh /opt/modelretrieval/production/backup.sh
chmod 700 /opt/modelretrieval/production/backup.sh
```

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

## 8. First Manual Staging Deploy

Set `APP_IMAGE` in `/opt/modelretrieval/staging/.env`.

Then:

```bash
cd /opt/modelretrieval/staging
docker compose pull
docker compose up -d
```

Smoke check:

```bash
curl -fsS https://staging.<domain>/health
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

Smoke check:

```bash
curl -fsS https://submit.<domain>/health
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
