"""terminal_panel.py

This module implements the terminal panel UI component using NiceGUI.

Key Features:
- Connects to the backend WebSocket terminal endpoint.
- Renders an interactive xterm.js terminal in the browser.
- Handles reconnection on Enter if disconnected.

"""

from typing import Final, Optional

from aiohttp import ClientConnectorError, ClientSession, WSMsgType
from nicegui import Client, ui
from nicegui.events import XtermDataEventArguments

FAILED_TO_CONNECT_MSG: Final[str] = (
    "Could not connect to orchestrator. Please check your network connection "
    "or that the orchestrator backend is running. Press 'Enter' to retry."
)

_XTERM_THEME = {
    "background": "#001e36",
    "foreground": "#e8edf2",
    "cursor": "#ffa700",
    "cursorAccent": "#001e36",
    "selectionBackground": "rgba(255,167,0,0.25)",
    "black": "#001e36",
    "brightBlack": "#4a6a80",
    "red": "#ff4444",
    "brightRed": "#ff6666",
    "green": "#3ddc84",
    "brightGreen": "#5fffaa",
    "yellow": "#ffa700",
    "brightYellow": "#ffcc44",
    "blue": "#4a9eff",
    "brightBlue": "#7bbfff",
    "magenta": "#c97bff",
    "brightMagenta": "#e0aaff",
    "cyan": "#00d4cc",
    "brightCyan": "#44ffee",
    "white": "#8fb3cc",
    "brightWhite": "#e8edf2",
}


class Terminal:
    def __init__(self):
        self._status_dot: Optional[ui.element] = None

        with (
            ui.column()
            .classes("flex-1 w-full overflow-hidden")
            .style(
                "gap: 0; background-color: var(--color-surface);"
                " border-bottom: 1px solid var(--color-border);"
            )
        ):
            with (
                ui.row()
                .classes("am-panel-header w-full items-center")
                .style("flex-shrink: 0;")
            ):
                ui.icon("terminal").style(
                    "color: var(--color-accent); font-size: 0.9rem; margin-right: 6px;"
                )
                ui.label("TERMINAL").style(
                    "font-family: var(--font-mono); font-size: 0.7rem;"
                    " letter-spacing: 0.12em; color: var(--color-accent); flex: 1;"
                )
                self._status_dot = ui.element("span").classes("am-status-dot")

            with (
                ui.column()
                .classes("w-full flex-1 overflow-hidden")
                .style("min-height: 0; padding: 4px;")
            ):
                self.terminal = ui.xterm(
                    {
                        "convertEol": True,
                        "windowsMode": True,
                        "theme": _XTERM_THEME,
                        "fontFamily": "'IBM Plex Mono', monospace",
                        "fontSize": 13,
                        "lineHeight": 1.4,
                        "cursorBlink": True,
                        "cursorStyle": "bar",
                    }
                ).classes("w-full h-full flex-1")

                @self.terminal.on_data
                async def _not_connected(event: XtermDataEventArguments):
                    client = event.client
                    if (
                        not client.storage.get("terminal_conn", False)
                        and event.data == "\r"
                    ):
                        await self.start_term_emulation(client)

    def _set_status(self, connected: bool) -> None:
        if self._status_dot is None:
            return
        if connected:
            self._status_dot.classes(add="connected", remove="error")
        else:
            self._status_dot.classes(add="error", remove="connected")

    async def start_term_emulation(self, client: Client):
        await self.terminal.run_terminal_method("reset")
        await self.terminal.write("Connecting to orchestrator...")
        self._set_status(False)
        session: Optional[ClientSession] = client.storage.get("session", None)
        if not session:
            await self.terminal.run_terminal_method("reset")
            self.terminal.write(FAILED_TO_CONNECT_MSG)
            client.storage["terminal_conn"] = False
            return
        try:
            async with session.ws_connect("/api/v1/termws", heartbeat=1) as ws:
                client.storage["terminal_conn"] = True
                self._set_status(True)

                @self.terminal.on_data
                async def _terminal_to_backend(
                    event: XtermDataEventArguments,
                ):
                    if not ws.closed:
                        await ws.send_str(event.data)

                while not ws.closed:
                    msg = await ws.receive()
                    match msg.type:
                        case WSMsgType.TEXT:
                            await self.terminal.write(msg.data)
        except ClientConnectorError:
            await self.terminal.run_terminal_method("reset")
            self.terminal.write(FAILED_TO_CONNECT_MSG)
            client.storage["terminal_conn"] = False
            self._set_status(False)
