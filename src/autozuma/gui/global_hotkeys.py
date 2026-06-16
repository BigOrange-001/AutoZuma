"""Global GUI hotkey polling independent of Qt window focus."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from autozuma.gui.settings import GuiHotkeySettings


class GuiHotkeyReader(Protocol):
    """Read the physical state of a GUI shortcut string."""

    def is_pressed(self, shortcut: str) -> bool:
        """Return whether the shortcut is currently pressed."""


@dataclass(frozen=True)
class GuiHotkeyEvents:
    toggle_arm: bool = False
    toggle_debug_snapshots: bool = False
    safe: bool = False


class GuiGlobalHotkeyPoller:
    """Edge-triggered global hotkey poller for the GUI controls."""

    def __init__(
        self,
        reader: GuiHotkeyReader,
        hotkeys: GuiHotkeySettings | None = None,
    ) -> None:
        self._reader = reader
        self._hotkeys = hotkeys or GuiHotkeySettings()
        self._previous: dict[str, bool] = {
            "toggle_arm": False,
            "snapshot": False,
            "safe": False,
        }

    def update_settings(self, hotkeys: GuiHotkeySettings) -> None:
        self._hotkeys = hotkeys
        self._previous = {key: False for key in self._previous}

    def poll(self) -> GuiHotkeyEvents:
        current = {
            "toggle_arm": self._is_pressed(self._hotkeys.toggle_arm),
            "snapshot": self._is_pressed(self._hotkeys.snapshot),
            "safe": self._is_pressed(self._hotkeys.safe),
        }
        events = GuiHotkeyEvents(
            toggle_arm=current["toggle_arm"] and not self._previous["toggle_arm"],
            toggle_debug_snapshots=current["snapshot"] and not self._previous["snapshot"],
            safe=current["safe"] and not self._previous["safe"],
        )
        self._previous = current
        return events

    def _is_pressed(self, shortcut: str) -> bool:
        if not shortcut.strip():
            return False
        return self._reader.is_pressed(shortcut)


class Win32GuiHotkeyReader:
    """Read GUI shortcuts through Win32 GetAsyncKeyState."""

    def is_pressed(self, shortcut: str) -> bool:
        combo = _parse_shortcut(shortcut)
        if combo is None:
            return False
        win32api, _ = _import_pywin32_key_modules()
        return all(bool(win32api.GetAsyncKeyState(vk) & 0x8000) for vk in combo)


def _parse_shortcut(shortcut: str) -> tuple[int, ...] | None:
    tokens = [token.strip().upper() for token in shortcut.split("+") if token.strip()]
    if not tokens:
        return None

    modifiers: list[int] = []
    key: int | None = None
    for token in tokens:
        if token in {"CTRL", "CONTROL"}:
            modifiers.append(0x11)
        elif token == "SHIFT":
            modifiers.append(0x10)
        elif token == "ALT":
            modifiers.append(0x12)
        elif token in {"META", "WIN", "WINDOWS"}:
            modifiers.append(0x5B)
        else:
            key = _key_code(token)
            if key is None:
                return None

    if key is None:
        return None
    return (*modifiers, key)


def _key_code(token: str) -> int | None:
    if token.startswith("F") and token[1:].isdigit():
        number = int(token[1:])
        if 1 <= number <= 24:
            return 0x70 + number - 1
    if len(token) == 1 and ("A" <= token <= "Z" or "0" <= token <= "9"):
        return ord(token)
    return {
        "ESC": 0x1B,
        "ESCAPE": 0x1B,
        "SPACE": 0x20,
        "TAB": 0x09,
        "ENTER": 0x0D,
    }.get(token)


def _import_pywin32_key_modules():
    import win32api

    return win32api, None
