# Architecture Recommendation

## Summary

Use a lightweight Python web application with SQLite and local file storage, deployed on a VPS.

## Current Implementation Checkpoint

The implemented stack matches this recommendation:

- FastAPI and Jinja2 are in use.
- SQLite schema/bootstrap is in place.
- Local filesystem storage is used for ground truth and submissions.
- `uv`, Pytest, and Ruff are configured.
- Participant validation, evaluation, score display, deadline controls, selected-period uploads, organizer submission review, private leaderboard, leaderboard CSV export, submission bundle download, and Bootstrap-based UI modernization are implemented.

The current implementation focus is staging and production deployment rehearsal and hardening.

Recommended stack:

- FastAPI for the backend.
- Jinja2 templates for server-rendered pages.
- Bootstrap 5 for UI components and layout.
- Local project CSS for task-specific visual polish.
- uv for Python dependency management and reproducible installs.
- SQLite for relational data.
- Local filesystem storage for uploaded submissions, ground truth, validation logs, and export bundles.
- Host Nginx as the public reverse proxy.
- HTTPS using Let's Encrypt.
- Docker Compose to run separate staging and production app containers.
- GitHub Container Registry for deployment images.
- GitHub Actions for CI/CD.

## Why This Stack

The submission system is workflow-heavy but not traffic-heavy. It needs reliable validation, reproducible evaluation, password-based accounts, local ground-truth protection, and organizer downloads. A server-rendered FastAPI app keeps this small and easy to maintain.

SQLite is appropriate because:

- The number of teams and submissions is limited.
- Writes are low volume.
- Backups are simple.
- It avoids operating a separate database service.

Local filesystem storage is appropriate because:

- Ground truth is required to live on the server.
- Uploaded `.txt` files are small, with a 10 MB maximum.
- Organizers need downloadable bundles.
- Evaluation should be reproducible from preserved files.

## VPS Deployment Model

The application should run on Sakura VPS with Docker Compose app containers behind host Nginx.

Suggested VPS layout:

```text
/opt/modelretrieval/
  staging/
    compose.yml
    .env
    data/
      app.sqlite3
      storage/
  production/
    compose.yml
    .env
    data/
      app.sqlite3
      storage/
    backup.sh
  backups/
```

Suggested runtime:

- Docker Compose runs the app containers on localhost-only ports.
- Staging listens on `127.0.0.1:8001`; production listens on `127.0.0.1:8002`.
- Host Nginx terminates HTTPS and proxies requests by hostname.
- GitHub Actions builds and publishes images to GHCR.
- Staging deploys from `main`; production deploys from immutable `v*` tags.
- SQLite database and local storage files are backed up together.

## Reverse Proxy

Use Nginx on the VPS host.

Current project hostnames:

- Staging: `submission-staging.modelretrieval-1.happysocial.net`.
- Production: `submission.modelretrieval-1.happysocial.net`.

If Nginx reports `could not build server_names_hash`, set `server_names_hash_bucket_size 128;` inside the `http { ... }` block in `/etc/nginx/nginx.conf`, then run `sudo nginx -t`.

## Backup Requirements

Backups should include:

- SQLite database.
- Uploaded submissions.
- Uploaded ground-truth files.
- Generated bundles and exports, if needed.
- Application configuration.

Recommended backup schedule:

- Daily backup during submission periods.
- Manual backup before ground-truth replacement or re-evaluation.
- Retain at least one offline copy after the task ends.

## Security Notes

- Ground-truth files must never be served as static files.
- Submission and ground-truth directories should be outside public web roots.
- Passwords must be stored as hashes, never plaintext.
- Generated passwords may be displayed once to organizers, but only hashes should be stored.
- Admin pages should require organizer login.
- Participant pages should only expose the signed-in team's own submissions and scores.
