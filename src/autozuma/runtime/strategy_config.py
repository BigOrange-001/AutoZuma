"""Adapt prototype-style runtime params into pure strategy parameter objects."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from autozuma.core.models import Point
from autozuma.decision.static_frame import (
    StatefulStaticFrameDecisionParams,
    StaticFrameDecisionParams,
)
from autozuma.runtime.modes import RuntimeModeParams, RuntimeModeState
from autozuma.runtime.params import RuntimeParameterResolver
from autozuma.strategy.action_updates import CommandOutcomeParams
from autozuma.strategy.coins import CoinScoringParams
from autozuma.strategy.discard import DiscardParams
from autozuma.strategy.selection import TargetSelectionParams
from autozuma.strategy.swap import SwapDecisionParams
from autozuma.strategy.targets import TargetScoringParams


@dataclass(frozen=True)
class RuntimeStrategyConfig:
    """Concrete pure runtime config derived from prototype-style raw parameters."""

    mode_params: RuntimeModeParams
    stateful_decision: StatefulStaticFrameDecisionParams

    @property
    def frame_decision(self) -> StaticFrameDecisionParams:
        return self.stateful_decision.frame_decision


def build_runtime_strategy_config(
    values: Mapping[str, float],
    mode_state: RuntimeModeState,
    active_coins: tuple[Point, ...] = (),
) -> RuntimeStrategyConfig:
    """Build concrete pure pipeline params from raw shared/INI-style values."""
    resolver = RuntimeParameterResolver(values)
    mode = mode_state.mode

    m_gap = resolver.get("M_GAP", mode)
    fire_cooldown = resolver.get("FIRE_COOLDOWN", mode)
    combo_hang_base = resolver.get("COMBO_HANG_BASE", mode)
    combo_hang_mult = resolver.get("COMBO_HANG_MULT", mode)
    soft_lock_radius = resolver.get("SOFT_LOCK_RADIUS", mode)
    coin_break_delay = resolver.get("COIN_BREAK_DELAY", mode)

    frame_decision = StaticFrameDecisionParams(
        target_scoring=TargetScoringParams(
            combo_priority=resolver.ranked_priority("PRIO_COMBO", mode),
            rollback_elim_priority=resolver.ranked_priority("PRIO_ROLLBACK_ELIM", mode),
            elim_priority=resolver.ranked_priority("PRIO_ELIM", mode),
            pair_priority=resolver.ranked_priority("PRIO_PAIR", mode),
            soft_lock_radius=soft_lock_radius,
        ),
        target_swap=SwapDecisionParams(),
        target_selection=TargetSelectionParams(),
        coin_scoring=CoinScoringParams(
            coin_priority=resolver.ranked_priority("PRIO_COIN", mode),
            min_gap=m_gap,
            breakthrough_delay_ms=int(coin_break_delay * 1000),
        ),
        active_coins=active_coins,
        fallback_discard=DiscardParams(min_gap=m_gap),
        p_start_exclude=resolver.get("TRACK_START_EXCLUDE", mode),
        p_end_exclude=resolver.get("TRACK_END_EXCLUDE", mode),
    )

    return RuntimeStrategyConfig(
        mode_params=RuntimeModeParams(
            rescue_distance_threshold=resolver.get("RESCUE_TH", mode),
            endgame_spawn_distance_threshold=resolver.get("ENDGAME_SPAWN_TH", mode),
        ),
        stateful_decision=StatefulStaticFrameDecisionParams(
            frame_decision=frame_decision,
            outcome=CommandOutcomeParams(
                fire_cooldown=fire_cooldown,
                combo_hang_base=combo_hang_base,
                combo_hang_mult=combo_hang_mult,
                breakthrough_delay=coin_break_delay,
            ),
        ),
    )
