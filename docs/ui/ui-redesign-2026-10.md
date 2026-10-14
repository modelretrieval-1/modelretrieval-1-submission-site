# UI Redesign Brief (2026-10)

Document role: design brief and acceptance criteria for the full visual redesign on
branch `feat/ui-refresh`. `ui-flow.md` remains the screen/workflow specification;
this brief changes presentation, hierarchy, and copy, not workflows or rules.

## Why

Owner feedback on the current UI: it looks generic/dated, is hard to understand,
is too dense, and works poorly on small screens. Baseline screenshots
(`tools/ui_preview`, label `before`) confirm:

- Default Bootstrap look (stock `#0d6efd` buttons, cyan/black badges with no
  consistent meaning); two Logout buttons on every page.
- Team dashboard repeats period information three times (stat cards, "Submission
  Status", "Submission Periods"); stat cards like "Normal deadline / Normal" carry
  no information; scores are squeezed into a table cell; history table wraps badly
  on mobile and hides scores.
- Upload page shows a fully disabled form when nothing can be uploaded, without one
  clear reason or next step; the checklist and helper text add a lot of reading.
- Organizer pages show raw status codes (`evaluation_failed`, `accepted`), an
  "Operations" section duplicating the sidebar, and wide tables that do not adapt.

## Constraints (non-negotiable)

- Stack stays: FastAPI + Jinja2 templates + `app/static/app.css`. No React/Vue, no
  build step, no new CDN dependencies or web fonts (system font stack). Bootstrap
  5.3.3 CSS/JS from the existing CDN may stay as the base (grid, offcanvas,
  collapse, utilities) but must be restyled through tokens so it no longer looks
  stock.
- Do not change routes, form `action`/`method`/field `name`s, hidden inputs, query
  parameters, links' targets, or what data a page shows/hides for a role. Do not
  change Python code except purely presentational template helpers if unavoidable
  (prefer Jinja macros).
- Preserve existing JavaScript behavior: upload XHR progress (determinate bar then
  indeterminate "checking" phase), status polling (`accepted`/`queued`/`processing`
  keep polling; terminal states stop), leaderboard/table sorting/filtering. Restyle
  freely; keep IDs/data attributes the scripts rely on (or update script and markup
  together, presentation-only).
- Participant visibility rules are business rules (e.g. hidden scores during a
  pending replacement, organizer-only per-query metrics). Do not expose anything new.

## Visual system

Translate the shared identity (`.research-ai-workflow/docs/UI_DESIGN_GUIDE.md`) into
CSS custom properties on `:root`, and map Bootstrap variables (`--bs-primary`,
`--bs-body-font-family`, `--bs-border-radius`, link colors, focus ring) onto them.

- `--primary` `#004D98` (actions, links, active nav, "in progress" info state)
- `--primary-dark` `#00294F` (sidebar / headings accents)
- `--accent` `#A50044` (sparing brand accent only — never errors)
- `--surface` `#FFFFFF`, `--surface-muted` `#F6F8FA`, `--surface-tint` `#E3EDF7`
- text `#1B2430` / secondary `#5F6B7A`; borders `#DDE3EA`
- semantic: success (green), warning (amber), danger (red), neutral (gray) — each
  with a soft background + strong text pair meeting WCAG AA.
- Type: system stack, limited scale (e.g. 28/20/16/14/12), tabular numbers for
  scores and timestamps, no all-caps micro-labels everywhere.
- Restrained: thin borders, small radius, at most one subtle shadow level, no
  gradients/glossy effects.

One status vocabulary, used identically on participant and organizer pages, always
text + color (+ small dot/icon), never raw codes:

| code | label | tone |
|---|---|---|
| `rejected` | Rejected | danger |
| `accepted`, `queued` | Queued | neutral |
| `processing` | Evaluating | info (primary), animated dot that respects `prefers-reduced-motion` |
| `evaluated` | Evaluated | success |
| `evaluation_failed` | Evaluation failed | danger (distinct icon from Rejected) |
| period `open` / `closed` / reopened override | Open / Closed / Reopened | success / neutral / info |

Implement as shared Jinja macros (e.g. `app/templates/_ui.html`: `status_badge`,
`period_badge`, page header, empty state, section card) so every page uses the same
markup.

## App shell

- Desktop (≥992px): slim left sidebar (brand, role-aware nav, account + single
  Logout at the bottom). Top bar shows the page title/breadcrumb, not a repeat of the
  account name. Exactly one Logout control visible at any width.
- Mobile/tablet: compact top bar (brand, Menu button); offcanvas nav with account
  and Logout. Touch targets ≥44px.
- Content max-width ~1200px for operational pages; reading text ≤ ~75ch.

## Participant pages (highest priority)

Team dashboard (`/team`) — answer "what can I do now, and what are my results?":
1. Header: team name; one line with the currently open period and its deadline
   (or "No submission period is open").
2. One card per registered subtask. For each period: state badge, deadline, and a
   single clear action or outcome (Upload / Upload replacement / latest status badge
   with link to its status page / Closed). Show the latest result's run scores
   inline in a compact table when visible to the team. Pending-replacement notice
   lives inside the affected subtask card.
3. Submission history (all attempts) as a secondary section; on mobile render rows
   as stacked items, not a squeezed table.
Remove the stat cards and the separate "Submission Periods" section.

Upload (`/team/submissions/{A|B}/new`):
- Clear steps: 1) choose period (radio cards; unavailable options explain why, e.g.
  "Closed" or "Already submitted — ask the organizers for a replacement"),
  2) choose file (styled file input / drop area showing the chosen file name and
  size), 3) Upload.
- If no period can be uploaded to, show a single explanatory empty state with the
  next step instead of a disabled form.
- Requirements checklist: concise, in a side column on desktop, collapsible on
  mobile. Add a short note that large files (≈100 MB) can take a few minutes to
  check and the page must stay open.
- Validation errors: summary at top with count, grouped, line numbers prominent;
  keep all current information.

Submission status (`/team/submissions/{id}`):
- Headline sentence for the state ("Evaluating your submission…", "Rejected — 4
  issues", …), the lifecycle stepper (horizontal desktop, vertical mobile), file
  name + submitted time, and the run score table when evaluated. Failed states say
  what to do next.

Login / home / change password: centered, calm card; task context on home; clear
error message on failed login.

## Organizer pages

- Dashboard: attention row first (counts; zero counts visually quiet, non-zero
  emphasized and linked), compact periods + ground-truth summary, recent
  submissions, recent validation failures. Drop the "Operations" card grid.
- Tables (submissions, teams, users, leaderboard, audit): consistent dense table
  style, human status labels, tabular numbers, sticky header where useful; on small
  screens wrap in a horizontal scroll container (no page-level horizontal scroll)
  or stack rows. Filters in a compact toolbar.
- Submission detail: summary header (team, subtask, period, status, file, checksum),
  then sections (runs/metrics, per-query metrics, validation errors, replacement
  history) with clear separation.
- Forms (teams, users, periods, ground truth): labeled, grouped, primary action
  obvious, destructive actions visually distinct.

## Acceptance criteria

- All pages render with HTTP 200 in `tools/ui_preview/screenshots.py` at desktop
  1440, tablet 834, mobile 390; no horizontal page scroll; no clipped text.
- A participant can tell from the dashboard, without reading help text, which
  subtask/period they can upload to now and the state of their latest submission.
- No raw status codes visible anywhere; one status vocabulary everywhere.
- One Logout control per viewport; active nav item obvious.
- Keyboard: visible focus ring on every interactive element; skip link to main.
- Color contrast AA for text and badges; status never conveyed by color alone.
- Upload progress, status polling, and table sorting/filtering still work.
- `uv run --offline --extra dev pytest -q` passes (test-asserted copy may only
  change with an explicit test update reviewed by the lead).
