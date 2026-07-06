from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

from app.config import Settings, settings
from app.db import initialize_database, verify_database_current
from app.routes.admin import router as admin_router
from app.routes.auth import router as auth_router
from app.routes.team import router as team_router
from app.storage import ensure_storage
from app.web import get_session_account, redirect, templates


def build_lifespan(app_settings: Settings):
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        ensure_storage(app_settings)
        if app_settings.environment in {"staging", "production"}:
            verify_database_current(app_settings.database_path)
        else:
            initialize_database(app_settings.database_path)
        yield

    return lifespan


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

    app.include_router(auth_router)
    app.include_router(team_router)
    app.include_router(admin_router)

    return app


app = create_app()
