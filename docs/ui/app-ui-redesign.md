# Application UI Redesign

## Purpose

This document defines the next UI direction for the NTCIR-19 ModelRetrieval submission system.

The goal is to make the product feel like a focused web application rather than a collection of standalone web pages. The redesign should improve navigation, situational awareness, and repeated operational workflows while preserving the existing server-rendered FastAPI/Jinja2 architecture.

## Product Principle

The interface should feel like an operations console for a research-task submission system.

It should be:

- Application-like.
- Fast to scan.
- Calm and trustworthy.
- Dense enough for organizers who repeat the same workflows.
- Clear enough for participants who may only submit a few times.
- Responsive on laptop, tablet, and mobile viewports.

It should not become:

- A marketing landing page.
- A decorative hero-style website.
- A single-page application.
- A visually busy dashboard full of low-value charts.

## Architecture Decision

Keep the current frontend architecture:

- FastAPI routes.
- Jinja2 templates.
- Bootstrap 5.
- Local project CSS in `app/static/app.css`.
- Minimal JavaScript, only for Bootstrap behavior or small progressive enhancements.

Do not introduce React, Vue, a frontend build pipeline, or a separate design system package for this redesign.

## App Shell

All authenticated pages should use a shared application shell.

Desktop layout:

- Persistent left sidebar.
- Compact top bar.
- Main content workspace.
- Role-aware navigation.
- Clear current-page active state.
- Account area with signed-in identity and logout action.

Mobile layout:

- Collapsed navigation available from a menu button.
- Top bar remains visible.
- Content stacks into a single-column workspace.
- Tables keep readable fallbacks through horizontal scrolling or compact row treatment.

The login page can remain outside the authenticated app shell, but it should visually match the application.

## Navigation Model

Organizer navigation:

- Dashboard: `/admin`
- Teams: `/admin/teams`
- Users: `/admin/users`
- Ground Truth: `/admin/ground-truth`
- Periods: `/admin/periods`
- Submissions: `/admin/submissions`
- Leaderboard: `/admin/leaderboard`
- Password: `/account/password`

Participant navigation:

- Dashboard: `/team`
- Upload: `/team/submissions/new`
- Results: contextual links from dashboard and upload/results pages
- Password: `/account/password`

Navigation should be role-aware. Teams must never see organizer-only links.

## Organizer Dashboard

The organizer dashboard should become the main operational overview.

Recommended sections:

- Summary metrics:
  - Active teams.
  - Evaluated submissions.
  - Rejected attempts.
  - Active ground-truth versions.
- Submission status by subtask and period.
- Deadline state for normal and late periods.
- Ground-truth status for Subtask A and Subtask B.
- Recent submissions and recent validation failures.
- Primary actions:
  - Add team.
  - Upload ground truth.
  - Review submissions.
  - View leaderboard.
  - Export CSV.
  - Download bundle.

The dashboard should prioritize operational status over decoration. Use cards only for discrete status summaries or repeated dashboard units.

## Participant Dashboard

The participant dashboard should guide a team through the submission process.

Recommended sections:

- Team identity and registered subtasks.
- Normal and late period status.
- Subtask A status and available action.
- Subtask B status and available action.
- Latest successful scores, if any.
- Latest rejected attempt summary, if useful.

The upload action should be easy to find, but only when the team is eligible and the selected period can accept a successful submission.

## List And Detail Pages

Organizer list pages should behave like app workspaces:

- Compact page header with title, description, and primary action.
- Filter bar directly above data tables.
- Dense tables with consistent status badges.
- Empty states that explain the next action.
- Detail pages with metadata panels and action groups.
- CSV and bundle actions placed near the filtered data they affect.

Forms should keep labels visible, use aligned actions, and show validation feedback close to the field or action that caused it.

## Visual System

Use a restrained visual language:

- Sidebar and top bar establish the app frame.
- Main workspace uses neutral backgrounds with clear content bands.
- Cards are allowed for discrete dashboard summaries, repeated items, and form/detail panels.
- Avoid nested cards.
- Avoid decorative gradients, oversized heroes, and ornamental illustrations.
- Use color primarily for status, emphasis, and navigation state.
- Keep tables, filters, forms, and badges visually consistent across pages.

Status colors should be consistent for:

- `evaluated`
- `rejected`
- `evaluation_failed`
- `normal`
- `late`
- `open`
- `closed`
- `reopened`
- Subtask A
- Subtask B

## Accessibility And Responsiveness

The redesign must preserve:

- Semantic HTML landmarks.
- Visible labels.
- Keyboard focus states.
- Color-independent status text.
- Sufficient contrast.
- Responsive behavior for all authenticated pages.
- Text that does not overflow buttons, cards, badges, sidebars, or tables.

## Implementation Slices

Recommended order:

1. Update shared `base.html` into an authenticated app shell while preserving the login page.
2. Add role-aware sidebar and top-bar navigation.
3. Redesign organizer dashboard as the main operational overview.
4. Redesign participant dashboard around subtask and period status.
5. Normalize page headers, filters, actions, status badges, and tables.
6. Polish upload, results, validation-error, and detail pages inside the new shell.
7. Add or update focused tests for navigation visibility and access control.
8. Run the full pytest and Ruff checks.

## Acceptance Criteria

- Authenticated pages feel like one cohesive application.
- Organizer pages have persistent navigation to all major admin workflows.
- Participant pages have persistent navigation to dashboard and upload flow.
- The active page is visually clear.
- Organizer dashboard gives a useful operational summary without needing to visit every page.
- Participant dashboard clearly shows what can be submitted and what has already succeeded.
- Existing permissions and role separation are unchanged.
- Existing routes and backend behavior are preserved unless explicitly documented.
- The app remains server-rendered with Bootstrap and local CSS.
- The UI remains usable on mobile and desktop viewports.
