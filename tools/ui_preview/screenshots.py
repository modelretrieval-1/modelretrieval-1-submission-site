"""Capture the actual app pages, authenticated states, and mobile navigation."""

from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

REPO_ROOT = Path(__file__).resolve().parents[2]
VIEWPORTS = {
    "desktop": {"width": 1440, "height": 900},
    "tablet": {"width": 834, "height": 1112},
    "mobile": {"width": 390, "height": 844},
}


class Capture:
    def __init__(self, base_url: str, out: Path, cdn_cache: Path):
        self.base_url = base_url.rstrip("/")
        self.out = out
        self.cdn_cache = cdn_cache
        self.shots: list[dict] = []
        self.responses: list[dict] = []
        self.notes: list[str] = []
        self.cdn: dict[str, bytes | None] = {}

    def note(self, message: str) -> None:
        if message not in self.notes:
            self.notes.append(message)
            print(f"NOTE: {message}", flush=True)

    def cdn_route(self, route) -> None:
        """Bound CDN waits; reuse the exact Bootstrap assets without editing the app."""
        url = route.request.url
        filename = Path(urlsplit(url).path).name
        content_type = "text/css" if filename.endswith(".css") else "application/javascript"
        if url not in self.cdn:
            cached = self.cdn_cache / filename
            if cached.is_file():
                self.cdn[url] = cached.read_bytes()
                self.note(f"Using cached CDN asset: {filename}")
            else:
                try:
                    response = route.fetch(timeout=5000)
                    if not response.ok:
                        raise RuntimeError(f"HTTP {response.status}")
                    self.cdn[url] = response.body()
                    self.cdn_cache.mkdir(parents=True, exist_ok=True)
                    cached.write_bytes(self.cdn[url])
                except (PlaywrightTimeoutError, RuntimeError, OSError) as exc:
                    self.cdn[url] = None
                    self.note(f"CDN unavailable ({filename}): {str(exc).splitlines()[0]}")
                except Exception as exc:
                    # Playwright also reports DNS / TLS failures as generic Error.
                    self.cdn[url] = None
                    self.note(f"CDN unavailable ({filename}): {str(exc).splitlines()[0]}")
        content = self.cdn[url]
        if content is None:
            route.abort()
        else:
            route.fulfill(status=200, body=content, content_type=content_type)

    def response(self, response) -> None:
        if urlsplit(response.url).netloc != urlsplit(self.base_url).netloc:
            return
        entry = {
            "method": response.request.method,
            "url": response.url,
            "status": response.status,
            "resource_type": response.request.resource_type,
        }
        self.responses.append(entry)
        if entry["resource_type"] in {"document", "xhr", "fetch"} or response.status >= 400:
            print(f"HTTP {response.status} {entry['method']} {response.url}", flush=True)

    def healthy(self) -> None:
        errors = [r for r in self.responses if r["status"] >= 400]
        if errors:
            raise RuntimeError(f"App returned HTTP errors: {errors}")

    def ready(self, page) -> None:
        page.wait_for_load_state("networkidle", timeout=15000)
        page.evaluate("document.fonts.ready")
        self.healthy()

    def goto(self, page, path: str) -> None:
        response = page.goto(self.base_url + path, wait_until="domcontentloaded")
        if response is None or response.status >= 400:
            raise RuntimeError(f"Navigation failed: {path}, response={response}")
        if urlsplit(page.url).path != urlsplit(path).path:
            raise RuntimeError(f"Unexpected redirect from {path} to {page.url}")
        self.ready(page)

    def login(self, page, credential: dict, destination: str) -> None:
        self.goto(page, "/login")
        page.locator('[name="user_id"]').fill(credential["user_id"])
        page.locator('[name="password"]').fill(credential["password"])
        with page.expect_navigation(wait_until="domcontentloaded"):
            page.locator('form button[type="submit"]').click()
        if urlsplit(page.url).path != destination:
            raise RuntimeError(f"Login failed for {credential['user_id']}: {page.url}")
        self.ready(page)

    def save(self, page, viewport: str, slug: str, path: str, *, note: str = "") -> None:
        self.ready(page)
        filename = f"{viewport}__{slug}.png"
        page.screenshot(path=str(self.out / filename), full_page=True, animations="disabled")
        self.shots.append(
            {
                "page": slug,
                "viewport": viewport,
                "file": filename,
                "path": path,
                "note": note,
            }
        )
        print(f"SHOT {filename}", flush=True)

    def menu(self, page, viewport: str, role: str) -> None:
        path = "/team" if role == "team" else "/admin"
        self.goto(page, path)
        page.get_by_role("button", name="Menu", exact=True).click()
        try:
            page.locator("#mobileNavigation.show").wait_for(state="visible", timeout=2000)
        except PlaywrightTimeoutError:
            if not any(content is None for content in self.cdn.values()):
                raise RuntimeError(f"{role} mobile Menu did not open") from None
            note = (
                f"{role} mobile Menu could not open because Bootstrap CDN assets are unavailable."
            )
            self.note(note)
            self.save(page, viewport, f"{role}-menu-unavailable", path, note=note)
            return
        # Wait for Bootstrap's offcanvas transition to settle.
        page.wait_for_function(
            "!document.querySelector('#mobileNavigation').classList.contains('showing')"
        )
        self.save(page, viewport, f"{role}-menu-open", path)

    def report(self) -> None:
        self.out.mkdir(parents=True, exist_ok=True)
        (self.out / "capture.json").write_text(
            json.dumps(
                {
                    "base_url": self.base_url,
                    "viewports": VIEWPORTS,
                    "shots": self.shots,
                    "responses": self.responses,
                    "notes": self.notes,
                },
                indent=2,
            )
            + "\n"
        )
        groups: dict[str, dict] = {}
        for shot in self.shots:
            groups.setdefault(shot["page"], {})[shot["viewport"]] = shot
        rows = []
        for slug, shots in groups.items():
            cells = []
            for viewport in VIEWPORTS:
                shot = shots.get(viewport)
                if shot:
                    file = html.escape(shot["file"], quote=True)
                    note = html.escape(shot["note"])
                    cells.append(
                        f'<td><a href="{file}"><img src="{file}" loading="lazy" '
                        f'alt="{html.escape(slug)} {viewport}"></a><p>{note}</p></td>'
                    )
                else:
                    cells.append("<td>—</td>")
            rows.append(f"<tr><th>{html.escape(slug)}</th>{''.join(cells)}</tr>")
        notes = "".join(f"<li>{html.escape(note)}</li>" for note in self.notes)
        (self.out / "index.html").write_text(
            '<!doctype html><html lang="en"><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            "<title>UI preview screenshots</title><style>"
            "body{font-family:system-ui;margin:24px}table{border-collapse:collapse;width:100%}"
            "td,th{border:1px solid #bbb;padding:8px;vertical-align:top}"
            "td{width:29%}img{width:100%;height:auto}th{text-align:left}p{font-size:14px}"
            "</style><h1>UI preview screenshots</h1><p>Click an image for its full-page PNG. "
            'HTTP response details are in <a href="capture.json">capture.json</a>.</p>'
            f"<ul>{notes}</ul><table><thead><tr><th>Page</th>"
            "<th>Desktop · 1440 × 900</th><th>Tablet · 834 × 1112</th>"
            "<th>Mobile · 390 × 844</th></tr></thead><tbody>"
            + "".join(rows)
            + "</tbody></table></html>"
        )


def capture(browser, recorder: Capture, manifest: dict) -> None:
    teams = {team["user_id"]: team for team in manifest["teams"]}
    primary = teams[manifest["primary_team"]]
    single = teams[manifest["single_subtask_team"]]
    representatives = manifest["representatives"]
    b_evaluated = next(
        team["submissions"]["evaluated"][0] for team in teams.values() if team["subtasks"] == ["B"]
    )
    for viewport, dimensions in VIEWPORTS.items():
        for role in ("public", "team", "single-team", "organizer"):
            # A fresh cookie jar for each role and viewport prevents auth leakage.
            with browser.new_context(viewport=dimensions, device_scale_factor=1) as context:
                context.route("https://cdn.jsdelivr.net/**", recorder.cdn_route)
                page = context.new_page()
                page.set_default_timeout(15000)
                page.on("response", recorder.response)
                page.on(
                    "requestfailed",
                    lambda request: (
                        recorder.note(f"Request failed: {request.url} ({request.failure})")
                        if "cdn.jsdelivr.net" in request.url
                        else None
                    ),
                )
                if role == "public":
                    for path, slug in (("/", "public-home"), ("/login", "public-login")):
                        recorder.goto(page, path)
                        recorder.save(page, viewport, slug, path)
                    page.locator('[name="user_id"]').fill("unknown-demo-user")
                    page.locator('[name="password"]').fill("intentionally-wrong")
                    with page.expect_navigation(wait_until="domcontentloaded"):
                        page.locator('form button[type="submit"]').click()
                    page.get_by_text("Invalid user ID or password.", exact=True).wait_for()
                    recorder.save(page, viewport, "public-login-error", "/login?error=invalid")
                    continue
                if role == "single-team":
                    recorder.login(page, single, "/team")
                    recorder.save(page, viewport, "team-single-subtask", "/team")
                    continue
                if role == "team":
                    recorder.login(page, primary, "/team")
                    pages = [
                        ("/team", "team-dashboard"),
                        ("/team/submissions/A/new", "team-upload-a"),
                        ("/team/submissions/B/new", "team-upload-b"),
                        ("/account/password", "team-password"),
                    ]
                    for status, ids in primary["submissions"].items():
                        pages.append((f"/team/submissions/{ids[0]}", f"team-status-{status}"))
                else:
                    recorder.login(page, manifest["organizer"], "/admin")
                    pages = [
                        (path, slug)
                        for path, slug in (
                            ("/admin", "admin-dashboard"),
                            ("/admin/teams", "admin-teams"),
                            ("/admin/users", "admin-users"),
                            ("/admin/ground-truth", "admin-ground-truth"),
                            ("/admin/periods", "admin-periods"),
                            ("/admin/submissions", "admin-submissions"),
                            ("/admin/leaderboard", "admin-leaderboard"),
                            ("/admin/audit-events", "admin-audit-events"),
                        )
                    ]
                    for name, submission_id in (
                        ("evaluated", representatives["evaluated"]),
                        ("rejected", representatives["rejected"]),
                        ("evaluated-b", b_evaluated),
                        ("superseded", manifest["replacement"]["superseded"]),
                    ):
                        pages.append(
                            (f"/admin/submissions/{submission_id}", f"admin-detail-{name}")
                        )
                for path, slug in pages:
                    recorder.goto(page, path)
                    if slug.startswith("team-status-"):
                        expected = slug.removeprefix("team-status-")
                        actual = page.locator("#submissionStatus").get_attribute("data-status")
                        if actual != expected:
                            raise RuntimeError(f"Seeded status changed at {path}: {actual}")
                    recorder.save(page, viewport, slug, path)
                if role == "team":
                    recorder.goto(page, "/team/submissions/A/new")
                    page.locator('[name="submission_period"][value="late"]').check()
                    page.locator('[name="file"]').set_input_files(manifest["invalid_upload"])
                    with page.expect_response(
                        lambda response: (
                            response.request.method == "POST"
                            and urlsplit(response.url).path == "/team/submissions/A/new"
                        )
                    ) as upload:
                        page.locator("#uploadSubmit").click()
                    if upload.value.status >= 400:
                        raise RuntimeError(f"Invalid upload returned HTTP {upload.value.status}")
                    page.locator("#validationSummaryTitle").wait_for()
                    recorder.save(page, viewport, "team-upload-errors", "/team/submissions/A/new")
                if viewport == "mobile":
                    recorder.menu(page, viewport, role)
                recorder.healthy()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8765")
    parser.add_argument("--manifest", type=Path, default=REPO_ROOT / ".ui-preview/manifest.json")
    parser.add_argument("--label", default="current")
    parser.add_argument("--out", type=Path)
    parser.add_argument(
        "--cdn-cache",
        type=Path,
        help="Optional directory containing original bootstrap.min.css and bundle JS",
    )
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", args.label):
        parser.error("--label must be a simple directory name (letters, digits, dots, _ or -)")
    manifest_path = args.manifest.expanduser().resolve()
    manifest = json.loads(manifest_path.read_text())
    out = (args.out or manifest_path.parent / "shots" / args.label).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    recorder = Capture(args.base_url, out, args.cdn_cache or manifest_path.parent / "cdn-cache")
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            try:
                capture(browser, recorder, manifest)
            finally:
                browser.close()
    except Exception as exc:
        recorder.note(f"Capture failed: {str(exc).splitlines()[0]}")
        raise
    finally:
        # Partial reports are useful when a route fails; the process still exits nonzero.
        recorder.report()
    print(f"Saved {len(recorder.shots)} screenshots and contact sheet: {out / 'index.html'}")


if __name__ == "__main__":
    main()
