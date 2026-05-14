"""Hotkey polling helpers for live control loops."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class Hotkey(Enum):
    F1 = "f1"
    F2 = "f2"
    F3 = "f3"


class HotkeyReader(Protocol):
    """Reads the current physical state of supported hotkeys."""

    def is_pressed(self, hotkey: Hotkey) -> bool:
        """Return whether a hotkey is currently pressed."""


@dataclass(frozen=True)
class HotkeyControlState:
    """Edge-triggered hotkey control state."""

    is_armed: bool = False
    previous_f1: bool = False
    previous_f2: bool = False
    previous_f3: bool = False


@dataclass(frozen=True)
class HotkeyEvents:
    """Events produced by one hotkey poll."""

    toggled_arm: bool = False
    armed_reset_requested: bool = False
    debug_requested: bool = False
    forced_safe: bool = False


@dataclass(frozen=True)
class HotkeyPollResult:
    state: HotkeyControlState
    events: HotkeyEvents


class Win32HotkeyReader:
    """Read F-key state through Win32 GetAsyncKeyState."""

    def is_pressed(self, hotkey: Hotkey) -> bool:
        win32api, win32con = _import_pywin32_key_modules()
        key_code = {
            Hotkey.F1: win32con.VK_F1,
            Hotkey.F2: win32con.VK_F2,
            Hotkey.F3: win32con.VK_F3,
        }[hotkey]
        return bool(win32api.GetAsyncKeyState(key_code) & 0x8000)


def poll_hotkeys(state: HotkeyControlState, reader: HotkeyReader) -> HotkeyPollResult:
    """Poll F1/F2/F3 and return edge-triggered control events."""
    current_f1 = reader.is_pressed(Hotkey.F1)
    current_f2 = reader.is_pressed(Hotkey.F2)
    current_f3 = reader.is_pressed(Hotkey.F3)

    f1_edge = current_f1 and not state.previous_f1
    f2_edge = current_f2 and not state.previous_f2
    f3_edge = current_f3 and not state.previous_f3

    is_armed = state.is_armed
    toggled_arm = False
    armed_reset_requested = False
    if f1_edge:
        toggled_arm = True
        is_armed = not is_armed
        armed_reset_requested = is_armed

    forced_safe = False
    if f3_edge:
        forced_safe = True
        is_armed = False

    return HotkeyPollResult(
        state=HotkeyControlState(
            is_armed=is_armed,
            previous_f1=current_f1,
            previous_f2=current_f2,
            previous_f3=current_f3,
        ),
        events=HotkeyEvents(
            toggled_arm=toggled_arm,
            armed_reset_requested=armed_reset_requested,
            debug_requested=f2_edge,
            forced_safe=forced_safe,
        ),
    )


def _import_pywin32_key_modules():
    import win32api
    import win32con

    return win32api, win32con
