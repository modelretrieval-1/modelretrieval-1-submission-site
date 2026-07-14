from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, Response

from app.accounts import get_team_subtasks
from app.config import Settings
from app.db import connect
from app.evaluation import (
    list_latest_team_submission_summaries,
    list_submission_results,
    pivot_evaluation_results,
)
from app.ground_truth import JST, get_active_ground_truth_requirements
from app.processing import process_submission
from app.submissions import (
    SubmissionValidationError,
    activate_current_submission,
    create_submission_attempt,
    get_current_successful_submission_id,
    get_resubmission_permission,
    get_submission_period_by_name,
    get_team_submission_status,
    get_unused_resubmission_permission_id,
    has_successful_submission,
    has_unused_resubmission_permission,
    is_submission_period_open,
    list_submission_periods,
    persist_submission_runs,
    persist_validation_errors,
    store_submission_file,
    validate_submission_against_requirements,
    validate_submission_size,
)
from app.web import get_session_account, redirect, require_team, templates

# Submission statuses that are still awaiting a terminal evaluation outcome.
IN_FLIGHT_STATUSES = ("queued", "processing")


def group_validation_errors(errors: tuple[SubmissionValidationError, ...]) -> tuple[dict, ...]:
    """Build stable, participant-facing validation error groups for templates."""
    labels = {
        "file": "File and format",
        "field_count": "File and format",
        "invalid_encoding": "File and format",
        "invalid_q0": "Field values",
        "invalid_rank": "Field values",
        "invalid_score": "Field values",
        "invalid_topic": "Field values",
        "invalid_doc": "Field values",
        "duplicate": "Ordering and duplicates",
        "rank_order": "Ordering and duplicates",
        "score_order": "Ordering and duplicates",
        "missing": "Completeness",
        "unknown": "Completeness",
        "run_limit": "Run limits",
        "successful_submission_exists": "Submission availability",
        "submission_period": "Submission period",
    }
    grouped: dict[str, list[SubmissionValidationError]] = {}
    for error in errors:
        category = next(
            (label for code, label in labels.items() if code in error.error_code),
            "Other validation issues",
        )
        grouped.setdefault(category, []).append(error)
    return tuple(
        {"label": label, "errors": tuple(items)} for label, items in grouped.items()
    )

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
    now_jst = datetime.now(JST)
    period_states = []
    with connect(app_settings.database_path) as connection:
        periods = list_submission_periods(connection)
        for period in periods:
            is_submitted = has_successful_submission(
                connection,
                internal_team_id=account.id,
                subtask=subtask,
                submission_period_id=period.id,
            )
            resubmission_allowed = has_unused_resubmission_permission(
                connection,
                internal_team_id=account.id,
                subtask=subtask,
                submission_period_id=period.id,
            )
            is_open = is_submission_period_open(period, now_jst=now_jst)
            can_submit = is_open and (not is_submitted or resubmission_allowed)
            state = (
                "reopened"
                if period.is_open_override
                else "open"
                if is_open
                else "closed"
            )
            period_states.append(
                {
                    "period": period,
                    "state": state,
                    "is_submitted": is_submitted,
                    "resubmission_allowed": resubmission_allowed,
                    "can_submit": can_submit,
                }
            )

    return templates.TemplateResponse(
        request,
        "team_submission_upload.html",
        {
            "app_name": app_settings.app_name,
            "account": account,
            "subtask": subtask,
            "periods": periods,
            "period_states": period_states,
            "selected_period": selected_period,
            "errors": errors,
            "error_groups": group_validation_errors(errors),
            "metrics": metrics,
            "metric_table": pivot_evaluation_results(tuple(metrics)),
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
        now_jst = datetime.now(JST)
        submission_slots = [
            {
                "subtask": subtask,
                "period": period,
                "is_open": is_submission_period_open(period, now_jst=now_jst),
                "is_submitted": has_successful_submission(
                    connection,
                    internal_team_id=account.id,
                    subtask=subtask,
                    submission_period_id=period.id,
                ),
                "resubmission_allowed": has_unused_resubmission_permission(
                    connection,
                    internal_team_id=account.id,
                    subtask=subtask,
                    submission_period_id=period.id,
                ),
            }
            for subtask in subtasks
            for period in periods
        ]
        for slot in submission_slots:
            slot["can_submit"] = slot["is_open"] and (
                not slot["is_submitted"] or slot["resubmission_allowed"]
            )
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
            "submission_slots": submission_slots,
            "available_submission_slots": sum(1 for slot in submission_slots if slot["can_submit"]),
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
    guard_errors = validate_submission_size(
        len(content),
        max_upload_bytes=app_settings.max_upload_bytes,
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
        current_submission_id = get_current_successful_submission_id(
            connection,
            internal_team_id=account.id,
            subtask=subtask,
            submission_period_id=period.id,
        )
        already_submitted = current_submission_id is not None
        resubmission_permission_id = get_unused_resubmission_permission_id(
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

        if not validation_errors and already_submitted and resubmission_permission_id is None:
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

        if validation_errors:
            submission_id = create_submission_attempt(
                connection,
                internal_team_id=account.id,
                subtask=subtask,
                submission_period_id=period.id,
                status="rejected",
                original_filename=filename or "submission.txt",
                file_size_bytes=len(content),
                stored_file_path=stored_file.path if stored_file is not None else None,
                file_sha256=stored_file.sha256 if stored_file is not None else None,
                validation_summary=f"{len(validation_errors)} validation error(s).",
                ground_truth_version_id=(
                    validation_result.ground_truth_version_id
                    if validation_result is not None
                    else None
                ),
            )
            persist_validation_errors(
                connection,
                submission_id=submission_id,
                errors=validation_errors,
            )
        else:
            # Validation passed. Reserve the slot as ``queued`` and defer the
            # slow scoring to the evaluation worker; the file, runs, supersession,
            # and replacement-permission consumption are all committed now.
            submission_id = create_submission_attempt(
                connection,
                internal_team_id=account.id,
                subtask=subtask,
                submission_period_id=period.id,
                status="queued",
                original_filename=filename or "submission.txt",
                file_size_bytes=len(content),
                stored_file_path=stored_file.path if stored_file is not None else None,
                file_sha256=stored_file.sha256 if stored_file is not None else None,
                validation_summary="Queued for evaluation.",
                ground_truth_version_id=validation_result.ground_truth_version_id,
            )
            persist_submission_runs(
                connection,
                submission_id=submission_id,
                parsed=validation_result.parsed,
            )
            permission = (
                get_resubmission_permission(
                    connection,
                    permission_id=resubmission_permission_id,
                )
                if resubmission_permission_id is not None
                else None
            )
            activate_current_submission(
                connection,
                submission_id=submission_id,
                superseded_submission_id=current_submission_id,
                resubmission_permission_id=resubmission_permission_id,
                organizer_id=permission.granted_by_organizer_id if permission else None,
                reason=permission.reason if permission else None,
            )

    if validation_errors:
        return render_submission_upload(
            request,
            account=account,
            subtask=subtask,
            selected_period=selected_period,
            errors=validation_errors,
        )

    # Evaluation is asynchronous. Eager mode drains the queue inline for
    # deterministic flows (tests, single-shot runs); worker mode leaves the
    # submission queued for the background thread. Either way, Post/Redirect/Get
    # sends the participant back to the dashboard, where the queued or completed
    # submission is included in the latest-submissions summary.
    if app_settings.evaluation_mode == "eager":
        process_submission(app_settings, submission_id)

    return redirect("/team")


@router.get("/team/submissions/{submission_id}", response_class=HTMLResponse)
def submission_status_page(request: Request, submission_id: int) -> Response:
    account, redirect_response = require_team(request)
    if redirect_response is not None:
        return redirect_response

    app_settings: Settings = request.app.state.settings
    with connect(app_settings.database_path) as connection:
        submission = get_team_submission_status(
            connection,
            submission_id=submission_id,
            internal_team_id=account.id,
        )
        if submission is None:
            return redirect("/team")
        metrics = list_submission_results(connection, submission_id=submission_id)

    is_terminal = submission.status not in IN_FLIGHT_STATUSES
    return templates.TemplateResponse(
        request,
        "team_submission_status.html",
        {
            "app_name": app_settings.app_name,
            "account": account,
            "submission": submission,
            "metrics": metrics,
            "metric_table": pivot_evaluation_results(tuple(metrics)),
            "is_terminal": is_terminal,
        },
    )


@router.get("/team/submissions/{submission_id}/status")
def submission_status_json(request: Request, submission_id: int) -> Response:
    account, redirect_response = require_team(request)
    if redirect_response is not None:
        return redirect_response

    app_settings: Settings = request.app.state.settings
    with connect(app_settings.database_path) as connection:
        submission = get_team_submission_status(
            connection,
            submission_id=submission_id,
            internal_team_id=account.id,
        )

    if submission is None:
        return JSONResponse({"error": "not_found"}, status_code=404)
    return JSONResponse({"status": submission.status, "summary": submission.validation_summary})
