import csv
import tempfile
from io import StringIO
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
        max_upload_bytes=50 * 1024 * 1024,
        evaluation_mode="eager",
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
            subtasks={"A", "B"},
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


def activate_subtask_b_ground_truth(settings: Settings, organizer_id: int) -> None:
    content = b"image_id,model_id\nimage1,model-a\nimage2,model-b\n"
    stored_file_path, file_sha256 = store_ground_truth_file(
        settings,
        subtask="B",
        filename="b-ground-truth.csv",
        content=content,
    )
    with connect(settings.database_path) as connection:
        version = create_ground_truth_version(
            connection,
            subtask="B",
            version_label="b-v1",
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


def valid_subtask_a_submission_content() -> bytes:
    return (
        b"q1 Q0 m1 1 2.0 run-a\n"
        b"q1 Q0 m2 2 1.0 run-a\n"
        b"q2 Q0 m2 1 2.0 run-a\n"
        b"q2 Q0 m1 2 1.0 run-a\n"
    )


def valid_subtask_b_submission_content() -> bytes:
    return (
        b"image1 Q0 model-a 1 2.0 run-b\n"
        b"image1 Q0 model-b 2 1.0 run-b\n"
        b"image2 Q0 model-b 1 2.0 run-b\n"
        b"image2 Q0 model-a 2 1.0 run-b\n"
    )


def seed_evaluated_submissions(client: TestClient, team_password: str) -> None:
    login(client, "team-001", team_password)
    subtask_a_response = client.post(
        "/team/submissions/A/new",
        data={"submission_period": "normal"},
        files={"file": ("a.txt", valid_subtask_a_submission_content(), "text/plain")},
    )
    subtask_b_response = client.post(
        "/team/submissions/B/new",
        data={"submission_period": "late"},
        files={"file": ("b.txt", valid_subtask_b_submission_content(), "text/plain")},
    )
    assert subtask_a_response.status_code == 200
    assert subtask_b_response.status_code == 200
    client.get("/logout")


def test_organizer_can_view_private_leaderboard_with_subtask_metrics():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        organizer, team = seed_accounts(settings)
        activate_subtask_a_ground_truth(settings, organizer.id)
        activate_subtask_b_ground_truth(settings, organizer.id)
        client = TestClient(create_app(settings))
        seed_evaluated_submissions(client, team.password)
        login(client, "admin", organizer.password)

        response = client.get("/admin/leaderboard")

        assert response.status_code == 200
        assert "Leaderboard" in response.text
        assert "Private organizer view of evaluated run-level metrics." in response.text
        assert "Clear filters" in response.text
        assert 'name="team_id"' in response.text
        assert "Showing 2 evaluated runs." in response.text
        assert "team-001" in response.text
        assert "run-a" in response.text
        assert "run-b" in response.text
        assert "nDCG@1" in response.text
        assert "nDCG@3" in response.text
        assert "nDCG@5" in response.text
        assert "MRR" in response.text
        assert "1.000000" in response.text
        assert 'id="leaderboardTable"' in response.text
        assert 'class="leaderboard-sort"' in response.text
        assert 'data-sort-type="number"' in response.text
        assert 'aria-sort="none"' in response.text


def test_organizer_can_filter_leaderboard_by_subtask_and_period():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        organizer, team = seed_accounts(settings)
        activate_subtask_a_ground_truth(settings, organizer.id)
        activate_subtask_b_ground_truth(settings, organizer.id)
        client = TestClient(create_app(settings))
        seed_evaluated_submissions(client, team.password)
        login(client, "admin", organizer.password)

        response = client.get("/admin/leaderboard?subtask=B&period=late")

        assert response.status_code == 200
        assert "Showing 1 evaluated run." in response.text
        assert "run-b" in response.text
        assert "run-a" not in response.text
        assert "late" in response.text


def test_organizer_can_filter_leaderboard_by_team():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        organizer, team = seed_accounts(settings)
        activate_subtask_a_ground_truth(settings, organizer.id)
        activate_subtask_b_ground_truth(settings, organizer.id)
        client = TestClient(create_app(settings))
        seed_evaluated_submissions(client, team.password)
        login(client, "admin", organizer.password)

        response = client.get("/admin/leaderboard?team_id=team-001")

        assert response.status_code == 200
        assert "Showing 2 evaluated runs." in response.text
        assert "team-001" in response.text
        assert "team_id=team-001" in response.text


def test_team_cannot_access_private_leaderboard():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        _organizer, team = seed_accounts(settings)
        client = TestClient(create_app(settings))
        login(client, "team-001", team.password)

        response = client.get("/admin/leaderboard", follow_redirects=False)

        assert response.status_code == 303
        assert response.headers["location"] == "/team"


def test_organizer_can_download_leaderboard_csv_with_all_metrics():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        organizer, team = seed_accounts(settings)
        activate_subtask_a_ground_truth(settings, organizer.id)
        activate_subtask_b_ground_truth(settings, organizer.id)
        client = TestClient(create_app(settings))
        seed_evaluated_submissions(client, team.password)
        login(client, "admin", organizer.password)

        response = client.get("/admin/leaderboard.csv")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")
        assert response.headers["content-disposition"] == 'attachment; filename="leaderboard.csv"'

        rows = list(csv.DictReader(StringIO(response.text)))

        assert rows[0]["team_id"] == "team-001"
        assert rows[0]["run_id"] == "run-a"
        assert rows[0]["ndcg@1"] == "1.000000"
        assert rows[0]["ndcg@3"] == "1.000000"
        assert rows[0]["ndcg@5"] == "1.000000"
        assert rows[0]["mrr"] == ""
        assert rows[1]["run_id"] == "run-b"
        assert rows[1]["mrr"] == "1.000000"


def test_leaderboard_csv_respects_subtask_and_period_filters():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        organizer, team = seed_accounts(settings)
        activate_subtask_a_ground_truth(settings, organizer.id)
        activate_subtask_b_ground_truth(settings, organizer.id)
        client = TestClient(create_app(settings))
        seed_evaluated_submissions(client, team.password)
        login(client, "admin", organizer.password)

        response = client.get("/admin/leaderboard.csv?subtask=B&period=late")

        assert response.status_code == 200
        rows = list(csv.DictReader(StringIO(response.text)))

        assert len(rows) == 1
        assert rows[0]["subtask"] == "B"
        assert rows[0]["period"] == "late"
        assert rows[0]["run_id"] == "run-b"
        assert rows[0]["mrr"] == "1.000000"


def test_team_cannot_download_leaderboard_csv():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        _organizer, team = seed_accounts(settings)
        client = TestClient(create_app(settings))
        login(client, "team-001", team.password)

        response = client.get("/admin/leaderboard.csv", follow_redirects=False)

        assert response.status_code == 303
        assert response.headers["location"] == "/team"
