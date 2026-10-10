"""Backend application factory and FastAPI instance."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from backend.app.middleware.error_handlers import register_exception_handlers
from backend.app.middleware.max_body import MaxBodySizeMiddleware
from backend.app.middleware.performance import PerformanceMiddleware
from backend.app.middleware.rate_limit import RateLimitMiddleware
from backend.app.middleware.request_id import RequestIDMiddleware
from backend.app.middleware.request_logging import RequestLoggingMiddleware
from backend.app.websocket.manager import manager as ws_manager
from backend.database import init_db
from backend.logging import configure_logging
from backend.settings import Settings, get_settings

settings = get_settings()
configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    """Initialize runtime dependencies before the application starts."""

    init_db()
    # Attach the running event loop to the WebSocket manager so simulation
    # threads can enqueue messages for broadcasting.
    try:
        loop = asyncio.get_running_loop()
        ws_manager.start(loop)
    except Exception:
        logger.exception("Failed to attach event loop to WebSocket manager")
    logger.info("QShield Twin backend initialized")
    try:
        yield
    finally:
        # Cancel the WebSocket consumer task so we do not leak background tasks
        # across application restarts.
        try:
            await ws_manager.shutdown()
        except Exception:
            logger.exception("Error during WebSocket manager shutdown")
        logger.info("QShield Twin backend shutdown complete")


def create_app(config: Settings | None = None) -> FastAPI:
    """Build the FastAPI application with all middleware and routers.

    ``config`` may be supplied to use a specific :class:`Settings` instance (used
    by tests to exercise auth/limit behaviour); otherwise the cached global
    settings are used. The resolved settings are stored on ``app.state.settings``
    so request-scoped dependencies read exactly the configuration in force.
    """

    from backend.router import router as versioned_router

    cfg = config or settings
    application = FastAPI(
        title=cfg.app_name,
        version=cfg.app_version,
        debug=cfg.debug,
        lifespan=lifespan,
        description="Quantum-resilient sybil defense research platform for virtual IoT networks.",
    )
    application.state.settings = cfg
    ws_manager.max_connections = cfg.max_ws_connections

    # Middlewares. Body-size and rate limiting are added first so they wrap the
    # request before heavier processing.
    application.add_middleware(MaxBodySizeMiddleware, max_bytes=cfg.max_request_bytes)
    application.add_middleware(
        RateLimitMiddleware,
        enabled=cfg.rate_limit_enabled,
        limit=cfg.rate_limit_requests,
        window_seconds=cfg.rate_limit_window_seconds,
    )
    application.add_middleware(GZipMiddleware, minimum_size=1000)
    # Only enable host checking when explicit hosts are configured. The default
    # "*" is intentionally permissive for local development; production
    # configuration validation forbids it.
    if "*" not in cfg.allowed_hosts:
        application.add_middleware(
            TrustedHostMiddleware, allowed_hosts=cfg.allowed_hosts
        )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    application.add_middleware(RequestIDMiddleware)
    application.add_middleware(PerformanceMiddleware)
    application.add_middleware(RequestLoggingMiddleware)

    application.include_router(versioned_router)
    register_exception_handlers(application)
    return application

