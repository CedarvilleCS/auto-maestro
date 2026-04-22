"""dependencies.py

This module provides FastAPI dependency functions for service injection.

Key Features:
- Retrieves ChatService, McpService, and DatabaseService from request state.
- Provides typed Annotated dependency aliases for use in route handlers.

"""

from typing import Annotated

from fastapi import Depends, Request

from backend.services.database import DatabaseService

from .services import ChatService, McpService


def get_chat_service(request: Request):
    if not hasattr(request.state, "chat_service"):
        raise ValueError("Chat service could not be found")
    return request.state.chat_service


def get_mcp_service(request: Request):
    if not hasattr(request.state, "mcp_service"):
        raise ValueError("MCP service could not be found")
    return request.state.mcp_service


def get_database_service(request: Request):
    if not hasattr(request.state, "db_service"):
        raise ValueError("Database service could not be found")
    return request.state.db_service


ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]
McpServiceDep = Annotated[McpService, Depends(get_mcp_service)]
DbServiceDep = Annotated[DatabaseService, Depends(get_database_service)]
