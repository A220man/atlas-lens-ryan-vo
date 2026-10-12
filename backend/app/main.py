"""Main application entrypoint exporting FastAPI app and create_app factory.

Docker containers and local CLI environments invoke the exact same entrypoint:
uvicorn app.main:app --host 127.0.0.1 --port 8000
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.audit import router as audit_router
from app.api.auth import router as auth_router
from app.api.chats import router as chats_router
from app.api.evaluations import router as eval_router
from app.api.hygiene import router as hygiene_router
from app.api.mcp import router as mcp_router
from app.core.config import Settings, get_settings
from app.core.database import init_database


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager for startup and shutdown routines."""
    settings = get_settings()
    # Initialize SQLite tables and schemas
    init_database(settings)
    yield


def create_app(settings: Settings | None = None) -> FastAPI:
    """Documented factory creating configured FastAPI instance."""
    if settings is None:
        settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Observability and prompt hygiene workbench for local and cloud LLMs",
        lifespan=lifespan,
    )

    # Configure CORS for local development and SPA frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:3000",
            "http://localhost:3000",
            "http://127.0.0.1:8000",
            "http://localhost:8000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health check endpoint
    @app.get("/api/health", tags=["Health"])
    def health_check() -> Dict[str, str]:
        """Health check endpoint for Docker and monitoring."""
        return {
            "status": "healthy",
            "app": settings.app_name,
            "version": settings.app_version,
            "env": settings.app_env,
            "demo_mode": str(settings.demo_mode).lower(),
        }

    # Mount API routers
    app.include_router(auth_router)
    app.include_router(chats_router)
    app.include_router(hygiene_router)
    app.include_router(mcp_router)
    app.include_router(eval_router)
    app.include_router(audit_router)

    # Global unhandled exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error occurred.", "error_type": type(exc).__name__}
        )

    return app


# Module-level app instance for uvicorn
app = create_app()
