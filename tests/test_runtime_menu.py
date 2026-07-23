import numpy as np

from autozuma.core.models import CommandType
from autozuma.runtime.grade import OcrReading
from autozuma.runtime.menu import (
    AdventureMenuParams,
    AdventureMenuState,
    run_adventure_menu_frame,
)


def test_adventure_menu_clicks_configured_doorway():
    result = run_adventure_menu_frame(
        frame_bgr=np.zeros((480, 640, 3), dtype=np.uint8),
        state=AdventureMenuState(),
        current_time=10.0,
        ocr_reader=_MenuOcr(),
    )

    assert result.detected is True
    assert result.command.command_type is CommandType.UI_CLICK
    assert result.command.primary_target.x == 251
    assert result.command.primary_target.y == 335
    assert result.state.last_click_time == 10.0


def test_adventure_menu_requires_both_title_and_play_button():
    result = run_adventure_menu_frame(
        frame_bgr=np.zeros((480, 640, 3), dtype=np.uint8),
        state=AdventureMenuState(),
        current_time=10.0,
        ocr_reader=_MenuOcr(play_text=""),
    )

    assert result.detected is False
    assert result.command.command_type is CommandType.NO_OP


def test_adventure_menu_throttles_repeated_clicks():
    result = run_adventure_menu_frame(
        frame_bgr=np.zeros((480, 640, 3), dtype=np.uint8),
        state=AdventureMenuState(last_poll_time=9.0, last_click_time=9.0),
        current_time=10.0,
        params=AdventureMenuParams(click_cooldown=2.0),
        ocr_reader=_MenuOcr(),
    )

    assert result.detected is True
    assert result.command.command_type is CommandType.NO_OP
    assert result.state.last_click_time == 9.0


class _MenuOcr:
    def __init__(self, play_text="PLAY"):
        self.play_text = play_text

    def recognize(self, image_bgr, *, field_name):
        text = "ADVENTURE" if field_name == "adventure_menu_title" else self.play_text
        return OcrReading(text=text, confidence=0.99)
