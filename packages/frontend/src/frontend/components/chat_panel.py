"""chat_panel.py

This module implements the chat panel UI component using NiceGUI.

Key Features:
- Displays conversation messages from both user and AI.
- Sends new user messages to the backend API.
- Supports starting new conversations.

"""

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, List

from aiohttp import ClientResponseError, ClientSession, ContentTypeError
from nicegui import ui
from nicegui.client import Client
from nicegui.events import ClickEventArguments, GenericEventArguments


@dataclass
class BaseMessage:
    name: str | None
    content: str | None


@dataclass
class BotMessage(BaseMessage):
    reasoning: str | None = None


@dataclass
class HumanMessage(BaseMessage):
    pass


class Chat:
    def __init__(self, client: Client, info_panel: Any | None = None):
        self._client = client
        self.messages: List[BaseMessage] = []

        self.info_panel = info_panel
        self._new_chat_in_progress = False
        with ui.column().classes(
            "flex-1 basis-1/2 flex flex-col h-full max-h-full overflow-hidden \
                 min-w-0 gap-[0] bg-surface border-b border-solid border-border"
        ):
            with ui.row().classes("am-panel-header w-full items-center shrink-0"):
                ui.icon("chat_bubble_outline").style(
                    "color: var(--color-accent); font-size: 0.9rem; margin-right: 6px;"
                )
                self._conv_title_label = ui.label("—").style(
                    "font-family: var(--font-mono); font-size: 0.7rem;"
                    " color: var(--color-secondary); letter-spacing: 0.05em;"
                    " white-space: nowrap; overflow: hidden; text-overflow: ellipsis;"
                    " flex: 1;"
                )

            self.message_container = ui.column().classes(
                "w-full flex-1 items-stretch overflow-y-auto overflow-x-hidden \
                     scroll-smooth py-8 px-8"
            )

            with (
                ui.row()
                .classes("w-full items-end px-2 py-2 shrink-0 bg-panel")
                .style("border-top: 1px solid var(--color-border); gap: 8px;")
            ):
                self._textarea = (
                    ui.textarea(
                        placeholder="Type a message… (Enter to send, Shift+Enter for newline)"  # noqa: E501
                    )
                    .props(
                        "outlined autogrow autofocus clearable"
                        " input-class='overflow-y-auto max-h-[10vh]'"
                    )
                    .classes("flex-1 font-mono text-sm")
                )
                self._textarea.on("keydown", self._handle_keydown)

                ui.button(icon="send", on_click=self._send_from_button).classes(
                    "am-btn-primary w-12 h-12 place-self-center"
                ).props("flat dense")

    def _handle_keydown(self, event: GenericEventArguments) -> None:
        key = event.args.get("key", "")
        shift = event.args.get("shiftKey", False)
        if key == "Enter" and not shift:
            asyncio.create_task(self.send_chat_message(event))

    async def _send_from_button(self) -> None:
        class _FakeSender:
            pass

        class _FakeEvent:
            pass

        e = _FakeEvent()
        e.sender = self._textarea  # type: ignore[attr-defined]
        e.client = self._client  # type: ignore[attr-defined]
        e.args = {}  # type: ignore[attr-defined]
        await self.send_chat_message(e)  # type: ignore[arg-type]

    def _set_conv_title(self, conversation: Dict[str, Any]) -> None:
        topic = conversation.get("topic")
        conv_id = conversation.get("id") or conversation.get("_id") or ""
        title = topic or f"#{str(conv_id)[-6:]}" if conv_id else "—"
        self._conv_title_label.set_text(title)
        self._client.storage["conv_title"] = title

    async def send_chat(
        self, session: ClientSession, current_conversation: Dict[str, Any], query: str
    ):
        if not current_conversation:
            raise RuntimeError("No active conversation in client session")

        owner = current_conversation.get("owner") or {}
        actor_id = owner.get("id")
        if not actor_id:
            raise RuntimeError("No actor id available for current conversation")

        data = {"query": query, "actor_id": str(actor_id)}
        async with session.post(
            f"/api/v1/conversations/{current_conversation['id']}/messages", json=data
        ) as response:
            if response.status >= 400:
                body = await response.text()
                raise ClientResponseError(
                    request_info=response.request_info,
                    history=response.history,
                    status=response.status,
                    message=body,
                    headers=response.headers,
                )

            try:
                json_data = await response.json()
            except ContentTypeError as exc:
                body = await response.text()
                raise RuntimeError(
                    f"Backend returned non-JSON response: {body[:200]}"
                ) from exc

        last_msg = json_data
        self.messages.append(
            BotMessage(
                name=last_msg.get("name"),
                content=last_msg.get("content"),
                reasoning=last_msg.get("reasoning"),
            )
        )

    async def send_chat_message(self, event: GenericEventArguments) -> None:
        sender = self._textarea
        client = self._client
        if not sender.value:
            return

        self.messages.append(HumanMessage(name="You", content=sender.value))

        session = client.storage.get("session", None)
        if not session:
            self.messages.append(
                BotMessage(
                    name="System",
                    content="Frontend session is not connected to backend.",
                )
            )
            self.chat_messages.refresh()
            return

        if not client.storage.get("current_conversation", None):
            await self.start_chat_session(client)
            if not client.storage.get("current_conversation", None):
                self.messages.append(
                    BotMessage(
                        name="System",
                        content="Could not start or resume a conversation.",
                    )
                )
                self.chat_messages.refresh()
                return

        def on_done(task: asyncio.Task[None]):
            exception = task.exception()
            if exception:
                self.messages.append(
                    BotMessage(
                        name="System",
                        content=f"Connection could not be made: {exception}",
                    )
                )
            self.chat_messages.refresh()

        asyncio.create_task(
            self.send_chat(
                session, client.storage.get("current_conversation", None), sender.value
            )
        ).add_done_callback(on_done)

        setattr(sender, "value", None)
        self.chat_messages.refresh()

    async def new_chat(self, client: Client) -> None:
        session = client.storage.get("session", None)

        if not session:
            self.messages.append(
                BotMessage(
                    name="System",
                    content="Frontend session is not connected to backend.",
                )
            )
            self.chat_messages.refresh()
            return

        current_conversation = client.storage.get("current_conversation", None)
        if not current_conversation:
            await self.start_chat_session(client)
            current_conversation = client.storage.get("current_conversation", None)

        owner = current_conversation.get("owner") if current_conversation else None
        owner_id = owner.get("id") if isinstance(owner, dict) else None
        if not owner_id:
            self.messages.append(
                BotMessage(
                    name="System",
                    content="Could not determine current actor for New Chat.",
                )
            )
            self.chat_messages.refresh()
            return

        try:
            async with session.post(
                "/api/v1/conversations",
                json={"owner_id": str(owner_id)},
            ) as response:
                if response.status >= 400:
                    body = await response.text()
                    raise ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=response.status,
                        message=body,
                        headers=response.headers,
                    )

                new_conversation = await response.json()

            new_conversation["owner"] = {
                "id": owner_id,
                "name": "Default",
                "role": "user",
            }
            new_conversation["messages"] = []
            client.storage["current_conversation"] = new_conversation

            self.messages = []
            if self.info_panel and hasattr(self.info_panel, "clear"):
                self.info_panel.clear()
            self.chat_messages.refresh()
        except Exception as exc:
            self.messages.append(
                BotMessage(
                    name="System",
                    content=f"Could not create a new conversation: {exc}",
                )
            )
            self.chat_messages.refresh()

    def _set_new_chat_busy(self, busy: bool) -> None:
        self._new_chat_in_progress = busy
        if busy:
            self.new_chat_button.disable()
        else:
            self.new_chat_button.enable()

    def _on_new_chat_click(self, event: ClickEventArguments) -> None:
        if self._new_chat_in_progress:
            return

        self._set_new_chat_busy(True)
        task = asyncio.create_task(self.new_chat(event.client))

        def on_done(done_task: asyncio.Task[None]) -> None:
            self._set_new_chat_busy(False)
            if done_task.cancelled():
                return

            exception = done_task.exception()
            if exception:
                self.messages.append(
                    BotMessage(
                        name="System",
                        content=f"Could not create a new conversation: {exception}",
                    )
                )
                self.chat_messages.refresh()

        task.add_done_callback(on_done)

    @ui.refreshable
    def chat_messages(self, container_id: int):
        if not self.messages:
            with (
                ui.column()
                .classes("w-full h-full items-center justify-center")
                .style("opacity: 0.35; gap: 8px;")
            ):
                ui.icon("terminal").style(
                    "font-size: 2.5rem; color: var(--color-accent);"
                )
                ui.label("AutoMaestro").style(
                    "font-family: var(--font-display); font-size: 1.1rem;"
                    " font-weight: 700; color: var(--color-accent);"
                    " letter-spacing: 0.12em;"
                )
                ui.label("Ready for your command").style(
                    "font-family: var(--font-mono); font-size: 0.72rem;"
                    " color: var(--color-muted); letter-spacing: 0.08em;"
                )
            return

        last_msg_id = None
        for message in self.messages:
            with ui.chat_message(
                name=message.name, sent=isinstance(message, HumanMessage)
            ) as msg:
                ui.markdown(message.content if message.content else "")
                last_msg_id = msg.id

            if last_msg_id is None:
                return

            ui.run_javascript(
                f"""
                var container = document.getElementById('c{container_id}');
                var lastMsg = document.getElementById('c{last_msg_id}');
                if (container && lastMsg) {{
                    var offsetTop = lastMsg.offsetTop - 20;
                    container.scrollTo({{ top: offsetTop, behavior: 'smooth' }});
                }}
                """
            )

    def render_chat_messages(self):
        with self.message_container:
            self.chat_messages(self.message_container.id)

    def _load_conversation_history(self, conversation: Dict[str, Any]) -> None:
        history = conversation.get("messages") or []
        hydrated_messages: List[BaseMessage] = []

        for item in history:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if not content:
                continue
            author = item.get("author") or {}
            role = author.get("role")
            name = author.get("name")

            if role == "user":
                hydrated_messages.append(HumanMessage(name="You", content=content))
            else:
                hydrated_messages.append(
                    BotMessage(name=name or "AutoMaestro", content=content)
                )

        self.messages = hydrated_messages
        self.chat_messages.refresh()

    async def load_conversation_by_id(self, conv_id: str, client: Client) -> None:
        session: ClientSession = client.storage.get("session", None)
        if not session:
            return

        try:
            async with session.get(f"/api/v1/conversations/{conv_id}") as response:
                if response.status >= 400:
                    body = await response.text()
                    self.messages.append(
                        BotMessage(
                            name="System",
                            content=f"Failed to load conversation ({response.status}): {body[:200]}",  # noqa: E501
                        )
                    )
                    self.chat_messages.refresh()
                    return
                json_data = await response.json()
        except Exception as exc:
            self.messages.append(
                BotMessage(
                    name="System",
                    content=f"Failed to load conversation: {exc}",
                )
            )
            self.chat_messages.refresh()
            return

        client.storage["current_conversation"] = json_data
        self._set_conv_title(json_data)
        self._load_conversation_history(json_data)

    async def new_conversation(self, client: Client) -> None:
        session: ClientSession = client.storage.get("session", None)
        if not session:
            return

        current = client.storage.get("current_conversation", None)
        if not current:
            return

        owner = current.get("owner") or {}
        owner_id = owner.get("id")
        if not owner_id:
            return

        try:
            async with session.post(
                "/api/v1/conversations", json={"owner_id": str(owner_id)}
            ) as response:
                if response.status >= 400:
                    body = await response.text()
                    self.messages.append(
                        BotMessage(
                            name="System",
                            content=f"Failed to create conversation ({response.status}): {body[:200]}",  # noqa: E501
                        )
                    )
                    self.chat_messages.refresh()
                    return
                json_data = await response.json()
        except Exception as exc:
            self.messages.append(
                BotMessage(
                    name="System",
                    content=f"Failed to create conversation: {exc}",
                )
            )
            self.chat_messages.refresh()
            return

        conv_id = json_data.get("_id") or json_data.get("id")
        if conv_id:
            await self.load_conversation_by_id(str(conv_id), client)
        else:
            client.storage["current_conversation"] = json_data
            self._set_conv_title(json_data)
            self.messages = []
            self.chat_messages.refresh()

    async def start_chat_session(self, client: Client):
        session: ClientSession = client.storage.get("session", None)

        if not session:
            raise ValueError("Cannot make chat session")

        max_attempts = 8
        for attempt in range(1, max_attempts + 1):
            try:
                async with session.post(
                    "/api/v1/conversations/resume", json={"actor_name": "Default"}
                ) as response:
                    if response.status >= 500 and attempt < max_attempts:
                        await asyncio.sleep(min(1.5, 0.25 * attempt))
                        continue

                    if response.status >= 400:
                        body = await response.text()
                        self.messages.append(
                            BotMessage(
                                name="System",
                                content=(
                                    "Conversation resume failed "
                                    f"({response.status}): {body[:200]}"
                                ),
                            )
                        )
                        self.chat_messages.refresh()
                        return

                    json_data = await response.json()
                    client.storage["current_conversation"] = json_data
                    self._set_conv_title(json_data)
                    self._load_conversation_history(json_data)
                    return
            except Exception as exc:
                if attempt < max_attempts:
                    await asyncio.sleep(min(1.5, 0.25 * attempt))
                    continue

                self.messages.append(
                    BotMessage(
                        name="System",
                        content=f"Conversation resume failed after retries: {exc}",
                    )
                )
                self.chat_messages.refresh()
                return
