"""Adventure menu detection and automatic new-game doorway clicks."""

from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np

from autozuma.core.models import Command, CommandType, Point
from autozuma.runtime.grade import StatsOcrReader, default_ocr_reader


@dataclass(frozen=True)
class AdventureMenuState:
    """Polling and click-throttle state for the Adventure menu."""

    last_poll_time: float = 0.0
    last_click_time: float = 0.0


@dataclass(frozen=True)
class AdventureMenuParams:
    """Detection pacing and normalized doorway target."""

    poll_interval: float = 0.75
    click_cooldown: float = 2.0
    target_x_ratio: float = 251.0 / 640.0
    target_y_ratio: float = 335.0 / 480.0


@dataclass(frozen=True)
class AdventureMenuFrameResult:
    """One Adventure-menu inspection and optional click command."""

    state: AdventureMenuState
    detected: bool = False
    command: Command = Command(command_type=CommandType.NO_OP)


_ADVENTURE_TITLE_ROI_640X480 = (10, 180, 0, 70)
_PLAY_BUTTON_ROI_640X480 = (550, 640, 415, 480)


def run_adventure_menu_frame(
    *,
    frame_bgr: np.ndarray,
    state: AdventureMenuState,
    current_time: float,
    params: AdventureMenuParams = AdventureMenuParams(),
    ocr_reader: StatsOcrReader | None = None,
) -> AdventureMenuFrameResult:
    """Detect the Adventure stage menu and click the configured doorway."""
    if current_time - state.last_poll_time < max(0.0, params.poll_interval):
        return AdventureMenuFrameResult(state=state)

    polled_state = AdventureMenuState(
        last_poll_time=current_time,
        last_click_time=state.last_click_time,
    )
    reader = ocr_reader or default_ocr_reader()
    try:
        adventure = reader.recognize(
            _scaled_crop(frame_bgr, _ADVENTURE_TITLE_ROI_640X480),
            field_name="adventure_menu_title",
        )
        play = reader.recognize(
            _scaled_crop(frame_bgr, _PLAY_BUTTON_ROI_640X480),
            field_name="adventure_menu_play",
        )
    except Exception:  # noqa: BLE001 - menu OCR must not terminate the game loop.
        return AdventureMenuFrameResult(state=polled_state)

    if "ADVENTURE" not in _letters(adventure.text) or "PLAY" not in _letters(play.text):
        return AdventureMenuFrameResult(state=polled_state)

    if current_time - state.last_click_time < max(0.0, params.click_cooldown):
        return AdventureMenuFrameResult(state=polled_state, detected=True)

    height, width = frame_bgr.shape[:2]
    target = Point(
        x=round(width * params.target_x_ratio),
        y=round(height * params.target_y_ratio),
    )
    return AdventureMenuFrameResult(
        state=AdventureMenuState(
            last_poll_time=current_time,
            last_click_time=current_time,
        ),
        detected=True,
        command=Command(
            command_type=CommandType.UI_CLICK,
            primary_target=target,
        ),
    )


def _scaled_crop(
    frame_bgr: np.ndarray,
    roi: tuple[int, int, int, int],
) -> np.ndarray:
    height, width = frame_bgr.shape[:2]
    base_x1, base_x2, base_y1, base_y2 = roi
    x1 = max(0, round(base_x1 * width / 640))
    x2 = min(width, round(base_x2 * width / 640))
    y1 = max(0, round(base_y1 * height / 480))
    y2 = min(height, round(base_y2 * height / 480))
    return frame_bgr[y1:y2, x1:x2]


def _letters(text: str) -> str:
    return re.sub(r"[^A-Z]", "", text.upper())
