"""Pure target prediction along level track geometry."""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass, replace

from autozuma.core.models import LevelRuntimeAssets, Point, TargetCandidate, TrackGeometry


@dataclass(frozen=True)
class TargetPredictionParams:
    """Parameters for geometry-only shot target prediction."""

    predict_multiplier: float = 0.05


def predict_targets(
    targets: Iterable[TargetCandidate],
    level: LevelRuntimeAssets,
    frog_pivot: Point,
    params: TargetPredictionParams = TargetPredictionParams(),
) -> tuple[TargetCandidate, ...]:
    """Return targets adjusted along their dense track by prototype prediction rules."""
    return tuple(
        predict_target(
            target=target,
            level=level,
            frog_pivot=frog_pivot,
            params=params,
        )
        for target in targets
    )


def predict_target(
    target: TargetCandidate,
    level: LevelRuntimeAssets,
    frog_pivot: Point,
    params: TargetPredictionParams = TargetPredictionParams(),
) -> TargetCandidate:
    """Project a target forward along its track according to launcher distance."""
    if target.secondary_x is not None or target.secondary_y is not None:
        return target
    if target.track_id is None or target.track_idx is None:
        return target

    track = _find_track(level, target.track_id)
    if track is None or not track.points:
        return target

    distance_to_frog = math.hypot(target.x - frog_pivot.x, target.y - frog_pivot.y)
    offset_idx = int(params.predict_multiplier * distance_to_frog)
    predicted_idx = _clamp_track_idx(target.track_idx + offset_idx, track)
    predicted_point = track.points[predicted_idx]

    return replace(
        target,
        x=predicted_point.x,
        y=predicted_point.y,
        track_idx=predicted_idx,
        reason=_append_prediction_reason(target.reason, offset_idx, predicted_idx),
    )


def _find_track(level: LevelRuntimeAssets, track_id: int) -> TrackGeometry | None:
    for track in level.geometry.tracks:
        if track.track_id == track_id:
            return track
    return None


def _clamp_track_idx(track_idx: int, track: TrackGeometry) -> int:
    return max(0, min(len(track.points) - 1, track_idx))


def _append_prediction_reason(reason: str, offset_idx: int, predicted_idx: int) -> str:
    prediction_reason = f"prediction offset_idx={offset_idx} predicted_idx={predicted_idx}"
    if not reason:
        return prediction_reason
    return f"{reason}; {prediction_reason}"
