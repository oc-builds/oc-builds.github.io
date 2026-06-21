"""FastAPI entry point.

Author: Sanjay Chauhan
Date:   2026-06-07
CS499 Enhancement Three rebuild of the CS340 Austin Animal Center project.

The Mongo client lifecycle lives in the lifespan context manager. This was
called out explicitly in Dr. Bolton's M2/M3 polish guidance: resources have
deterministic ownership, no module-global handles. On startup we connect,
build the Repository, attach it to app.state. On shutdown we close the
client. The original notebook had no shutdown path at all.

The exception handler returns JSON in the shape `{error: "..."}` with the
appropriate HTTP status. The original code's silent `try/except: return
False` made debugging awful; here, errors propagate, get logged, and the
caller sees a useful structured response.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pymongo import MongoClient
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import settings
from .db import build_repository
from .db_provider import ClientFactory
from .routes_animals import router as animals_router
from .routes_auth import limiter, router as auth_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Own the MongoClient for the lifetime of the process.

    Why a single client: PyMongo's MongoClient is itself a connection pool.
    Constructing a fresh client per request was a common antipattern in the
    original codebase ecosystem and produced socket exhaustion under load.
    """
    logger.info("connecting to MongoDB at %s", _safe_uri(settings.mongo_uri))
    client = MongoClient(settings.mongo_uri)
    db = client[settings.db_name]
    repo = build_repository(
        db,
        animals_collection=settings.animals_collection,
        users_collection=settings.users_collection,
        audit_collection=settings.audit_collection,
    )
    # M7 DB-tier isolation: the ClientFactory hands out a Repository bound to
    # a role-appropriate connection pool. In fallback mode (no per-role URIs
    # configured) it resolves every role to the same service account, so this
    # is strictly additive -- the legacy app.state.repository below still
    # exists and still works. Routes prefer the factory when present.
    factory = ClientFactory()
    app.state.mongo_client = client
    app.state.repository = repo
    app.state.client_factory = factory
    try:
        yield
    finally:
        logger.info("closing MongoDB client(s)")
        client.close()
        factory.close()


def _safe_uri(uri: str) -> str:
    """Strip credentials from a Mongo URI before logging."""
    if "@" in uri:
        scheme_and_creds, host = uri.split("@", 1)
        scheme = scheme_and_creds.split("//", 1)[0]
        return f"{scheme}//<redacted>@{host}"
    return uri


def create_app() -> FastAPI:
    app = FastAPI(
        title="Austin Animal Center API (CS499 Enhancement Three)",
        version="0.1.0",
        description=(
            "MongoDB-backed shelter service. CS499 rebuild of the CS340 "
            "Austin Animal Center project. The OpenAPI document at "
            "/openapi.json is the explicit interface contract."
        ),
        lifespan=lifespan,
    )

    # slowapi wiring: attach the limiter so the @limiter.limit decorators
    # in routes_auth resolve. The default handler returns 429.
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.include_router(auth_router)
    app.include_router(animals_router)

    # Structured error envelope. The original code swallowed exceptions
    # silently; here we make sure callers always see {error: "..."} with
    # a real HTTP status code.

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.detail},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # exc.errors() can include ValueError instances under the "ctx"
        # key when a custom field_validator raised one (e.g. GeoPoint).
        # Coerce non-JSON-serializable contents to str so the envelope is
        # always renderable. The original silent try/except in the CS340
        # notebook is exactly the failure mode we are NOT going to repeat.
        safe_details = []
        for err in exc.errors():
            entry = dict(err)
            ctx = entry.get("ctx")
            if isinstance(ctx, dict):
                entry["ctx"] = {k: str(v) for k, v in ctx.items()}
            safe_details.append(entry)
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": "validation failed", "details": safe_details},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.exception("unhandled exception: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "internal server error"},
        )

    return app


app = create_app()
