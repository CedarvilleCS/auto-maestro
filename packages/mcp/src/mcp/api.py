"""api.py

This module defines the MCP API routes for Docker container interaction.

Key Features:
- List running containers and their network addresses.
- Execute arbitrary commands inside a named container.
- Ping a target from within a container.
- Forward ports between containers.

"""

import requests
from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool

from mcp import docker_client

router = APIRouter()


@router.get("/containers")
async def containers():
    try:
        data = await run_in_threadpool(docker_client.list_containers)
        return {"status": "ok", "containers": data}
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@router.post("/exec")
async def exec_cmd(payload: dict):
    container = payload.get("container")
    cmd = payload.get("cmd")

    if not container or not cmd:
        raise HTTPException(400, detail="container and cmd are required")

    try:
        output = await run_in_threadpool(docker_client.exec_command, container, cmd)
        return {"status": "ok", "output": output}
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@router.post("/ping")
async def ping(payload: dict):
    container = payload.get("container")
    target = payload.get("target")

    if not container or not target:
        raise HTTPException(400, detail="container and target are required")

    try:
        output = await run_in_threadpool(docker_client.ping, container, target)
        return {"status": "ok", "output": output}
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@router.post("/forward")
async def forward(payload: dict):
    container = payload.get("container")
    url = payload.get("url")

    if not container or not url:
        raise HTTPException(400, detail="container and url are required")

    try:
        ip = await run_in_threadpool(docker_client.resolve_container_ip, container)
        target_url = url.replace("localhost", ip)
        r = requests.get(target_url, timeout=5)
        return {
            "status": "ok",
            "forwarded_url": target_url,
            "response": r.text,
        }
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@router.get("/health")
async def health():
    return {"status": "alive"}
