import hashlib
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from app.accounts import create_organizer, create_team
from app.config import Settings
from app.db import connect, initialize_database
from app.ground_truth import get_active_ground_truth_requirements
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


def login(client: TestClient, user_id: str, password: str) -> None:
    response = client.post(
        "/login",
        data={"user_id": user_id, "password": password},
        follow_redirects=True,
    )
    assert response.status_code == 200


def test_organizer_can_view_ground_truth_page():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        organizer, _team = seed_accounts(settings)
        client = TestClient(create_app(settings))
        login(client, "admin", organizer.password)

        response = client.get("/admin/ground-truth")

        assert response.status_code == 200
        assert "Ground Truth" in response.text
        assert (
            "Upload, validate, activate, and audit protected evaluation ground-truth versions."
            in response.text
        )
        assert "Upload Version" in response.text
        assert "Version History" in response.text
        assert "Showing 0 ground-truth versions." in response.text


def test_team_cannot_view_ground_truth_page():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        _organizer, team = seed_accounts(settings)
        client = TestClient(create_app(settings))
        login(client, "team-001", team.password)

        response = client.get("/admin/ground-truth", follow_redirects=False)

        assert response.status_code == 303
        assert response.headers["location"] == "/team"


def test_organizer_can_upload_subtask_a_ground_truth():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        organizer, _team = seed_accounts(settings)
        client = TestClient(create_app(settings))
        login(client, "admin", organizer.password)
        content = b"task_id,model_id,relevance_score\n1,1,3\n"

        response = client.post(
            "/admin/ground-truth",
            data={
                "subtask": "A",
                "version_label": "a-v1",
                "notes": "Subtask A test ground truth",
            },
            files={"file": ("a-ground-truth.csv", content, "text/csv")},
        )

        assert response.status_code == 200
        assert "Uploaded ground truth for Subtask A." in response.text
        assert "a-v1" in response.text

        with connect(settings.database_path) as connection:
            row = connection.execute(
                """
                SELECT subtask, version_label, stored_file_path, file_sha256, validation_status
                FROM ground_truth_versions
                WHERE version_label = ?
                """,
                ("a-v1",),
            ).fetchone()

        assert row["subtask"] == "A"
        assert row["file_sha256"] == hashlib.sha256(content).hexdigest()
        assert row["validation_status"] == "validated"
        assert Path(row["stored_file_path"]).read_bytes() == content
        assert settings.ground_truth_dir in Path(row["stored_file_path"]).parents


def test_organizer_can_upload_subtask_b_ground_truth():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        organizer, _team = seed_accounts(settings)
        client = TestClient(create_app(settings))
        login(client, "admin", organizer.password)
        content = b"image_id,model_id\n1,7\n"

        response = client.post(
            "/admin/ground-truth",
            data={
                "subtask": "B",
                "version_label": "b-v1",
                "notes": "",
            },
            files={"file": ("b-ground-truth.csv", content, "text/csv")},
        )

        assert response.status_code == 200
        assert "Uploaded ground truth for Subtask B." in response.text
        assert "b-v1" in response.text

        with connect(settings.database_path) as connection:
            row = connection.execute(
                """
                SELECT subtask, stored_file_path
                FROM ground_truth_versions
                WHERE version_label = ?
                """,
                ("b-v1",),
            ).fetchone()

        assert row["subtask"] == "B"
        assert Path(row["stored_file_path"]).read_bytes() == content


def test_empty_ground_truth_file_is_rejected():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        organizer, _team = seed_accounts(settings)
        client = TestClient(create_app(settings))
        login(client, "admin", organizer.password)

        response = client.post(
            "/admin/ground-truth",
            data={"subtask": "A", "version_label": "empty", "notes": ""},
            files={"file": ("empty.csv", b"", "text/csv")},
        )

        assert response.status_code == 200
        assert "Ground-truth file is empty." in response.text

        with connect(settings.database_path) as connection:
            count = connection.execute("SELECT COUNT(*) FROM ground_truth_versions").fetchone()[0]

        assert count == 0


def test_subtask_a_ground_truth_missing_relevance_score_is_rejected():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        organizer, _team = seed_accounts(settings)
        client = TestClient(create_app(settings))
        login(client, "admin", organizer.password)

        response = client.post(
            "/admin/ground-truth",
            data={"subtask": "A", "version_label": "bad-a", "notes": ""},
            files={
                "file": (
                    "bad-a.csv",
                    b"task_id,model_id\n1,1\n",
                    "text/csv",
                )
            },
        )

        assert response.status_code == 200
        assert "Missing required column(s): relevance_score." in response.text

        with connect(settings.database_path) as connection:
            count = connection.execute("SELECT COUNT(*) FROM ground_truth_versions").fetchone()[0]

        assert count == 0
        assert not settings.ground_truth_dir.exists()


def test_subtask_b_ground_truth_missing_image_id_is_rejected():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        organizer, _team = seed_accounts(settings)
        client = TestClient(create_app(settings))
        login(client, "admin", organizer.password)

        response = client.post(
            "/admin/ground-truth",
            data={"subtask": "B", "version_label": "bad-b", "notes": ""},
            files={"file": ("bad-b.csv", b"model_id\n7\n", "text/csv")},
        )

        assert response.status_code == 200
        assert "Missing required column(s): image_id." in response.text

        with connect(settings.database_path) as connection:
            count = connection.execute("SELECT COUNT(*) FROM ground_truth_versions").fetchone()[0]

        assert count == 0
        assert not settings.ground_truth_dir.exists()


def test_ground_truth_with_header_only_is_rejected():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        organizer, _team = seed_accounts(settings)
        client = TestClient(create_app(settings))
        login(client, "admin", organizer.password)

        response = client.post(
            "/admin/ground-truth",
            data={"subtask": "A", "version_label": "header-only", "notes": ""},
            files={
                "file": (
                    "header-only.csv",
                    b"task_id,model_id,relevance_score\n",
                    "text/csv",
                )
            },
        )

        assert response.status_code == 200
        assert "Ground-truth file must include at least one data row." in response.text

        with connect(settings.database_path) as connection:
            count = connection.execute("SELECT COUNT(*) FROM ground_truth_versions").fetchone()[0]

        assert count == 0


def test_ground_truth_files_are_not_served_as_static_files():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        organizer, _team = seed_accounts(settings)
        client = TestClient(create_app(settings))
        login(client, "admin", organizer.password)
        client.post(
            "/admin/ground-truth",
            data={"subtask": "A", "version_label": "a-v1", "notes": ""},
            files={"file": ("a-ground-truth.csv", b"secret", "text/csv")},
        )

        response = client.get("/storage/ground-truth/A/a-ground-truth.csv")

        assert response.status_code == 404


def ground_truth_ids(settings: Settings) -> list[int]:
    with connect(settings.database_path) as connection:
        rows = connection.execute(
            "SELECT id FROM ground_truth_versions ORDER BY id"
        ).fetchall()
    return [row["id"] for row in rows]


def test_organizer_can_activate_validated_subtask_a_ground_truth():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        organizer, _team = seed_accounts(settings)
        client = TestClient(create_app(settings))
        login(client, "admin", organizer.password)
        client.post(
            "/admin/ground-truth",
            data={"subtask": "A", "version_label": "a-v1", "notes": ""},
            files={
                "file": (
                    "a.csv",
                    b"task_id,model_id,relevance_score\n1,1,3\n",
                    "text/csv",
                )
            },
        )
        version_id = ground_truth_ids(settings)[0]

        response = client.post(f"/admin/ground-truth/{version_id}/activate")

        assert response.status_code == 200
        assert "Ground-truth version activated." in response.text

        with connect(settings.database_path) as connection:
            row = connection.execute(
                "SELECT is_active FROM ground_truth_versions WHERE id = ?",
                (version_id,),
            ).fetchone()

        assert row["is_active"] == 1


def test_organizer_can_activate_validated_subtask_b_ground_truth():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        organizer, _team = seed_accounts(settings)
        client = TestClient(create_app(settings))
        login(client, "admin", organizer.password)
        client.post(
            "/admin/ground-truth",
            data={"subtask": "B", "version_label": "b-v1", "notes": ""},
            files={"file": ("b.csv", b"image_id,model_id\n1,7\n", "text/csv")},
        )
        version_id = ground_truth_ids(settings)[0]

        response = client.post(f"/admin/ground-truth/{version_id}/activate")

        assert response.status_code == 200
        assert "Ground-truth version activated." in response.text

        with connect(settings.database_path) as connection:
            row = connection.execute(
                "SELECT is_active FROM ground_truth_versions WHERE id = ?",
                (version_id,),
            ).fetchone()

        assert row["is_active"] == 1


def test_activating_second_version_deactivates_previous_same_subtask():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        organizer, _team = seed_accounts(settings)
        client = TestClient(create_app(settings))
        login(client, "admin", organizer.password)
        for label in ["a-v1", "a-v2"]:
            client.post(
                "/admin/ground-truth",
                data={"subtask": "A", "version_label": label, "notes": ""},
                files={
                    "file": (
                        f"{label}.csv",
                        b"task_id,model_id,relevance_score\n1,1,3\n",
                        "text/csv",
                    )
                },
            )
        first_id, second_id = ground_truth_ids(settings)

        client.post(f"/admin/ground-truth/{first_id}/activate")
        client.post(f"/admin/ground-truth/{second_id}/activate")

        with connect(settings.database_path) as connection:
            rows = connection.execute(
                "SELECT id, is_active FROM ground_truth_versions ORDER BY id"
            ).fetchall()

        assert [(row["id"], row["is_active"]) for row in rows] == [(first_id, 0), (second_id, 1)]


def test_activating_subtask_a_does_not_affect_active_subtask_b():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        organizer, _team = seed_accounts(settings)
        client = TestClient(create_app(settings))
        login(client, "admin", organizer.password)
        client.post(
            "/admin/ground-truth",
            data={"subtask": "A", "version_label": "a-v1", "notes": ""},
            files={
                "file": (
                    "a.csv",
                    b"task_id,model_id,relevance_score\n1,1,3\n",
                    "text/csv",
                )
            },
        )
        client.post(
            "/admin/ground-truth",
            data={"subtask": "B", "version_label": "b-v1", "notes": ""},
            files={"file": ("b.csv", b"image_id,model_id\n1,7\n", "text/csv")},
        )
        a_id, b_id = ground_truth_ids(settings)

        client.post(f"/admin/ground-truth/{b_id}/activate")
        client.post(f"/admin/ground-truth/{a_id}/activate")

        with connect(settings.database_path) as connection:
            rows = connection.execute(
                "SELECT subtask, is_active FROM ground_truth_versions ORDER BY subtask"
            ).fetchall()

        assert [(row["subtask"], row["is_active"]) for row in rows] == [("A", 1), ("B", 1)]


def test_team_cannot_activate_ground_truth():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        organizer, team = seed_accounts(settings)
        client = TestClient(create_app(settings))
        login(client, "admin", organizer.password)
        client.post(
            "/admin/ground-truth",
            data={"subtask": "A", "version_label": "a-v1", "notes": ""},
            files={
                "file": (
                    "a.csv",
                    b"task_id,model_id,relevance_score\n1,1,3\n",
                    "text/csv",
                )
            },
        )
        version_id = ground_truth_ids(settings)[0]
        client.get("/logout", follow_redirects=True)
        login(client, "team-001", team.password)

        response = client.post(
            f"/admin/ground-truth/{version_id}/activate",
            follow_redirects=False,
        )

        assert response.status_code == 303
        assert response.headers["location"] == "/team"


def test_active_subtask_a_ground_truth_produces_required_ids():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        organizer, _team = seed_accounts(settings)
        client = TestClient(create_app(settings))
        login(client, "admin", organizer.password)
        client.post(
            "/admin/ground-truth",
            data={"subtask": "A", "version_label": "a-v1", "notes": ""},
            files={
                "file": (
                    "a.csv",
                    b"task_id,model_id,relevance_score\nQ1,M1,3\nQ1,M2,2\nQ2,M1,1\n",
                    "text/csv",
                )
            },
        )
        version_id = ground_truth_ids(settings)[0]
        client.post(f"/admin/ground-truth/{version_id}/activate")

        with connect(settings.database_path) as connection:
            requirements = get_active_ground_truth_requirements(connection, "A")

        assert requirements is not None
        assert requirements.ground_truth_version_id == version_id
        assert requirements.required_topic_ids == frozenset({"Q1", "Q2"})
        assert requirements.required_doc_ids == frozenset({"M1", "M2"})


def test_active_subtask_b_ground_truth_produces_required_ids():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        organizer, _team = seed_accounts(settings)
        client = TestClient(create_app(settings))
        login(client, "admin", organizer.password)
        client.post(
            "/admin/ground-truth",
            data={"subtask": "B", "version_label": "b-v1", "notes": ""},
            files={"file": ("b.csv", b"image_id,model_id\nI1,L1\nI2,L2\n", "text/csv")},
        )
        version_id = ground_truth_ids(settings)[0]
        client.post(f"/admin/ground-truth/{version_id}/activate")

        with connect(settings.database_path) as connection:
            requirements = get_active_ground_truth_requirements(connection, "B")

        assert requirements is not None
        assert requirements.ground_truth_version_id == version_id
        assert requirements.required_topic_ids == frozenset({"I1", "I2"})
        assert requirements.required_doc_ids == frozenset({"L1", "L2"})


def test_missing_active_ground_truth_returns_none():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        seed_accounts(settings)

        with connect(settings.database_path) as connection:
            requirements = get_active_ground_truth_requirements(connection, "A")

        assert requirements is None
