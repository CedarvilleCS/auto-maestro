from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from aiohttp import ClientSession
from nicegui import Client, ui

if TYPE_CHECKING:
    from frontend.components.chat_panel import Chat


def _format_date(date_str: Optional[str]) -> str:
    if not date_str:
        return ""
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        delta = now - dt
        if delta.days == 0:
            return "today"
        if delta.days == 1:
            return "yesterday"
        if delta.days < 7:
            return f"{delta.days}d ago"
        if delta.days < 30:
            return f"{delta.days // 7}w ago"
        return dt.strftime("%b %d")
    except Exception:
        return ""


class Sidebar:
    def __init__(self, chat: "Chat", drawer: ui.left_drawer, client: Client):
        self._chat = chat
        self._drawer = drawer
        self._client = client
        self._conversations: List[Dict[str, Any]] = []

        with (
            ui.column()
            .classes("w-full h-full")
            .style("background-color: var(--color-panel); gap: 0; overflow: hidden;")
        ):
            with (
                ui.row()
                .classes("am-panel-header w-full items-center")
                .style("border-top: 2px solid var(--color-accent);")
            ):
                ui.label("AutoMaestro").style(
                    "font-family: var(--font-display); font-size: 0.9rem;"
                    " font-weight: 700; color: var(--color-accent);"
                    " letter-spacing: 0.1em;"
                )

            ui.button("+ New Chat", on_click=self._new_chat).classes(
                "am-btn-primary w-full"
            ).style("margin: 12px; width: calc(100% - 24px);").props("no-caps")

            with (
                ui.row()
                .classes("items-center px-3 py-2")
                .style("border-bottom: 1px solid var(--color-border);")
            ):
                ui.label("CONVERSATIONS").style(
                    "font-family: var(--font-mono); font-size: 0.65rem;"
                    " letter-spacing: 0.12em; color: var(--color-muted); flex: 1;"
                )
                ui.button(icon="refresh", on_click=self._load_conversations).classes(
                    "am-btn-icon"
                ).props("flat dense size=xs")

            self._list_container = (
                ui.column()
                .classes("w-full overflow-y-auto")
                .style("flex: 1; gap: 0; min-height: 0;")
            )

        ui.timer(0.1, self._load_conversations, once=True)

    async def _new_chat(self):
        self._drawer.hide()
        await self._chat.new_conversation(self._client)

    async def _load_conversations(self):
        session: Optional[ClientSession] = self._client.storage.get("session", None)
        if not session:
            return

        try:
            async with session.get(
                "/api/v1/conversations/",
                params={
                    "order_by": "last_activity_at",
                    "order_in": -1,
                    "limit": 50,
                },
            ) as response:
                if response.status >= 400:
                    return
                data = await response.json()
                self._conversations = data.get("conversations", [])
        except Exception:
            return

        self._render_conversations()

    @ui.refreshable
    def _render_conversations(self):
        self._list_container.clear()
        with self._list_container:
            if not self._conversations:
                ui.label("No conversations yet").style(
                    "color: var(--color-muted); font-size: 0.75rem;"
                    " padding: 16px; font-family: var(--font-mono);"
                )
                return

            active_id = ""
            current = self._client.storage.get("current_conversation")
            if current:
                active_id = str(current.get("id", current.get("_id", "")))

            for conv in self._conversations:
                conv_id = str(conv.get("_id", conv.get("id", "")))
                topic = conv.get("topic") or "Untitled conversation"
                date_str = conv.get("last_activity_at") or conv.get("created_at") or ""
                date_label = _format_date(date_str)
                is_active = conv_id == active_id

                item_classes = "am-conv-item w-full"
                if is_active:
                    item_classes += " am-conv-active"

                with (
                    ui.column()
                    .classes(item_classes)
                    .style("gap: 2px;")
                    .on("click", lambda _cid=conv_id: self._select_conversation(_cid))
                ):
                    ui.label(topic).style(
                        "font-family: var(--font-mono); font-size: 0.78rem;"
                        " color: var(--color-primary); white-space: nowrap;"
                        " overflow: hidden; text-overflow: ellipsis; max-width: 200px;"
                    )
                    ui.label(date_label).style(
                        "font-family: var(--font-mono); font-size: 0.65rem;"
                        " color: var(--color-muted);"
                    )

    def _select_conversation(self, conv_id: str):
        self._drawer.hide()
        import asyncio

        asyncio.create_task(self._load_and_switch(conv_id))

    async def _load_and_switch(self, conv_id: str):
        await self._chat.load_conversation_by_id(conv_id, self._client)
        self._render_conversations.refresh()
