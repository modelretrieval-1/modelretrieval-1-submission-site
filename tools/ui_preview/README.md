# UI preview tooling

Run from the repository root (dev dependencies and Playwright Chromium must already
be installed). These tools create only local demo data; they do not modify app code
or templates. All metrics come from the app evaluator using synthetic ground truth,
not competition data.

Three-command workflow:

```sh
uv run --offline --extra dev python tools/ui_preview/seed_demo.py
uv run --offline --extra dev python tools/ui_preview/serve.py
# In another terminal while the server is running:
uv run --offline --extra dev python tools/ui_preview/screenshots.py --label current
```

Open `.ui-preview/shots/current/index.html` for the contact sheet. Individual images
use `<viewport>__<page>.png`; `capture.json` records all screenshots, app HTTP status
codes, CDN warnings, and any capture failure. App HTTP errors fail the command, as
do unexpected redirects/auth failures. The intentional failed-login flow currently
returns 303 followed by 200, and its error message is checked.

Use another label (e.g. `--label redesigned`) to compare a subsequent UI version.
Reusing a label overwrites matching images and reports. Each viewport has isolated
public, primary-team, single-subtask-team, and organizer sessions.

Custom demo root and output:

```sh
uv run --offline --extra dev python tools/ui_preview/seed_demo.py --root /tmp/uiprev-test
uv run --offline --extra dev python tools/ui_preview/serve.py --root /tmp/uiprev-test
uv run --offline --extra dev python tools/ui_preview/screenshots.py \
  --manifest /tmp/uiprev-test/manifest.json --base-url http://127.0.0.1:8765 \
  --out /tmp/uiprev-test/shots/current
```

The default root is `.ui-preview/` at the repository root and is ignored by Git.
Seeding refuses a nonempty directory. To reseed, choose a new root or explicitly
remove your old demo directory yourself. Preserved upload paths are absolute: do
not move a seeded root. Custom roots are not automatically ignored by Git.

The manifest lists every credential and submission ID per team/status. All passwords
are `demo-password-123`; organizer login is `admin`. Teams are `tsukuba-ir` (A+B),
`kyoto-nlp` (A), `osaka-vision` (B), and `tohoku-retrieval` (A+B). The primary team
contains evaluated, rejected, evaluation_failed, queued, processing, and accepted
examples. The accepted example is superseded history; the primary team's four
current slots contain evaluated, evaluation_failed, queued, and processing.
There are completed organizer-approved replacements and an unused replacement
permission on A/late. Normal is closed; late is open until 2099. Each ground truth
has 20 topics and six models; each valid upload has three complete TREC_EVAL runs.
Accounts, ground truth, uploads, replacement grants, and audit events use app APIs
and TestClient flows. In-flight/failure statuses are explicitly synthetic fixtures;
no fabricated scores are attached to them.

`serve.py` binds only `127.0.0.1:8765` (override with `--port`). It sets
`DATABASE_PATH`, `STORAGE_ROOT`, `SECRET_KEY`, `APP_ENV=development`, and
`EVALUATION_MODE=eager`. In `app/main.py`, only `worker` mode starts a worker and
recovers orphaned processing rows. Eager mode starts neither; upload handling only
evaluates the newly uploaded submission ID. Thus browsing and the intentional
invalid upload never drain the seeded queued/processing rows. Do not start a
separate worker or use the ordinary app server against this database. The scripts
do not inherit production database/storage settings. Demo credentials and the
fixed local secret are intended only for this loopback preview.

The screenshots include all HTML page templates, each at desktop 1440×900, tablet
834×1112, and mobile 390×844, plus the team and organizer mobile Menu opened. They
also include Subtask B organizer metrics and superseded replacement history.
The complete set is 83 PNGs: each of these 27 page states at three viewports,
plus `mobile__team-menu-open.png` and `mobile__organizer-menu-open.png`:

| Group | Page slugs (prefix with `<viewport>__`, suffix with `.png`) |
| --- | --- |
| Public | `public-home`, `public-login`, `public-login-error` |
| Team | `team-dashboard`, `team-upload-a`, `team-upload-b`, `team-upload-errors`, `team-password`, `team-single-subtask` |
| Team status | `team-status-evaluated`, `team-status-rejected`, `team-status-evaluation_failed`, `team-status-queued`, `team-status-processing`, `team-status-accepted` |
| Organizer | `admin-dashboard`, `admin-teams`, `admin-users`, `admin-ground-truth`, `admin-periods`, `admin-submissions`, `admin-leaderboard`, `admin-audit-events` |
| Organizer detail | `admin-detail-evaluated`, `admin-detail-rejected`, `admin-detail-evaluated-b`, `admin-detail-superseded` |

Screenshot capture posts one invalid upload and login/audit events per viewport;
repeated captures add rejected attempts and audit rows, but preserve the existing
submission statuses and replacement permission. Reseed for a clean baseline.

Bootstrap comes from `cdn.jsdelivr.net`. Capture bounds CDN requests to five seconds
and caches the original CSS/JS in `<root>/cdn-cache/` for subsequent offline runs.
You can supply `--cdn-cache DIR` containing `bootstrap.min.css` and
`bootstrap.bundle.min.js`. If neither CDN nor cache is available, the script still
captures the pages and records the missing styles/scripts. If Bootstrap JS cannot
open Menu, it captures `mobile__team-menu-unavailable.png` / the organizer
equivalent and clearly records that the open-navigation state could not be rendered;
it never invents an open offcanvas state or changes app HTML/CSS.

Validation:

```sh
uv run --offline --extra dev pytest -q
uv run --offline --extra dev ruff check app tests tools
```

If your sandbox blocks the normal uv cache, prefix commands with
`UV_CACHE_DIR=/tmp/uiprev-uv-cache` (the existing virtualenv must contain the dev
dependencies when running offline).
