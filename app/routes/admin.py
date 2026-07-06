from __future__ import annotations

import csv
import sqlite3
from collections import Counter
from datetime import datetime
from io import BytesIO, StringIO
from pathlib import Path
from typing import Annotated
from urllib.parse import urlencode
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, Response

from app.accounts import (
    create_organizer,
    create_team,
    list_organizers,
    list_teams,
    reset_organizer_password_by_username,
    reset_team_password_by_team_id,
)
from app.config import Settings
from app.db import connect
from app.evaluation import (
    list_leaderboard_rows,
    list_submission_query_results,
    list_submission_results,
)
from app.ground_truth import (
    JST,
    activate_ground_truth_version,
    create_ground_truth_version,
    list_ground_truth_versions,
    safe_filename,
    store_ground_truth_file,
    validate_ground_truth_content,
)
from app.submissions import (
    get_admin_submission_detail,
    is_submission_period_open,
    list_admin_submission_summaries,
    list_submission_bundle_entries,
    list_submission_periods,
    list_submission_runs,
    list_submission_validation_errors,
    parse_jst_datetime,
    update_submission_period,
)
from app.web import get_session_account, redirect, require_organizer, templates

router = APIRouter()


def render_admin_teams(
    request: Request,
    *,
    account,
    error: str | None = None,
    generated_team_id: str | None = None,
    generated_password: str | None = None,
) -> HTMLResponse:
    app_settings: Settings = request.app.state.settings
    with connect(app_settings.database_path) as connection:
        teams = list_teams(connection)
    return templates.TemplateResponse(
        request,
        "admin_teams.html",
        {
            "app_name": app_settings.app_name,
            "account": account,
            "teams": teams,
            "error": error,
            "generated_team_id": generated_team_id,
            "generated_password": generated_password,
        },
    )


def render_admin_users(
    request: Request,
    *,
    account,
    error: str | None = None,
    generated_username: str | None = None,
    generated_password: str | None = None,
) -> HTMLResponse:
    app_settings: Settings = request.app.state.settings
    with connect(app_settings.database_path) as connection:
        organizers = list_organizers(connection)
    return templates.TemplateResponse(
        request,
        "admin_users.html",
        {
            "app_name": app_settings.app_name,
            "account": account,
            "organizers": organizers,
            "error": error,
            "generated_username": generated_username,
            "generated_password": generated_password,
        },
    )


def render_ground_truth(
    request: Request,
    *,
    account,
    error: str | None = None,
    success: str | None = None,
) -> HTMLResponse:
    app_settings: Settings = request.app.state.settings
    with connect(app_settings.database_path) as connection:
        versions = list_ground_truth_versions(connection)
    return templates.TemplateResponse(
        request,
        "admin_ground_truth.html",
        {
            "app_name": app_settings.app_name,
            "account": account,
            "versions": versions,
            "error": error,
            "success": success,
        },
    )


def render_periods(
    request: Request,
    *,
    account,
    error: str | None = None,
    success: str | None = None,
) -> HTMLResponse:
    app_settings: Settings = request.app.state.settings
    with connect(app_settings.database_path) as connection:
        periods = list_submission_periods(connection)
    return templates.TemplateResponse(
        request,
        "admin_periods.html",
        {
            "app_name": app_settings.app_name,
            "account": account,
            "periods": periods,
            "error": error,
            "success": success,
        },
    )


def get_submission_bundle_filters(request: Request) -> dict[str, str]:
    requested_subtask = request.query_params.get("subtask", "").strip().upper()
    requested_period = request.query_params.get("period", "").strip().lower()
    return {
        "subtask": requested_subtask if requested_subtask in {"A", "B"} else "",
        "period": requested_period if requested_period in {"normal", "late"} else "",
    }


def submission_bundle_content(entries) -> bytes:
    output = BytesIO()
    with ZipFile(output, mode="w", compression=ZIP_DEFLATED) as archive:
        metadata_rows = []
        for entry in entries:
            archive_path = ""
            if entry.stored_file_path:
                stored_path = Path(entry.stored_file_path)
                if stored_path.exists():
                    archive_path = (
                        "submissions/"
                        f"{entry.submission_id}_{entry.team_public_id}_"
                        f"{entry.subtask}_{entry.period_name}_"
                        f"{safe_filename(entry.original_filename)}"
                    )
                    archive.write(stored_path, archive_path)
            metadata_rows.append((entry, archive_path))
        archive.writestr("metadata.csv", submission_bundle_metadata_csv(metadata_rows))
    return output.getvalue()


def submission_bundle_metadata_csv(metadata_rows) -> str:
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "submission_id",
            "team_id",
            "team_display_name",
            "subtask",
            "period",
            "status",
            "original_filename",
            "bundle_file",
            "file_sha256",
            "file_size_bytes",
            "submitted_at_jst",
            "validation_summary",
        ]
    )
    for entry, archive_path in metadata_rows:
        writer.writerow(
            [
                entry.submission_id,
                entry.team_public_id,
                entry.team_display_name,
                entry.subtask,
                entry.period_name,
                entry.status,
                entry.original_filename,
                archive_path,
                entry.file_sha256 or "",
                entry.file_size_bytes,
                entry.submitted_at_jst,
                entry.validation_summary or "",
            ]
        )
    return output.getvalue()


def render_admin_submissions(request: Request, *, account) -> HTMLResponse:
    app_settings: Settings = request.app.state.settings
    filters = {
        "team_id": request.query_params.get("team_id", "").strip(),
        "subtask": request.query_params.get("subtask", "").strip().upper(),
        "period": request.query_params.get("period", "").strip().lower(),
        "status": request.query_params.get("status", "").strip(),
    }
    subtask_filter = filters["subtask"] if filters["subtask"] in {"A", "B"} else ""
    period_filter = filters["period"] if filters["period"] in {"normal", "late"} else ""
    with connect(app_settings.database_path) as connection:
        submissions = list_admin_submission_summaries(
            connection,
            team_public_id=filters["team_id"] or None,
            subtask=subtask_filter or None,
            period_name=period_filter or None,
            status=filters["status"] or None,
        )
    return templates.TemplateResponse(
        request,
        "admin_submissions.html",
        {
            "app_name": app_settings.app_name,
            "account": account,
            "submissions": submissions,
            "filters": {
                "team_id": filters["team_id"],
                "subtask": subtask_filter,
                "period": period_filter,
                "status": filters["status"],
            },
            "bundle_query": urlencode(
                {
                    key: value
                    for key, value in {
                        "subtask": subtask_filter,
                        "period": period_filter,
                    }.items()
                    if value
                }
            ),
        },
    )


def render_admin_submission_detail(
    request: Request,
    *,
    account,
    submission_id: int,
) -> HTMLResponse | None:
    app_settings: Settings = request.app.state.settings
    with connect(app_settings.database_path) as connection:
        submission = get_admin_submission_detail(connection, submission_id=submission_id)
        if submission is None:
            return None
        validation_errors = list_submission_validation_errors(
            connection,
            submission_id=submission_id,
        )
        runs = list_submission_runs(connection, submission_id=submission_id)
        metrics = list_submission_results(connection, submission_id=submission_id)
        query_metrics = list_submission_query_results(connection, submission_id=submission_id)
    return templates.TemplateResponse(
        request,
        "admin_submission_detail.html",
        {
            "app_name": app_settings.app_name,
            "account": account,
            "submission": submission,
            "validation_errors": validation_errors,
            "runs": runs,
            "metrics": metrics,
            "query_metrics": query_metrics,
        },
    )


def get_leaderboard_filters(request: Request) -> dict[str, str]:
    requested_subtask = request.query_params.get("subtask", "").strip().upper()
    requested_period = request.query_params.get("period", "").strip().lower()
    return {
        "subtask": requested_subtask if requested_subtask in {"A", "B"} else "",
        "period": requested_period if requested_period in {"normal", "late"} else "",
    }


def leaderboard_csv_content(rows) -> str:
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "team_id",
            "team_display_name",
            "subtask",
            "period",
            "run_id",
            "ndcg@1",
            "ndcg@3",
            "ndcg@5",
            "mrr",
            "submitted_at_jst",
        ]
    )
    for row in rows:
        writer.writerow(
            [
                row.team_public_id,
                row.team_display_name,
                row.subtask,
                row.period_name,
                row.run_id,
                format_metric_value(row.metric_values.get("ndcg@1")),
                format_metric_value(row.metric_values.get("ndcg@3")),
                format_metric_value(row.metric_values.get("ndcg@5")),
                format_metric_value(row.metric_values.get("mrr")),
                row.submitted_at_jst,
            ]
        )
    return output.getvalue()


def format_metric_value(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.6f}"


def render_admin_leaderboard(request: Request, *, account) -> HTMLResponse:
    app_settings: Settings = request.app.state.settings
    filters = get_leaderboard_filters(request)
    with connect(app_settings.database_path) as connection:
        rows = list_leaderboard_rows(
            connection,
            subtask=filters["subtask"] or None,
            period_name=filters["period"] or None,
        )
    return templates.TemplateResponse(
        request,
        "admin_leaderboard.html",
        {
            "app_name": app_settings.app_name,
            "account": account,
            "rows": rows,
            "filters": filters,
            "export_query": urlencode({key: value for key, value in filters.items() if value}),
        },
    )


@router.get("/admin", response_class=HTMLResponse)
def admin_dashboard(request: Request) -> Response:
    app_settings: Settings = request.app.state.settings
    account = get_session_account(request)
    if account is None:
        return redirect("/login")
    if account.role != "organizer":
        return redirect("/team")

    with connect(app_settings.database_path) as connection:
        teams = list_teams(connection)
        periods = list_submission_periods(connection)
        ground_truth_versions = list_ground_truth_versions(connection)
        submissions = list_admin_submission_summaries(connection)

    active_teams = sum(1 for team in teams if team.is_active)
    now_jst = datetime.now(JST)
    period_states = [
        {
            "period": period,
            "state": "reopened"
            if period.is_open_override
            else "open"
            if is_submission_period_open(period, now_jst=now_jst)
            else "closed",
        }
        for period in periods
    ]
    status_counts = Counter(submission.status for submission in submissions)
    subtask_counts = Counter(
        (submission.subtask, submission.period_name)
        for submission in submissions
        if submission.status in {"evaluated", "accepted", "evaluation_failed"}
    )
    active_ground_truth = {
        subtask: next(
            (
                version
                for version in ground_truth_versions
                if version.subtask == subtask and version.is_active
            ),
            None,
        )
        for subtask in ("A", "B")
    }
    recent_validation_failures = [
        submission for submission in submissions if submission.status == "rejected"
    ][:5]

    return templates.TemplateResponse(
        request,
        "admin_dashboard.html",
        {
            "app_name": app_settings.app_name,
            "account": account,
            "active_teams": active_teams,
            "total_teams": len(teams),
            "evaluated_submission_count": status_counts.get("evaluated", 0),
            "rejected_submission_count": status_counts.get("rejected", 0),
            "periods": periods,
            "period_states": period_states,
            "active_ground_truth": active_ground_truth,
            "recent_submissions": submissions[:6],
            "recent_validation_failures": recent_validation_failures,
            "subtask_counts": subtask_counts,
        },
    )


@router.get("/admin/teams", response_class=HTMLResponse)
def admin_teams(request: Request) -> Response:
    account, redirect_response = require_organizer(request)
    if redirect_response is not None:
        return redirect_response
    return render_admin_teams(request, account=account)


@router.post("/admin/teams", response_class=HTMLResponse)
async def add_team(request: Request) -> Response:
    app_settings: Settings = request.app.state.settings
    account, redirect_response = require_organizer(request)
    if redirect_response is not None:
        return redirect_response

    form = await request.form()
    team_id = str(form.get("team_id", "")).strip()
    display_name = str(form.get("display_name", "")).strip()
    subtasks = {str(value) for value in form.getlist("subtasks")}

    if not team_id or not display_name:
        return render_admin_teams(
            request,
            account=account,
            error="Team ID and display name are required.",
        )

    if not subtasks:
        return render_admin_teams(
            request,
            account=account,
            error="Select at least one subtask.",
        )

    if not subtasks.issubset({"A", "B"}):
        return render_admin_teams(
            request,
            account=account,
            error="Invalid subtask selection.",
        )

    try:
        with connect(app_settings.database_path) as connection:
            generated = create_team(
                connection,
                team_id=team_id,
                display_name=display_name,
                subtasks=set(subtasks),  # type: ignore[arg-type]
                created_by_organizer_id=account.id,
            )
    except ValueError as exc:
        return render_admin_teams(request, account=account, error=str(exc))
    except sqlite3.IntegrityError:
        return render_admin_teams(
            request,
            account=account,
            error="Could not create team. Check whether the team ID already exists.",
        )

    return render_admin_teams(
        request,
        account=account,
        generated_team_id=generated.user_id,
        generated_password=generated.password,
    )


@router.post("/admin/teams/{team_id}/password", response_class=HTMLResponse)
def regenerate_team_password(request: Request, team_id: str) -> Response:
    app_settings: Settings = request.app.state.settings
    account, redirect_response = require_organizer(request)
    if redirect_response is not None:
        return redirect_response

    with connect(app_settings.database_path) as connection:
        generated_password = reset_team_password_by_team_id(connection, team_id)

    if generated_password is None:
        return render_admin_teams(request, account=account, error="Team not found.")

    return render_admin_teams(
        request,
        account=account,
        generated_team_id=team_id,
        generated_password=generated_password,
    )


@router.get("/admin/users", response_class=HTMLResponse)
def admin_users(request: Request) -> Response:
    account, redirect_response = require_organizer(request)
    if redirect_response is not None:
        return redirect_response
    return render_admin_users(request, account=account)


@router.post("/admin/users", response_class=HTMLResponse)
async def add_organizer(request: Request) -> Response:
    app_settings: Settings = request.app.state.settings
    account, redirect_response = require_organizer(request)
    if redirect_response is not None:
        return redirect_response

    form = await request.form()
    username = str(form.get("username", "")).strip()
    display_name = str(form.get("display_name", "")).strip()

    if not username or not display_name:
        return render_admin_users(
            request,
            account=account,
            error="Username and display name are required.",
        )

    try:
        with connect(app_settings.database_path) as connection:
            generated = create_organizer(
                connection,
                username=username,
                display_name=display_name,
            )
    except sqlite3.IntegrityError:
        return render_admin_users(
            request,
            account=account,
            error="Could not create organizer. Check whether the username already exists.",
        )

    return render_admin_users(
        request,
        account=account,
        generated_username=generated.user_id,
        generated_password=generated.password,
    )


@router.post("/admin/users/{username}/password", response_class=HTMLResponse)
def regenerate_organizer_password(request: Request, username: str) -> Response:
    app_settings: Settings = request.app.state.settings
    account, redirect_response = require_organizer(request)
    if redirect_response is not None:
        return redirect_response

    with connect(app_settings.database_path) as connection:
        generated_password = reset_organizer_password_by_username(connection, username)

    if generated_password is None:
        return render_admin_users(request, account=account, error="Organizer not found.")

    return render_admin_users(
        request,
        account=account,
        generated_username=username,
        generated_password=generated_password,
    )


@router.get("/admin/ground-truth", response_class=HTMLResponse)
def ground_truth_page(request: Request) -> Response:
    account, redirect_response = require_organizer(request)
    if redirect_response is not None:
        return redirect_response
    return render_ground_truth(request, account=account)


@router.post("/admin/ground-truth", response_class=HTMLResponse)
async def upload_ground_truth(
    request: Request,
    subtask: Annotated[str, Form()],
    version_label: Annotated[str, Form()],
    file: Annotated[UploadFile, File()],
    notes: str = Form(""),
) -> Response:
    app_settings: Settings = request.app.state.settings
    account, redirect_response = require_organizer(request)
    if redirect_response is not None:
        return redirect_response

    subtask = subtask.strip()
    version_label = version_label.strip()
    notes = notes.strip()

    if subtask not in {"A", "B"}:
        return render_ground_truth(request, account=account, error="Select a valid subtask.")

    if not version_label:
        return render_ground_truth(request, account=account, error="Version label is required.")

    content = await file.read()
    if not content:
        return render_ground_truth(
            request,
            account=account,
            error="Ground-truth file is empty.",
        )

    validation_errors = validate_ground_truth_content(subtask, content)  # type: ignore[arg-type]
    if validation_errors:
        return render_ground_truth(
            request,
            account=account,
            error=" ".join(validation_errors),
        )

    stored_file_path, file_sha256 = store_ground_truth_file(
        app_settings,
        subtask=subtask,  # type: ignore[arg-type]
        filename=file.filename or "ground-truth.txt",
        content=content,
    )

    with connect(app_settings.database_path) as connection:
        create_ground_truth_version(
            connection,
            subtask=subtask,  # type: ignore[arg-type]
            version_label=version_label,
            stored_file_path=stored_file_path,
            file_sha256=file_sha256,
            uploaded_by_organizer_id=account.id,
            notes=notes or None,
            validation_status="validated",
        )

    return render_ground_truth(
        request,
        account=account,
        success=f"Uploaded ground truth for Subtask {subtask}.",
    )


@router.post("/admin/ground-truth/{version_id}/activate", response_class=HTMLResponse)
def activate_ground_truth(request: Request, version_id: int) -> Response:
    app_settings: Settings = request.app.state.settings
    account, redirect_response = require_organizer(request)
    if redirect_response is not None:
        return redirect_response

    with connect(app_settings.database_path) as connection:
        activated = activate_ground_truth_version(connection, version_id)

    if not activated:
        return render_ground_truth(
            request,
            account=account,
            error="Ground-truth version cannot be activated.",
        )

    return render_ground_truth(
        request,
        account=account,
        success="Ground-truth version activated.",
    )


@router.get("/admin/periods", response_class=HTMLResponse)
def admin_periods(request: Request) -> Response:
    account, redirect_response = require_organizer(request)
    if redirect_response is not None:
        return redirect_response
    return render_periods(request, account=account)


@router.post("/admin/periods/{period_name}", response_class=HTMLResponse)
async def update_period(request: Request, period_name: str) -> Response:
    app_settings: Settings = request.app.state.settings
    account, redirect_response = require_organizer(request)
    if redirect_response is not None:
        return redirect_response

    period_name = period_name.strip().lower()
    if period_name not in {"normal", "late"}:
        return render_periods(request, account=account, error="Submission period not found.")

    form = await request.form()
    starts_at_jst = str(form.get("starts_at_jst", "")).strip() or None
    deadline_at_jst = str(form.get("deadline_at_jst", "")).strip()
    is_open_override = form.get("is_open_override") == "on"

    if not deadline_at_jst:
        return render_periods(request, account=account, error="Deadline is required.")

    try:
        if starts_at_jst is not None:
            parse_jst_datetime(starts_at_jst)
        parse_jst_datetime(deadline_at_jst)
    except ValueError:
        return render_periods(
            request,
            account=account,
            error="Use timestamp format YYYY-MM-DD HH:MM:SS.",
        )

    with connect(app_settings.database_path) as connection:
        updated = update_submission_period(
            connection,
            period_name=period_name,
            starts_at_jst=starts_at_jst,
            deadline_at_jst=deadline_at_jst,
            is_open_override=is_open_override,
        )

    if not updated:
        return render_periods(request, account=account, error="Submission period not found.")

    return render_periods(request, account=account, success="Submission period updated.")


@router.get("/admin/submissions", response_class=HTMLResponse)
def admin_submissions(request: Request) -> Response:
    account, redirect_response = require_organizer(request)
    if redirect_response is not None:
        return redirect_response
    return render_admin_submissions(request, account=account)


@router.get("/admin/submissions/bundle.zip")
def admin_submissions_bundle(request: Request) -> Response:
    app_settings: Settings = request.app.state.settings
    _account, redirect_response = require_organizer(request)
    if redirect_response is not None:
        return redirect_response

    filters = get_submission_bundle_filters(request)
    with connect(app_settings.database_path) as connection:
        entries = list_submission_bundle_entries(
            connection,
            subtask=filters["subtask"] or None,
            period_name=filters["period"] or None,
        )
    return Response(
        content=submission_bundle_content(entries),
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="submissions-bundle.zip"'},
    )


@router.get("/admin/submissions/{submission_id}", response_class=HTMLResponse)
def admin_submission_detail(request: Request, submission_id: int) -> Response:
    account, redirect_response = require_organizer(request)
    if redirect_response is not None:
        return redirect_response

    response = render_admin_submission_detail(
        request,
        account=account,
        submission_id=submission_id,
    )
    if response is None:
        return redirect("/admin/submissions")
    return response


@router.get("/admin/leaderboard", response_class=HTMLResponse)
def admin_leaderboard(request: Request) -> Response:
    account, redirect_response = require_organizer(request)
    if redirect_response is not None:
        return redirect_response
    return render_admin_leaderboard(request, account=account)


@router.get("/admin/leaderboard.csv")
def admin_leaderboard_csv(request: Request) -> Response:
    app_settings: Settings = request.app.state.settings
    _account, redirect_response = require_organizer(request)
    if redirect_response is not None:
        return redirect_response

    filters = get_leaderboard_filters(request)
    with connect(app_settings.database_path) as connection:
        rows = list_leaderboard_rows(
            connection,
            subtask=filters["subtask"] or None,
            period_name=filters["period"] or None,
        )
    return Response(
        content=leaderboard_csv_content(rows),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="leaderboard.csv"'},
    )
