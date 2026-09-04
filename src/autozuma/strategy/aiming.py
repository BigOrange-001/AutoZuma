"""Shared forward-biased aim selection for targets that are balls."""

from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass
from typing import Iterable

from autozuma.core.models import BallEntity, Point, TrackGeometry

BALL_AIM_FORWARD_DISTANCE = 16.0


@dataclass(frozen=True)
class BallAim:
    """A shootable point derived from an ordered, reachable set of balls."""

    point: Point
    context_entity: BallEntity
    track_idx: int


def aim_at_ball_entities(
    entities: Iterable[BallEntity],
    track: TrackGeometry,
    forward_distance: float = BALL_AIM_FORWARD_DISTANCE,
) -> BallAim | None:
    """Aim at the endpoint-biased middle of a reachable ball sequence.

    A single ball and any odd-sized sequence use the middle ball shifted forward
    along the track. An even-sized sequence uses the endpoint-side middle ball.
    """
    ordered = tuple(sorted(entities, key=lambda entity: entity.track_idx))
    if not ordered or not track.points:
        return None

    middle = ordered[len(ordered) // 2]
    if len(ordered) % 2 == 0 or forward_distance <= 0.0:
        return BallAim(
            point=Point(x=middle.x, y=middle.y),
            context_entity=middle,
            track_idx=middle.track_idx,
        )

    track_idx = forward_track_index(middle.track_idx, track, forward_distance)
    return BallAim(
        point=track.points[track_idx],
        context_entity=middle,
        track_idx=track_idx,
    )


def forward_track_index(
    track_idx: int,
    track: TrackGeometry,
    distance_pixels: float,
) -> int:
    """Return an index at least ``distance_pixels`` farther toward the track end."""
    clamped_idx = _clamp_track_idx(track_idx, track)
    if (
        distance_pixels <= 0.0
        or not track.cumulative_distances
        or len(track.cumulative_distances) != len(track.points)
    ):
        return clamped_idx

    target_distance = track.cumulative_distances[clamped_idx] + distance_pixels
    target_idx = _clamp_track_idx(
        bisect_left(track.cumulative_distances, target_distance),
        track,
    )
    return _clamp_to_visibility_region(clamped_idx, target_idx, track)


def _clamp_track_idx(track_idx: int, track: TrackGeometry) -> int:
    return max(0, min(len(track.points) - 1, track_idx))


def _clamp_to_visibility_region(
    source_idx: int,
    target_idx: int,
    track: TrackGeometry,
) -> int:
    if len(track.visibility_region_ids) != len(track.points):
        return target_idx
    source_region = track.visibility_region_ids[source_idx]
    if source_region < 0 or track.visibility_region_ids[target_idx] == source_region:
        return target_idx
    while target_idx > source_idx and track.visibility_region_ids[target_idx] != source_region:
        target_idx -= 1
    return target_idx
