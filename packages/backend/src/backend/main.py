"""main.py

This module serves as the entry point for the FastAPI application.

Key Features:
- Initializes the FastAPI app with a custom lifespan context manager.
- Adds middleware for wide-event request logging.
- Registers versioned API routers.

"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from backend.api import api
from backend.services.database import DatabaseService

from .services import ChatService, McpService

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db_service = DatabaseService()
    mcp_service = McpService()
    chat_service = ChatService(mcp_service=mcp_service)
    yield {
        "chat_service": chat_service,
        "mcp_service": mcp_service,
        "db_service": db_service,
    }
    await db_service.shutdown()
    await mcp_service.shutdown()


app = FastAPI(
    lifespan=lifespan,
    version="1.0.0",
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/v1/docs",
)


@app.middleware("http")
async def wide_event_log(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
):
    start_time = time.perf_counter()
    client = request.client
    wide_event = {
        "method": request.method,
        "path": request.url.path,
        "client_ip": client.host if client else None,
        "client_port": client.port if client else None,
        "headers": dict(request.headers),
    }

    if request.query_params:
        wide_event["query_params"] = dict(request.query_params)

    request.state.wide_event = wide_event

    response = None
    try:
        response = await call_next(request)
        wide_event["status_code"] = response.status_code
        wide_event["outcome"] = "success"
    except Exception as e:
        logger.exception(
            "Unhandled request failure for %s %s", request.method, request.url.path
        )
        wide_event["status_code"] = 500
        wide_event["outcome"] = "error"
        wide_event["error_type"] = str(type(e))
        wide_event["error_message"] = repr(e)
        response = JSONResponse({"outcome": "error", "error": repr(e)}, 500)
    finally:
        duration_ms = (time.perf_counter() - start_time) * 1000
        wide_event["duration_ms"] = duration_ms
        if response is None:
            response = JSONResponse({"outcome": "error", "error": "unknown"}, 500)
        response.headers.append("X-Process-Time", str(duration_ms))

        db: DatabaseService | None = getattr(request.state, "db_service", None)
        if db is not None:
            asyncio.create_task(db.create_wide_event(wide_event))
        else:
            logger.warning("Database service missing from request.state during logging")
    return response


app.include_router(api.router)
