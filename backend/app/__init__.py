"""Backend application factory and FastAPI instance."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from backend.database import init_db
from backend.logging import configure_logging
from backend.settings import get_settings
from backend.app.middleware.error_handlers import register_exception_handlers
from backend.app.middleware.request_id import RequestIDMiddleware
from backend.app.middleware.request_logging import RequestLoggingMiddleware
from backend.app.middleware.performance import PerformanceMiddleware
from backend.app.websocket.manager import manager as ws_manager
import asyncio

settings = get_settings()
configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    """Initialize runtime dependencies before the application starts."""

    init_db()
    # Attach the FastAPI event loop to the WebSocket manager so simulation
    # threads can enqueue messages for broadcasting.
    try:
        loop = asyncio.get_event_loop()
        ws_manager.set_event_loop(loop)
    except Exception:
        logger.exception("Failed to attach event loop to WebSocket manager")
    logger.info("QShield Twin backend initialized")
    yield
    logger.info("QShield Twin backend shutdown complete")


def create_app() -> FastAPI:
    """Build the FastAPI application with all middleware and routers."""

    from backend.router import router as versioned_router

    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
        description="Quantum-resilient sybil defense research platform for virtual IoT networks.",
    )

    # Middlewares
    application.add_middleware(GZipMiddleware, minimum_size=1000)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.add_middleware(RequestIDMiddleware)
    application.add_middleware(PerformanceMiddleware)
    application.add_middleware(RequestLoggingMiddleware)

    application.include_router(versioned_router)
    register_exception_handlers(application)
    return application

