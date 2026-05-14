"""Basic target scoring from perceived world state."""

from __future__ import annotations

import math
from dataclasses import dataclass

from autozuma.core.models import (
    Cluster,
    LevelRuntimeAssets,
    Point,
    TargetCandidate,
    TrackGeometry,
    WorldState,
)
from autozuma.vision.colors import UNKNOWN_COLOR

ELIM_TARGET = "ELIM"
PAIR_TARGET = "PAIR"
COMBO_TARGET = "COMBO"
ROLLBACK_ELIM_TARGET = "ROLLBACK_ELIM"


@dataclass(frozen=True)
class TargetScoringParams:
    combo_priority: float = 10000.0
    rollback_elim_priority: float = 3000.0
    elim_priority: float = 1000.0
    pair_priority: float = 100.0
    distance_weight: float = 3.5
    orthogonality_weight: float = 1.75
    distance_normalizer: float = 600.0
    bad_geometry_penalty: float = 5.0
    min_orthogonality: float = 0.42
    min_straightness: float = 0.86
    combo_depth_bonus: float = 0.6
    max_combo_depth_bonus: float = 2.0


def score_basic_targets(
    world_state: WorldState,
    level: LevelRuntimeAssets,
    params: TargetScoringParams = TargetScoringParams(),
) -> tuple[TargetCandidate, ...]:
    """Score basic same-color elimination and pair-insertion targets."""
    return score_basic_targets_for_color(
        world_state=world_state,
        level=level,
        target_color=world_state.launcher.current_ball,
        params=params,
    )


def score_basic_targets_for_color(
    world_state: WorldState,
    level: LevelRuntimeAssets,
    target_color: str,
    params: TargetScoringParams = TargetScoringParams(),
) -> tuple[TargetCandidate, ...]:
    """Score basic targets as if the launcher ball had the given color."""
    if target_color == UNKNOWN_COLOR:
        return ()

    candidates: list[TargetCandidate] = []
    for cluster_idx, cluster in enumerate(world_state.clusters):
        if cluster.color != target_color:
            continue
        if not cluster.entities:
            continue
        if _is_adjacent_to_same_color_cluster(world_state.clusters, cluster_idx, target_color):
            continue

        track = _find_track(level, cluster.track_id)
        if track is None:
            continue

        candidate = _score_cluster(
            clusters=world_state.clusters,
            cluster_idx=cluster_idx,
            track=track,
            target_color=target_color,
            frog_pivot=level.topology.frog_pivot,
            params=params,
        )
        candidates.append(candidate)

    candidates.sort(key=lambda target: target.score, reverse=True)
    return tuple(candidates)


def _find_track(level: LevelRuntimeAssets, track_id: int) -> TrackGeometry | None:
    for track in level.geometry.tracks:
        if track.track_id == track_id:
            return track
    return None


def _score_cluster(
    clusters: tuple[Cluster, ...],
    cluster_idx: int,
    track: TrackGeometry,
    target_color: str,
    frog_pivot: Point,
    params: TargetScoringParams,
) -> TargetCandidate:
    cluster = clusters[cluster_idx]
    center_x = sum(entity.x for entity in cluster.entities) / cluster.size
    center_y = sum(entity.y for entity in cluster.entities) / cluster.size
    center_entity = cluster.entities[len(cluster.entities) // 2]
    track_idx = _clamp_track_idx(center_entity.track_idx, track)

    target_type, base_score, combo_depth = _classify_target(
        clusters=clusters,
        cluster_idx=cluster_idx,
        target_color=target_color,
        params=params,
    )
    distance = math.hypot(center_x - frog_pivot.x, center_y - frog_pivot.y)
    orthogonality = _shot_track_orthogonality(
        target=Point(x=center_x, y=center_y),
        frog_pivot=frog_pivot,
        track=track,
        track_idx=track_idx,
    )
    straightness = _track_straightness(track, track_idx)
    normalized_distance = max(0.0, min(1.0, 1.0 - distance / params.distance_normalizer))
    depth_bonus = min(params.max_combo_depth_bonus, combo_depth * params.combo_depth_bonus)
    final_score = base_score * (
        1.0
        + params.distance_weight * normalized_distance
        + params.orthogonality_weight * orthogonality
        + depth_bonus
    )

    is_bad_geometry = (
        orthogonality < params.min_orthogonality or straightness < params.min_straightness
    )
    if is_bad_geometry:
        final_score /= params.bad_geometry_penalty

    return TargetCandidate(
        x=center_x,
        y=center_y,
        score=final_score,
        target_type=target_type,
        reason=(
            f"cluster track={cluster.track_id} color={cluster.color} size={cluster.size} "
            f"orthogonality={orthogonality:.3f} straightness={straightness:.3f} "
            f"combo_depth={combo_depth}"
        ),
        combo_depth=combo_depth,
        track_id=cluster.track_id,
        track_idx=center_entity.track_idx,
        cluster_start_idx=cluster.start_idx,
        cluster_end_idx=cluster.end_idx,
    )


def _classify_target(
    clusters: tuple[Cluster, ...],
    cluster_idx: int,
    target_color: str,
    params: TargetScoringParams,
) -> tuple[str, float, int]:
    cluster = clusters[cluster_idx]
    if cluster.size < 2:
        return PAIR_TARGET, params.pair_priority, 0

    combo_depth = _potential_combo_depth(clusters, cluster_idx) - 1
    max_other_depth = _max_nearby_other_combo_depth(clusters, cluster_idx)
    if max_other_depth > combo_depth + 1:
        return PAIR_TARGET, params.pair_priority, 0
    if combo_depth >= 1:
        return COMBO_TARGET, params.combo_priority, combo_depth
    if _is_rollback_elimination(clusters, cluster_idx, target_color):
        return ROLLBACK_ELIM_TARGET, params.rollback_elim_priority, 0
    return ELIM_TARGET, params.elim_priority, 0


def _potential_combo_depth(clusters: tuple[Cluster, ...], cluster_idx: int) -> int:
    depth = 1
    left_idx = cluster_idx - 1
    right_idx = cluster_idx + 1
    while True:
        left_idx = _previous_known_cluster_idx(clusters, left_idx)
        right_idx = _next_known_cluster_idx(clusters, right_idx)
        if left_idx is None or right_idx is None:
            break

        left = clusters[left_idx]
        right = clusters[right_idx]
        target = clusters[cluster_idx]
        if (
            left.track_id == right.track_id == target.track_id
            and left.color == right.color
            and left.size + right.size >= 3
        ):
            depth += 1
            left_idx -= 1
            right_idx += 1
            continue
        break
    return depth


def _max_nearby_other_combo_depth(clusters: tuple[Cluster, ...], cluster_idx: int) -> int:
    max_depth = 0
    for other_idx, other_cluster in enumerate(clusters):
        if other_idx == cluster_idx:
            continue
        if other_cluster.color == UNKNOWN_COLOR:
            continue
        if abs(other_idx - cluster_idx) <= 4 and other_cluster.size >= 2:
            max_depth = max(max_depth, _potential_combo_depth(clusters, other_idx))
    return max_depth


def _is_rollback_elimination(
    clusters: tuple[Cluster, ...],
    cluster_idx: int,
    target_color: str,
) -> bool:
    left_idx = _previous_known_cluster_idx(clusters, cluster_idx - 1)
    right_idx = _next_known_cluster_idx(clusters, cluster_idx + 1)
    if left_idx is None or right_idx is None:
        return False

    cluster = clusters[cluster_idx]
    left = clusters[left_idx]
    right = clusters[right_idx]
    return (
        left.track_id == right.track_id == cluster.track_id
        and left.color == right.color
        and left.color != target_color
    )


def _is_adjacent_to_same_color_cluster(
    clusters: tuple[Cluster, ...],
    cluster_idx: int,
    target_color: str,
) -> bool:
    left_idx = _previous_known_cluster_idx(clusters, cluster_idx - 1)
    if left_idx is not None:
        left = clusters[left_idx]
        if left.track_id == clusters[cluster_idx].track_id and left.color == target_color:
            return True

    right_idx = _next_known_cluster_idx(clusters, cluster_idx + 1)
    if right_idx is not None:
        right = clusters[right_idx]
        if right.track_id == clusters[cluster_idx].track_id and right.color == target_color:
            return True
    return False


def _previous_known_cluster_idx(clusters: tuple[Cluster, ...], start_idx: int) -> int | None:
    idx = start_idx
    while idx >= 0 and clusters[idx].color == UNKNOWN_COLOR:
        idx -= 1
    if idx < 0:
        return None
    return idx


def _next_known_cluster_idx(clusters: tuple[Cluster, ...], start_idx: int) -> int | None:
    idx = start_idx
    while idx < len(clusters) and clusters[idx].color == UNKNOWN_COLOR:
        idx += 1
    if idx >= len(clusters):
        return None
    return idx


def _shot_track_orthogonality(
    target: Point,
    frog_pivot: Point,
    track: TrackGeometry,
    track_idx: int,
) -> float:
    max_idx = len(track.points) - 1
    idx_m5 = max(0, track_idx - 5)
    idx_p5 = min(max_idx, track_idx + 5)
    if idx_p5 > idx_m5:
        track_dx = track.points[idx_p5].x - track.points[idx_m5].x
        track_dy = track.points[idx_p5].y - track.points[idx_m5].y
        track_length = math.hypot(track_dx, track_dy)
    else:
        track_dx, track_dy, track_length = 1.0, 0.0, 1.0

    shot_dx = target.x - frog_pivot.x
    shot_dy = target.y - frog_pivot.y
    shot_length = math.hypot(shot_dx, shot_dy)
    if track_length <= 0.0 or shot_length <= 0.0:
        return 1.0

    cos_theta = (track_dx * shot_dx + track_dy * shot_dy) / (track_length * shot_length)
    return 1.0 - abs(cos_theta)


def _track_straightness(track: TrackGeometry, track_idx: int) -> float:
    max_idx = len(track.points) - 1
    idx_m15 = max(0, track_idx - 15)
    idx_p15 = min(max_idx, track_idx + 15)
    if track_idx - idx_m15 <= 0 or idx_p15 - track_idx <= 0:
        return 1.0

    prev_point = track.points[idx_m15]
    center_point = track.points[track_idx]
    next_point = track.points[idx_p15]
    prev_dx = center_point.x - prev_point.x
    prev_dy = center_point.y - prev_point.y
    next_dx = next_point.x - center_point.x
    next_dy = next_point.y - center_point.y
    prev_length = math.hypot(prev_dx, prev_dy)
    next_length = math.hypot(next_dx, next_dy)
    if prev_length <= 0.0 or next_length <= 0.0:
        return 1.0

    return (prev_dx * next_dx + prev_dy * next_dy) / (prev_length * next_length)


def _clamp_track_idx(track_idx: int, track: TrackGeometry) -> int:
    return max(0, min(len(track.points) - 1, track_idx))
