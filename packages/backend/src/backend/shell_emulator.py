"""shell_emulator.py

This module implements a WebSocket-based interactive terminal emulator.

Key Features:
- Input buffering with cursor movement and backspace support.
- Command history navigation (up/down arrows).
- ANSI escape sequence output for terminal rendering.

"""

from enum import Enum
from typing import Tuple

import ansi
from fastapi import WebSocket

from backend.util import clamp


class EmulatorAction(Enum):
    DISPLAY = "DISPLAY"
    SEND_COMMAND = "SEND_COMMAND"
    NONE = "NONE"


class ShellEmulator:
    def __init__(self, websocket: WebSocket, prompt: str = " > "):
        self.websocket = websocket
        self.connected_pty = ""
        self.__prompt = prompt
        self.__cursor = 0
        self.__history = []
        self.__history_index = 0
        self.__buffer = ""

    async def accept(self):
        await self.websocket.accept()
        await self.websocket.send_text(f"\x1bc{self.__prompt}")

    def traverse_history(self, direction: int) -> str | None:
        history_len = len(self.__history)
        next_index = self.__history_index + direction
        self.__history_index = clamp(next_index, -history_len, 0)
        if self.__history and next_index < 0:
            return self.__history[self.__history_index]

        return None

    def get_next_history(self) -> str | None:
        return self.traverse_history(1)

    def get_last_history(self) -> str | None:
        return self.traverse_history(-1)

    def move_cursor(self, direction: int):
        new_cursor = clamp(self.__cursor + direction, 0, len(self.__buffer))
        if new_cursor != self.__cursor:
            self.__cursor = new_cursor
            return True
        return False

    def flush_buffer(self) -> str:
        text = self.__buffer
        self.__buffer = ""
        if text:
            self.__history.append(text)
        self.__cursor = 0
        self.__history_index = 0
        return text

    def get_prompt(self) -> str:
        return self.__prompt

    def handle_input(self, text: str) -> Tuple[EmulatorAction, str]:
        action = EmulatorAction.DISPLAY
        match text:
            case "\r":
                text = self.flush_buffer()
                action = EmulatorAction.SEND_COMMAND
            case "\x7f":  # DELETE (effectively BACKSPACE)
                if self.move_cursor(-1):
                    end = ""
                    if self.__cursor < len(self.__buffer):
                        end = self.__buffer[self.__cursor + 1 :]
                    self.__buffer = self.__buffer[: self.__cursor] + end
                    text = (
                        f"{ansi.cursor.back(0)}{ansi.cursor.save_cursor(0)}"
                        f"{ansi.cursor.erase_line(0)}{end}{ansi.cursor.load_cursor(0)}"
                    )
                else:
                    action = EmulatorAction.NONE
            case "\x1b[3~":  # DELETE (actually DELETE)
                if self.__cursor < len(self.__buffer):
                    end = self.__buffer[self.__cursor + 1 :]
                    self.__buffer = self.__buffer[: self.__cursor] + end
                    text = (
                        f"{ansi.cursor.save_cursor(0)}"
                        f"{ansi.cursor.erase_line(0)}{end}{ansi.cursor.load_cursor(0)}"
                    )
                else:
                    action = EmulatorAction.NONE
            case "\x08":  # BACKSPACE (not really though)
                pass
            case "\x1b[A":  # UP
                text = ""
                event = self.get_last_history()
                text = (
                    f"{ansi.cursor.erase_line(2)}{ansi.cursor.goto_x(0)}{self.__prompt}"
                )
                if not event:
                    self.__buffer = ""
                else:
                    self.__buffer = event
                    text += event
            case "\x1b[B":  # DOWN
                text = ""
                event = self.get_next_history()
                text = (
                    f"{ansi.cursor.erase_line(2)}{ansi.cursor.goto_x(0)}{self.__prompt}"
                )
                if not event:
                    self.__buffer = ""
                else:
                    self.__buffer = event
                    text += event
            case "\x1b[C":  # RIGHT
                changed = self.move_cursor(1)
                if not changed:
                    action = EmulatorAction.NONE
            case "\x1b[D":  # LEFT
                changed = self.move_cursor(-1)
                if not changed:
                    action = EmulatorAction.NONE
            case _:
                self.__buffer += text
                self.__cursor += 1
        return action, text

    async def handle_fake_command(self, command: list[str]) -> Tuple[bool, str]:
        handled = False
        match command:
            case ["connect", container]:
                if container:
                    self.connected_pty = container
                else:
                    await self.websocket.send_text("Usage: connect <container>")
                handled = True
            case ["cls"] | ["clear"]:
                await self.websocket.send_text(
                    f"{ansi.cursor.erase('')}{ansi.cursor.goto(0)}{self.__prompt}"
                )
                handled = True
        return handled
