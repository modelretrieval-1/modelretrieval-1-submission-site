from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, Response

from app.accounts import get_team_subtasks
from app.config import Settings
from app.db import connect
from app.evaluation import (
    evaluate_submission,
    list_latest_team_submission_summaries,
    list_submission_results,
    mark_evaluation_failed,
    persist_evaluation_results,
)
from app.ground_truth import JST, get_active_ground_truth_requirements, get_ground_truth_version
from app.submissions import (
    SubmissionValidationError,
    create_submission_attempt,
    get_submission_period_by_name,
    has_successful_submission,
    is_submission_period_open,
    list_submission_periods,
    persist_submission_runs,
    persist_validation_errors,
    store_submission_file,
    validate_submission_against_requirements,
    validate_submission_filename,
    validate_submission_size,
)
from app.web import get_session_account, redirect, require_team, templates

router = APIRouter()


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


@router.get("/team", response_class=HTMLResponse)
def team_dashboard(request: Request) -> Response:
    app_settings: Settings = request.app.state.settings
    account = get_session_account(request)
    if account is None:
        return redirect("/login")
    if account.role != "team":
        return redirect("/admin")

    with connect(app_settings.database_path) as connection:
        subtasks = sorted(get_team_subtasks(connection, account.id))
        periods = list_submission_periods(connection)
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
            "periods": periods,
            "submission_summaries": submission_summaries,
        },
    )


@router.get("/team/submissions/new")
def submission_upload_redirect(request: Request) -> Response:
    account, redirect_response = require_team(request)
    if redirect_response is not None:
        return redirect_response

    app_settings: Settings = request.app.state.settings
    with connect(app_settings.database_path) as connection:
        subtasks = sorted(get_team_subtasks(connection, account.id))

    if not subtasks:
        return redirect("/team")
    return redirect(f"/team/submissions/{subtasks[0]}/new")


@router.get("/team/submissions/{subtask}/new", response_class=HTMLResponse)
def submission_upload_page(request: Request, subtask: str) -> Response:
    app_settings: Settings = request.app.state.settings
    account, redirect_response = require_team(request)
    if redirect_response is not None:
        return redirect_response

    subtask = subtask.strip().upper()
    with connect(app_settings.database_path) as connection:
        subtasks = get_team_subtasks(connection, account.id)

    if subtask not in subtasks:
        return redirect("/team")

    return render_submission_upload(request, account=account, subtask=subtask)


@router.post("/team/submissions/{subtask}/new", response_class=HTMLResponse)
async def upload_submission(
    request: Request,
    subtask: str,
    file: Annotated[UploadFile, File()],
    submission_period: Annotated[str, Form()] = "",
) -> Response:
    app_settings: Settings = request.app.state.settings
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
