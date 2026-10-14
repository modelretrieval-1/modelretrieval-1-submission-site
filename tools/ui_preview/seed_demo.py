"""Seed synthetic, internally consistent UI fixtures using the app's APIs."""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import replace
from pathlib import Path

# Support `python tools/ui_preview/seed_demo.py` without installing the project.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fastapi.testclient import TestClient  # noqa: E402

from app.accounts import (  # noqa: E402
    change_organizer_password,
    change_team_password,
    create_organizer,
    create_team,
)
from app.audit import record_audit_event  # noqa: E402
from app.db import connect, initialize_database  # noqa: E402
from app.ground_truth import list_ground_truth_versions  # noqa: E402
from app.main import create_app  # noqa: E402
from app.storage import ensure_storage  # noqa: E402
from app.submissions import (  # noqa: E402
    list_admin_submission_summaries,
    list_submission_periods,
    mark_submission_status,
    update_submission_period,
)
from tools.ui_preview.common import (  # noqa: E402
    DEFAULT_ROOT,
    PASSWORD,
    REPO_ROOT,
    preview_settings,
)

TEAMS = (
    ("tsukuba-ir", "Tsukuba IR Lab", {"A", "B"}),
    ("kyoto-nlp", "KyotoNLP", {"A"}),
    ("osaka-vision", "Osaka Vision & Media", {"B"}),
    ("tohoku-retrieval", "Tohoku Multimodal Retrieval", {"A", "B"}),
)


def ground_truth_content(subtask: str) -> bytes:
    """20 topics and six candidates; B's relevant model cycles through all six."""
    rows = ["task_id,model_id,relevance_score" if subtask == "A" else "image_id,model_id"]
    for topic in range(1, 21):
        relevant = (topic - 1) % 6 + 1
        if subtask == "A":
            for model in range(1, 7):
                offset = (model - relevant) % 6
                rows.append(f"task-{topic:03},bert-{model:02},{max(0, 3 - offset)}")
        else:
            rows.append(f"test-0001-{topic:04}.png,{relevant:04}")
    return ("\n".join(rows) + "\n").encode()


def run_content(subtask: str, *, variant: int = 0) -> bytes:
    rows = []
    for run, name in enumerate(("dense-baseline", "reranker-v2", "ensemble")):
        for topic in range(1, 21):
            relevant = (topic - 1) % 6 + 1
            offset = (variant + run) % 6
            models = [((relevant - 1 + offset + i) % 6) + 1 for i in range(6)]
            for rank, model in enumerate(models, 1):
                topic_id = f"task-{topic:03}" if subtask == "A" else f"test-0001-{topic:04}"
                doc_id = f"bert-{model:02}" if subtask == "A" else str(model)
                rows.append(f"{topic_id} Q0 {doc_id} {rank} {7 - rank:.3f} {name}")
    return ("\n".join(rows) + "\n").encode()


def invalid_content() -> bytes:
    return (
        b"task-001 BAD bert-01 1 5.0 malformed\n"
        b"task-002 Q0 bert-02 zero 4.0 malformed\n"
        b"task-003 Q0 bert-03 1 not-a-score malformed\n"
        b"only three fields\n"
    )


def check(response, expected_text: str | None = None) -> None:
    if response.status_code != 200 or (expected_text and expected_text not in response.text):
        raise RuntimeError(f"Unexpected {response.status_code} at {response.url}: {response.text}")


def login(client: TestClient, user_id: str) -> None:
    client.get("/logout")
    response = client.post("/login", data={"user_id": user_id, "password": PASSWORD})
    check(response, "Organizer Dashboard" if user_id == "admin" else "Team Dashboard")


def seed(root: Path) -> dict:
    # Never silently delete a user's database, screenshots, or unrelated directory.
    if root.exists() and any(root.iterdir()):
        raise ValueError(f"Root must be new or empty: {root}. Choose another --root to reseed.")
    root.mkdir(parents=True, exist_ok=True)
    settings = preview_settings(root)
    ensure_storage(settings)
    initialize_database(settings.database_path)
    teams = []
    with connect(settings.database_path) as connection:
        organizer = create_organizer(connection, username="admin", display_name="Demo Organizer")
        if not change_organizer_password(
            connection,
            organizer_id=organizer.id,
            current_password=organizer.password,
            new_password=PASSWORD,
        ):
            raise RuntimeError("Could not set organizer demo password")
        for user_id, display_name, subtasks in TEAMS:
            team = create_team(
                connection,
                team_id=user_id,
                display_name=display_name,
                subtasks=subtasks,
                created_by_organizer_id=organizer.id,
            )
            if not change_team_password(
                connection,
                internal_team_id=team.id,
                current_password=team.password,
                new_password=PASSWORD,
            ):
                raise RuntimeError(f"Could not set password for {user_id}")
            teams.append(
                {
                    "id": team.id,
                    "user_id": user_id,
                    "password": PASSWORD,
                    "display_name": display_name,
                    "subtasks": sorted(subtasks),
                }
            )
        # Temporarily open normal to create realistic historical successful uploads.
        for period in ("normal", "late"):
            update_submission_period(
                connection,
                period_name=period,
                starts_at_jst="2026-01-01 00:00:00",
                deadline_at_jst="2099-12-31 23:59:00",
                is_open_override=False,
            )

    def upload(client, subtask, period, *, variant=0, invalid=False):
        response = client.post(
            f"/team/submissions/{subtask}/new",
            data={"submission_period": period},
            files={
                "file": (
                    f"{'invalid' if invalid else 'retrieval'}-{subtask}-{period}.txt",
                    invalid_content() if invalid else run_content(subtask, variant=variant),
                    "text/plain",
                )
            },
        )
        check(response, "Submission rejected." if invalid else "Team Dashboard")
        with connect(settings.database_path) as connection:
            return max(row.submission_id for row in list_admin_submission_summaries(connection))

    def grant(client, submission_id):
        login(client, "admin")
        check(
            client.post(
                f"/admin/submissions/{submission_id}/resubmission",
                data={"reason": "Demo: organizer-approved correction of run ordering."},
            ),
            "Replacement upload permission granted.",
        )
        login(client, "tsukuba-ir")

    with TestClient(create_app(settings)) as client:
        login(client, "admin")
        for subtask in ("A", "B"):
            check(
                client.post(
                    "/admin/ground-truth",
                    data={
                        "subtask": subtask,
                        "version_label": f"demo-{subtask.lower()}-v1",
                        "notes": "Synthetic UI fixture: 20 topics, six candidate models.",
                    },
                    files={
                        "file": (f"demo-{subtask}.csv", ground_truth_content(subtask), "text/csv")
                    },
                ),
                "Uploaded ground truth",
            )
            with connect(settings.database_path) as connection:
                version = next(
                    v for v in list_ground_truth_versions(connection) if v.subtask == subtask
                )
            check(client.post(f"/admin/ground-truth/{version.id}/activate"))
        for index, team in enumerate(teams):
            login(client, team["user_id"])
            for subtask in team["subtasks"]:
                upload(client, subtask, "normal", invalid=True)
                # Reserve primary team's B normal slot for the failure fixture.
                if index == 0 and subtask == "B":
                    continue
                submission_id = upload(client, subtask, "normal", variant=index)
                if index == 0:
                    grant(client, submission_id)
                    superseded_id = submission_id
                    replacement_id = upload(client, "A", "normal", variant=1)
                else:
                    upload(client, subtask, "late", variant=index + 1)

    # A non-worker, non-eager TestClient preserves the upload flow's queued rows.
    # Only presentation fixtures are changed; no results are fabricated for them.
    with TestClient(create_app(replace(settings, evaluation_mode="manual"))) as client:
        login(client, "tsukuba-ir")
        failed_id = upload(client, "B", "normal")
        queued_id = upload(client, "A", "late")
        accepted_id = upload(client, "B", "late")
        with connect(settings.database_path) as connection:
            mark_submission_status(
                connection,
                submission_id=failed_id,
                status="evaluation_failed",
                validation_summary=(
                    "Demo fixture: evaluation service interrupted; please contact the organizers."
                ),
            )
            mark_submission_status(
                connection,
                submission_id=accepted_id,
                status="accepted",
                validation_summary="Preparing for evaluation.",
            )
        grant(client, accepted_id)
        processing_id = upload(client, "B", "late", variant=2)
        with connect(settings.database_path) as connection:
            mark_submission_status(
                connection,
                submission_id=processing_id,
                status="processing",
                validation_summary="Evaluating demo runs.",
            )
            for submission_id, event_type in (
                (failed_id, "submission_evaluation_failed"),
                (processing_id, "submission_evaluation_started"),
            ):
                record_audit_event(
                    connection,
                    actor_type="system",
                    actor_id=None,
                    event_type=event_type,
                    entity_type="submission",
                    entity_id=submission_id,
                    metadata={"demo_fixture": True},
                )
        # Leave one unused replacement permission to expose the approved-upload UI.
        grant(client, queued_id)
        upload(client, "A", "late", invalid=True)

    with connect(settings.database_path) as connection:
        update_submission_period(
            connection,
            period_name="normal",
            starts_at_jst="2026-01-01 00:00:00",
            deadline_at_jst="2026-08-01 15:00:00",
            is_open_override=False,
        )
        submissions = list_admin_submission_summaries(connection)
        for team in teams:
            team["submissions"] = {}
            for row in submissions:
                if row.team_public_id == team["user_id"]:
                    team["submissions"].setdefault(row.status, []).append(row.submission_id)
        manifest = {
            "schema_version": 1,
            "root": str(root),
            "database_path": str(settings.database_path),
            "storage_root": str(settings.storage_root),
            "evaluation_mode": "eager",
            "organizer": {"id": organizer.id, "user_id": "admin", "password": PASSWORD},
            "teams": teams,
            "primary_team": "tsukuba-ir",
            "single_subtask_team": "kyoto-nlp",
            "representatives": {
                "evaluated": replacement_id,
                "evaluation_failed": failed_id,
                "queued": queued_id,
                "processing": processing_id,
                "accepted": accepted_id,
                "rejected": teams[0]["submissions"]["rejected"][0],
            },
            "replacement": {
                "superseded": superseded_id,
                "current": replacement_id,
                "pending_permission_submission": queued_id,
            },
            "periods": [
                {"name": p.name, "deadline_at_jst": p.deadline_at_jst}
                for p in list_submission_periods(connection)
            ],
            "ground_truth": [
                {"id": v.id, "subtask": v.subtask, "is_active": v.is_active}
                for v in list_ground_truth_versions(connection)
            ],
        }
    fixtures = root / "fixtures"
    fixtures.mkdir()
    invalid_file = fixtures / "invalid-submission.txt"
    invalid_file.write_bytes(invalid_content())
    manifest["invalid_upload"] = str(invalid_file)
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()
    root = args.root.expanduser().resolve()
    os.chdir(REPO_ROOT)  # App static/template paths are repository-relative.
    try:
        manifest = seed(root)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
