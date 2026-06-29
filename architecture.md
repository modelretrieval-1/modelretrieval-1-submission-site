# Architecture Recommendation

## Summary

Use a lightweight Python web application with SQLite and local file storage, deployed on a VPS.

## Current Implementation Checkpoint

The implemented stack matches this recommendation:

- FastAPI and Jinja2 are in use.
- SQLite schema/bootstrap is in place.
- Local filesystem storage is used for ground truth and submissions.
- `uv`, Pytest, and Ruff are configured.
- Participant validation, evaluation, score display, deadline controls, and selected-period uploads are implemented.

The next implementation focus is Sprint 4 organizer submission review. VPS deployment hardening remains a later sprint.

Recommended stack:

- FastAPI for the backend.
- Jinja2 templates for server-rendered pages.
- uv for Python dependency management and reproducible installs.
- SQLite for relational data.
- Local filesystem storage for uploaded submissions, ground truth, validation logs, and export bundles.
- Nginx or Caddy as the public reverse proxy.
- HTTPS using Let's Encrypt.
- systemd to run the app as a long-lived service.

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

The application should run on a VPS as a normal Python service.

Suggested production layout:

```text
/opt/modelretrieval-submissions/
  app/
  data/
    app.sqlite3
    submissions/
    ground-truth/
    bundles/
    exports/
  logs/
  backups/
```

Suggested runtime:

- Uvicorn runs the FastAPI app on localhost.
- Nginx or Caddy terminates HTTPS and proxies requests to Uvicorn.
- systemd starts and restarts the app service.
- uv installs dependencies from `uv.lock`.
- SQLite database and local files are backed up together.

## Reverse Proxy

Use either Nginx or Caddy.

Caddy is simpler if automatic HTTPS is preferred.

Nginx is also fine if the server already uses it or the organizer is more familiar with it.

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
