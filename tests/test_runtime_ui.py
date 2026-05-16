from pathlib import Path

import numpy as np

from autozuma.core.models import CommandType, ImageAsset
from autozuma.runtime.ui import (
    UiAutomationParams,
    UiAutomationState,
    detect_ui_button,
    run_ui_automation_frame,
)


def test_detect_ui_button_returns_first_matching_template_center():
    template = _template()
    frame = np.zeros((12, 14, 3), dtype=np.uint8)
    frame[4:7, 5:8] = template.bgr

    result = detect_ui_button(frame, {"ok": template})

    assert result is not None
    assert result.template_id == "ok"
    assert result.confidence > 0.75
    assert result.match_location.x == 5
    assert result.match_location.y == 4
    assert result.target.x == 6
    assert result.target.y == 5


def test_detect_ui_button_skips_templates_larger_than_frame():
    result = detect_ui_button(
        np.zeros((2, 2, 3), dtype=np.uint8),
        {"ok": _template()},
    )

    assert result is None


def test_ui_automation_schedules_and_clicks_detected_button():
    template = _template()
    frame = np.zeros((12, 14, 3), dtype=np.uint8)
    frame[4:7, 5:8] = template.bgr

    result = run_ui_automation_frame(
        frame_bgr=frame,
        templates={"ok": template},
        state=UiAutomationState(),
        current_time=2.0,
        params=UiAutomationParams(click_burst_count=3),
    )

    assert result.should_skip_gameplay is True
    assert result.reset_session is False
    assert result.state.last_poll_time == 2.0
    assert result.state.click_count == 2
    assert result.state.next_click_time == 3.0
    assert result.command.command_type == CommandType.UI_CLICK
    assert result.command.primary_target.x == 6
    assert result.command.primary_target.y == 5


def test_ui_automation_retries_quickly_when_button_disappears_and_resets_on_final_try():
    result = run_ui_automation_frame(
        frame_bgr=np.zeros((12, 14, 3), dtype=np.uint8),
        templates={"ok": _template()},
        state=UiAutomationState(last_poll_time=2.0, click_count=1, next_click_time=4.0),
        current_time=4.0,
    )

    assert result.should_skip_gameplay is True
    assert result.reset_session is True
    assert result.state.click_count == 0
    assert result.state.next_click_time == 4.1
    assert result.command.command_type == CommandType.NO_OP


def _template() -> ImageAsset:
    gray = np.array(
        [
            [0, 60, 120],
            [30, 200, 80],
            [160, 90, 240],
        ],
        dtype=np.uint8,
    )
    bgr = np.dstack([gray, gray, gray])
    return ImageAsset(path=Path("ui_ok.png"), bgr=bgr, gray=gray)
