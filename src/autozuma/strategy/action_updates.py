"""Pure command-result updates for action memory and cooldown planning."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from autozuma.core.models import (
    Command,
    CommandType,
    LevelRuntimeAssets,
    Point,
    TargetCandidate,
    WorldState,
)
from autozuma.strategy.actions import (
    ActionTrackerState,
    add_cluster_lock,
    add_deadzone,
    add_virtual_ball,
    prune_action_tracker_state,
)
from autozuma.strategy.coins import BREAKTHROUGH_COIN_TARGET, DIRECT_COIN_TARGET
from autozuma.strategy.discard import DISCARD_TARGET
from autozuma.strategy.targets import COMBO_TARGET, ELIM_TARGET, PAIR_TARGET, ROLLBACK_ELIM_TARGET
from autozuma.vision.coins import CoinTrackerState, lock_coin
from autozuma.vision.colors import UNKNOWN_COLOR


@dataclass(frozen=True)
class CommandOutcomeState:
    """Runtime state advanced after a selected command is emitted."""

    action_tracker: ActionTrackerState = field(default_factory=ActionTrackerState)
    coin_tracker: CoinTrackerState = field(default_factory=CoinTrackerState)
    last_swap_time: float = 0.0
    next_fire_ready_time: float = 0.0
    last_fire_time: float = 0.0


@dataclass(frozen=True)
class CommandOutcomeParams:
    """Tunable timing parameters used by pure command-result updates."""

    bullet_speed: float = 800.0
    fire_cooldown: float = 0.3
    swap_fire_extra_delay: float = 0.05
    combo_hang_base: float = 0.8
    combo_hang_mult: float = 0.6
    combo_lock_track_radius: int = 150
    adjacent_combo_lock_padding: int = 80
    adjacent_combo_lock_extra: float = 0.5
    direct_coin_lock_duration: float = 1.0
    breakthrough_coin_lock_duration: float = 2.0
    breakthrough_delay: float = 0.25


def apply_command_outcome(
    *,
    state: CommandOutcomeState,
    command: Command,
    selected_target: TargetCandidate | None,
    world_state: WorldState,
    level: LevelRuntimeAssets,
    current_time: float,
    params: CommandOutcomeParams = CommandOutcomeParams(),
) -> CommandOutcomeState:
    """Return updated pure runtime state after a command has been selected."""
    action_tracker = prune_action_tracker_state(state.action_tracker, current_time)
    coin_tracker = _prune_coin_locks(state.coin_tracker, current_time)

    if command.command_type in {CommandType.NO_OP, CommandType.UI_CLICK}:
        return CommandOutcomeState(
            action_tracker=action_tracker,
            coin_tracker=coin_tracker,
            last_swap_time=state.last_swap_time,
            next_fire_ready_time=state.next_fire_ready_time,
            last_fire_time=state.last_fire_time,
        )

    is_swapping = command.command_type in {
        CommandType.SWAP_SHOOT,
        CommandType.SWAP_DOUBLE_SHOOT,
    }
    swap_extra = params.swap_fire_extra_delay if is_swapping else 0.0
    last_swap_time = current_time if is_swapping else state.last_swap_time

    if selected_target is None:
        return CommandOutcomeState(
            action_tracker=action_tracker,
            coin_tracker=coin_tracker,
            last_swap_time=last_swap_time,
            next_fire_ready_time=current_time + params.fire_cooldown + swap_extra,
            last_fire_time=current_time,
        )

    travel_time = _travel_time(
        frog_pivot=level.topology.frog_pivot,
        target=Point(x=selected_target.x, y=selected_target.y),
        bullet_speed=params.bullet_speed,
    )
    fired_color = _fired_color(world_state, is_swapping)

    match selected_target.target_type:
        case target_type if target_type == BREAKTHROUGH_COIN_TARGET:
            action_tracker = add_deadzone(
                action_tracker,
                point=Point(x=selected_target.x, y=selected_target.y),
                current_time=current_time,
                duration=travel_time,
            )
            if selected_target.secondary_x is not None and selected_target.secondary_y is not None:
                coin_tracker = lock_coin(
                    coin_tracker,
                    point=Point(x=selected_target.secondary_x, y=selected_target.secondary_y),
                    current_time=current_time,
                    duration=params.breakthrough_coin_lock_duration,
                )
            delay = _command_delay_seconds(command, selected_target, params)
            next_fire_ready_time = current_time + delay + params.fire_cooldown + swap_extra

        case target_type if target_type == DIRECT_COIN_TARGET:
            action_tracker = add_deadzone(
                action_tracker,
                point=Point(x=selected_target.x, y=selected_target.y),
                current_time=current_time,
                duration=travel_time,
            )
            coin_tracker = lock_coin(
                coin_tracker,
                point=Point(x=selected_target.x, y=selected_target.y),
                current_time=current_time,
                duration=params.direct_coin_lock_duration,
            )
            next_fire_ready_time = current_time + params.fire_cooldown + swap_extra

        case target_type if target_type == COMBO_TARGET:
            lock_duration = (
                travel_time
                + params.combo_hang_base
                + selected_target.combo_depth * params.combo_hang_mult
            )
            action_tracker = _add_combo_locks(
                state=action_tracker,
                target=selected_target,
                world_state=world_state,
                current_time=current_time,
                duration=lock_duration,
                params=params,
            )
            action_tracker = add_deadzone(
                action_tracker,
                point=Point(x=selected_target.x, y=selected_target.y),
                current_time=current_time,
                duration=lock_duration,
            )
            next_fire_ready_time = current_time + lock_duration + swap_extra

        case target_type if target_type in {ELIM_TARGET, ROLLBACK_ELIM_TARGET}:
            action_tracker = add_deadzone(
                action_tracker,
                point=Point(x=selected_target.x, y=selected_target.y),
                current_time=current_time,
                duration=travel_time,
            )
            next_fire_ready_time = current_time + params.fire_cooldown + swap_extra

        case target_type if target_type == PAIR_TARGET:
            action_tracker = add_deadzone(
                action_tracker,
                point=Point(x=selected_target.x, y=selected_target.y),
                current_time=current_time,
                duration=travel_time,
            )
            if (
                selected_target.track_id is not None
                and selected_target.track_idx is not None
                and fired_color != UNKNOWN_COLOR
            ):
                action_tracker = add_virtual_ball(
                    action_tracker,
                    track_id=selected_target.track_id,
                    track_idx=selected_target.track_idx,
                    color=fired_color,
                    current_time=current_time,
                    duration=travel_time,
                )
            next_fire_ready_time = current_time + params.fire_cooldown + swap_extra

        case target_type if target_type == DISCARD_TARGET:
            next_fire_ready_time = current_time + params.fire_cooldown + swap_extra

        case _:
            action_tracker = add_deadzone(
                action_tracker,
                point=Point(x=selected_target.x, y=selected_target.y),
                current_time=current_time,
                duration=travel_time,
            )
            next_fire_ready_time = current_time + params.fire_cooldown + swap_extra

    return CommandOutcomeState(
        action_tracker=action_tracker,
        coin_tracker=coin_tracker,
        last_swap_time=last_swap_time,
        next_fire_ready_time=next_fire_ready_time,
        last_fire_time=current_time,
    )


def _add_combo_locks(
    *,
    state: ActionTrackerState,
    target: TargetCandidate,
    world_state: WorldState,
    current_time: float,
    duration: float,
    params: CommandOutcomeParams,
) -> ActionTrackerState:
    if target.track_id is None or target.track_idx is None:
        return state

    state = add_cluster_lock(
        state,
        track_id=target.track_id,
        start_idx=target.track_idx - params.combo_lock_track_radius,
        end_idx=target.track_idx + params.combo_lock_track_radius,
        current_time=current_time,
        duration=duration,
    )

    target_cluster_idx = _target_cluster_index(target, world_state)
    if target_cluster_idx is None:
        return state

    for adjacent_idx in (
        _previous_known_cluster_idx(world_state, target_cluster_idx - 1),
        _next_known_cluster_idx(world_state, target_cluster_idx + 1),
    ):
        if adjacent_idx is None:
            continue
        cluster = world_state.clusters[adjacent_idx]
        state = add_cluster_lock(
            state,
            track_id=cluster.track_id,
            start_idx=cluster.start_idx - params.adjacent_combo_lock_padding,
            end_idx=cluster.end_idx + params.adjacent_combo_lock_padding,
            current_time=current_time,
            duration=duration + params.adjacent_combo_lock_extra,
        )

    return state


def _target_cluster_index(target: TargetCandidate, world_state: WorldState) -> int | None:
    if target.track_id is None or target.cluster_start_idx is None or target.cluster_end_idx is None:
        return None
    for idx, cluster in enumerate(world_state.clusters):
        if (
            cluster.track_id == target.track_id
            and cluster.start_idx == target.cluster_start_idx
            and cluster.end_idx == target.cluster_end_idx
        ):
            return idx
    return None


def _previous_known_cluster_idx(world_state: WorldState, start_idx: int) -> int | None:
    idx = start_idx
    while idx >= 0 and world_state.clusters[idx].color == UNKNOWN_COLOR:
        idx -= 1
    if idx < 0:
        return None
    return idx


def _next_known_cluster_idx(world_state: WorldState, start_idx: int) -> int | None:
    idx = start_idx
    while idx < len(world_state.clusters) and world_state.clusters[idx].color == UNKNOWN_COLOR:
        idx += 1
    if idx >= len(world_state.clusters):
        return None
    return idx


def _travel_time(frog_pivot: Point, target: Point, bullet_speed: float) -> float:
    if bullet_speed <= 0.0:
        raise ValueError("bullet_speed must be positive")
    return math.hypot(target.x - frog_pivot.x, target.y - frog_pivot.y) / bullet_speed


def _fired_color(world_state: WorldState, is_swapping: bool) -> str:
    return world_state.launcher.next_ball if is_swapping else world_state.launcher.current_ball


def _command_delay_seconds(
    command: Command,
    target: TargetCandidate,
    params: CommandOutcomeParams,
) -> float:
    if command.delay_ms > 0:
        return command.delay_ms / 1000.0
    if target.delay_ms > 0:
        return target.delay_ms / 1000.0
    return params.breakthrough_delay


def _prune_coin_locks(state: CoinTrackerState, current_time: float) -> CoinTrackerState:
    return CoinTrackerState(
        tracks=state.tracks,
        locks=tuple(lock for lock in state.locks if lock.expires_at > current_time),
    )
