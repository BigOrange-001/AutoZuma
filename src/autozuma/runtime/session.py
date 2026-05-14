"""Static-level session state machine for already-captured frames."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum

import numpy as np

from autozuma.control.execution import ExecutionDriver
from autozuma.core.models import AssetRegistry, LauncherTemplateSet, LevelDetectionResult
from autozuma.runtime.host import StaticHostFrameParams, StaticHostFrameResult, run_static_host_frame
from autozuma.runtime.static_runtime import StaticRuntimeState, initial_static_runtime_state
from autozuma.vision.level_recognition import STATIC_LEVEL_MATCH_THRESHOLD, detect_static_level


class StaticSessionPhase(Enum):
    DETECTING = "detecting"
    PLAYING = "playing"


@dataclass(frozen=True)
class StaticSessionState:
    """Runtime state for static-level detection and playing sessions."""

    phase: StaticSessionPhase = StaticSessionPhase.DETECTING
    level_id: str | None = None
    runtime_state: StaticRuntimeState | None = None
    last_map_detect_time: float = 0.0


@dataclass(frozen=True)
class StaticSessionParams:
    """Parameters for static-level session orchestration."""

    host: StaticHostFrameParams
    level_min_confidence: float = STATIC_LEVEL_MATCH_THRESHOLD
    map_redetect_interval: float = 4.0


@dataclass(frozen=True)
class StaticSessionFrameResult:
    """Detailed result for one already-captured static session frame."""

    state: StaticSessionState
    detection_result: LevelDetectionResult | None = None
    host_result: StaticHostFrameResult | None = None
    level_changed: bool = False


def initial_static_session_state() -> StaticSessionState:
    """Return a detecting session state with no selected level."""
    return StaticSessionState()


def run_static_session_frame(
    *,
    frame_bgr: np.ndarray,
    registry: AssetRegistry,
    launcher_templates: LauncherTemplateSet,
    state: StaticSessionState,
    current_time: float,
    params: StaticSessionParams,
    driver: ExecutionDriver,
) -> StaticSessionFrameResult:
    """Run one already-captured frame through static-level session orchestration."""
    if state.phase is StaticSessionPhase.DETECTING:
        return _detect_initial_level(
            frame_bgr=frame_bgr,
            registry=registry,
            state=state,
            current_time=current_time,
            params=params,
        )

    active_state, detection_result, level_changed = _maybe_redetect_level(
        frame_bgr=frame_bgr,
        registry=registry,
        state=state,
        current_time=current_time,
        params=params,
    )
    if active_state.level_id is None or active_state.runtime_state is None:
        return StaticSessionFrameResult(
            state=StaticSessionState(last_map_detect_time=current_time),
            detection_result=detection_result,
        )

    host_result = run_static_host_frame(
        frame_bgr=frame_bgr,
        level=registry.levels[active_state.level_id],
        launcher_templates=launcher_templates,
        state=active_state.runtime_state,
        current_time=current_time,
        params=params.host,
        driver=driver,
    )
    return StaticSessionFrameResult(
        state=replace(active_state, runtime_state=host_result.state),
        detection_result=detection_result,
        host_result=host_result,
        level_changed=level_changed,
    )


def _detect_initial_level(
    *,
    frame_bgr: np.ndarray,
    registry: AssetRegistry,
    state: StaticSessionState,
    current_time: float,
    params: StaticSessionParams,
) -> StaticSessionFrameResult:
    detection_result = detect_static_level(
        frame_bgr,
        registry,
        min_confidence=params.level_min_confidence,
    )
    if detection_result is None:
        return StaticSessionFrameResult(state=state)

    return StaticSessionFrameResult(
        state=StaticSessionState(
            phase=StaticSessionPhase.PLAYING,
            level_id=detection_result.level_id,
            runtime_state=initial_static_runtime_state(current_time),
            last_map_detect_time=current_time,
        ),
        detection_result=detection_result,
        level_changed=True,
    )


def _maybe_redetect_level(
    *,
    frame_bgr: np.ndarray,
    registry: AssetRegistry,
    state: StaticSessionState,
    current_time: float,
    params: StaticSessionParams,
) -> tuple[StaticSessionState, LevelDetectionResult | None, bool]:
    if current_time - state.last_map_detect_time <= params.map_redetect_interval:
        return state, None, False

    detection_result = detect_static_level(
        frame_bgr,
        registry,
        min_confidence=params.level_min_confidence,
    )
    refreshed_state = replace(state, last_map_detect_time=current_time)
    if detection_result is None or detection_result.level_id == state.level_id:
        return refreshed_state, detection_result, False

    return (
        StaticSessionState(
            phase=StaticSessionPhase.PLAYING,
            level_id=detection_result.level_id,
            runtime_state=initial_static_runtime_state(current_time),
            last_map_detect_time=current_time,
        ),
        detection_result,
        True,
    )
