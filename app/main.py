from __future__ import annotations

import csv
import sqlite3
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from io import BytesIO, StringIO
from pathlib import Path
from typing import Annotated
from urllib.parse import urlencode
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import FastAPI, File, Form, Request, UploadFile, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.accounts import (
    authenticate,
    change_organizer_password,
    create_organizer,
    create_team,
    get_organizer_account,
    get_team_account,
    get_team_subtasks,
    list_organizers,
    list_teams,
    reset_organizer_password_by_username,
    reset_team_password_by_team_id,
)
from app.config import Settings, settings
from app.db import connect, initialize_database
from app.evaluation import (
    evaluate_submission,
    list_latest_team_submission_summaries,
    list_leaderboard_rows,
    list_submission_results,
    mark_evaluation_failed,
    persist_evaluation_results,
)
from app.ground_truth import (
    JST,
    activate_ground_truth_version,
    create_ground_truth_version,
    get_active_ground_truth_requirements,
    get_ground_truth_version,
    list_ground_truth_versions,
    safe_filename,
    store_ground_truth_file,
    validate_ground_truth_content,
)
from app.sessions import SESSION_COOKIE, create_session_value, parse_session_value
from app.storage import ensure_storage
from app.submissions import (
    SubmissionValidationError,
    create_submission_attempt,
    get_admin_submission_detail,
    get_submission_period_by_name,
    has_successful_submission,
    is_submission_period_open,
    list_admin_submission_summaries,
    list_submission_bundle_entries,
    list_submission_periods,
    list_submission_runs,
    list_submission_validation_errors,
    parse_jst_datetime,
    persist_submission_runs,
    persist_validation_errors,
    store_submission_file,
    update_submission_period,
    validate_submission_against_requirements,
    validate_submission_filename,
    validate_submission_size,
)

templates = Jinja2Templates(directory="app/templates")


def build_lifespan(app_settings: Settings):
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        ensure_storage(app_settings)
        initialize_database(app_settings.database_path)
        yield

    return lifespan


def redirect(path: str) -> RedirectResponse:
    return RedirectResponse(path, status_code=status.HTTP_303_SEE_OTHER)


def get_session_account(request: Request):
    app_settings: Settings = request.app.state.settings
    session = parse_session_value(app_settings.secret_key, request.cookies.get(SESSION_COOKIE))
    if session is None:
        return None

    with connect(app_settings.database_path) as connection:
        if session.role == "organizer":
            return get_organizer_account(connection, session.id)
        return get_team_account(connection, session.id)


def render_login(request: Request, *, error: str | None = None) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "login.html",
        {"app_name": request.app.state.settings.app_name, "error": error},
    )


def require_organizer(request: Request):
    account = get_session_account(request)
    if account is None:
        return None, redirect("/login")
    if account.role != "organizer":
        return None, redirect("/team")
    return account, None


def require_team(request: Request):
    account = get_session_account(request)
    if account is None:
        return None, redirect("/login")
    if account.role != "team":
        return None, redirect("/admin")
    return account, None


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


def render_password_change(
    request: Request,
    *,
    account,
    error: str | None = None,
    success: str | None = None,
) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "password_change.html",
        {
            "app_name": request.app.state.settings.app_name,
            "account": account,
            "error": error,
            "success": success,
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


def render_submission_upload(
    request: Request,
    *,
    account,
    subtask: str,
    errors: tuple[SubmissionValidationError, ...] = (),
    metrics=(),
    success: str | None = None,
    selected_period: str = "normal",
) -> HTMLResponse:
    app_settings: Settings = request.app.state.settings
    with connect(app_settings.database_path) as connection:
        periods = list_submission_periods(connection)
    return templates.TemplateResponse(
        request,
        "team_submission_upload.html",
        {
            "app_name": app_settings.app_name,
            "account": account,
            "subtask": subtask,
            "periods": periods,
            "selected_period": selected_period,
            "errors": errors,
            "metrics": metrics,
            "success": success,
        },
    )


def create_app(app_settings: Settings = settings) -> FastAPI:
    app = FastAPI(title=app_settings.app_name, lifespan=build_lifespan(app_settings))
    app.state.settings = app_settings
    app.mount("/static", StaticFiles(directory="app/static"), name="static")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "environment": app_settings.environment}

    @app.get("/", response_class=HTMLResponse)
    def home(request: Request) -> Response:
        account = get_session_account(request)
        if account is not None:
            if account.role == "organizer":
                return redirect("/admin")
            return redirect("/team")

        return templates.TemplateResponse(
            request,
            "home.html",
            {"app_name": app_settings.app_name},
        )

    @app.get("/login", response_class=HTMLResponse)
    def login_form(request: Request, error: str | None = None) -> HTMLResponse:
        message = "Invalid user ID or password." if error == "invalid" else None
        return render_login(request, error=message)

    @app.post("/login")
    def login(user_id: str = Form(...), password: str = Form(...)) -> Response:
        with connect(app_settings.database_path) as connection:
            account = authenticate(connection, user_id, password)

        if account is None:
            return redirect("/login?error=invalid")

        destination = "/admin" if account.role == "organizer" else "/team"
        response = redirect(destination)
        response.set_cookie(
            SESSION_COOKIE,
            create_session_value(app_settings.secret_key, role=account.role, account_id=account.id),
            httponly=True,
            samesite="lax",
        )
        return response

    @app.get("/logout")
    def logout() -> RedirectResponse:
        response = redirect("/login")
        response.delete_cookie(SESSION_COOKIE)
        return response

    @app.get("/team", response_class=HTMLResponse)
    def team_dashboard(request: Request) -> Response:
        account = get_session_account(request)
        if account is None:
            return redirect("/login")
        if account.role != "team":
            return redirect("/admin")

        with connect(app_settings.database_path) as connection:
            subtasks = sorted(get_team_subtasks(connection, account.id))
            submission_summaries = list_latest_team_submission_summaries(
                connection,
                internal_team_id=account.id,
            )

        return templates.TemplateResponse(
            request,
            "team_dashboard.html",
            {
                "app_name": app_settings.app_name,
                "account": account,
                "subtasks": subtasks,
                "submission_summaries": submission_summaries,
            },
        )

    @app.get("/team/submissions/{subtask}/new", response_class=HTMLResponse)
    def submission_upload_page(request: Request, subtask: str) -> Response:
        account, redirect_response = require_team(request)
        if redirect_response is not None:
            return redirect_response

        subtask = subtask.strip().upper()
        with connect(app_settings.database_path) as connection:
            subtasks = get_team_subtasks(connection, account.id)

        if subtask not in subtasks:
            return redirect("/team")

        return render_submission_upload(request, account=account, subtask=subtask)

    @app.post("/team/submissions/{subtask}/new", response_class=HTMLResponse)
    async def upload_submission(
        request: Request,
        subtask: str,
        file: Annotated[UploadFile, File()],
        submission_period: Annotated[str, Form()] = "",
    ) -> Response:
        account, redirect_response = require_team(request)
        if redirect_response is not None:
            return redirect_response

        subtask = subtask.strip().upper()
        with connect(app_settings.database_path) as connection:
            subtasks = get_team_subtasks(connection, account.id)

        if subtask not in subtasks:
            return redirect("/team")

        filename = file.filename or ""
        content = await file.read()
        guard_errors = (
            validate_submission_filename(filename)
            + validate_submission_size(
                len(content),
                max_upload_bytes=app_settings.max_upload_bytes,
            )
        )

        with connect(app_settings.database_path) as connection:
            selected_period = submission_period.strip().lower()
            if not selected_period:
                return render_submission_upload(
                    request,
                    account=account,
                    subtask=subtask,
                    selected_period=selected_period,
                    errors=(
                        SubmissionValidationError(
                            field_name="submission_period",
                            error_code="missing_submission_period",
                            message="Choose a submission period.",
                        ),
                    ),
                )
            period = get_submission_period_by_name(connection, selected_period)
            if period is None:
                return render_submission_upload(
                    request,
                    account=account,
                    subtask=subtask,
                    selected_period=selected_period,
                    errors=(
                        SubmissionValidationError(
                            field_name="submission_period",
                            error_code="invalid_submission_period",
                            message="Choose normal or late submission.",
                        ),
                    ),
                )
            if not is_submission_period_open(period, now_jst=datetime.now(JST)):
                return render_submission_upload(
                    request,
                    account=account,
                    subtask=subtask,
                    selected_period=selected_period,
                    errors=(
                        SubmissionValidationError(
                            field_name="submission_period",
                            error_code="submission_period_closed",
                            message=f"The {period.name} submission period is closed.",
                        ),
                    ),
                )

            stored_file = None
            if not guard_errors:
                stored_file = store_submission_file(
                    app_settings,
                    internal_team_id=account.id,
                    subtask=subtask,
                    filename=filename,
                    content=content,
                )

            requirements = (
                get_active_ground_truth_requirements(connection, subtask)  # type: ignore[arg-type]
                if not guard_errors
                else None
            )
            already_submitted = has_successful_submission(
                connection,
                internal_team_id=account.id,
                subtask=subtask,
                submission_period_id=period.id,
            )

            if guard_errors:
                validation_errors = guard_errors
                validation_result = None
            else:
                try:
                    text = content.decode("utf-8-sig")
                except UnicodeDecodeError:
                    validation_errors = (
                        SubmissionValidationError(
                            field_name="file",
                            error_code="invalid_encoding",
                            message="Submission file must be UTF-8 encoded.",
                        ),
                    )
                    validation_result = None
                else:
                    validation_result = validate_submission_against_requirements(
                        text,
                        requirements,
                    )
                    validation_errors = validation_result.errors

            if not validation_errors and already_submitted:
                validation_errors = (
                    SubmissionValidationError(
                        field_name="file",
                        error_code="successful_submission_exists",
                        message=(
                            "A successful submission already exists for this subtask "
                            "and period."
                        ),
                    ),
                )

            submission_id = create_submission_attempt(
                connection,
                internal_team_id=account.id,
                subtask=subtask,
                submission_period_id=period.id,
                status="rejected" if validation_errors else "accepted",
                original_filename=filename or "submission.txt",
                file_size_bytes=len(content),
                stored_file_path=stored_file.path if stored_file is not None else None,
                file_sha256=stored_file.sha256 if stored_file is not None else None,
                validation_summary=(
                    f"{len(validation_errors)} validation error(s)."
                    if validation_errors
                    else "Submission accepted."
                ),
                ground_truth_version_id=(
                    validation_result.ground_truth_version_id
                    if validation_result is not None
                    else None
                ),
            )
            if validation_errors:
                persist_validation_errors(
                    connection,
                    submission_id=submission_id,
                    errors=validation_errors,
                )
                metrics = ()
            elif validation_result is not None:
                persist_submission_runs(
                    connection,
                    submission_id=submission_id,
                    parsed=validation_result.parsed,
                )
                ground_truth_version = get_ground_truth_version(
                    connection,
                    validation_result.ground_truth_version_id,
                )
                if ground_truth_version is None:
                    mark_evaluation_failed(connection, submission_id=submission_id)
                else:
                    metrics = evaluate_submission(
                        validation_result.parsed,
                        subtask=subtask,  # type: ignore[arg-type]
                        ground_truth_version=ground_truth_version,
                    )
                    persist_evaluation_results(
                        connection,
                        submission_id=submission_id,
                        ground_truth_version_id=ground_truth_version.id,
                        metrics=metrics,
                    )
                metrics = list_submission_results(connection, submission_id=submission_id)
            else:
                metrics = ()

        if validation_errors:
            return render_submission_upload(
                request,
                account=account,
                subtask=subtask,
                selected_period=selected_period,
                errors=validation_errors,
            )

        return render_submission_upload(
            request,
            account=account,
            subtask=subtask,
            selected_period=selected_period,
            metrics=metrics,
            success="Submission accepted and evaluated.",
        )

    @app.get("/admin", response_class=HTMLResponse)
    def admin_dashboard(request: Request) -> Response:
        account = get_session_account(request)
        if account is None:
            return redirect("/login")
        if account.role != "organizer":
            return redirect("/team")

        return templates.TemplateResponse(
            request,
            "admin_dashboard.html",
            {"app_name": app_settings.app_name, "account": account},
        )

    @app.get("/admin/teams", response_class=HTMLResponse)
    def admin_teams(request: Request) -> Response:
        account, redirect_response = require_organizer(request)
        if redirect_response is not None:
            return redirect_response
        return render_admin_teams(request, account=account)

    @app.post("/admin/teams", response_class=HTMLResponse)
    async def add_team(request: Request) -> Response:
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

    @app.post("/admin/teams/{team_id}/password", response_class=HTMLResponse)
    def regenerate_team_password(request: Request, team_id: str) -> Response:
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

    @app.get("/admin/users", response_class=HTMLResponse)
    def admin_users(request: Request) -> Response:
        account, redirect_response = require_organizer(request)
        if redirect_response is not None:
            return redirect_response
        return render_admin_users(request, account=account)

    @app.get("/admin/periods", response_class=HTMLResponse)
    def admin_periods(request: Request) -> Response:
        account, redirect_response = require_organizer(request)
        if redirect_response is not None:
            return redirect_response
        return render_periods(request, account=account)

    @app.get("/admin/submissions", response_class=HTMLResponse)
    def admin_submissions(request: Request) -> Response:
        account, redirect_response = require_organizer(request)
        if redirect_response is not None:
            return redirect_response
        return render_admin_submissions(request, account=account)

    @app.get("/admin/submissions/bundle.zip")
    def admin_submissions_bundle(request: Request) -> Response:
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

    @app.get("/admin/submissions/{submission_id}", response_class=HTMLResponse)
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

    @app.get("/admin/leaderboard", response_class=HTMLResponse)
    def admin_leaderboard(request: Request) -> Response:
        account, redirect_response = require_organizer(request)
        if redirect_response is not None:
            return redirect_response
        return render_admin_leaderboard(request, account=account)

    @app.get("/admin/leaderboard.csv")
    def admin_leaderboard_csv(request: Request) -> Response:
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

    @app.post("/admin/periods/{period_name}", response_class=HTMLResponse)
    async def update_period(request: Request, period_name: str) -> Response:
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

    @app.post("/admin/users", response_class=HTMLResponse)
    async def add_organizer(request: Request) -> Response:
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

    @app.post("/admin/users/{username}/password", response_class=HTMLResponse)
    def regenerate_organizer_password(request: Request, username: str) -> Response:
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

    @app.get("/account/password", response_class=HTMLResponse)
    def password_change_form(request: Request) -> Response:
        account, redirect_response = require_organizer(request)
        if redirect_response is not None:
            return redirect_response
        return render_password_change(request, account=account)

    @app.post("/account/password", response_class=HTMLResponse)
    async def password_change(request: Request) -> Response:
        account, redirect_response = require_organizer(request)
        if redirect_response is not None:
            return redirect_response

        form = await request.form()
        current_password = str(form.get("current_password", ""))
        new_password = str(form.get("new_password", ""))
        confirm_password = str(form.get("confirm_password", ""))

        if not current_password or not new_password or not confirm_password:
            return render_password_change(
                request,
                account=account,
                error="All password fields are required.",
            )

        if new_password != confirm_password:
            return render_password_change(
                request,
                account=account,
                error="New password and confirmation do not match.",
            )

        with connect(app_settings.database_path) as connection:
            changed = change_organizer_password(
                connection,
                organizer_id=account.id,
                current_password=current_password,
                new_password=new_password,
            )

        if not changed:
            return render_password_change(
                request,
                account=account,
                error="Current password is incorrect.",
            )

        return render_password_change(
            request,
            account=account,
            success="Password changed.",
        )

    @app.get("/admin/ground-truth", response_class=HTMLResponse)
    def ground_truth_page(request: Request) -> Response:
        account, redirect_response = require_organizer(request)
        if redirect_response is not None:
            return redirect_response
        return render_ground_truth(request, account=account)

    @app.post("/admin/ground-truth", response_class=HTMLResponse)
    async def upload_ground_truth(
        request: Request,
        subtask: Annotated[str, Form()],
        version_label: Annotated[str, Form()],
        file: Annotated[UploadFile, File()],
        notes: str = Form(""),
    ) -> Response:
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

    @app.post("/admin/ground-truth/{version_id}/activate", response_class=HTMLResponse)
    def activate_ground_truth(request: Request, version_id: int) -> Response:
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

    return app


app = create_app()
