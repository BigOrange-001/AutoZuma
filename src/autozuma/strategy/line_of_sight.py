"""Line-of-sight checks for candidate shots."""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass

from autozuma.core.models import BallEntity, Point

BALL_RADIUS = 15.0
PHYSICAL_CLEARANCE_LIMIT = 36.0
TARGET_CLUSTER_INDEX_PADDING = 20
SAME_TRACK_NEAR_TARGET_TOLERANCE = 60.0


@dataclass(frozen=True)
class LineOfSightResult:
    is_clear: bool
    min_distance: float


def check_line_of_sight(
    frog_pivot: Point,
    target: Point,
    entities: Iterable[BallEntity],
    min_gap: float,
    target_track_id: int | None = None,
    target_track_idx: int | None = None,
    cluster_start_idx: int | None = None,
    cluster_end_idx: int | None = None,
    ball_radius: float = BALL_RADIUS,
) -> LineOfSightResult:
    """Return whether the ray from launcher to target is free of blocking balls."""
    del target_track_idx

    filtered_entities = tuple(
        entity
        for entity in entities
        if _can_block_target(
            entity=entity,
            target=target,
            target_track_id=target_track_id,
            cluster_start_idx=cluster_start_idx,
            cluster_end_idx=cluster_end_idx,
            ball_radius=ball_radius,
        )
    )
    if not filtered_entities:
        return LineOfSightResult(is_clear=True, min_distance=float("inf"))

    ray_dx = target.x - frog_pivot.x
    ray_dy = target.y - frog_pivot.y
    target_distance = math.hypot(ray_dx, ray_dy)
    if target_distance < 1e-4:
        return LineOfSightResult(is_clear=True, min_distance=float("inf"))

    unit_x = ray_dx / target_distance
    unit_y = ray_dy / target_distance
    min_distance = float("inf")

    for entity in filtered_entities:
        to_entity_x = entity.x - frog_pivot.x
        to_entity_y = entity.y - frog_pivot.y
        projection = to_entity_x * unit_x + to_entity_y * unit_y
        if projection <= ball_radius * 1.5:
            continue
        if projection >= target_distance - ball_radius * 0.5:
            continue

        perpendicular_x = to_entity_x - projection * unit_x
        perpendicular_y = to_entity_y - projection * unit_y
        min_distance = min(min_distance, math.hypot(perpendicular_x, perpendicular_y))

    if math.isinf(min_distance):
        return LineOfSightResult(is_clear=True, min_distance=float("inf"))

    safe_clearance = max(PHYSICAL_CLEARANCE_LIMIT, min_gap)
    return LineOfSightResult(
        is_clear=min_distance >= safe_clearance,
        min_distance=min_distance,
    )


def _can_block_target(
    entity: BallEntity,
    target: Point,
    target_track_id: int | None,
    cluster_start_idx: int | None,
    cluster_end_idx: int | None,
    ball_radius: float,
) -> bool:
    distance_to_target = math.hypot(entity.x - target.x, entity.y - target.y)
    if distance_to_target < ball_radius * 1.5:
        return False

    if target_track_id is None or entity.track_id != target_track_id:
        return True

    if cluster_start_idx is not None and cluster_end_idx is not None:
        if (
            cluster_start_idx - TARGET_CLUSTER_INDEX_PADDING
            <= entity.track_idx
            <= cluster_end_idx + TARGET_CLUSTER_INDEX_PADDING
        ):
            return False

    return distance_to_target >= SAME_TRACK_NEAR_TARGET_TOLERANCE
