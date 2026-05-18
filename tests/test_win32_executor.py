from autozuma.control.win32_executor import (
    WindowRect,
    _clamp_client_target_to_screen,
    _client_target,
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
