"""Select playable targets from scored strategy candidates."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from autozuma.core.models import Point, TargetCandidate, WorldState
from autozuma.strategy.line_of_sight import check_line_of_sight


@dataclass(frozen=True)
class TargetSelectionParams:
    min_gap: float = 0.0


def select_best_clear_target(
    world_state: WorldState,
    candidates: Iterable[TargetCandidate],
    frog_pivot: Point,
    params: TargetSelectionParams = TargetSelectionParams(),
) -> TargetCandidate | None:
    """Return the highest-scoring target with a clear launcher-to-target path."""
    for candidate in sorted(candidates, key=lambda target: target.score, reverse=True):
        line_of_sight = check_line_of_sight(
            frog_pivot=frog_pivot,
            target=Point(x=candidate.x, y=candidate.y),
            entities=world_state.entities,
            min_gap=params.min_gap,
            target_track_id=candidate.track_id,
            target_track_idx=candidate.track_idx,
            cluster_start_idx=candidate.cluster_start_idx,
            cluster_end_idx=candidate.cluster_end_idx,
        )
        if line_of_sight.is_clear:
            return candidate
    return None
