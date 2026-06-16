"""Line-of-sight checks for candidate shots."""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass

from autozuma.core.models import BallEntity, Point

BALL_RADIUS = 16.0
PROJECTILE_WIDTH = 32.0
NEAR_OCCLUSION_RADIUS = 18.0
FAR_OCCLUSION_RADIUS = 22.0
FULL_SCREEN_DISTANCE = 900.0
LOCAL_TARGET_TRACK_IDX_PADDING = 85


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
    projectile_width: float = PROJECTILE_WIDTH,
) -> LineOfSightResult:
    """Return whether the ray from launcher to target is free of blocking balls."""
    filtered_entities = tuple(
        entity
        for entity in entities
        if _can_block_target(
            entity=entity,
            target=target,
            target_track_id=target_track_id,
            target_track_idx=target_track_idx,
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

    safe_clearance = max(
        min_gap,
        projectile_clearance_for_distance(
            target_distance,
            near_radius=NEAR_OCCLUSION_RADIUS,
            far_radius=FAR_OCCLUSION_RADIUS,
            full_distance=FULL_SCREEN_DISTANCE,
            projectile_width=projectile_width,
        ),
    )
    return LineOfSightResult(
        is_clear=min_distance >= safe_clearance,
        min_distance=min_distance,
    )


def reachable_entities(
    *,
    frog_pivot: Point,
    targets: Iterable[BallEntity],
    entities: Iterable[BallEntity],
    near_radius: float = NEAR_OCCLUSION_RADIUS,
    far_radius: float = FAR_OCCLUSION_RADIUS,
    full_distance: float = FULL_SCREEN_DISTANCE,
    projectile_width: float = PROJECTILE_WIDTH,
    cluster_start_idx: int | None = None,
    cluster_end_idx: int | None = None,
) -> tuple[BallEntity, ...]:
    """Return target balls whose launcher ray is not blocked by another track."""
    blockers = tuple(entities)
    return tuple(
        target
        for target in targets
        if is_entity_reachable(
            frog_pivot=frog_pivot,
            target=target,
            entities=blockers,
            near_radius=near_radius,
            far_radius=far_radius,
            full_distance=full_distance,
            projectile_width=projectile_width,
            cluster_start_idx=cluster_start_idx,
            cluster_end_idx=cluster_end_idx,
        )
    )


def is_entity_reachable(
    *,
    frog_pivot: Point,
    target: BallEntity,
    entities: Iterable[BallEntity],
    near_radius: float = NEAR_OCCLUSION_RADIUS,
    far_radius: float = FAR_OCCLUSION_RADIUS,
    full_distance: float = FULL_SCREEN_DISTANCE,
    projectile_width: float = PROJECTILE_WIDTH,
    cluster_start_idx: int | None = None,
    cluster_end_idx: int | None = None,
) -> bool:
    """Return whether a single ball center is reachable by the launcher."""
    target_point = Point(x=target.x, y=target.y)
    ray_dx = target_point.x - frog_pivot.x
    ray_dy = target_point.y - frog_pivot.y
    target_distance = math.hypot(ray_dx, ray_dy)
    if target_distance < 1e-4:
        return True

    line_of_sight = check_line_of_sight(
        frog_pivot=frog_pivot,
        target=target_point,
        entities=entities,
        min_gap=projectile_clearance_for_distance(
            target_distance,
            near_radius=near_radius,
            far_radius=far_radius,
            full_distance=full_distance,
            projectile_width=projectile_width,
        ),
        target_track_id=target.track_id,
        target_track_idx=target.track_idx,
        cluster_start_idx=cluster_start_idx,
        cluster_end_idx=cluster_end_idx,
        ball_radius=BALL_RADIUS,
        projectile_width=projectile_width,
    )
    return line_of_sight.is_clear


def projectile_clearance_for_distance(
    distance: float,
    *,
    near_radius: float = NEAR_OCCLUSION_RADIUS,
    far_radius: float = FAR_OCCLUSION_RADIUS,
    full_distance: float = FULL_SCREEN_DISTANCE,
    projectile_width: float = PROJECTILE_WIDTH,
) -> float:
    """Return centerline clearance for a finite-width projectile strip."""
    return max(0.0, projectile_width) / 2.0 + occlusion_radius_for_distance(
        distance,
        near_radius=near_radius,
        far_radius=far_radius,
        full_distance=full_distance,
    )


def occlusion_radius_for_distance(
    distance: float,
    *,
    near_radius: float = NEAR_OCCLUSION_RADIUS,
    far_radius: float = FAR_OCCLUSION_RADIUS,
    full_distance: float = FULL_SCREEN_DISTANCE,
) -> float:
    """Interpolate the projectile clearance radius from close to full-screen shots."""
    if full_distance <= 0.0:
        return far_radius
    ratio = max(0.0, min(1.0, distance / full_distance))
    return near_radius + (far_radius - near_radius) * ratio


def _can_block_target(
    entity: BallEntity,
    target: Point,
    target_track_id: int | None,
    target_track_idx: int | None,
    cluster_start_idx: int | None,
    cluster_end_idx: int | None,
    ball_radius: float,
) -> bool:
    distance_to_target = math.hypot(entity.x - target.x, entity.y - target.y)
    if distance_to_target < ball_radius * 1.5:
        return False

    if _is_local_target_neighbor(
        entity=entity,
        target_track_id=target_track_id,
        target_track_idx=target_track_idx,
        cluster_start_idx=cluster_start_idx,
        cluster_end_idx=cluster_end_idx,
    ):
        return False

    return True


def _is_local_target_neighbor(
    *,
    entity: BallEntity,
    target_track_id: int | None,
    target_track_idx: int | None,
    cluster_start_idx: int | None,
    cluster_end_idx: int | None,
) -> bool:
    if target_track_id is None or entity.track_id != target_track_id:
        return False

    if cluster_start_idx is not None and cluster_end_idx is not None:
        return (
            cluster_start_idx - LOCAL_TARGET_TRACK_IDX_PADDING
            <= entity.track_idx
            <= cluster_end_idx + LOCAL_TARGET_TRACK_IDX_PADDING
        )

    if target_track_idx is None:
        return False
    return abs(entity.track_idx - target_track_idx) <= LOCAL_TARGET_TRACK_IDX_PADDING
