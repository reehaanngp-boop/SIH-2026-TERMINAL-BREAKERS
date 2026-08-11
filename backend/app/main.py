"""FastAPI application factory for DigiRaksha."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import APP_NAME, __version__
from app.api.routes import (
    analyze,
    analytics,
    auth,
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
            "AI-based detection & awareness system against deepfake voice/video fraud "
            "and 'Digital Arrest' scams. Analyze a suspicious call recording, voice "
            "note or video clip and get an explainable risk score."
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
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API routes (registered first so they take precedence over the SPA mount).
    for router in (
        health.router,
        meta.router,
        auth.router,
        analyze.router,
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
        app.mount(
            "/",
            StaticFiles(directory=str(settings.static_dir), html=True),
            name="frontend",
        )

    return app


app = create_app()


def run() -> None:
    """Console entry point: ``digiraksha``."""
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
