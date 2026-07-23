"""Static-level session state machine for already-captured frames."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum

import numpy as np

from autozuma.control.execution import (
    ExecutionDriver,
    ExecutionPlan,
    build_command_execution_plan,
    execute_plan,
)
from autozuma.core.models import (
    AssetRegistry,
    Command,
    CommandType,
    LauncherTemplateSet,
    LevelDetectionResult,
)
from autozuma.runtime.grade import (
    FileGradeArchive,
    GameOverCaptureResult,
    GradeCaptureParams,
    GradeCaptureResult,
    GradeCaptureState,
    GradeCaptureStatus,
    capture_completed_level,
    capture_game_over,
)
from autozuma.runtime.host import StaticHostFrameParams, StaticHostFrameResult, run_static_host_frame
from autozuma.runtime.menu import (
    AdventureMenuFrameResult,
    AdventureMenuParams,
    AdventureMenuState,
    run_adventure_menu_frame,
)
from autozuma.runtime.static_runtime import StaticRuntimeState, initial_static_runtime_state
from autozuma.runtime.ui import (
    UiAutomationFrameResult,
    UiAutomationParams,
    UiAutomationState,
    run_ui_automation_frame,
)
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
    ui_state: UiAutomationState = UiAutomationState()
    grade_state: GradeCaptureState = GradeCaptureState()
    menu_state: AdventureMenuState = AdventureMenuState()


@dataclass(frozen=True)
class StaticSessionParams:
    """Parameters for static-level session orchestration."""

    host: StaticHostFrameParams
    level_min_confidence: float = STATIC_LEVEL_MATCH_THRESHOLD
    map_redetect_interval: float = 4.0
    ui: UiAutomationParams = UiAutomationParams()
    grade: GradeCaptureParams = GradeCaptureParams()
    menu: AdventureMenuParams = AdventureMenuParams()


@dataclass(frozen=True)
class StaticSessionUiResult:
    """UI automation output and execution plan for a static session frame."""

    automation: UiAutomationFrameResult
    execution_plan: ExecutionPlan
    grade_state: GradeCaptureState = GradeCaptureState()
    grade_capture: GradeCaptureResult | None = None
    game_over_capture: GameOverCaptureResult | None = None
    menu_state: AdventureMenuState = AdventureMenuState()
    menu: AdventureMenuFrameResult | None = None


@dataclass(frozen=True)
class StaticSessionFrameResult:
    """Detailed result for one already-captured static session frame."""

    state: StaticSessionState
    detection_result: LevelDetectionResult | None = None
    host_result: StaticHostFrameResult | None = None
    ui_result: StaticSessionUiResult | None = None
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
    ui_result = _run_ui_frame(
        frame_bgr=frame_bgr,
        registry=registry,
        state=state,
        current_time=current_time,
        params=params,
        driver=driver,
    )
    if ui_result.automation.should_skip_gameplay:
        next_state = replace(
            state,
            ui_state=ui_result.automation.state,
            grade_state=ui_result.grade_state,
            menu_state=ui_result.menu_state,
        )
        if ui_result.automation.reset_session:
            next_state = StaticSessionState(
                ui_state=ui_result.automation.state,
                grade_state=ui_result.grade_state,
                menu_state=ui_result.menu_state,
            )
        return StaticSessionFrameResult(
            state=next_state,
            ui_result=ui_result,
        )

    state = replace(
        state,
        ui_state=ui_result.automation.state,
        grade_state=ui_result.grade_state,
        menu_state=ui_result.menu_state,
    )
    if state.phase is StaticSessionPhase.DETECTING:
        result = _detect_initial_level(
            frame_bgr=frame_bgr,
            registry=registry,
            state=state,
            current_time=current_time,
            params=params,
        )
        return replace(result, ui_result=ui_result)

    active_state, detection_result, level_changed = _maybe_redetect_level(
        frame_bgr=frame_bgr,
        registry=registry,
        state=state,
        current_time=current_time,
        params=params,
    )
    if active_state.level_id is None or active_state.runtime_state is None:
        return StaticSessionFrameResult(
            state=StaticSessionState(
                last_map_detect_time=current_time,
                ui_state=active_state.ui_state,
                grade_state=active_state.grade_state,
                menu_state=active_state.menu_state,
            ),
            detection_result=detection_result,
            ui_result=ui_result,
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
        ui_result=ui_result,
        level_changed=level_changed,
    )


def _run_ui_frame(
    *,
    frame_bgr: np.ndarray,
    registry: AssetRegistry,
    state: StaticSessionState,
    current_time: float,
    params: StaticSessionParams,
    driver: ExecutionDriver,
) -> StaticSessionUiResult:
    automation = run_ui_automation_frame(
        frame_bgr=frame_bgr,
        templates=registry.templates.ui,
        state=state.ui_state,
        current_time=current_time,
        params=params.ui,
    )
    automation, grade_state, grade_capture, game_over_capture = (
        _capture_outcome_before_click(
            frame_bgr=frame_bgr,
            state=state,
            current_time=current_time,
            params=params,
            automation=automation,
        )
    )
    menu_result = None
    menu_state = state.menu_state
    if not automation.should_skip_gameplay and state.phase is StaticSessionPhase.DETECTING:
        menu_result = run_adventure_menu_frame(
            frame_bgr=frame_bgr,
            state=state.menu_state,
            current_time=current_time,
            params=params.menu,
        )
        menu_state = menu_result.state
        if menu_result.detected:
            automation = replace(
                automation,
                command=menu_result.command,
                should_skip_gameplay=True,
                reset_session=False,
            )
    execution_plan = build_command_execution_plan(
        automation.command,
        swap_delay_ms=params.host.swap_delay_ms,
    )
    if params.host.execute_commands:
        execute_plan(execution_plan, driver)
    return StaticSessionUiResult(
        automation=automation,
        execution_plan=execution_plan,
        grade_state=grade_state,
        grade_capture=grade_capture,
        game_over_capture=game_over_capture,
        menu_state=menu_state,
        menu=menu_result,
    )


def _capture_outcome_before_click(
    *,
    frame_bgr: np.ndarray,
    state: StaticSessionState,
    current_time: float,
    params: StaticSessionParams,
    automation: UiAutomationFrameResult,
) -> tuple[
    UiAutomationFrameResult,
    GradeCaptureState,
    GradeCaptureResult | None,
    GameOverCaptureResult | None,
]:
    detection = automation.detection_result
    if detection is None or detection.template_id != "ok":
        return automation, state.grade_state, None, None

    grade_capture = capture_completed_level(
        frame_bgr=frame_bgr,
        ok_target=detection.target,
        level_id=state.level_id,
        raw_values=params.host.runtime.raw_values,
        current_time=current_time,
        params=params.grade,
        recorded_fingerprint=state.grade_state.recorded_fingerprint,
    )
    game_over_capture = None
    capture: GradeCaptureResult | GameOverCaptureResult = grade_capture
    if grade_capture.status is GradeCaptureStatus.NOT_STATS:
        game_over_capture = capture_game_over(
            frame_bgr=frame_bgr,
            ok_target=detection.target,
            level_id=state.level_id,
            raw_values=params.host.runtime.raw_values,
            current_time=current_time,
            params=params.grade,
            recorded_fingerprint=state.grade_state.recorded_fingerprint,
        )
        capture = game_over_capture
    if capture.status is GradeCaptureStatus.NOT_STATS:
        return automation, GradeCaptureState(), grade_capture, game_over_capture
    if capture.status in {GradeCaptureStatus.RECORDED, GradeCaptureStatus.DUPLICATE}:
        return (
            automation,
            GradeCaptureState(recorded_fingerprint=capture.fingerprint),
            grade_capture,
            game_over_capture,
        )

    retry_count = state.grade_state.retry_count + 1
    grade_state = GradeCaptureState(
        recorded_fingerprint=state.grade_state.recorded_fingerprint,
        retry_count=retry_count,
    )
    if retry_count < max(1, params.grade.max_parse_attempts):
        return (
            _defer_ui_click(
                automation,
                current_time=current_time,
                retry_interval=params.grade.retry_interval,
            ),
            grade_state,
            grade_capture,
            game_over_capture,
        )

    try:
        FileGradeArchive(root=params.grade.root).save_failure(
            frame_bgr=frame_bgr,
            current_time=current_time,
            error=capture.error or "unknown STATS recognition failure",
        )
    except (OSError, ValueError):
        pass
    return automation, GradeCaptureState(), grade_capture, game_over_capture


def _defer_ui_click(
    automation: UiAutomationFrameResult,
    *,
    current_time: float,
    retry_interval: float,
) -> UiAutomationFrameResult:
    if automation.command.command_type is not CommandType.UI_CLICK:
        return automation
    deferred_state = replace(
        automation.state,
        click_count=automation.state.click_count + 1,
        next_click_time=current_time + max(0.01, retry_interval),
    )
    return replace(
        automation,
        state=deferred_state,
        command=Command(command_type=CommandType.NO_OP),
        reset_session=False,
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
            ui_state=state.ui_state,
            grade_state=state.grade_state,
            menu_state=state.menu_state,
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
            ui_state=state.ui_state,
            grade_state=state.grade_state,
            menu_state=state.menu_state,
        ),
        detection_result,
        True,
    )
