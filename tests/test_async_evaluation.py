import sqlite3
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import processing
from app.accounts import create_organizer, create_team
from app.audit import record_audit_event
from app.config import Settings
from app.db import connect, initialize_database
from app.evaluation import list_leaderboard_rows
from app.ground_truth import (
    activate_ground_truth_version,
    create_ground_truth_version,
    store_ground_truth_file,
)
from app.main import create_app
from app.processing import recover_orphaned_submissions, run_pending_evaluations
from app.routes import team as team_routes
from app.submissions import claim_next_queued_submission, mark_submission_status


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
        # Keep upload tests independent of the real competition deadlines.
        connection.execute("UPDATE submission_periods SET deadline_at_jst = '2099-12-31 23:59:00'")
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


def test_worker_mode_updates_summary_through_evaluation():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp, evaluation_mode="worker")
        organizer, team, _other = seed_accounts(settings)
        activate_subtask_a_ground_truth(settings, organizer.id)
        client = TestClient(create_app(settings))

        upload_valid(client, "team-001", team.password)

        # Validation passed synchronously, but scoring is deferred: the slot is
        # reserved as queued and no worker is running in this test.
        with connect(settings.database_path) as connection:
            submission = connection.execute(
                "SELECT id, status, validation_summary FROM submissions"
            ).fetchone()
            status = submission["status"]
            status_location = f"/team/submissions/{submission['id']}"
        assert status == "queued"
        assert submission["validation_summary"] == "Queued for evaluation."

        status_page = client.get(status_location)
        assert status_page.status_code == 200
        assert "Queued for evaluation…" in status_page.text
        assert "Submission accepted and evaluated." not in status_page.text

        queued_json = client.get(f"{status_location}/status")
        assert queued_json.status_code == 200
        assert queued_json.json()["status"] == "queued"

        with connect(settings.database_path) as connection:
            assert claim_next_queued_submission(connection) == submission["id"]
        with connect(settings.database_path) as connection:
            claimed = connection.execute(
                "SELECT status, validation_summary FROM submissions"
            ).fetchone()
            assert tuple(claimed) == ("processing", "Evaluating.")
            assert claim_next_queued_submission(connection) is None

        processing.process_submission(settings, submission["id"])
        assert run_pending_evaluations(settings) == 0

        evaluated_json = client.get(f"{status_location}/status")
        assert evaluated_json.json()["status"] == "evaluated"

        evaluated_page = client.get(status_location)
        assert "Submission accepted and evaluated." in evaluated_page.text
        assert "nDCG@5" in evaluated_page.text
        assert "1.0000" in evaluated_page.text

        with connect(settings.database_path) as connection:
            evaluated = connection.execute(
                "SELECT status, validation_summary FROM submissions"
            ).fetchone()
            assert tuple(evaluated) == ("evaluated", "Evaluated.")
            metric_count = connection.execute(
                "SELECT COUNT(*) FROM evaluation_results"
            ).fetchone()[0]
        assert metric_count == 3


@pytest.mark.parametrize("evaluation_mode", ["worker", "eager"])
def test_upload_only_queues_after_runs_and_activation(monkeypatch, evaluation_mode):
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp, evaluation_mode=evaluation_mode)
        organizer, team, _other = seed_accounts(settings)
        activate_subtask_a_ground_truth(settings, organizer.id)
        client = TestClient(create_app(settings))
        persist_runs = team_routes.persist_submission_runs
        mark_status = team_routes.mark_submission_status
        stages = []

        def checked_persist_runs(connection, *, submission_id, parsed):
            with connect(settings.database_path) as observer:
                row = observer.execute(
                    "SELECT status, is_current FROM submissions WHERE id = ?", (submission_id,)
                ).fetchone()
                assert (row["status"], row["is_current"]) == ("accepted", 0)
                assert observer.execute("SELECT COUNT(*) FROM runs").fetchone()[0] == 0
                assert claim_next_queued_submission(observer) is None
            stages.append("persist_runs")
            persist_runs(connection, submission_id=submission_id, parsed=parsed)

        def checked_mark_status(connection, *, submission_id, status, validation_summary=None):
            with connect(settings.database_path) as observer:
                row = observer.execute(
                    "SELECT status, is_current FROM submissions WHERE id = ?", (submission_id,)
                ).fetchone()
                assert (row["status"], row["is_current"]) == ("accepted", 1)
                assert observer.execute("SELECT run_id FROM runs").fetchone()[0] == "run1"
                assert claim_next_queued_submission(observer) is None
            assert status == "queued"
            stages.append("queue")
            mark_status(
                connection,
                submission_id=submission_id,
                status=status,
                validation_summary=validation_summary,
            )

        monkeypatch.setattr(team_routes, "persist_submission_runs", checked_persist_runs)
        monkeypatch.setattr(team_routes, "mark_submission_status", checked_mark_status)

        upload_valid(client, "team-001", team.password)

        assert stages == ["persist_runs", "queue"]
        with connect(settings.database_path) as connection:
            row = connection.execute("SELECT status, is_current FROM submissions").fetchone()
            assert row["status"] == ("queued" if evaluation_mode == "worker" else "evaluated")
            assert row["is_current"] == 1
            assert connection.execute("SELECT COUNT(*) FROM runs").fetchone()[0] == 1


@pytest.mark.parametrize(
    "stage", ["parse_trec_eval", "evaluate_submission", "evaluate_submission_query_metrics"]
)
def test_processing_allows_other_writers_during_parsing_and_scoring(monkeypatch, stage):
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        organizer, team, _other = seed_accounts(settings)
        activate_subtask_a_ground_truth(settings, organizer.id)
        client = TestClient(create_app(settings))
        upload_valid(client, "team-001", team.password)
        original = getattr(processing, stage)
        writes = []

        def checked_stage(*args, **kwargs):
            # Use SQLite directly so the app's longer timeout cannot mask a lock.
            with sqlite3.connect(settings.database_path, timeout=0.1) as writer:
                assert writer.execute(
                    "SELECT COUNT(*) FROM audit_events "
                    "WHERE event_type = 'submission_evaluation_started'"
                ).fetchone()[0] == 1
                assert writer.execute(
                    "SELECT status, validation_summary FROM submissions"
                ).fetchone() == ("processing", "Evaluating.")
                record_audit_event(
                    writer, actor_type="system", actor_id=None, event_type="concurrent_write"
                )
            writes.append(stage)
            return original(*args, **kwargs)

        monkeypatch.setattr(processing, stage, checked_stage)

        assert run_pending_evaluations(settings) == 1

        assert writes == [stage]
        with connect(settings.database_path) as connection:
            assert connection.execute("SELECT status FROM submissions").fetchone()[0] == "evaluated"
            assert connection.execute(
                "SELECT COUNT(*) FROM audit_events WHERE event_type = 'concurrent_write'"
            ).fetchone()[0] == 1


@pytest.mark.parametrize("outcome", ["evaluated", "scoring_failure", "ground_truth_unavailable"])
def test_processing_commits_terminal_audit_before_context_exit(monkeypatch, outcome):
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        organizer, team, _other = seed_accounts(settings)
        activate_subtask_a_ground_truth(settings, organizer.id)
        client = TestClient(create_app(settings))
        upload_valid(client, "team-001", team.password)
        with connect(settings.database_path) as connection:
            submission_id = connection.execute("SELECT id FROM submissions").fetchone()[0]

        if outcome == "scoring_failure":
            def fail_scoring(*args, **kwargs):
                raise RuntimeError("Scoring failed")

            monkeypatch.setattr(processing, "evaluate_submission", fail_scoring)
        elif outcome == "ground_truth_unavailable":
            monkeypatch.setattr(processing, "get_ground_truth_version", lambda *args: None)

        exits = []

        class CheckedConnection(sqlite3.Connection):
            def __exit__(self, *args):
                assert not self.in_transaction
                with connect(settings.database_path) as observer:
                    row = observer.execute(
                        "SELECT status, validation_summary FROM submissions"
                    ).fetchone()
                    status = row["status"]
                    expected = "evaluated" if outcome == "evaluated" else "evaluation_failed"
                    assert status == expected
                    summaries = {
                        "evaluated": "Evaluated.",
                        "scoring_failure": "Evaluation failed: Scoring failed",
                        "ground_truth_unavailable": (
                            "Evaluation failed: ground truth version is unavailable."
                        ),
                    }
                    assert row["validation_summary"] == summaries[outcome]
                    assert observer.execute(
                        "SELECT event_type FROM audit_events ORDER BY id DESC LIMIT 1"
                    ).fetchone()[0] == f"submission_{status}"
                exits.append(outcome)
                return super().__exit__(*args)

        def checked_connect(database_path):
            connection = sqlite3.connect(database_path, factory=CheckedConnection)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            return connection

        monkeypatch.setattr(processing, "connect", checked_connect)
        processing.process_submission(settings, submission_id)
        assert exits == [outcome]


def test_accepted_submission_remains_pending_and_has_no_leaderboard_scores():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        organizer, team, _other = seed_accounts(settings)
        activate_subtask_a_ground_truth(settings, organizer.id)
        client = TestClient(create_app(settings))
        upload_valid(client, "team-001", team.password)

        with connect(settings.database_path) as connection:
            submission_id = connection.execute("SELECT id FROM submissions").fetchone()[0]
            mark_submission_status(connection, submission_id=submission_id, status="accepted")
            assert list_leaderboard_rows(connection) == ()

        page = client.get(f"/team/submissions/{submission_id}")
        assert page.status_code == 200
        assert 'data-terminal="false"' in page.text
        assert 'data.status !== "accepted"' in page.text
        assert "Submission accepted and evaluated." not in page.text
        status_json = client.get(f"/team/submissions/{submission_id}/status")
        assert status_json.json()["status"] == "accepted"
        dashboard = client.get("/team")
        assert dashboard.status_code == 200
        assert "accepted" in dashboard.text
        assert "No scores yet" in dashboard.text


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
            assert claim_next_queued_submission(connection) == submission_id

        requeued = recover_orphaned_submissions(settings)
        assert requeued == 1

        with connect(settings.database_path) as connection:
            row = connection.execute(
                "SELECT status, validation_summary FROM submissions WHERE id = ?", (submission_id,)
            ).fetchone()
        assert tuple(row) == ("queued", "Queued for evaluation.")
        assert recover_orphaned_submissions(settings) == 0

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
