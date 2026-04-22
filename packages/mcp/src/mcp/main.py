"""main.py

This module serves as the entry point for the MCP container proxy server.

Key Features:
- Initializes the FastAPI app for the MCP service.
- Mounts the container-control API router.

"""

from fastapi import FastAPI

from mcp.api import router

app = FastAPI(
    title="MCP Server",
    version="0.1.0",
)

app.include_router(router)
