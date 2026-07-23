import pytest

from autozuma.control.win32_executor import (
    Win32CommandExecutor,
    WindowRect,
    _clamp_client_target_to_screen,
    _client_target,
    find_game_window,
)
from autozuma.core.models import Point


def test_client_target_preserves_captured_frame_coordinates_for_virtual_clicks():
    assert _client_target(Point(x=123.7, y=45.2)) == (123, 45)


def test_clamp_client_target_to_screen_adds_window_offset_for_physical_clicks():
    rect = WindowRect(left=100, top=200, width=640, height=480)

    assert _clamp_client_target_to_screen(Point(x=320, y=240), rect) == (420, 440)


def test_clamp_client_target_to_screen_keeps_physical_clicks_inside_client_rect():
    rect = WindowRect(left=100, top=200, width=640, height=480)

    assert _clamp_client_target_to_screen(Point(x=-50, y=-20), rect) == (110, 210)
    assert _clamp_client_target_to_screen(Point(x=700, y=600), rect) == (730, 670)


def test_ui_click_uses_focused_physical_input_even_in_virtual_mode(monkeypatch):
    executor = Win32CommandExecutor(
        hwnd=10,
        rect=WindowRect(left=100, top=200, width=640, height=480),
        use_virtual=True,
    )
    calls = []
    monkeypatch.setattr(executor, "_focus_game_window", lambda: calls.append(("focus",)))
    monkeypatch.setattr(
        executor,
        "_send_physical_left_click",
        lambda target, **timing: calls.append(("physical", target, timing)),
    )
    monkeypatch.setattr(
        executor,
        "_send_virtual_left_click",
        lambda *args, **kwargs: calls.append(("virtual",)),
    )

    executor.ui_click(Point(x=326, y=386))

    assert calls == [
        ("focus",),
        (
            "physical",
            Point(x=326, y=386),
            {"move_delay": 0.08, "click_delay": 0.12},
        ),
    ]


def test_gameplay_left_click_stays_virtual_when_configured(monkeypatch):
    executor = Win32CommandExecutor(
        hwnd=10,
        rect=WindowRect(left=100, top=200, width=640, height=480),
        use_virtual=True,
    )
    calls = []
    monkeypatch.setattr(
        executor,
        "_send_virtual_left_click",
        lambda target, **timing: calls.append((target, timing)),
    )

    executor.left_click(Point(x=320, y=240))

    assert calls == [
        (
            Point(x=320, y=240),
            {"move_delay": 0.01, "click_delay": 0.02},
        )
    ]


def test_find_game_window_prefers_game_title_over_browser_tab_match(monkeypatch):
    win32gui = _FakeWin32Gui(
        {
            10: _FakeWindow(
                title="Zuma Deluxe 1.0",
                client_rect=(0, 0, 640, 480),
                screen_origin=(100, 200),
            ),
            20: _FakeWindow(
                title="BigOrange-001/AutoZuma: Zuma Deluxe project - Microsoft Edge",
                client_rect=(0, 0, 1200, 900),
                screen_origin=(0, 0),
            ),
        }
    )
    monkeypatch.setattr(
        "autozuma.control.win32_executor._import_pywin32",
        lambda: (object(), object(), win32gui),
    )

    hwnd, rect = find_game_window("zuma deluxe")

    assert hwnd == 10
    assert rect == WindowRect(left=100, top=200, width=640, height=480)


def test_find_game_window_rejects_too_small_title_match(monkeypatch):
    win32gui = _FakeWin32Gui(
        {
            20: _FakeWindow(
                title="BigOrange-001/AutoZuma: Zuma Deluxe project - Microsoft Edge",
                client_rect=(0, 0, 144, 20),
                screen_origin=(-31992, -32000),
            ),
        }
    )
    monkeypatch.setattr(
        "autozuma.control.win32_executor._import_pywin32",
        lambda: (object(), object(), win32gui),
    )

    with pytest.raises(RuntimeError, match="could not find visible window"):
        find_game_window("zuma deluxe")


class _FakeWindow:
    def __init__(
        self,
        *,
        title: str,
        client_rect: tuple[int, int, int, int],
        screen_origin: tuple[int, int],
        visible: bool = True,
        iconic: bool = False,
    ) -> None:
        self.title = title
        self.client_rect = client_rect
        self.screen_origin = screen_origin
        self.visible = visible
        self.iconic = iconic


class _FakeWin32Gui:
    def __init__(self, windows: dict[int, _FakeWindow]) -> None:
        self.windows = windows

    def EnumWindows(self, callback, payload):
        for hwnd in self.windows:
            callback(hwnd, payload)

    def IsWindowVisible(self, hwnd: int) -> bool:
        return self.windows[hwnd].visible

    def IsIconic(self, hwnd: int) -> bool:
        return self.windows[hwnd].iconic

    def GetWindowText(self, hwnd: int) -> str:
        return self.windows[hwnd].title

    def GetClientRect(self, hwnd: int) -> tuple[int, int, int, int]:
        return self.windows[hwnd].client_rect

    def ClientToScreen(self, hwnd: int, point: tuple[int, int]) -> tuple[int, int]:
        left, top = self.windows[hwnd].screen_origin
        return left + point[0], top + point[1]
