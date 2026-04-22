"""v1.py

This module defines the v1 API router and its endpoints.

Key Features:
- Registers actor and conversation route groups.
- Exposes the AI agent graph visualization endpoint.
- Provides an MCP command execution endpoint.
- Handles WebSocket-based terminal emulation sessions.

"""

import json

from backend.dependencies import ChatServiceDep, McpServiceDep
from backend.services.mcp import McpService
from backend.shell_emulator import EmulatorAction, ShellEmulator
from backend.transfer_models import McpExecuteRequest
from fastapi import APIRouter, HTTPException, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

from .routes import actors, conversations

router = APIRouter(prefix="/v1")

router.include_router(actors.router)
router.include_router(conversations.router)


@router.get("/graph")
def read_graph(chat_service: ChatServiceDep):
    img_bytes = chat_service.get_graph()
    return Response(content=img_bytes, media_type="image/png")


@router.post("/execute")
async def execute(req: McpExecuteRequest, mcp_service: McpServiceDep):
    try:
        result = await mcp_service.execute_command(req.container, req.command)
        return result
    except ConnectionError as e:
        port = f":{e.port}" if e.port else ""
        raise HTTPException(
            status_code=504, detail=f"Could not connect to {e.host}{port}"
        )


@router.get("/stream/agent-info")
async def agent_info(chat_service: ChatServiceDep):
    async def event_loop():
        listener_id = chat_service.agent_graph.add_listener("state_transition")

        try:
            while True:
                # print(f"waiting for data on id {listener_id}")
                event_data = await chat_service.agent_graph.wait_for_event(listener_id)
                # print(f"obtained data {event_data}")

                yield f"event: state_transition\ndata: {json.dumps(event_data)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        finally:
            chat_service.agent_graph.remove_listener(listener_id)

    return StreamingResponse(
        event_loop(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.websocket("/termws")
async def term_websocket(websocket: WebSocket):
    mcp_service: McpService = websocket.state.mcp_service
    emulator = ShellEmulator(websocket)
    await emulator.accept()

    try:
        while True:
            text = await websocket.receive_text()

            action, text = emulator.handle_input(text)

            match action:
                case EmulatorAction.DISPLAY:
                    # print(text.encode())
                    await websocket.send_text(text)
                case EmulatorAction.SEND_COMMAND:
                    await websocket.send_text("\r\n")
                    try:
                        cmd_elements = text.split()
                        if cmd_elements:
                            if await emulator.handle_fake_command(cmd_elements):
                                continue

                            if not emulator.connected_pty:
                                containers = await mcp_service.get_running_containers()
                                cons = json.dumps(containers, indent=2)
                                await websocket.send_text(
                                    "Not connected to a pty. First, run `connect "
                                    "<container>` to connect to one of the following "
                                    f"containers:{cons}"
                                )
                                continue

                            output = await mcp_service.execute_command(
                                emulator.connected_pty, cmd_elements
                            )
                            await websocket.send_text(f"{output['output']}")
                    except ConnectionError as e:
                        await websocket.send_text(
                            f"Could not connect to mcp server at {e.host}:{e.port}"
                        )
                    await websocket.send_text(f"\r\n{emulator.get_prompt()}")
    except WebSocketDisconnect:
        pass
