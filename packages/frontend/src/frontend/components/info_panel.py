"""info_panel.py

This module implements the info/log panel UI component using NiceGUI.

Key Features:
- Streams and displays live agent state output from the backend.
- Provides a scrollable log view.

"""

from typing import Optional

from aiohttp import ClientSession
from nicegui import Client, ui


class Info:
    def __init__(self):
        with (
            ui.column()
            .classes("w-full overflow-hidden")
            .style(
                "height: 180px; min-height: 180px; max-height: 180px;"
                " gap: 0; background-color: var(--color-surface);"
                " border-top: 1px solid var(--color-border);"
            )
        ):
            with (
                ui.row()
                .classes("am-panel-header w-full items-center")
                .style("flex-shrink: 0;")
            ):
                ui.icon("memory").style(
                    "color: var(--color-accent); font-size: 0.9rem; margin-right: 6px;"
                )
                ui.label("AGENT STATE").style(
                    "font-family: var(--font-mono); font-size: 0.7rem;"
                    " letter-spacing: 0.12em; color: var(--color-accent);"
                )

            self.log = (
                ui.log()
                .classes("w-full flex-1")
                .style(
                    "min-height: 0; background-color: var(--color-base);"
                    " color: var(--color-accent); font-family: var(--font-mono);"
                    " font-size: 0.72rem; border: none; padding: 6px 10px;"
                )
            )

    def clear(self):
        self.log.clear()

    async def start_state_visualization(self, client: Client):
        session: Optional[ClientSession] = client.storage.get("session", None)
        if not session:
            raise ValueError("Cannot start visualization")

        try:
            async with session.get("/api/v1/stream/agent-info") as stream:
                async for line in stream.content:
                    line = line.decode()
                    if line == "\n":
                        continue
                    self.log.push(line)
        except Exception as e:
            raise e
