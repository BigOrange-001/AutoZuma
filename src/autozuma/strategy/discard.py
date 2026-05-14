"""Pure fallback discard target selection."""

from __future__ import annotations

import math
from dataclasses import dataclass

from autozuma.core.models import Cluster, LevelRuntimeAssets, Point, TargetCandidate, WorldState
from autozuma.strategy.line_of_sight import check_line_of_sight
from autozuma.vision.colors import UNKNOWN_COLOR

DISCARD_TARGET = "DISCARD"


@dataclass(frozen=True)
class DiscardParams:
    """Parameters for fallback discard target selection."""

    enabled: bool = True
    min_gap: float = 36.0
    edge_step: int = 20
    edge_margin: float = 5.0
    gap_max_track_idx_delta: int = 100
    fallback_up_distance: float = 100.0


def discard_target(
    world_state: WorldState,
    level: LevelRuntimeAssets,
    roi_size: tuple[int, int],
    params: DiscardParams = DiscardParams(),
) -> TargetCandidate | None:
    """Return a fallback discard target for a known current ball."""
    if not params.enabled or world_state.launcher.current_ball == UNKNOWN_COLOR:
        return None

    width, height = roi_size
    frog_pivot = level.topology.frog_pivot

    edge_target = _nearest_clear_edge_target(world_state, frog_pivot, width, height, params)
    if edge_target is not None:
        return edge_target

    gap_target = _reachable_gap_target(world_state, level, frog_pivot, params)
    if gap_target is not None:
        return gap_target

    cluster_target = _single_or_earliest_cluster_target(world_state, level)
    if cluster_target is not None:
        return cluster_target

    return TargetCandidate(
        x=frog_pivot.x,
        y=frog_pivot.y - params.fallback_up_distance,
        score=0.0,
        target_type=DISCARD_TARGET,
        reason="fallback upward discard",
    )


def _nearest_clear_edge_target(
    world_state: WorldState,
    frog_pivot: Point,
    width: int,
    height: int,
    params: DiscardParams,
) -> TargetCandidate | None:
    best_point: Point | None = None
    best_distance = float("inf")
    for point in _edge_points(width, height, params.edge_step, params.edge_margin):
        line_of_sight = check_line_of_sight(
            frog_pivot=frog_pivot,
            target=point,
            entities=world_state.entities,
            min_gap=params.min_gap,
        )
        if not line_of_sight.is_clear:
            continue

        distance = math.hypot(point.x - frog_pivot.x, point.y - frog_pivot.y)
        if distance < best_distance:
            best_point = point
            best_distance = distance

    if best_point is None:
        return None
    return TargetCandidate(
        x=best_point.x,
        y=best_point.y,
        score=0.0,
        target_type=DISCARD_TARGET,
        reason="fallback nearest clear edge",
    )


def _edge_points(width: int, height: int, step: int, margin: float) -> tuple[Point, ...]:
    points: list[Point] = []
    for x in range(0, width, step):
        points.append(Point(x=float(x), y=margin))
        points.append(Point(x=float(x), y=height - margin))
    for y in range(0, height, step):
        points.append(Point(x=margin, y=float(y)))
        points.append(Point(x=width - margin, y=float(y)))
    return tuple(points)


def _reachable_gap_target(
    world_state: WorldState,
    level: LevelRuntimeAssets,
    frog_pivot: Point,
    params: DiscardParams,
) -> TargetCandidate | None:
    reachable_gaps: list[TargetCandidate] = []
    clusters = world_state.clusters
    for idx in range(len(clusters) - 1):
        left = clusters[idx]
        right = clusters[idx + 1]
        if left.color == UNKNOWN_COLOR or right.color == UNKNOWN_COLOR:
            continue
        if left.track_id != right.track_id or left.color == right.color:
            continue
        left_entity = left.entities[-1]
        right_entity = right.entities[0]
        if right_entity.track_idx - left_entity.track_idx >= params.gap_max_track_idx_delta:
            continue

        gap_idx = (left_entity.track_idx + right_entity.track_idx) // 2
        gap_point = _track_point(level, left.track_id, gap_idx)
        if gap_point is None:
            continue

        line_of_sight = check_line_of_sight(
            frog_pivot=frog_pivot,
            target=gap_point,
            entities=world_state.entities,
            min_gap=params.min_gap,
            target_track_id=left.track_id,
            target_track_idx=gap_idx,
        )
        if not line_of_sight.is_clear:
            continue

        reachable_gaps.append(
            TargetCandidate(
                x=gap_point.x,
                y=gap_point.y,
                score=0.0,
                target_type=DISCARD_TARGET,
                reason="fallback reachable gap",
                track_id=left.track_id,
                track_idx=gap_idx,
            )
        )

    if not reachable_gaps:
        return None

    same_color_clusters = [
        cluster
        for cluster in clusters
        if cluster.color == world_state.launcher.current_ball and cluster.color != UNKNOWN_COLOR
    ]
    if same_color_clusters:
        nearest_to_same_color = _gap_nearest_same_color_cluster(reachable_gaps, same_color_clusters)
        if nearest_to_same_color is not None:
            return nearest_to_same_color

    return min(
        reachable_gaps,
        key=lambda target: math.hypot(target.x - frog_pivot.x, target.y - frog_pivot.y),
    )


def _gap_nearest_same_color_cluster(
    gaps: list[TargetCandidate],
    same_color_clusters: list[Cluster],
) -> TargetCandidate | None:
    best_gap: TargetCandidate | None = None
    min_idx_diff = float("inf")
    for gap in gaps:
        if gap.track_id is None or gap.track_idx is None:
            continue
        for cluster in same_color_clusters:
            if cluster.track_id != gap.track_id:
                continue
            diff = min(abs(gap.track_idx - cluster.start_idx), abs(gap.track_idx - cluster.end_idx))
            if diff < min_idx_diff:
                min_idx_diff = diff
                best_gap = gap
    return best_gap


def _single_or_earliest_cluster_target(
    world_state: WorldState,
    level: LevelRuntimeAssets,
) -> TargetCandidate | None:
    known_clusters = [cluster for cluster in world_state.clusters if cluster.color != UNKNOWN_COLOR]
    single_clusters = [cluster for cluster in known_clusters if cluster.size == 1]
    candidate_clusters = single_clusters or known_clusters
    if not candidate_clusters:
        return None

    cluster = min(candidate_clusters, key=lambda item: item.start_idx)
    point = _track_point(level, cluster.track_id, cluster.start_idx)
    if point is None:
        return None
    return TargetCandidate(
        x=point.x,
        y=point.y,
        score=0.0,
        target_type=DISCARD_TARGET,
        reason="fallback size-1 cluster" if cluster.size == 1 else "fallback earliest cluster",
        track_id=cluster.track_id,
        track_idx=cluster.start_idx,
        cluster_start_idx=cluster.start_idx,
        cluster_end_idx=cluster.end_idx,
    )


def _track_point(level: LevelRuntimeAssets, track_id: int, track_idx: int) -> Point | None:
    for track in level.geometry.tracks:
        if track.track_id != track_id or not track.points:
            continue
        clamped_idx = max(0, min(len(track.points) - 1, track_idx))
        return track.points[clamped_idx]
    return None
