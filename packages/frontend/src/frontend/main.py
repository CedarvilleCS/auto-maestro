"""main.py

This module serves as the entry point for the NiceGUI frontend application.

Key Features:
- Renders a three-panel layout: chat, terminal, and info panels.
- Manages session-level HTTP and WebSocket connections to the backend.
- Handles background async tasks for real-time UI updates.

"""

import asyncio
from typing import Optional

from aiohttp import ClientConnectorError, ClientSession
from nicegui import Client, app, ui

from frontend.components.chat_panel import Chat
from frontend.components.info_panel import Info
from frontend.components.sidebar import Sidebar
from frontend.components.terminal_panel import Terminal
from frontend.config import settings

_GOOGLE_FONTS = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Oxanium:wght@400;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
"""  # noqa: E501

_THEME_CSS = """
:root {
    --color-base:        #001e36;
    --color-surface:     #003864;
    --color-raised:      #004f8a;
    --color-panel:       #00294d;
    --color-accent:         #ffa700;
    --color-accent-dim:     #cc8500;
    --color-accent-glow:    rgba(255,167,0,0.15);
    --color-primary:   #e8edf2;
    --color-secondary: #8fb3cc;
    --color-muted:     #4a6a80;
    --color-border:         #0a4a70;
    --color-border-accent:  rgba(255,167,0,0.4);
    --font-display:   'Oxanium', monospace;
    --font-mono:      'IBM Plex Mono', monospace;
    --radius:         0px;
}

body, .q-body--prevent-scroll {
    background-color: var(--color-base) !important;
    font-family: var(--font-mono) !important;
    color: var(--color-primary) !important;
}

.nicegui-content {
    background-color: var(--color-base) !important;
    padding: 0 !important;
}

.q-page {
    background-color: var(--color-base) !important;
}

/* ── Scrollbars ─────────────────────────────────────────── */
* {
    scrollbar-width: thin;
    scrollbar-color: var(--color-raised) transparent;
}
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--color-raised); border-radius: 0; }

/* ── Drawer ─────────────────────────────────────────────── */
.q-drawer {
    background-color: var(--color-panel) !important;
    border-right: 1px solid var(--color-border) !important;
}

/* ── Buttons ────────────────────────────────────────────── */
.q-btn {
    border-radius: 0 !important;
    font-family: var(--font-mono) !important;
    letter-spacing: 0.05em !important;
    text-transform: none !important;
}
.am-btn-primary {
    background-color: var(--color-accent) !important;
    color: #001e36 !important;
    font-weight: 600 !important;
}
.am-btn-primary:hover {
    background-color: var(--color-accent-dim) !important;
}
.am-btn-ghost {
    background-color: transparent !important;
    color: var(--color-secondary) !important;
    border: 1px solid var(--color-border) !important;
}
.am-btn-ghost:hover {
    border-color: var(--color-accent) !important;
    color: var(--color-accent) !important;
}
.am-btn-icon {
    background-color: transparent !important;
    color: var(--color-muted) !important;
}
.am-btn-icon:hover {
    color: var(--color-accent) !important;
}

/* ── Input / Textarea ───────────────────────────────────── */
.q-field__control {
    border-radius: 0 !important;
    background-color: var(--color-base) !important;
}
.q-field--outlined .q-field__control:before {
    border-color: var(--color-border) !important;
    border-radius: 0 !important;
}
.q-field--outlined .q-field__control:hover:before {
    border-color: var(--color-accent) !important;
}
.q-field--outlined.q-field--focused .q-field__control:after {
    border-color: var(--color-accent) !important;
    border-radius: 0 !important;
}
.q-field__native, .q-field__input {
    color: var(--color-primary) !important;
    font-family: var(--font-mono) !important;
    caret-color: var(--color-accent) !important;
}
.q-field__label {
    color: var(--color-muted) !important;
    font-family: var(--font-mono) !important;
}
.q-placeholder::placeholder {
    color: var(--color-muted) !important;
}

/* ── Cards ──────────────────────────────────────────────── */
.q-card {
    border-radius: 0 !important;
    background-color: var(--color-surface) !important;
    border: 1px solid var(--color-border) !important;
    box-shadow: none !important;
}

/* ── Chat messages ──────────────────────────────────────── */
.q-message-container > div {
    flex: 1 1 auto !important;
    max-width: 100% !important;
}
.q-message-text {
    border-radius: 0 !important;
    font-family: var(--font-mono) !important;
    font-size: 0.85rem !important;
}
.q-message-text-content {
    max-width: 100% !important;
}
.q-message:not(.q-message-sent) .q-message-text {
    background-color: var(--color-raised) !important;
    color: var(--color-primary) !important;
    border-left: 2px solid var(--color-border-accent) !important;
}
.q-message-sent .q-message-text {
    background-color: var(--color-surface) !important;
    color: var(--color-primary) !important;
    border-right: 2px solid var(--color-accent) !important;
}
.q-message-name {
    color: var(--color-muted) !important;
    font-family: var(--font-mono) !important;
    font-size: 0.7rem !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
}
.q-message-sent .q-message-name {
    color: var(--color-accent-dim) !important;
}
.q-message-avatar {
    display: none !important;
}

.nicegui-markdown, .nicegui-markdown * {
    max-width: 100% !important;
    white-space: normal !important;
    overflow-wrap: break-word !important;
    word-break: break-word !important;
    color: var(--color-primary) !important;
    font-family: var(--font-mono) !important;
}
.nicegui-markdown code {
    background-color: var(--color-base) !important;
    color: var(--color-accent) !important;
    padding: 1px 4px !important;
    font-size: 0.82em !important;
}
.nicegui-markdown pre {
    background-color: var(--color-base) !important;
    border: 1px solid var(--color-border) !important;
    border-left: 2px solid var(--color-accent-dim) !important;
    padding: 8px 12px !important;
}

/* ── Panel headers ──────────────────────────────────────── */
.am-panel-header {
    background-color: var(--color-panel) !important;
    border-bottom: 1px solid var(--color-border) !important;
    border-top: 2px solid var(--color-accent) !important;
    padding: 6px 12px !important;
    font-family: var(--font-mono) !important;
    font-size: 0.7rem !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase !important;
    color: var(--color-accent) !important;
    min-height: 32px !important;
}

/* ── App header ─────────────────────────────────────────── */
.am-app-header {
    background-color: var(--color-panel) !important;
    border-bottom: 1px solid var(--color-border) !important;
    height: 48px !important;
}

/* ── Sidebar conversation items ─────────────────────────── */
.am-conv-item {
    border-bottom: 1px solid var(--color-border) !important;
    cursor: pointer !important;
    padding: 10px 14px !important;
    transition: background-color 0.15s !important;
}
.am-conv-item:hover {
    background-color: var(--color-raised) !important;
}
.am-conv-item.am-conv-active {
    background-color: var(--color-raised) !important;
    border-left: 2px solid var(--color-accent) !important;
}

/* ── Status dot ─────────────────────────────────────────── */
.am-status-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    display: inline-block;
    background-color: var(--color-muted);
}
.am-status-dot.connected { background-color: #3ddc84; }
.am-status-dot.error     { background-color: #ff4444; }

/* ── Log panel ──────────────────────────────────────────── */
.nicegui-log {
    background-color: var(--color-base) !important;
    color: var(--color-accent) !important;
    font-family: var(--font-mono) !important;
    font-size: 0.75rem !important;
    border: none !important;
    padding: 6px 10px !important;
}

/* ── xterm ──────────────────────────────────────────────── */
.xterm {
    padding: 6px !important;
}

/* ── Separator ──────────────────────────────────────────── */
.q-separator {
    background-color: var(--color-border) !important;
}
"""


@ui.page("/")
async def main(client: Client):
    ui.query("body").classes("overflow-hidden")
    ui.query(".q-page").classes("flex h-screen")
    ui.query(".nicegui-content").classes("w-full h-full p-0 m-0")
    ui.add_head_html(_GOOGLE_FONTS)
    ui.add_css(_THEME_CSS)

    drawer = ui.left_drawer(value=False, bordered=True).style(
        "width: 260px; min-width: 260px; padding: 0;"
    )

    with (
        ui.row()
        .classes("am-app-header w-full flex-nowrap items-center gap-2 px-3")
        .style("flex-shrink:0; z-index:10;")
    ):
        ui.button(icon="menu", on_click=drawer.toggle).classes("am-btn-icon").props(
            "flat dense"
        )
        ui.label("AutoMaestro").style(
            "font-family: var(--font-display); font-size: 1.1rem;"
            " font-weight: 700; color: var(--color-accent); letter-spacing: 0.1em;"
        )
        ui.space()
        ui.label("").classes("text-xs").style(
            "color: var(--color-muted); font-family: var(--font-mono);"
        ).bind_text_from(client.storage, "conv_title", backward=lambda v: v or "")

    with (
        ui.row()
        .classes("w-full grow flex-nowrap overflow-hidden items-stretch")
        .style("min-height: 0;")
    ):
        chat = Chat(client)

        with (
            ui.column()
            .classes("flex-1 basis-1/2 flex h-full max-h-full min-w-0")
            .style("gap: 0;")
        ):
            terminal = Terminal()
            info = Info()

    with drawer:
        Sidebar(chat, drawer, client)

    await client.connected()

    def _report_task_error(name: str):
        def _callback(task: asyncio.Task):
            exception = task.exception()
            if exception:
                print(f"{name} failed: {exception}")

        return _callback

    chat_task = asyncio.create_task(chat.start_chat_session(client))
    chat_task.add_done_callback(_report_task_error("chat.start_chat_session"))

    terminal_task = asyncio.create_task(terminal.start_term_emulation(client))
    terminal_task.add_done_callback(_report_task_error("terminal.start_term_emulation"))

    info_task = asyncio.create_task(info.start_state_visualization(client))
    info_task.add_done_callback(_report_task_error("info.start_state_visualization"))

    chat.render_chat_messages()


if __name__ in {"__main__", "__mp_main__"}:

    async def on_connect(client: Client):
        try:
            session = ClientSession(base_url=settings.get_backend_url())
            client.storage["session"] = session
        except ClientConnectorError:
            pass

    async def on_disconnect(client: Client):
        session: Optional[ClientSession] = client.storage.get("session", None)
        if session:
            await session.close()

    app.on_connect(on_connect)
    app.on_disconnect(on_disconnect)

    ui.run(
        title="AutoMaestro",
        host=settings.frontend_host,
        port=settings.frontend_port,
        dark=True,
    )
