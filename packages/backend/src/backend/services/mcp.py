"""mcp.py

This module provides a client service for communicating with the MCP server.

Key Features:
- Execute shell commands inside Docker containers.
- List running containers and their network info.
- Graceful connection and session management.

"""

from typing import List, Optional

from aiohttp import ClientConnectorError, ClientSession

from backend.config import settings


class ConnectionError(Exception):
    """Generic exception class for connection errors."""

    host: str
    port: Optional[int]

    def __init__(self, host: str, port: Optional[int] = None, *args):
        super().__init__(*args)
        self.host = host
        self.port = port


class McpService:
    def __init__(self):
        self.session = None

    def _make_connection(self):
        if not self.session:
            self.session = ClientSession(
                base_url=settings.get_mcp_url(), trust_env=True
            )
        return self.session

    async def execute_command(self, container: str, command: List[str]):
        session = self._make_connection()
        data = {
            "container": container,
            "cmd": command,
        }
        try:
            async with session.post("/exec", json=data) as resp:
                return await resp.json()
        except ClientConnectorError as e:
            print(e)
            raise ConnectionError(e.host, e.port)

    async def get_running_containers(self):
        session = self._make_connection()
        try:
            async with session.get("/containers") as resp:
                json_resp = await resp.json()
                running_containers = []
                for c in json_resp["containers"]:
                    if c["status"] == "running":
                        running_containers.append({"id": c["id"], "name": c["name"]})

                return running_containers
        except ClientConnectorError as e:
            print(e)
            raise ConnectionError(e.host, e.port)

    async def shutdown(self):
        if self.session:
            await self.session.close()
