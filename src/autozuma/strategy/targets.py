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


@dataclass(frozen=True)
class TargetScoringParams:
    elim_priority: float = 1000.0
    pair_priority: float = 100.0
    distance_weight: float = 3.5
    orthogonality_weight: float = 1.75
    distance_normalizer: float = 600.0
    bad_geometry_penalty: float = 5.0
    min_orthogonality: float = 0.42
    min_straightness: float = 0.86


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
    for cluster in world_state.clusters:
        if cluster.color != target_color:
            continue
        if not cluster.entities:
            continue

        track = _find_track(level, cluster.track_id)
        if track is None:
            continue

        candidate = _score_cluster(cluster, track, level.topology.frog_pivot, params)
        candidates.append(candidate)

    candidates.sort(key=lambda target: target.score, reverse=True)
    return tuple(candidates)


def _find_track(level: LevelRuntimeAssets, track_id: int) -> TrackGeometry | None:
    for track in level.geometry.tracks:
        if track.track_id == track_id:
            return track
    return None


def _score_cluster(
    cluster: Cluster,
    track: TrackGeometry,
    frog_pivot: Point,
    params: TargetScoringParams,
) -> TargetCandidate:
    center_x = sum(entity.x for entity in cluster.entities) / cluster.size
    center_y = sum(entity.y for entity in cluster.entities) / cluster.size
    center_entity = cluster.entities[len(cluster.entities) // 2]
    track_idx = _clamp_track_idx(center_entity.track_idx, track)

    target_type = ELIM_TARGET if cluster.size >= 2 else PAIR_TARGET
    base_score = params.elim_priority if target_type == ELIM_TARGET else params.pair_priority
    distance = math.hypot(center_x - frog_pivot.x, center_y - frog_pivot.y)
    orthogonality = _shot_track_orthogonality(
        target=Point(x=center_x, y=center_y),
        frog_pivot=frog_pivot,
        track=track,
        track_idx=track_idx,
    )
    straightness = _track_straightness(track, track_idx)
    normalized_distance = max(0.0, min(1.0, 1.0 - distance / params.distance_normalizer))
    final_score = base_score * (
        1.0
        + params.distance_weight * normalized_distance
        + params.orthogonality_weight * orthogonality
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
            f"orthogonality={orthogonality:.3f} straightness={straightness:.3f}"
        ),
        track_id=cluster.track_id,
        track_idx=center_entity.track_idx,
        cluster_start_idx=cluster.start_idx,
        cluster_end_idx=cluster.end_idx,
    )


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
