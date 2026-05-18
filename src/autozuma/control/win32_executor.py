"""Win32 side-effect adapter for command execution plans."""

from __future__ import annotations

import ctypes
import time
from dataclasses import dataclass

from autozuma.core.models import Point


@dataclass(frozen=True)
class WindowRect:
    left: int
    top: int
    width: int
    height: int


class Win32CommandExecutor:
    """Execute planned command steps against a Zuma client-window frame."""

    def __init__(self, hwnd: int, rect: WindowRect, use_virtual: bool = False) -> None:
        self.hwnd = hwnd
        self.rect = rect
        self.use_virtual = use_virtual

    def left_click(self, target: Point) -> None:
        if self.use_virtual:
            self._send_virtual_left_click(target, move_delay=0.01, click_delay=0.02)
        else:
            self._send_physical_left_click(target, move_delay=0.01, click_delay=0.02)

    def ui_click(self, target: Point) -> None:
        if self.use_virtual:
            self._send_virtual_left_click(target, move_delay=0.05, click_delay=0.05)
        else:
            self._send_physical_left_click(target, move_delay=0.05, click_delay=0.05)

    def right_click(self) -> None:
        if self.use_virtual:
            self._send_virtual_right_click()
        else:
            self._send_physical_right_click()

    def wait(self, delay_ms: int) -> None:
        time.sleep(delay_ms / 1000.0)

    def _send_virtual_left_click(
        self,
        target: Point,
        *,
        move_delay: float,
        click_delay: float,
    ) -> None:
        win32api, win32con, win32gui = _import_pywin32()
        client_x, client_y = _client_target(target)
        lparam = win32api.MAKELONG(client_x, client_y)
        win32gui.SendMessage(self.hwnd, win32con.WM_MOUSEMOVE, 0, lparam)
        time.sleep(move_delay)
        win32gui.SendMessage(self.hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lparam)
        time.sleep(click_delay)
        win32gui.SendMessage(self.hwnd, win32con.WM_LBUTTONUP, 0, lparam)

    def _send_physical_left_click(
        self,
        target: Point,
        *,
        move_delay: float,
        click_delay: float,
    ) -> None:
        win32api, _, _ = _import_pywin32()
        safe_x, safe_y = _clamp_client_target_to_screen(target, self.rect)
        win32api.SetCursorPos((safe_x, safe_y))
        time.sleep(move_delay)
        _send_mouse_input(_MouseFlag.LEFT_DOWN)
        time.sleep(click_delay)
        _send_mouse_input(_MouseFlag.LEFT_UP)

    def _send_virtual_right_click(self) -> None:
        win32api, win32con, win32gui = _import_pywin32()
        client_x = int(self.rect.width / 2)
        client_y = int(self.rect.height / 2)
        lparam = win32api.MAKELONG(client_x, client_y)
        win32gui.SendMessage(self.hwnd, win32con.WM_RBUTTONDOWN, win32con.MK_RBUTTON, lparam)
        time.sleep(0.02)
        win32gui.SendMessage(self.hwnd, win32con.WM_RBUTTONUP, 0, lparam)

    def _send_physical_right_click(self) -> None:
        _send_mouse_input(_MouseFlag.RIGHT_DOWN)
        time.sleep(0.02)
        _send_mouse_input(_MouseFlag.RIGHT_UP)


def find_game_window(window_title: str = "zuma deluxe") -> tuple[int, WindowRect]:
    """Locate the game window and return its handle plus client screen rect."""
    win32api, _, win32gui = _import_pywin32()
    matched_hwnd = 0

    def enum_window_callback(hwnd: int, _: object) -> None:
        nonlocal matched_hwnd
        if win32gui.IsWindowVisible(hwnd) and window_title.lower() in win32gui.GetWindowText(
            hwnd
        ).lower():
            matched_hwnd = hwnd

    win32gui.EnumWindows(enum_window_callback, None)
    if not matched_hwnd:
        raise RuntimeError(f"could not find visible window matching {window_title!r}")

    client_rect = win32gui.GetClientRect(matched_hwnd)
    left, top = win32gui.ClientToScreen(matched_hwnd, (client_rect[0], client_rect[1]))
    rect = WindowRect(
        left=left,
        top=top,
        width=client_rect[2] - client_rect[0],
        height=client_rect[3] - client_rect[1],
    )
    return matched_hwnd, rect


def _import_pywin32():
    import win32api
    import win32con
    import win32gui

    return win32api, win32con, win32gui


def _client_target(target: Point) -> tuple[int, int]:
    return int(target.x), int(target.y)


def _clamp_client_target_to_screen(target: Point, rect: WindowRect) -> tuple[int, int]:
    screen_x = rect.left + target.x
    screen_y = rect.top + target.y
    safe_x = int(max(rect.left + 10, min(rect.left + rect.width - 10, screen_x)))
    safe_y = int(max(rect.top + 10, min(rect.top + rect.height - 10, screen_y)))
    return safe_x, safe_y


class _MouseFlag:
    LEFT_DOWN = 0x0002
    LEFT_UP = 0x0004
    RIGHT_DOWN = 0x0008
    RIGHT_UP = 0x0010


PUL = ctypes.POINTER(ctypes.c_ulong)


class _MouseInput(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", PUL),
    ]


class _InputUnion(ctypes.Union):
    _fields_ = [("mi", _MouseInput)]


class _Input(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong), ("ii", _InputUnion)]


def _send_mouse_input(flags: int) -> None:
    extra = ctypes.c_ulong(0)
    input_union = _InputUnion()
    input_union.mi = _MouseInput(0, 0, 0, flags, 0, ctypes.pointer(extra))
    command = _Input(ctypes.c_ulong(0), input_union)
    ctypes.windll.user32.SendInput(1, ctypes.pointer(command), ctypes.sizeof(command))
