"""Pure UI button detection and click scheduling for live sessions."""

from __future__ import annotations

from dataclasses import dataclass, replace

import cv2
import numpy as np

from autozuma.core.models import Command, CommandType, ImageAsset, Point

UI_TEMPLATE_MATCH_THRESHOLD = 0.75


@dataclass(frozen=True)
class UiDetectionResult:
    """Matched UI button template and click target in captured-frame coordinates."""

    template_id: str
    confidence: float
    match_location: Point
    target: Point


@dataclass(frozen=True)
class UiAutomationState:
    """State for prototype-compatible repeated UI button clicking."""

    last_poll_time: float = 0.0
    click_count: int = 0
    next_click_time: float = 0.0


@dataclass(frozen=True)
class UiAutomationParams:
    """Timing and threshold parameters for UI automation."""

    match_threshold: float = UI_TEMPLATE_MATCH_THRESHOLD
    poll_interval: float = 1.0
    click_burst_count: int = 5
    success_interval: float = 1.0
    miss_retry_interval: float = 0.1


@dataclass(frozen=True)
class UiAutomationFrameResult:
    """UI automation result for one captured frame."""

    state: UiAutomationState
    detection_result: UiDetectionResult | None = None
    command: Command = Command(command_type=CommandType.NO_OP)
    should_skip_gameplay: bool = False
    reset_session: bool = False


def detect_ui_button(
    frame_bgr: np.ndarray,
    templates: dict[str, ImageAsset],
    min_confidence: float = UI_TEMPLATE_MATCH_THRESHOLD,
) -> UiDetectionResult | None:
    """Find the first configured UI button template above the prototype threshold."""
    if not templates:
        return None
    frame_gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    for template_id, template in templates.items():
        if template.gray is None or not _can_match(frame_gray, template.gray):
            continue
        _, max_value, _, max_location = cv2.minMaxLoc(
            cv2.matchTemplate(frame_gray, template.gray, cv2.TM_CCOEFF_NORMED)
        )
        if max_value > min_confidence:
            height, width = template.gray.shape[:2]
            return UiDetectionResult(
                template_id=template_id,
                confidence=float(max_value),
                match_location=Point(x=max_location[0], y=max_location[1]),
                target=Point(
                    x=max_location[0] + width // 2,
                    y=max_location[1] + height // 2,
                ),
            )
    return None


def run_ui_automation_frame(
    *,
    frame_bgr: np.ndarray,
    templates: dict[str, ImageAsset],
    state: UiAutomationState,
    current_time: float,
    params: UiAutomationParams = UiAutomationParams(),
) -> UiAutomationFrameResult:
    """Advance UI auto-click state for one frame."""
    if not templates:
        return UiAutomationFrameResult(state=state)

    active_state = state
    detection_result: UiDetectionResult | None = None
    command = Command(command_type=CommandType.NO_OP)

    if current_time - active_state.last_poll_time > params.poll_interval:
        detection_result = detect_ui_button(
            frame_bgr,
            templates,
            min_confidence=params.match_threshold,
        )
        active_state = replace(active_state, last_poll_time=current_time)
        if detection_result is not None and active_state.click_count == 0:
            active_state = replace(
                active_state,
                click_count=params.click_burst_count,
                next_click_time=current_time,
            )

    if active_state.click_count <= 0:
        return UiAutomationFrameResult(state=active_state, detection_result=detection_result)

    if current_time >= active_state.next_click_time:
        detection_result = detect_ui_button(
            frame_bgr,
            templates,
            min_confidence=params.match_threshold,
        )
        next_count = active_state.click_count - 1
        if detection_result is not None:
            command = Command(
                command_type=CommandType.UI_CLICK,
                primary_target=detection_result.target,
            )
            next_click_time = current_time + params.success_interval
        else:
            next_click_time = current_time + params.miss_retry_interval
        active_state = replace(
            active_state,
            click_count=next_count,
            next_click_time=next_click_time,
        )

    return UiAutomationFrameResult(
        state=active_state,
        detection_result=detection_result,
        command=command,
        should_skip_gameplay=True,
        reset_session=active_state.click_count == 0,
    )


def _can_match(frame_gray: np.ndarray, template_gray: np.ndarray) -> bool:
    frame_height, frame_width = frame_gray.shape[:2]
    template_height, template_width = template_gray.shape[:2]
    return frame_height >= template_height and frame_width >= template_width
