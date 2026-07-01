from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, Response

from app.accounts import authenticate, change_organizer_password, change_team_password
from app.config import Settings
from app.db import connect
from app.sessions import SESSION_COOKIE, create_session_value
from app.web import get_session_account, redirect, templates

router = APIRouter()


def render_login(request: Request, *, error: str | None = None) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "login.html",
        {"app_name": request.app.state.settings.app_name, "error": error},
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


@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request, error: str | None = None) -> HTMLResponse:
    message = "Invalid user ID or password." if error == "invalid" else None
    return render_login(request, error=message)


@router.post("/login")
def login(request: Request, user_id: str = Form(...), password: str = Form(...)) -> Response:
    app_settings: Settings = request.app.state.settings
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


@router.get("/logout")
def logout() -> Response:
    response = redirect("/login")
    response.delete_cookie(SESSION_COOKIE)
    return response


@router.get("/account/password", response_class=HTMLResponse)
def password_change_form(request: Request) -> Response:
    account = get_session_account(request)
    if account is None:
        return redirect("/login")
    return render_password_change(request, account=account)


@router.post("/account/password", response_class=HTMLResponse)
async def password_change(request: Request) -> Response:
    app_settings: Settings = request.app.state.settings
    account = get_session_account(request)
    if account is None:
        return redirect("/login")

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
        if account.role == "organizer":
            changed = change_organizer_password(
                connection,
                organizer_id=account.id,
                current_password=current_password,
                new_password=new_password,
            )
        else:
            changed = change_team_password(
                connection,
                internal_team_id=account.id,
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
