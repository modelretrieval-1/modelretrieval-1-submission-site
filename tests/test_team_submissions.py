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


def make_settings(tmp: str, *, max_upload_bytes: int = 10 * 1024 * 1024) -> Settings:
    root = Path(tmp)
    return Settings(
        app_name="Test Submission System",
        environment="test",
        database_path=root / "app.sqlite3",
        storage_root=root / "storage",
        secret_key="test-secret",
        max_upload_bytes=max_upload_bytes,
    )


def seed_accounts(settings: Settings, *, subtasks: set[str] | None = None):
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
            subtasks=subtasks or {"A"},
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


def valid_submission_content() -> bytes:
    return (
        b"q1 Q0 m1 1 2.0 run1\n"
        b"q1 Q0 m2 2 1.0 run1\n"
        b"q2 Q0 m2 1 2.0 run1\n"
        b"q2 Q0 m1 2 1.0 run1\n"
    )


def test_team_dashboard_links_to_submission_upload():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        _organizer, team = seed_accounts(settings)
        client = TestClient(create_app(settings))
        login(client, "team-001", team.password)

        response = client.get("/team")

        assert response.status_code == 200
        assert "/team/submissions/A/new" in response.text


def test_team_can_open_upload_page_for_eligible_subtask():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        _organizer, team = seed_accounts(settings)
        client = TestClient(create_app(settings))
        login(client, "team-001", team.password)

        response = client.get("/team/submissions/A/new")

        assert response.status_code == 200
        assert "Upload Subtask A Submission" in response.text


def test_team_cannot_open_upload_page_for_ineligible_subtask():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        _organizer, team = seed_accounts(settings)
        client = TestClient(create_app(settings))
        login(client, "team-001", team.password)

        response = client.get("/team/submissions/B/new", follow_redirects=False)

        assert response.status_code == 303
        assert response.headers["location"] == "/team"


def test_non_txt_submission_is_rejected_and_persisted():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        organizer, team = seed_accounts(settings)
        activate_subtask_a_ground_truth(settings, organizer.id)
        client = TestClient(create_app(settings))
        login(client, "team-001", team.password)

        response = client.post(
            "/team/submissions/A/new",
            files={"file": ("submission.csv", b"not trec", "text/csv")},
        )

        assert response.status_code == 200
        assert "Submission file must be a .txt file." in response.text

        with connect(settings.database_path) as connection:
            submission = connection.execute("SELECT status FROM submissions").fetchone()
            error = connection.execute("SELECT error_code FROM validation_errors").fetchone()

        assert submission["status"] == "rejected"
        assert error["error_code"] == "invalid_file_extension"


def test_oversized_submission_is_rejected_and_persisted():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp, max_upload_bytes=4)
        organizer, team = seed_accounts(settings)
        activate_subtask_a_ground_truth(settings, organizer.id)
        client = TestClient(create_app(settings))
        login(client, "team-001", team.password)

        response = client.post(
            "/team/submissions/A/new",
            files={"file": ("submission.txt", b"12345", "text/plain")},
        )

        assert response.status_code == 200
        assert "Submission file is larger than 4 bytes." in response.text

        with connect(settings.database_path) as connection:
            error = connection.execute("SELECT error_code FROM validation_errors").fetchone()

        assert error["error_code"] == "file_too_large"


def test_missing_active_ground_truth_is_rejected_and_persisted():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        _organizer, team = seed_accounts(settings)
        client = TestClient(create_app(settings))
        login(client, "team-001", team.password)

        response = client.post(
            "/team/submissions/A/new",
            files={"file": ("submission.txt", valid_submission_content(), "text/plain")},
        )

        assert response.status_code == 200
        assert "No active ground truth is configured for this subtask." in response.text

        with connect(settings.database_path) as connection:
            error = connection.execute("SELECT error_code FROM validation_errors").fetchone()

        assert error["error_code"] == "missing_active_ground_truth"


def test_invalid_trec_submission_is_rejected_and_persisted():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        organizer, team = seed_accounts(settings)
        activate_subtask_a_ground_truth(settings, organizer.id)
        client = TestClient(create_app(settings))
        login(client, "team-001", team.password)

        response = client.post(
            "/team/submissions/A/new",
            files={"file": ("submission.txt", b"q1 BAD m1 1 2.0 run1\n", "text/plain")},
        )

        assert response.status_code == 200
        assert "Field 2 must be Q0." in response.text

        with connect(settings.database_path) as connection:
            submission = connection.execute(
                "SELECT status, stored_file_path FROM submissions"
            ).fetchone()
            error = connection.execute("SELECT error_code FROM validation_errors").fetchone()

        assert submission["status"] == "rejected"
        assert Path(submission["stored_file_path"]).read_bytes() == b"q1 BAD m1 1 2.0 run1\n"
        assert error["error_code"] == "invalid_q0"


def test_valid_subtask_a_submission_is_evaluated_and_results_are_persisted():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        organizer, team = seed_accounts(settings)
        activate_subtask_a_ground_truth(settings, organizer.id)
        client = TestClient(create_app(settings))
        login(client, "team-001", team.password)

        response = client.post(
            "/team/submissions/A/new",
            files={"file": ("submission.txt", valid_submission_content(), "text/plain")},
        )

        assert response.status_code == 200
        assert "Submission accepted and evaluated." in response.text

        with connect(settings.database_path) as connection:
            submission = connection.execute(
                "SELECT status, ground_truth_version_id FROM submissions"
            ).fetchone()
            run = connection.execute(
                "SELECT run_id, line_count, query_count FROM runs"
            ).fetchone()
            metrics = connection.execute(
                """
                SELECT evaluation_results.metric_name, evaluation_results.metric_value
                FROM evaluation_results
                JOIN runs ON runs.id = evaluation_results.run_id
                WHERE runs.run_id = 'run1'
                ORDER BY evaluation_results.metric_name
                """
            ).fetchall()

        assert submission["status"] == "evaluated"
        assert submission["ground_truth_version_id"] is not None
        assert run["run_id"] == "run1"
        assert run["line_count"] == 4
        assert run["query_count"] == 2
        assert [metric["metric_name"] for metric in metrics] == ["ndcg@1", "ndcg@3", "ndcg@5"]
        assert [metric["metric_value"] for metric in metrics] == [1.0, 1.0, 1.0]


def test_valid_subtask_b_submission_is_evaluated_and_results_are_persisted():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        organizer, team = seed_accounts(settings, subtasks={"B"})
        activate_subtask_b_ground_truth(settings, organizer.id)
        client = TestClient(create_app(settings))
        login(client, "team-001", team.password)

        response = client.post(
            "/team/submissions/B/new",
            files={
                "file": (
                    "submission.txt",
                    (
                        b"image1 Q0 model-a 1 2.0 run1\n"
                        b"image1 Q0 model-b 2 1.0 run1\n"
                        b"image2 Q0 model-b 1 2.0 run1\n"
                        b"image2 Q0 model-a 2 1.0 run1\n"
                    ),
                    "text/plain",
                )
            },
        )

        assert response.status_code == 200
        assert "Submission accepted and evaluated." in response.text

        with connect(settings.database_path) as connection:
            submission = connection.execute("SELECT status FROM submissions").fetchone()
            metric = connection.execute(
                """
                SELECT metric_name, metric_value
                FROM evaluation_results
                """
            ).fetchone()

        assert submission["status"] == "evaluated"
        assert metric["metric_name"] == "mrr"
        assert metric["metric_value"] == 1.0
