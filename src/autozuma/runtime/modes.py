"""Pure rescue/endgame runtime mode detection."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from autozuma.core.models import BallEntity, LevelRuntimeAssets, TrackGeometry, WorldState


class RuntimeMode(Enum):
    NORMAL = "normal"
    RESCUE = "rescue"
    ENDGAME = "endgame"


@dataclass(frozen=True)
class RuntimeModeState:
    """State needed to preserve prototype rescue/endgame timing behavior."""

    is_rescue_mode: bool = False
    is_endgame_mode: bool = False
    spawn_start_time: float = 0.0
    last_spawn_time: float = 0.0

    @property
    def mode(self) -> RuntimeMode:
        if self.is_rescue_mode:
            return RuntimeMode.RESCUE
        if self.is_endgame_mode:
            return RuntimeMode.ENDGAME
        return RuntimeMode.NORMAL


@dataclass(frozen=True)
class RuntimeModeParams:
    """Thresholds and timing windows for pure runtime mode detection."""

    rescue_distance_threshold: float = 400.0
    endgame_spawn_distance_threshold: float = 150.0
    spawn_sustain_time: float = 2.0
    spawn_absence_time: float = 3.0


@dataclass(frozen=True)
class RuntimeModeUpdate:
    state: RuntimeModeState
    spawn_detected: bool


def initial_runtime_mode_state(current_time: float) -> RuntimeModeState:
    """Return prototype-equivalent initial mode state for a newly detected level."""
    return RuntimeModeState(
        is_rescue_mode=False,
        is_endgame_mode=False,
        spawn_start_time=0.0,
        last_spawn_time=current_time,
    )


def update_runtime_mode_state(
    *,
    previous: RuntimeModeState,
    world_state: WorldState,
    level: LevelRuntimeAssets,
    current_time: float,
    params: RuntimeModeParams = RuntimeModeParams(),
) -> RuntimeModeUpdate:
    """Advance rescue/endgame state from the current perceived world state."""
    rescue_detected = False
    spawn_detected = False

    track_by_id = {track.track_id: track for track in level.geometry.tracks}
    for entity in world_state.entities:
        track = track_by_id.get(entity.track_id)
        if track is None or not track.cumulative_distances:
            continue

        distance = _distance_context(entity, track)
        if distance is None:
            continue

        distance_to_end = distance.total_length - distance.along_path
        if distance_to_end < params.rescue_distance_threshold:
            rescue_detected = True
        if distance.along_path < params.endgame_spawn_distance_threshold:
            spawn_detected = True

    spawn_start_time = previous.spawn_start_time
    last_spawn_time = previous.last_spawn_time
    is_endgame_mode = previous.is_endgame_mode

    if spawn_detected:
        if spawn_start_time == 0.0:
            spawn_start_time = current_time
        last_spawn_time = current_time
        if current_time - spawn_start_time > params.spawn_sustain_time:
            is_endgame_mode = False
    else:
        spawn_start_time = 0.0
        if current_time - last_spawn_time > params.spawn_absence_time:
            is_endgame_mode = True

    return RuntimeModeUpdate(
        state=RuntimeModeState(
            is_rescue_mode=rescue_detected,
            is_endgame_mode=is_endgame_mode,
            spawn_start_time=spawn_start_time,
            last_spawn_time=last_spawn_time,
        ),
        spawn_detected=spawn_detected,
    )


@dataclass(frozen=True)
class _DistanceContext:
    along_path: float
    total_length: float


def _distance_context(entity: BallEntity, track: TrackGeometry) -> _DistanceContext | None:
    max_idx = len(track.cumulative_distances) - 1
    if max_idx < 0:
        return None

    track_idx = max(0, min(max_idx, entity.track_idx))
    return _DistanceContext(
        along_path=track.cumulative_distances[track_idx],
        total_length=track.cumulative_distances[-1],
    )
