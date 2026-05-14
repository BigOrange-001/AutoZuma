"""Pure single-frame decision pipeline for static-background levels."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from autozuma.control.commands import map_command_to_screen
from autozuma.core.models import Command, LevelRuntimeAssets, LauncherTemplateSet, Point
from autozuma.strategy.commands import command_for_selected_target
from autozuma.strategy.coins import CoinScoringParams, score_coin_targets_for_color
from autozuma.strategy.discard import DiscardParams, discard_target
from autozuma.strategy.prediction import TargetPredictionParams, predict_targets
from autozuma.strategy.selection import TargetSelectionParams, select_best_clear_target
from autozuma.strategy.swap import SwapDecisionParams, choose_swap_candidates
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
    target_prediction: TargetPredictionParams = TargetPredictionParams()
    target_selection: TargetSelectionParams = TargetSelectionParams()
    coin_scoring: CoinScoringParams = CoinScoringParams()
    active_coins: tuple[Point, ...] = ()
    fallback_discard: DiscardParams = DiscardParams()
    p_start_exclude: float = 0.0
    p_end_exclude: float = 0.0


def decide_static_frame_command(
    frame_bgr: np.ndarray,
    level: LevelRuntimeAssets,
    launcher_templates: LauncherTemplateSet,
    params: StaticFrameDecisionParams = StaticFrameDecisionParams(),
) -> Command:
    """Return a screen-frame command for one static-background game frame."""
    roi_result = extract_game_roi(frame_bgr, level)
    world_state = detect_static_world_state_from_roi(
        frame_roi_bgr=roi_result.frame,
        level=level,
        launcher_templates=launcher_templates,
        p_start_exclude=params.p_start_exclude,
        p_end_exclude=params.p_end_exclude,
    )
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
    swap_decision = choose_swap_candidates(
        current_candidates=candidates,
        next_candidates=next_candidates,
        current_color=world_state.launcher.current_ball,
        next_color=world_state.launcher.next_ball,
        params=params.target_swap,
    )
    predicted_candidates = predict_targets(
        targets=swap_decision.candidates,
        level=level,
        frog_pivot=level.topology.frog_pivot,
        params=params.target_prediction,
    )
    selected_target = select_best_clear_target(
        world_state=world_state,
        candidates=predicted_candidates,
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
    return map_command_to_screen(roi_command, roi_result)
