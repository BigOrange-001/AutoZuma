"""Pure single-frame decision pipeline for static-background levels."""

from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np

from autozuma.control.commands import map_command_to_screen
from autozuma.core.models import (
    Command,
    CommandType,
    GameRoiResult,
    LevelRuntimeAssets,
    LauncherTemplateSet,
    Point,
    TargetCandidate,
    WorldState,
)
from autozuma.strategy.action_updates import (
    CommandOutcomeParams,
    CommandOutcomeState,
    apply_command_outcome,
)
from autozuma.strategy.actions import apply_virtual_balls_to_clusters
from autozuma.strategy.commands import command_for_selected_target
from autozuma.strategy.coins import CoinScoringParams, score_coin_targets_for_color
from autozuma.strategy.discard import DiscardParams, discard_target
from autozuma.strategy.selection import TargetSelectionParams, select_best_clear_target
from autozuma.strategy.swap import SwapDecision, SwapDecisionParams, choose_swap_candidates
from autozuma.strategy.targets import (
    TargetScoringParams,
    score_basic_targets,
    score_basic_targets_for_color,
)
from autozuma.vision.roi import extract_game_roi
from autozuma.vision.world_state import detect_static_world_state_from_roi


@dataclass(frozen=True)
class StaticFrameDecisionParams:
    """Parameters for a pure static-frame decision pass."""

    target_scoring: TargetScoringParams = TargetScoringParams()
    target_swap: SwapDecisionParams = SwapDecisionParams()
    target_selection: TargetSelectionParams = TargetSelectionParams()
    coin_scoring: CoinScoringParams = CoinScoringParams()
    active_coins: tuple[Point, ...] = ()
    fallback_discard: DiscardParams = DiscardParams()
    p_start_exclude: float = 0.0
    p_end_exclude: float = 0.0


@dataclass(frozen=True)
class StaticFrameDecisionResult:
    """Detailed result for one pure static-frame decision pass."""

    roi_result: GameRoiResult
    world_state: WorldState
    current_candidates: tuple[TargetCandidate, ...]
    next_candidates: tuple[TargetCandidate, ...]
    swap_decision: SwapDecision
    aim_candidates: tuple[TargetCandidate, ...]
    selected_target: TargetCandidate | None
    roi_command: Command
    screen_command: Command
    used_fallback: bool = False


@dataclass(frozen=True)
class StatefulStaticFrameDecisionParams:
    """Parameters for pure stateful static-frame decision planning."""

    frame_decision: StaticFrameDecisionParams = StaticFrameDecisionParams()
    outcome: CommandOutcomeParams = CommandOutcomeParams()
    swap_cooldown: float = 0.5


@dataclass(frozen=True)
class StatefulStaticFrameDecisionResult:
    """Pure frame decision plus updated runtime-planning state."""

    decision: StaticFrameDecisionResult
    state: CommandOutcomeState
    can_fire: bool
    can_swap: bool


def decide_static_frame_command(
    frame_bgr: np.ndarray,
    level: LevelRuntimeAssets,
    launcher_templates: LauncherTemplateSet,
    params: StaticFrameDecisionParams = StaticFrameDecisionParams(),
) -> Command:
    """Return a screen-frame command for one static-background game frame."""
    return decide_static_frame(
        frame_bgr=frame_bgr,
        level=level,
        launcher_templates=launcher_templates,
        params=params,
    ).screen_command


def decide_static_frame(
    frame_bgr: np.ndarray,
    level: LevelRuntimeAssets,
    launcher_templates: LauncherTemplateSet,
    params: StaticFrameDecisionParams = StaticFrameDecisionParams(),
    allow_swap: bool = True,
) -> StaticFrameDecisionResult:
    """Return detailed pure decision data for one static-background game frame."""
    roi_result = extract_game_roi(frame_bgr, level)
    world_state = detect_static_world_state_from_roi(
        frame_roi_bgr=roi_result.frame,
        level=level,
        launcher_templates=launcher_templates,
        p_start_exclude=params.p_start_exclude,
        p_end_exclude=params.p_end_exclude,
    )
    return decide_static_frame_from_world(
        roi_result=roi_result,
        world_state=world_state,
        level=level,
        params=params,
        allow_swap=allow_swap,
    )


def decide_stateful_static_frame(
    frame_bgr: np.ndarray,
    level: LevelRuntimeAssets,
    launcher_templates: LauncherTemplateSet,
    state: CommandOutcomeState,
    current_time: float,
    params: StatefulStaticFrameDecisionParams = StatefulStaticFrameDecisionParams(),
) -> StatefulStaticFrameDecisionResult:
    """Return a pure static-frame decision and updated runtime-planning state."""
    frame_params = _params_with_action_state(
        params.frame_decision,
        state=state,
        current_time=current_time,
    )
    roi_result = extract_game_roi(frame_bgr, level)
    world_state = detect_static_world_state_from_roi(
        frame_roi_bgr=roi_result.frame,
        level=level,
        launcher_templates=launcher_templates,
        p_start_exclude=frame_params.p_start_exclude,
        p_end_exclude=frame_params.p_end_exclude,
    )
    return decide_stateful_static_frame_from_world(
        roi_result=roi_result,
        world_state=world_state,
        level=level,
        state=state,
        current_time=current_time,
        params=params,
    )


def decide_stateful_static_frame_from_world(
    roi_result: GameRoiResult,
    world_state: WorldState,
    level: LevelRuntimeAssets,
    state: CommandOutcomeState,
    current_time: float,
    params: StatefulStaticFrameDecisionParams = StatefulStaticFrameDecisionParams(),
) -> StatefulStaticFrameDecisionResult:
    """Return a stateful pure decision from an already-extracted ROI/world state."""
    frame_params = _params_with_action_state(
        params.frame_decision,
        state=state,
        current_time=current_time,
    )
    can_swap = current_time - state.last_swap_time >= params.swap_cooldown
    decision = decide_static_frame_from_world(
        roi_result=roi_result,
        world_state=world_state,
        level=level,
        params=frame_params,
        allow_swap=can_swap,
    )
    decision = _apply_virtual_balls_to_decision(
        decision=decision,
        level=level,
        params=frame_params,
        state=state,
        current_time=current_time,
        allow_swap=can_swap,
    )

    can_fire = current_time >= state.next_fire_ready_time
    if not can_fire and _is_shoot_command(decision.screen_command):
        decision = replace(
            decision,
            roi_command=Command(command_type=CommandType.NO_OP),
            screen_command=Command(command_type=CommandType.NO_OP),
        )

    if _is_shoot_command(decision.screen_command):
        updated_state = apply_command_outcome(
            state=state,
            command=decision.roi_command,
            selected_target=decision.selected_target,
            world_state=decision.world_state,
            level=level,
            current_time=current_time,
            params=params.outcome,
        )
    else:
        updated_state = apply_command_outcome(
            state=state,
            command=Command(command_type=CommandType.NO_OP),
            selected_target=None,
            world_state=decision.world_state,
            level=level,
            current_time=current_time,
            params=params.outcome,
        )

    return StatefulStaticFrameDecisionResult(
        decision=decision,
        state=updated_state,
        can_fire=can_fire,
        can_swap=can_swap,
    )


def decide_static_frame_from_world(
    roi_result: GameRoiResult,
    world_state: WorldState,
    level: LevelRuntimeAssets,
    params: StaticFrameDecisionParams = StaticFrameDecisionParams(),
    allow_swap: bool = True,
) -> StaticFrameDecisionResult:
    """Return detailed decision data from an already-extracted ROI and world state."""
    candidates = score_basic_targets(
        world_state=world_state,
        level=level,
        params=params.target_scoring,
    ) + score_coin_targets_for_color(
        world_state=world_state,
        level=level,
        active_coins=params.active_coins,
        target_color=world_state.launcher.current_ball,
        params=params.coin_scoring,
    )
    next_candidates = score_basic_targets_for_color(
        world_state=world_state,
        level=level,
        target_color=world_state.launcher.next_ball,
        params=params.target_scoring,
    ) + score_coin_targets_for_color(
        world_state=world_state,
        level=level,
        active_coins=params.active_coins,
        target_color=world_state.launcher.next_ball,
        params=params.coin_scoring,
    )
    if allow_swap:
        swap_decision = choose_swap_candidates(
            current_candidates=candidates,
            next_candidates=next_candidates,
            current_color=world_state.launcher.current_ball,
            next_color=world_state.launcher.next_ball,
            params=params.target_swap,
        )
    else:
        swap_decision = _stay_for_swap_cooldown(candidates, next_candidates)
    aim_candidates = tuple(swap_decision.candidates)
    selected_target = select_best_clear_target(
        world_state=world_state,
        candidates=aim_candidates,
        frog_pivot=level.topology.frog_pivot,
        params=params.target_selection,
    )
    should_discard = selected_target is None and bool(swap_decision.candidates)
    if selected_target is None and (should_discard or not swap_decision.candidates):
        selected_target = discard_target(
            world_state=world_state,
            level=level,
            roi_size=(roi_result.frame.shape[1], roi_result.frame.shape[0]),
            params=params.fallback_discard,
        )
        swap = False
    else:
        swap = swap_decision.should_swap

    roi_command = command_for_selected_target(selected_target, swap=swap)
    screen_command = map_command_to_screen(roi_command, roi_result)
    return StaticFrameDecisionResult(
        roi_result=roi_result,
        world_state=world_state,
        current_candidates=tuple(candidates),
        next_candidates=tuple(next_candidates),
        swap_decision=swap_decision,
        aim_candidates=aim_candidates,
        selected_target=selected_target,
        roi_command=roi_command,
        screen_command=screen_command,
        used_fallback=selected_target is not None and not swap and should_discard,
    )


def _params_with_action_state(
    params: StaticFrameDecisionParams,
    state: CommandOutcomeState,
    current_time: float,
) -> StaticFrameDecisionParams:
    target_scoring = replace(
        params.target_scoring,
        action_state=state.action_tracker,
        current_time=current_time,
    )
    return replace(params, target_scoring=target_scoring)


def _apply_virtual_balls_to_decision(
    *,
    decision: StaticFrameDecisionResult,
    level: LevelRuntimeAssets,
    params: StaticFrameDecisionParams,
    state: CommandOutcomeState,
    current_time: float,
    allow_swap: bool,
) -> StaticFrameDecisionResult:
    clusters = apply_virtual_balls_to_clusters(
        clusters=decision.world_state.clusters,
        state=state.action_tracker,
        current_time=current_time,
    )
    if clusters == decision.world_state.clusters:
        return decision
    return decide_static_frame_from_world(
        roi_result=decision.roi_result,
        world_state=replace(decision.world_state, clusters=clusters),
        level=level,
        params=params,
        allow_swap=allow_swap,
    )


def _stay_for_swap_cooldown(
    candidates: tuple[TargetCandidate, ...],
    next_candidates: tuple[TargetCandidate, ...],
) -> SwapDecision:
    return SwapDecision(
        should_swap=False,
        candidates=candidates,
        current_best_score=_best_positive_score(candidates),
        next_best_score=_best_positive_score(next_candidates),
        reason="swap cooldown active",
    )


def _best_positive_score(candidates: tuple[TargetCandidate, ...]) -> float:
    if not candidates:
        return 0.0
    return max(0.0, max(candidate.score for candidate in candidates))


def _is_shoot_command(command: Command) -> bool:
    return command.command_type in {
        CommandType.SHOOT,
        CommandType.DOUBLE_SHOOT,
        CommandType.SWAP_SHOOT,
        CommandType.SWAP_DOUBLE_SHOOT,
    }
