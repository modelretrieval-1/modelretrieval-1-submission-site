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


def set_periods(
    settings: Settings,
    *,
    normal_deadline: str,
    late_deadline: str,
    normal_override: bool = False,
    late_override: bool = False,
) -> None:
    with connect(settings.database_path) as connection:
        connection.execute(
            """
            UPDATE submission_periods
            SET deadline_at_jst = ?, is_open_override = ?
            WHERE name = 'normal'
            """,
            (normal_deadline, int(normal_override)),
        )
        connection.execute(
            """
            UPDATE submission_periods
            SET deadline_at_jst = ?, is_open_override = ?
            WHERE name = 'late'
            """,
            (late_deadline, int(late_override)),
        )
        connection.commit()


def test_team_dashboard_links_to_submission_upload():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        _organizer, team = seed_accounts(settings)
        client = TestClient(create_app(settings))
        login(client, "team-001", team.password)

        response = client.get("/team")

        assert response.status_code == 200
        assert "/team/submissions/A/new" in response.text


def test_team_dashboard_shows_closed_submission_slots_without_upload_actions():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        _organizer, team = seed_accounts(settings)
        set_periods(
            settings,
            normal_deadline="2026-01-01 00:00:00",
            late_deadline="2026-01-02 00:00:00",
        )
        client = TestClient(create_app(settings))
        login(client, "team-001", team.password)

        response = client.get("/team")

        assert response.status_code == 200
        assert "Available submissions" in response.text
        assert '<strong class="stat-value">0</strong>' in response.text
        assert "closed" in response.text
        assert 'href="/team/submissions/A/new">Upload</a>' not in response.text
        assert 'href="/team/submissions/new">Upload submission</a>' not in response.text


def test_team_dashboard_marks_successful_period_as_submitted():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        organizer, team = seed_accounts(settings)
        activate_subtask_a_ground_truth(settings, organizer.id)
        client = TestClient(create_app(settings))
        login(client, "team-001", team.password)

        upload_response = client.post(
            "/team/submissions/A/new",
            data={"submission_period": "normal"},
            files={"file": ("submission.txt", valid_submission_content(), "text/plain")},
        )
        assert upload_response.status_code == 200

        response = client.get("/team")

        assert response.status_code == 200
        assert "submitted" in response.text
        assert '<strong class="stat-value">1</strong>' in response.text
        assert 'href="/team/submissions/A/new">Upload</a>' in response.text


def test_team_can_open_upload_page_for_eligible_subtask():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        _organizer, team = seed_accounts(settings)
        client = TestClient(create_app(settings))
        login(client, "team-001", team.password)

        response = client.get("/team/submissions/A/new")

        assert response.status_code == 200
        assert "Upload Subtask A Submission" in response.text
        assert "Submission period" in response.text
        assert 'value="normal"' in response.text
        assert 'value="late"' in response.text


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
            data={"submission_period": "normal"},
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
            data={"submission_period": "normal"},
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
            data={"submission_period": "normal"},
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
            data={"submission_period": "normal"},
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
            data={"submission_period": "normal"},
            files={"file": ("submission.txt", valid_submission_content(), "text/plain")},
        )

        assert response.status_code == 200
        assert "Submission accepted and evaluated." in response.text
        assert "ndcg@1" in response.text
        assert "ndcg@3" in response.text
        assert "ndcg@5" in response.text
        assert "1.000000" in response.text

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

        dashboard = client.get("/team")

        assert dashboard.status_code == 200
        assert "Latest Submissions" in dashboard.text
        assert "Subtask A" in dashboard.text
        assert "evaluated" in dashboard.text
        assert "run1 ndcg@5" in dashboard.text


def test_valid_subtask_b_submission_is_evaluated_and_results_are_persisted():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        organizer, team = seed_accounts(settings, subtasks={"B"})
        activate_subtask_b_ground_truth(settings, organizer.id)
        client = TestClient(create_app(settings))
        login(client, "team-001", team.password)

        response = client.post(
            "/team/submissions/B/new",
            data={"submission_period": "normal"},
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
        assert "mrr" in response.text
        assert "1.000000" in response.text

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

        dashboard = client.get("/team")

        assert dashboard.status_code == 200
        assert "Subtask B" in dashboard.text
        assert "run1 mrr" in dashboard.text


def test_rejected_upload_can_be_followed_by_valid_upload():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        organizer, team = seed_accounts(settings)
        activate_subtask_a_ground_truth(settings, organizer.id)
        client = TestClient(create_app(settings))
        login(client, "team-001", team.password)

        rejected_response = client.post(
            "/team/submissions/A/new",
            data={"submission_period": "normal"},
            files={"file": ("submission.txt", b"q1 BAD m1 1 2.0 run1\n", "text/plain")},
        )
        valid_response = client.post(
            "/team/submissions/A/new",
            data={"submission_period": "normal"},
            files={"file": ("submission.txt", valid_submission_content(), "text/plain")},
        )

        assert rejected_response.status_code == 200
        assert "Submission rejected." in rejected_response.text
        assert valid_response.status_code == 200
        assert "Submission accepted and evaluated." in valid_response.text

        with connect(settings.database_path) as connection:
            statuses = [
                row["status"]
                for row in connection.execute(
                    "SELECT status FROM submissions ORDER BY id"
                ).fetchall()
            ]

        assert statuses == ["rejected", "evaluated"]


def test_second_successful_upload_for_same_subtask_period_shows_friendly_error():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        organizer, team = seed_accounts(settings)
        activate_subtask_a_ground_truth(settings, organizer.id)
        client = TestClient(create_app(settings))
        login(client, "team-001", team.password)

        first_response = client.post(
            "/team/submissions/A/new",
            data={"submission_period": "normal"},
            files={"file": ("submission.txt", valid_submission_content(), "text/plain")},
        )
        second_response = client.post(
            "/team/submissions/A/new",
            data={"submission_period": "normal"},
            files={"file": ("submission.txt", valid_submission_content(), "text/plain")},
        )

        assert first_response.status_code == 200
        assert "Submission accepted and evaluated." in first_response.text
        assert second_response.status_code == 200
        assert "A successful submission already exists for this subtask and period." in (
            second_response.text
        )

        with connect(settings.database_path) as connection:
            statuses = [
                row["status"]
                for row in connection.execute(
                    "SELECT status FROM submissions ORDER BY id"
                ).fetchall()
            ]
            metric_count = connection.execute(
                "SELECT COUNT(*) FROM evaluation_results"
            ).fetchone()[0]

        assert statuses == ["evaluated", "rejected"]
        assert metric_count == 3


def test_team_can_submit_to_selected_late_period_when_late_is_open():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        organizer, team = seed_accounts(settings)
        activate_subtask_a_ground_truth(settings, organizer.id)
        client = TestClient(create_app(settings))
        login(client, "team-001", team.password)

        response = client.post(
            "/team/submissions/A/new",
            data={"submission_period": "late"},
            files={"file": ("submission.txt", valid_submission_content(), "text/plain")},
        )

        assert response.status_code == 200
        assert "Submission accepted and evaluated." in response.text

        with connect(settings.database_path) as connection:
            period = connection.execute(
                """
                SELECT submission_periods.name
                FROM submissions
                JOIN submission_periods ON submission_periods.id = submissions.submission_period_id
                """
            ).fetchone()

        assert period["name"] == "late"


def test_selecting_closed_normal_is_rejected_even_when_late_is_open():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        organizer, team = seed_accounts(settings)
        activate_subtask_a_ground_truth(settings, organizer.id)
        set_periods(
            settings,
            normal_deadline="2026-01-01 00:00:00",
            late_deadline="2099-01-01 00:00:00",
        )
        client = TestClient(create_app(settings))
        login(client, "team-001", team.password)

        response = client.post(
            "/team/submissions/A/new",
            data={"submission_period": "normal"},
            files={"file": ("submission.txt", valid_submission_content(), "text/plain")},
        )

        assert response.status_code == 200
        assert "The normal submission period is closed." in response.text

        with connect(settings.database_path) as connection:
            submission_count = connection.execute("SELECT COUNT(*) FROM submissions").fetchone()[0]

        assert submission_count == 0


def test_selecting_closed_late_is_rejected_even_when_normal_is_open():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        organizer, team = seed_accounts(settings)
        activate_subtask_a_ground_truth(settings, organizer.id)
        set_periods(
            settings,
            normal_deadline="2099-01-01 00:00:00",
            late_deadline="2026-01-02 00:00:00",
        )
        client = TestClient(create_app(settings))
        login(client, "team-001", team.password)

        response = client.post(
            "/team/submissions/A/new",
            data={"submission_period": "late"},
            files={"file": ("submission.txt", valid_submission_content(), "text/plain")},
        )

        assert response.status_code == 200
        assert "The late submission period is closed." in response.text

        with connect(settings.database_path) as connection:
            submission_count = connection.execute("SELECT COUNT(*) FROM submissions").fetchone()[0]

        assert submission_count == 0


def test_missing_submission_period_is_rejected_without_storing_submission():
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
        assert "Choose a submission period." in response.text

        with connect(settings.database_path) as connection:
            submission_count = connection.execute("SELECT COUNT(*) FROM submissions").fetchone()[0]

        assert submission_count == 0


def test_invalid_submission_period_is_rejected_without_storing_submission():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        organizer, team = seed_accounts(settings)
        activate_subtask_a_ground_truth(settings, organizer.id)
        client = TestClient(create_app(settings))
        login(client, "team-001", team.password)

        response = client.post(
            "/team/submissions/A/new",
            data={"submission_period": "final"},
            files={"file": ("submission.txt", valid_submission_content(), "text/plain")},
        )

        assert response.status_code == 200
        assert "Choose normal or late submission." in response.text

        with connect(settings.database_path) as connection:
            submission_count = connection.execute("SELECT COUNT(*) FROM submissions").fetchone()[0]

        assert submission_count == 0


def test_when_both_periods_are_reopened_selected_period_is_used():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        organizer, team = seed_accounts(settings)
        activate_subtask_a_ground_truth(settings, organizer.id)
        set_periods(
            settings,
            normal_deadline="2026-01-01 00:00:00",
            late_deadline="2026-01-02 00:00:00",
            normal_override=True,
            late_override=True,
        )
        client = TestClient(create_app(settings))
        login(client, "team-001", team.password)

        response = client.post(
            "/team/submissions/A/new",
            data={"submission_period": "late"},
            files={"file": ("submission.txt", valid_submission_content(), "text/plain")},
        )

        assert response.status_code == 200
        assert "Submission accepted and evaluated." in response.text

        with connect(settings.database_path) as connection:
            period = connection.execute(
                """
                SELECT submission_periods.name
                FROM submissions
                JOIN submission_periods ON submission_periods.id = submissions.submission_period_id
                """
            ).fetchone()

        assert period["name"] == "late"
