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
from app.processing import recover_orphaned_submissions, run_pending_evaluations
from app.submissions import mark_submission_status


def make_settings(tmp: str, *, evaluation_mode: str = "worker") -> Settings:
    root = Path(tmp)
    return Settings(
        app_name="Test Submission System",
        environment="test",
        database_path=root / "app.sqlite3",
        storage_root=root / "storage",
        secret_key="test-secret",
        max_upload_bytes=10 * 1024 * 1024,
        evaluation_mode=evaluation_mode,
    )


def seed_accounts(settings: Settings):
    initialize_database(settings.database_path)
    with connect(settings.database_path) as connection:
        organizer = create_organizer(connection, username="admin", display_name="Admin User")
        team = create_team(
            connection,
            team_id="team-001",
            display_name="Team 001",
            subtasks={"A"},
            created_by_organizer_id=organizer.id,
        )
        other_team = create_team(
            connection,
            team_id="team-002",
            display_name="Team 002",
            subtasks={"A"},
            created_by_organizer_id=organizer.id,
        )
    return organizer, team, other_team


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


def upload_valid(client: TestClient, team_id: str, password: str) -> str:
    login(client, team_id, password)
    response = client.post(
        "/team/submissions/A/new",
        data={"submission_period": "normal"},
        files={"file": ("submission.txt", valid_submission_content(), "text/plain")},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/team"
    return response.headers["location"]


def test_worker_mode_leaves_submission_queued_until_drained():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp, evaluation_mode="worker")
        organizer, team, _other = seed_accounts(settings)
        activate_subtask_a_ground_truth(settings, organizer.id)
        client = TestClient(create_app(settings))

        upload_valid(client, "team-001", team.password)

        # Validation passed synchronously, but scoring is deferred: the slot is
        # reserved as queued and no worker is running in this test.
        with connect(settings.database_path) as connection:
            submission = connection.execute("SELECT id, status FROM submissions").fetchone()
            status = submission["status"]
            status_location = f"/team/submissions/{submission['id']}"
        assert status == "queued"

        status_page = client.get(status_location)
        assert status_page.status_code == 200
        assert "Queued for evaluation…" in status_page.text
        assert "Submission accepted and evaluated." not in status_page.text

        queued_json = client.get(f"{status_location}/status")
        assert queued_json.status_code == 200
        assert queued_json.json()["status"] == "queued"

        # Draining the queue evaluates the submission to a terminal state.
        processed = run_pending_evaluations(settings)
        assert processed == 1

        evaluated_json = client.get(f"{status_location}/status")
        assert evaluated_json.json()["status"] == "evaluated"

        evaluated_page = client.get(status_location)
        assert "Submission accepted and evaluated." in evaluated_page.text
        assert "nDCG@5" in evaluated_page.text
        assert "1.0000" in evaluated_page.text

        with connect(settings.database_path) as connection:
            metric_count = connection.execute(
                "SELECT COUNT(*) FROM evaluation_results"
            ).fetchone()[0]
        assert metric_count == 3


def test_recovery_requeues_interrupted_processing_submissions():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp, evaluation_mode="worker")
        organizer, team, _other = seed_accounts(settings)
        activate_subtask_a_ground_truth(settings, organizer.id)
        client = TestClient(create_app(settings))

        upload_valid(client, "team-001", team.password)

        with connect(settings.database_path) as connection:
            submission_id = connection.execute("SELECT id FROM submissions").fetchone()["id"]
            # Simulate a worker that claimed the row and then crashed.
            mark_submission_status(connection, submission_id=submission_id, status="processing")

        requeued = recover_orphaned_submissions(settings)
        assert requeued == 1

        with connect(settings.database_path) as connection:
            status = connection.execute(
                "SELECT status FROM submissions WHERE id = ?", (submission_id,)
            ).fetchone()["status"]
        assert status == "queued"

        assert run_pending_evaluations(settings) == 1
        with connect(settings.database_path) as connection:
            status = connection.execute(
                "SELECT status FROM submissions WHERE id = ?", (submission_id,)
            ).fetchone()["status"]
        assert status == "evaluated"


def test_status_page_and_endpoint_reject_other_team():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp, evaluation_mode="eager")
        organizer, team, other_team = seed_accounts(settings)
        activate_subtask_a_ground_truth(settings, organizer.id)
        client = TestClient(create_app(settings))

        upload_valid(client, "team-001", team.password)

        with connect(settings.database_path) as connection:
            submission_id = connection.execute("SELECT id FROM submissions").fetchone()["id"]
        status_location = f"/team/submissions/{submission_id}"

        client.get("/logout")
        login(client, "team-002", other_team.password)

        page = client.get(status_location, follow_redirects=False)
        assert page.status_code == 303
        assert page.headers["location"] == "/team"

        status_json = client.get(f"{status_location}/status")
        assert status_json.status_code == 404
