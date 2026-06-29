import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from app.accounts import create_organizer, create_team
from app.config import Settings
from app.db import connect, initialize_database
from app.ground_truth import (
    activate_ground_truth_version,
    create_ground_truth_version,
    store_ground_truth_file,
)
from app.main import create_app


def make_settings(tmp: str) -> Settings:
    root = Path(tmp)
    return Settings(
        app_name="Test Submission System",
        environment="test",
        database_path=root / "app.sqlite3",
        storage_root=root / "storage",
        secret_key="test-secret",
        max_upload_bytes=10 * 1024 * 1024,
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


def activate_subtask_a_ground_truth(settings: Settings, organizer_id: int) -> None:
    content = b"task_id,model_id,relevance_score\nq1,m1,3\nq1,m2,0\nq2,m1,1\nq2,m2,2\n"
    stored_file_path, file_sha256 = store_ground_truth_file(
        settings,
        subtask="A",
        filename="a-ground-truth.csv",
        content=content,
    )
    with connect(settings.database_path) as connection:
        version = create_ground_truth_version(
            connection,
            subtask="A",
            version_label="a-v1",
            stored_file_path=stored_file_path,
            file_sha256=file_sha256,
            uploaded_by_organizer_id=organizer_id,
            validation_status="validated",
        )
        assert activate_ground_truth_version(connection, version.id)


def login(client: TestClient, user_id: str, password: str) -> None:
    response = client.post(
        "/login",
        data={"user_id": user_id, "password": password},
        follow_redirects=True,
    )
    assert response.status_code == 200


def valid_submission_content() -> bytes:
    return (
        b"q1 Q0 m1 1 2.0 run1\n"
        b"q1 Q0 m2 2 1.0 run1\n"
        b"q2 Q0 m2 1 2.0 run1\n"
        b"q2 Q0 m1 2 1.0 run1\n"
    )


def seed_submission_attempts(client: TestClient, team_password: str) -> None:
    login(client, "team-001", team_password)
    rejected_response = client.post(
        "/team/submissions/A/new",
        data={"submission_period": "normal"},
        files={"file": ("bad.txt", b"q1 BAD m1 1 2.0 run1\n", "text/plain")},
    )
    evaluated_response = client.post(
        "/team/submissions/A/new",
        data={"submission_period": "late"},
        files={"file": ("good.txt", valid_submission_content(), "text/plain")},
    )
    assert rejected_response.status_code == 200
    assert evaluated_response.status_code == 200
    client.get("/logout")


def test_organizer_can_view_submissions_table_and_filter_by_status():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        organizer, team = seed_accounts(settings)
        activate_subtask_a_ground_truth(settings, organizer.id)
        client = TestClient(create_app(settings))
        seed_submission_attempts(client, team.password)
        login(client, "admin", organizer.password)

        response = client.get("/admin/submissions")

        assert response.status_code == 200
        assert "Submissions" in response.text
        assert "team-001" in response.text
        assert "rejected" in response.text
        assert "evaluated" in response.text
        assert "normal" in response.text
        assert "late" in response.text
        assert "bad.txt" in response.text
        assert "good.txt" in response.text

        filtered = client.get("/admin/submissions?status=evaluated")

        assert filtered.status_code == 200
        assert "evaluated" in filtered.text
        assert "good.txt" in filtered.text
        assert "bad.txt" not in filtered.text


def test_organizer_can_filter_submissions_by_subtask_period_and_team():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        organizer, team = seed_accounts(settings)
        activate_subtask_a_ground_truth(settings, organizer.id)
        client = TestClient(create_app(settings))
        seed_submission_attempts(client, team.password)
        login(client, "admin", organizer.password)

        response = client.get("/admin/submissions?team_id=team-001&subtask=A&period=late")

        assert response.status_code == 200
        assert "good.txt" in response.text
        assert "bad.txt" not in response.text
        assert "late" in response.text


def test_organizer_can_view_rejected_submission_detail_with_validation_errors():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        organizer, team = seed_accounts(settings)
        activate_subtask_a_ground_truth(settings, organizer.id)
        client = TestClient(create_app(settings))
        seed_submission_attempts(client, team.password)
        login(client, "admin", organizer.password)

        with connect(settings.database_path) as connection:
            submission = connection.execute(
                "SELECT id FROM submissions WHERE status = 'rejected'"
            ).fetchone()

        response = client.get(f"/admin/submissions/{submission['id']}")

        assert response.status_code == 200
        assert "Submission" in response.text
        assert "bad.txt" in response.text
        assert "Validation Errors" in response.text
        assert "invalid_q0" in response.text
        assert "Field 2 must be Q0." in response.text
        assert "No metrics recorded." in response.text


def test_organizer_can_view_evaluated_submission_detail_with_runs_and_metrics():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        organizer, team = seed_accounts(settings)
        activate_subtask_a_ground_truth(settings, organizer.id)
        client = TestClient(create_app(settings))
        seed_submission_attempts(client, team.password)
        login(client, "admin", organizer.password)

        with connect(settings.database_path) as connection:
            submission = connection.execute(
                "SELECT id FROM submissions WHERE status = 'evaluated'"
            ).fetchone()

        response = client.get(f"/admin/submissions/{submission['id']}")

        assert response.status_code == 200
        assert "good.txt" in response.text
        assert "run1" in response.text
        assert "ndcg@1" in response.text
        assert "ndcg@3" in response.text
        assert "ndcg@5" in response.text
        assert "1.000000" in response.text
        assert "No validation errors recorded." in response.text


def test_team_cannot_access_organizer_submission_views():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        _organizer, team = seed_accounts(settings)
        client = TestClient(create_app(settings))
        login(client, "team-001", team.password)

        list_response = client.get("/admin/submissions", follow_redirects=False)
        detail_response = client.get("/admin/submissions/1", follow_redirects=False)

        assert list_response.status_code == 303
        assert list_response.headers["location"] == "/team"
        assert detail_response.status_code == 303
        assert detail_response.headers["location"] == "/team"
