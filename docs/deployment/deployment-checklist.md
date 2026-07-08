# Deployment Checklist

## Purpose

This checklist is used before launch and before each production deployment.

## Confirmed Deployment Inputs

- [x] Staging hostname: `submission-staging.modelretrieval-1.happysocial.net`.
- [x] Production hostname: `submission.modelretrieval-1.happysocial.net`.
- [x] Sakura VPS hosts staging and production on the same machine.
- [x] Docker Engine and Docker Compose are used for app containers.
- [x] Host Nginx is the reverse proxy.
- [x] HTTPS certificates are issued with Certbot.
- [x] GitHub Container Registry stores deployment images.
- [x] GitHub Actions handles CI/CD.
- [x] Staging deploys from `main`.
- [x] Production deploys from immutable `v*` tags.
- [x] Deploy user uses SSH key authentication and no usable password login.
- [ ] Confirm backup retention period.
- [ ] Confirm who has SSH access to the VPS.
- [ ] `vps-setup.md` has been followed for the target VPS.
- [x] `github-secrets.md` has been followed for GitHub Actions staging deployment.

## One-Time VPS Checklist

- [ ] DNS A record exists for staging.
- [ ] DNS A record exists for production.
- [ ] Firewall allows SSH, HTTP, and HTTPS.
- [ ] Docker is installed.
- [ ] Docker Compose plugin is installed.
- [ ] Nginx is installed.
- [ ] Certbot is installed.
- [ ] Staging Nginx config has real hostname and proxies to `127.0.0.1:8001`.
- [ ] Production Nginx config has real hostname and proxies to `127.0.0.1:8002`.
- [ ] Nginx config includes `client_max_body_size 60m` or larger.
- [ ] Nginx `server_names_hash_bucket_size` is increased if long hostnames make `nginx -t` fail.
- [ ] `sudo nginx -t` passes.
- [ ] `/opt/modelretrieval/staging` exists.
- [ ] `/opt/modelretrieval/production` exists.
- [ ] `/opt/modelretrieval/backups` exists.
- [ ] `deployment/scripts/backup.sh` is available on the VPS or runnable from the checkout.
- [ ] `/opt/modelretrieval/production/backup.sh` exists and is executable.
- [ ] `compose.staging.yml` has been copied to staging as `compose.yml`.
- [ ] `compose.production.yml` has been copied to production as `compose.yml`.
- [ ] Staging `.env` exists and is not committed.
- [ ] Production `.env` exists and is not committed.
- [ ] Staging `APP_IMAGE` points to an existing GHCR image.
- [ ] Production `APP_IMAGE` points to an immutable `v*` GHCR image.
- [ ] Docker Compose user can pull `APP_IMAGE` from GHCR.
- [ ] Staging and production use different `SECRET_KEY` values.
- [ ] Staging and production use separate data directories.
- [ ] Staging data directory ownership matches the app container UID/GID.
- [ ] Production data directory ownership matches the app container UID/GID.
- [x] GitHub Actions deploy user can SSH to the VPS for staging deployment.
- [ ] Deploy user has no usable password login.
- [ ] Deploy user uses SSH keys only.
- [ ] GitHub Actions deploy user can run Docker Compose in both environment directories.

## Staging Verification

- [x] CI tests pass.
- [x] CI lint passes.
- [x] Docker image was pushed to GitHub Container Registry.
- [x] Staging deploy completes.
- [x] Staging `APP_IMAGE` was updated in remote `.env`.
- [x] `https://submission-staging.modelretrieval-1.happysocial.net/health` returns success.
- [x] Login page loads over HTTPS.
- [ ] Upload-size behavior is not blocked by Nginx before the app's 50 MB validation rule.
- [ ] Organizer login works.
- [ ] Organizer can create a team.
- [ ] Team login works.
- [ ] Team cannot access organizer pages.
- [ ] Organizer can upload and activate ground truth.
- [ ] Team can upload a valid sample submission.
- [ ] Team can see scores.
- [ ] Organizer can see private leaderboard.
- [ ] CSV export works.
- [ ] Submission bundle download works.

## Production Pre-Deploy

- [ ] Production image tag is immutable.
- [ ] Production `APP_IMAGE` is set in `/opt/modelretrieval/production/.env`.
- [ ] Production deployment is triggered by a `v*` tag.
- [ ] Staging was verified using the same commit or image.
- [ ] Production backup completed.
- [ ] Production `.env` is present.
- [ ] Production data directory is present.
- [ ] Nginx production config is enabled.
- [ ] HTTPS certificate is valid.
- [ ] Production Nginx config preserves `X-Forwarded-*` headers.
- [ ] Rollback image tag is known.

## Production Post-Deploy

- [ ] `https://submission.modelretrieval-1.happysocial.net/health` returns success.
- [ ] Login page loads over HTTPS.
- [ ] Organizer login works.
- [ ] Team login works for a test or official account.
- [ ] Admin pages are inaccessible to team accounts.
- [ ] Team pages are inaccessible to organizer accounts where expected.
- [ ] Ground-truth history is intact.
- [ ] Existing submissions are visible.
- [ ] Existing evaluation results are visible.
- [ ] Private leaderboard loads.
- [ ] Nginx error logs show no deployment-related errors.
- [ ] Application logs show no startup errors.
- [ ] `deployment/scripts/smoke-check.sh` passes against production URL.

## Backup Verification

- [ ] Backup contains SQLite database.
- [ ] Backup contains storage directory.
- [ ] Backup has a timestamped manifest.
- [ ] Backup env snapshot is protected or intentionally omitted.
- [ ] Backup can be copied off the VPS.
- [ ] Restore process has been tested on staging.

## Launch Readiness

- [ ] First production organizer account created.
- [ ] Official teams imported or created.
- [ ] Team credentials distributed securely.
- [ ] Normal deadline confirmed as `2026-08-01 15:00 JST`.
- [ ] Late deadline confirmed as `2026-10-15 23:59 JST`.
- [ ] Production ground truth uploaded and activated.
- [ ] Sample validation failure checked.
- [ ] Sample valid submission checked.
- [ ] Organizer leaderboard checked.
- [ ] Backup schedule active.
- [ ] Rollback procedure understood.
