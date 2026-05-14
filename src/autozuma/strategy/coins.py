"""Pure coin target scoring from already-detected active coin points."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from autozuma.core.models import Cluster, LevelRuntimeAssets, Point, TargetCandidate, WorldState
from autozuma.strategy.line_of_sight import check_line_of_sight
from autozuma.vision.colors import UNKNOWN_COLOR

DIRECT_COIN_TARGET = "direct_coin"
BREAKTHROUGH_COIN_TARGET = "breakthrough_coin"


@dataclass(frozen=True)
class CoinScoringParams:
    """Parameters for pure coin target generation."""

    coin_priority: float = 100000.0
    min_gap: float = 36.0
    breakthrough_aim_offset_idx: int = 15
    breakthrough_delay_ms: int = 250


def score_coin_targets(
    world_state: WorldState,
    level: LevelRuntimeAssets,
    active_coins: Iterable[Point],
    params: CoinScoringParams = CoinScoringParams(),
) -> tuple[TargetCandidate, ...]:
    """Score active coins for the launcher current ball."""
    return score_coin_targets_for_color(
        world_state=world_state,
        level=level,
        active_coins=active_coins,
        target_color=world_state.launcher.current_ball,
        params=params,
    )


def score_coin_targets_for_color(
    world_state: WorldState,
    level: LevelRuntimeAssets,
    active_coins: Iterable[Point],
    target_color: str,
    params: CoinScoringParams = CoinScoringParams(),
) -> tuple[TargetCandidate, ...]:
    """Score direct and breakthrough coin targets for a specific ball color."""
    if target_color == UNKNOWN_COLOR or not world_state.entities:
        return ()

    targets: list[TargetCandidate] = []
    for coin in active_coins:
        blockers = _coin_blockers(
            world_state=world_state,
            frog_pivot=level.topology.frog_pivot,
            coin=coin,
            params=params,
        )
        if not blockers:
            targets.append(_direct_coin_target(coin, params))
            continue
        if len(blockers) == 1:
            target = _breakthrough_coin_target(
                blocker=blockers[0],
                coin=coin,
                target_color=target_color,
                level=level,
                params=params,
            )
            if target is not None:
                targets.append(target)

    targets.sort(key=lambda target: target.score, reverse=True)
    return tuple(targets)


def _coin_blockers(
    world_state: WorldState,
    frog_pivot: Point,
    coin: Point,
    params: CoinScoringParams,
) -> tuple[Cluster, ...]:
    blockers: list[Cluster] = []
    for cluster in world_state.clusters:
        if cluster.color == UNKNOWN_COLOR:
            continue
        line_of_sight = check_line_of_sight(
            frog_pivot=frog_pivot,
            target=coin,
            entities=cluster.entities,
            min_gap=params.min_gap,
        )
        if not line_of_sight.is_clear:
            blockers.append(cluster)
    return tuple(blockers)


def _direct_coin_target(coin: Point, params: CoinScoringParams) -> TargetCandidate:
    return TargetCandidate(
        x=coin.x,
        y=coin.y,
        score=params.coin_priority * 2.0,
        target_type=DIRECT_COIN_TARGET,
        reason="direct coin line of sight is clear",
    )


def _breakthrough_coin_target(
    blocker: Cluster,
    coin: Point,
    target_color: str,
    level: LevelRuntimeAssets,
    params: CoinScoringParams,
) -> TargetCandidate | None:
    if blocker.color != target_color or blocker.size < 2:
        return None

    center_entity = blocker.entities[len(blocker.entities) // 2]
    track = next(
        (track for track in level.geometry.tracks if track.track_id == blocker.track_id),
        None,
    )
    if track is None or not track.points:
        return None

    aim_idx = min(center_entity.track_idx + params.breakthrough_aim_offset_idx, len(track.points) - 1)
    aim_point = track.points[aim_idx]
    return TargetCandidate(
        x=aim_point.x,
        y=aim_point.y,
        score=params.coin_priority * 1.5,
        target_type=BREAKTHROUGH_COIN_TARGET,
        reason=(
            f"breakthrough coin blocker track={blocker.track_id} "
            f"color={blocker.color} size={blocker.size}"
        ),
        track_id=blocker.track_id,
        track_idx=aim_idx,
        cluster_start_idx=blocker.start_idx,
        cluster_end_idx=blocker.end_idx,
        secondary_x=coin.x,
        secondary_y=coin.y,
        delay_ms=params.breakthrough_delay_ms,
    )
