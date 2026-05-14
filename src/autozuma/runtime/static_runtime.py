"""Pure single-frame runtime orchestration for static-background levels."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace

import cv2
import numpy as np

from autozuma.core.models import LevelRuntimeAssets, LauncherTemplateSet
from autozuma.decision.static_frame import (
    StatefulStaticFrameDecisionResult,
    decide_stateful_static_frame_from_world,
)
from autozuma.runtime.modes import (
    RuntimeModeState,
    RuntimeModeUpdate,
    initial_runtime_mode_state,
    update_runtime_mode_state,
)
from autozuma.runtime.strategy_config import RuntimeStrategyConfig, build_runtime_strategy_config
from autozuma.strategy.action_updates import CommandOutcomeState
from autozuma.vision.coins import (
    CoinDetectionParams,
    CoinTrackerUpdate,
    CoinTrackingParams,
    update_active_coins_from_frame,
    update_coin_tracker_state,
)
from autozuma.vision.roi import extract_game_roi
from autozuma.vision.world_state import detect_static_world_state_from_roi


@dataclass(frozen=True)
class StaticRuntimeState:
    """Pure runtime state threaded through static-background frame decisions."""

    mode_state: RuntimeModeState
    command_outcome: CommandOutcomeState


@dataclass(frozen=True)
class StaticRuntimeFrameParams:
    """Parameters for pure static runtime frame orchestration."""

    raw_values: Mapping[str, float]
    coin_detection: CoinDetectionParams = CoinDetectionParams()
    coin_tracking: CoinTrackingParams = CoinTrackingParams()


@dataclass(frozen=True)
class StaticRuntimeFrameResult:
    """Detailed pure runtime result for one static-background frame."""

    state: StaticRuntimeState
    decision: StatefulStaticFrameDecisionResult
    coin_update: CoinTrackerUpdate
    mode_update: RuntimeModeUpdate
    strategy_config: RuntimeStrategyConfig


def initial_static_runtime_state(current_time: float) -> StaticRuntimeState:
    """Return prototype-equivalent runtime state for a newly selected static level."""
    return StaticRuntimeState(
        mode_state=initial_runtime_mode_state(current_time),
        command_outcome=CommandOutcomeState(),
    )


def run_static_runtime_frame(
    *,
    frame_bgr: np.ndarray,
    level: LevelRuntimeAssets,
    launcher_templates: LauncherTemplateSet,
    state: StaticRuntimeState,
    current_time: float,
    params: StaticRuntimeFrameParams,
) -> StaticRuntimeFrameResult:
    """Run one pure static-background runtime frame without capture or command execution."""
    pre_config = build_runtime_strategy_config(
        values=params.raw_values,
        mode_state=state.mode_state,
    )
    roi_result = extract_game_roi(frame_bgr, level)
    coin_update = _update_active_coins(
        roi_frame_bgr=roi_result.frame,
        level=level,
        state=state.command_outcome,
        current_time=current_time,
        params=params,
    )

    command_state = replace(state.command_outcome, coin_tracker=coin_update.state)
    coin_config = build_runtime_strategy_config(
        values=params.raw_values,
        mode_state=state.mode_state,
        active_coins=coin_update.active_coins,
    )
    world_state = detect_static_world_state_from_roi(
        frame_roi_bgr=roi_result.frame,
        level=level,
        launcher_templates=launcher_templates,
        p_start_exclude=coin_config.frame_decision.p_start_exclude,
        p_end_exclude=coin_config.frame_decision.p_end_exclude,
    )
    mode_update = update_runtime_mode_state(
        previous=state.mode_state,
        world_state=world_state,
        level=level,
        current_time=current_time,
        params=pre_config.mode_params,
    )
    strategy_config = build_runtime_strategy_config(
        values=params.raw_values,
        mode_state=mode_update.state,
        active_coins=coin_update.active_coins,
    )
    decision = decide_stateful_static_frame_from_world(
        roi_result=roi_result,
        world_state=world_state,
        level=level,
        state=command_state,
        current_time=current_time,
        params=strategy_config.stateful_decision,
    )

    return StaticRuntimeFrameResult(
        state=StaticRuntimeState(
            mode_state=mode_update.state,
            command_outcome=decision.state,
        ),
        decision=decision,
        coin_update=coin_update,
        mode_update=mode_update,
        strategy_config=strategy_config,
    )


def _update_active_coins(
    *,
    roi_frame_bgr: np.ndarray,
    level: LevelRuntimeAssets,
    state: CommandOutcomeState,
    current_time: float,
    params: StaticRuntimeFrameParams,
) -> CoinTrackerUpdate:
    if level.background is None or not level.topology.treasure_points:
        return update_coin_tracker_state(
            state=state.coin_tracker,
            presences=(),
            treasure_points=level.topology.treasure_points,
            current_time=current_time,
            params=params.coin_tracking,
        )

    return update_active_coins_from_frame(
        frame_gray=cv2.cvtColor(roi_frame_bgr, cv2.COLOR_BGR2GRAY),
        background_gray=level.background.gray,
        treasure_points=level.topology.treasure_points,
        state=state.coin_tracker,
        current_time=current_time,
        detection_params=params.coin_detection,
        tracking_params=params.coin_tracking,
    )
