"""FastAPI application factory for DigiRaksha."""

from __future__ import annotations

from contextlib import asynccontextmanager
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")

from fastapi import FastAPI, Response
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import APP_NAME, __version__
from app.api.routes import (
    analyze,
    analytics,
    assistant,
    auth,
    blockchain,
    bulk,
    cases,
    evidence,
    export,
    health,
    meta,
    people,
    phone,
    registry,
    reports,
    stream,
    voice_match,
)
from app.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.db.database import init_db

settings = get_settings()


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        init_db()
        yield

    app = FastAPI(
        title=APP_NAME,
        version=__version__,
        description=(
            "AI-Powered Real-Time Detection & Prevention of Voice Cloning Impersonation Attacks "
            "(SIH PS 26104 / AICTE Cyber Security Cell). Analyze live telephony/VoIP streams, "
            "detect neural vocoder artifacts & prosody anomalies, verify CXO identities, and anchor "
            "forensic certificates on an immutable blockchain ledger."
        ),
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    register_exception_handlers(app)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_origin_regex=r"^https://.*\.pages\.dev$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def add_no_cache_header(request, call_next):
        response = await call_next(request)
        path = request.url.path
        if path == "/" or path.startswith("/assets") or path.endswith(".html") or path.endswith(".js") or path.endswith(".css"):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon() -> Response:
        return Response(status_code=204)

    # API routes (registered first so they take precedence over the SPA mount).
    for router in (
        health.router,
        meta.router,
        stream.router,
        blockchain.router,
        auth.router,
        analyze.router,
        assistant.router,
        registry.router,
        cases.router,
        evidence.router,
        people.router,
        voice_match.router,
        phone.router,
        analytics.router,
        reports.router,
        export.router,
        bulk.router,
    ):
        app.include_router(router, prefix=settings.api_prefix)

    # Serve the built React frontend if it exists (production / demo mode).
    index_html = settings.static_dir / "index.html"
    if index_html.exists():
        assets_dir = settings.static_dir / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        async def spa_fallback(full_path: str) -> Response:
            target_path = (settings.static_dir / full_path).resolve()
            try:
                target_path.relative_to(settings.static_dir.resolve())
            except ValueError:
                return FileResponse(index_html)

            if full_path and target_path.is_file():
                return FileResponse(target_path)
            return FileResponse(index_html)

    return app


app = create_app()


def run() -> None:
    """Console entry point: ``digiraksha``."""
    import os
    import threading
    import time
    import webbrowser
    import uvicorn

    # Automatically open the web browser when launched via console/shortcut
    if os.environ.get("DIGIRAKSHA_NO_BROWSER", "").lower() not in ("1", "true"):
        def _open_browser() -> None:
            time.sleep(1.5)
            try:
                webbrowser.open("http://127.0.0.1:8000")
            except Exception:
                pass

        threading.Thread(target=_open_browser, daemon=True).start()

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )


if __name__ == "__main__":
    run()

