from __future__ import annotations

from fastapi import Request, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.accounts import get_organizer_account, get_team_account
from app.config import Settings
from app.db import connect
from app.sessions import SESSION_COOKIE, parse_session_value

templates = Jinja2Templates(directory="app/templates")


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
