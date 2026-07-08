import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from app.accounts import create_organizer, create_team
from app.config import Settings
from app.db import connect, initialize_database
from app.main import create_app


def make_settings(tmp: str) -> Settings:
    root = Path(tmp)
    return Settings(
        app_name="Test Submission System",
        environment="test",
        database_path=root / "app.sqlite3",
        storage_root=root / "storage",
        secret_key="test-secret",
        max_upload_bytes=50 * 1024 * 1024,
    )


def seed_accounts(settings: Settings):
    initialize_database(settings.database_path)
    with connect(settings.database_path) as connection:
        organizer = create_organizer(
            connection,
            username="admin",
            display_name="Admin User",
        )
        team = create_team(
            connection,
            team_id="team-001",
            display_name="Team 001",
            subtasks={"A"},
            created_by_organizer_id=organizer.id,
        )
    return organizer, team


def login(client: TestClient, user_id: str, password: str) -> None:
    response = client.post(
        "/login",
        data={"user_id": user_id, "password": password},
        follow_redirects=True,
    )
    assert response.status_code == 200


def test_organizer_shell_shows_admin_navigation_and_active_page():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        organizer, _team = seed_accounts(settings)
        client = TestClient(create_app(settings))
        login(client, "admin", organizer.password)

        response = client.get("/admin/periods")

        assert response.status_code == 200
        assert 'href="/admin">Dashboard</a>' in response.text
        assert 'href="/admin/teams">Teams</a>' in response.text
        assert 'href="/admin/users">Users</a>' in response.text
        assert 'href="/admin/ground-truth">Ground Truth</a>' in response.text
        assert 'href="/admin/periods">Periods</a>' in response.text
        assert 'href="/admin/submissions">Submissions</a>' in response.text
        assert 'href="/admin/leaderboard">Leaderboard</a>' in response.text
        assert 'app-nav-link active" href="/admin/periods"' in response.text


def test_authenticated_shell_includes_mobile_navigation_controls():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        organizer, _team = seed_accounts(settings)
        client = TestClient(create_app(settings))
        login(client, "admin", organizer.password)

        response = client.get("/admin")

        assert response.status_code == 200
        assert 'class="app-sidebar"' in response.text
        assert 'data-bs-toggle="offcanvas"' in response.text
        assert 'data-bs-target="#mobileNavigation"' in response.text
        assert 'class="offcanvas offcanvas-start app-mobile-nav"' in response.text
        assert 'aria-labelledby="mobileNavigationLabel"' in response.text
        assert 'class="app-topbar"' in response.text


def test_team_shell_hides_organizer_navigation():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        _organizer, team = seed_accounts(settings)
        client = TestClient(create_app(settings))
        login(client, "team-001", team.password)

        response = client.get("/team")

        assert response.status_code == 200
        assert 'href="/team">Dashboard</a>' in response.text
        assert 'href="/team/submissions/new">Upload</a>' in response.text
        assert 'href="/account/password">Password</a>' in response.text
        assert 'href="/admin/teams">Teams</a>' not in response.text
        assert 'href="/admin/users">Users</a>' not in response.text
        assert 'href="/admin/ground-truth">Ground Truth</a>' not in response.text
        assert 'href="/admin/leaderboard">Leaderboard</a>' not in response.text
        assert 'app-nav-link active" href="/team"' in response.text


def test_public_pages_remain_outside_authenticated_shell():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        seed_accounts(settings)
        client = TestClient(create_app(settings))

        response = client.get("/login")

        assert response.status_code == 200
        assert 'class="navbar app-navbar"' in response.text
        assert 'class="app-shell"' not in response.text
        assert 'id="mobileNavigation"' not in response.text


def test_team_upload_navigation_redirects_to_first_registered_subtask():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        _organizer, team = seed_accounts(settings)
        client = TestClient(create_app(settings))
        login(client, "team-001", team.password)

        response = client.get("/team/submissions/new", follow_redirects=False)

        assert response.status_code == 303
        assert response.headers["location"] == "/team/submissions/A/new"


def test_team_upload_page_marks_upload_navigation_active():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        _organizer, team = seed_accounts(settings)
        client = TestClient(create_app(settings))
        login(client, "team-001", team.password)

        response = client.get("/team/submissions/A/new")

        assert response.status_code == 200
        assert 'app-nav-link active" href="/team/submissions/new"' in response.text


def test_key_workspace_tables_use_responsive_wrappers():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        organizer, _team = seed_accounts(settings)
        client = TestClient(create_app(settings))
        login(client, "admin", organizer.password)

        paths = (
            "/admin",
            "/admin/teams",
            "/admin/users",
            "/admin/ground-truth",
            "/admin/periods",
            "/admin/submissions",
            "/admin/leaderboard",
        )

        for path in paths:
            response = client.get(path)
            assert response.status_code == 200
            if "<table" in response.text:
                assert 'class="table-wrap"' in response.text


def test_key_forms_keep_visible_labels():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        organizer, team = seed_accounts(settings)
        client = TestClient(create_app(settings))

        login(client, "admin", organizer.password)
        admin_form_pages = (
            "/admin/teams",
            "/admin/users",
            "/admin/ground-truth",
            "/admin/periods",
            "/admin/submissions",
            "/admin/leaderboard",
            "/account/password",
        )
        for path in admin_form_pages:
            response = client.get(path)
            assert response.status_code == 200
            if "<form" in response.text:
                assert 'class="form-label"' in response.text

        client.get("/logout")
        login(client, "team-001", team.password)
        team_form_pages = ("/team/submissions/A/new", "/account/password")
        for path in team_form_pages:
            response = client.get(path)
            assert response.status_code == 200
            assert 'class="form-label"' in response.text


def test_admin_dashboard_links_to_submission_bundle_route():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        organizer, _team = seed_accounts(settings)
        client = TestClient(create_app(settings))
        login(client, "admin", organizer.password)

        response = client.get("/admin")

        assert response.status_code == 200
        assert 'href="/admin/submissions/bundle.zip"' in response.text
        assert 'href="/admin/submissions/bundle"' not in response.text
