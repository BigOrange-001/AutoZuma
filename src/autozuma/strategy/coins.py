"""Pure coin target scoring from already-detected active coin points."""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass

from autozuma.core.models import (
    BallEntity,
    Cluster,
    LevelRuntimeAssets,
    Point,
    TargetCandidate,
    WorldState,
)
from autozuma.strategy.aiming import aim_at_ball_entities
from autozuma.strategy.line_of_sight import check_line_of_sight, reachable_entities
from autozuma.vision.colors import UNKNOWN_COLOR

DIRECT_COIN_TARGET = "direct_coin"
BREAKTHROUGH_COIN_TARGET = "breakthrough_coin"


@dataclass(frozen=True)
class CoinScoringParams:
    """Parameters for pure coin target generation."""

    coin_priority: float = 100000.0
    min_gap: float = 36.0
    projectile_width: float = 32.0
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
        direct_aim = _clear_coin_aim(
            frog_pivot=level.topology.frog_pivot,
            coin=coin,
            entities=world_state.entities,
            params=params,
        )
        if direct_aim is not None:
            targets.append(_direct_coin_target(direct_aim, coin, params))
            continue

        for blocker in world_state.clusters:
            if blocker.color != target_color or blocker.size < 2:
                continue
            blocker_entities = frozenset(blocker.entities)
            remaining_entities = tuple(
                entity
                for entity in world_state.entities
                if entity not in blocker_entities
            )
            coin_aim = _clear_coin_aim(
                frog_pivot=level.topology.frog_pivot,
                coin=coin,
                entities=remaining_entities,
                params=params,
            )
            if coin_aim is None:
                continue
            target = _breakthrough_coin_target(
                blocker=blocker,
                coin=coin,
                coin_aim=coin_aim,
                target_color=target_color,
                world_state=world_state,
                level=level,
                params=params,
            )
            if target is not None:
                targets.append(target)

    targets.sort(key=lambda target: target.score, reverse=True)
    return tuple(targets)


def _clear_coin_aim(
    frog_pivot: Point,
    coin: Point,
    entities: Iterable[BallEntity],
    params: CoinScoringParams,
) -> Point | None:
    blockers = tuple(entities)
    for aim_point in _coin_aim_points(
        frog_pivot,
        coin,
        collision_width=params.projectile_width,
    ):
        line_of_sight = check_line_of_sight(
            frog_pivot=frog_pivot,
            target=aim_point,
            entities=blockers,
            min_gap=params.min_gap,
            projectile_width=params.projectile_width,
        )
        if line_of_sight.is_clear:
            return aim_point
    return None


def _coin_aim_points(
    frog_pivot: Point,
    coin: Point,
    collision_width: float,
) -> tuple[Point, ...]:
    """Return center-first rays whose collision strip still covers the coin."""
    dx = coin.x - frog_pivot.x
    dy = coin.y - frog_pivot.y
    distance = math.hypot(dx, dy)
    half_width = max(0.0, collision_width) / 2.0
    if distance <= 1e-6 or half_width <= 0.0:
        return (coin,)

    perpendicular_x = -dy / distance
    perpendicular_y = dx / distance
    offsets: list[float] = [0.0]
    whole_pixels = int(math.floor(half_width))
    for offset in range(1, whole_pixels + 1):
        offsets.extend((float(offset), float(-offset)))
    if half_width > whole_pixels:
        offsets.extend((half_width, -half_width))

    points: list[Point] = []
    seen: set[tuple[int, int]] = set()
    for offset in offsets:
        point = Point(
            x=float(int(coin.x + perpendicular_x * offset)),
            y=float(int(coin.y + perpendicular_y * offset)),
        )
        key = (int(point.x), int(point.y))
        if key in seen:
            continue
        if _distance_from_ray(frog_pivot, point, coin) > half_width + 1e-6:
            continue
        seen.add(key)
        points.append(point)
    return tuple(points)


def _distance_from_ray(origin: Point, aim: Point, point: Point) -> float:
    ray_dx = aim.x - origin.x
    ray_dy = aim.y - origin.y
    ray_length = math.hypot(ray_dx, ray_dy)
    if ray_length <= 1e-6:
        return math.hypot(point.x - origin.x, point.y - origin.y)
    return abs(
        (point.x - origin.x) * ray_dy - (point.y - origin.y) * ray_dx
    ) / ray_length


def _direct_coin_target(
    aim_point: Point,
    coin: Point,
    params: CoinScoringParams,
) -> TargetCandidate:
    return TargetCandidate(
        x=aim_point.x,
        y=aim_point.y,
        score=params.coin_priority * 2.0,
        target_type=DIRECT_COIN_TARGET,
        reason="coin collision strip has clear line of sight",
        coin_x=coin.x,
        coin_y=coin.y,
    )


def _breakthrough_coin_target(
    blocker: Cluster,
    coin: Point,
    coin_aim: Point,
    target_color: str,
    world_state: WorldState,
    level: LevelRuntimeAssets,
    params: CoinScoringParams,
) -> TargetCandidate | None:
    if blocker.color != target_color or blocker.size < 2:
        return None

    track = next(
        (track for track in level.geometry.tracks if track.track_id == blocker.track_id),
        None,
    )
    if track is None or not track.points:
        return None

    reachable = reachable_entities(
        frog_pivot=level.topology.frog_pivot,
        targets=blocker.entities,
        entities=world_state.entities,
        projectile_width=params.projectile_width,
        cluster_start_idx=blocker.start_idx,
        cluster_end_idx=blocker.end_idx,
    )
    ball_aim = aim_at_ball_entities(reachable, track)
    if ball_aim is None:
        return None
    return TargetCandidate(
        x=ball_aim.point.x,
        y=ball_aim.point.y,
        score=params.coin_priority * 1.5,
        target_type=BREAKTHROUGH_COIN_TARGET,
        reason=(
            f"breakthrough coin blocker track={blocker.track_id} "
            f"color={blocker.color} size={blocker.size}"
        ),
        track_id=blocker.track_id,
        visibility_region=blocker.visibility_region,
        track_idx=ball_aim.track_idx,
        cluster_start_idx=blocker.start_idx,
        cluster_end_idx=blocker.end_idx,
        secondary_x=coin_aim.x,
        secondary_y=coin_aim.y,
        coin_x=coin.x,
        coin_y=coin.y,
        delay_ms=params.breakthrough_delay_ms,
    )
