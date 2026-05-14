from pathlib import Path

from autozuma.core.models import (
    BallEntity,
    LevelGeometry,
    LevelRuntimeAssets,
    LevelTopology,
    LauncherState,
    Point,
    TrackGeometry,
    WorldState,
)
from autozuma.runtime.modes import (
    RuntimeMode,
    RuntimeModeParams,
    RuntimeModeState,
    initial_runtime_mode_state,
    update_runtime_mode_state,
)


def test_initial_runtime_mode_state_matches_level_reset_behavior():
    state = initial_runtime_mode_state(current_time=10.0)

    assert state == RuntimeModeState(
        is_rescue_mode=False,
        is_endgame_mode=False,
        spawn_start_time=0.0,
        last_spawn_time=10.0,
    )
    assert state.mode == RuntimeMode.NORMAL


def test_update_runtime_mode_state_detects_rescue_near_track_end():
    update = update_runtime_mode_state(
        previous=initial_runtime_mode_state(current_time=10.0),
        world_state=_world_state((_entity(track_idx=96),)),
        level=_level(),
        current_time=10.5,
        params=RuntimeModeParams(rescue_distance_threshold=5.0),
    )

    assert update.state.is_rescue_mode
    assert update.state.mode == RuntimeMode.RESCUE


def test_update_runtime_mode_state_uses_strict_rescue_threshold():
    update = update_runtime_mode_state(
        previous=initial_runtime_mode_state(current_time=10.0),
        world_state=_world_state((_entity(track_idx=95),)),
        level=_level(),
        current_time=10.5,
        params=RuntimeModeParams(rescue_distance_threshold=5.0),
    )

    assert not update.state.is_rescue_mode


def test_update_runtime_mode_state_tracks_spawn_presence_and_clears_endgame_after_window():
    previous = RuntimeModeState(
        is_rescue_mode=False,
        is_endgame_mode=True,
        spawn_start_time=10.0,
        last_spawn_time=11.0,
    )

    update = update_runtime_mode_state(
        previous=previous,
        world_state=_world_state((_entity(track_idx=10),)),
        level=_level(),
        current_time=12.1,
        params=RuntimeModeParams(
            endgame_spawn_distance_threshold=15.0,
            spawn_sustain_time=2.0,
        ),
    )

    assert update.spawn_detected
    assert update.state.spawn_start_time == 10.0
    assert update.state.last_spawn_time == 12.1
    assert not update.state.is_endgame_mode


def test_update_runtime_mode_state_starts_spawn_window_on_first_spawn_detection():
    update = update_runtime_mode_state(
        previous=RuntimeModeState(last_spawn_time=10.0),
        world_state=_world_state((_entity(track_idx=10),)),
        level=_level(),
        current_time=12.0,
        params=RuntimeModeParams(endgame_spawn_distance_threshold=15.0),
    )

    assert update.spawn_detected
    assert update.state.spawn_start_time == 12.0
    assert update.state.last_spawn_time == 12.0


def test_update_runtime_mode_state_enters_endgame_after_spawn_absence_timeout():
    update = update_runtime_mode_state(
        previous=RuntimeModeState(last_spawn_time=10.0, spawn_start_time=9.0),
        world_state=_world_state(()),
        level=_level(),
        current_time=13.1,
        params=RuntimeModeParams(spawn_absence_time=3.0),
    )

    assert not update.spawn_detected
    assert update.state.spawn_start_time == 0.0
    assert update.state.is_endgame_mode
    assert update.state.mode == RuntimeMode.ENDGAME


def test_update_runtime_mode_state_uses_strict_spawn_absence_timeout():
    update = update_runtime_mode_state(
        previous=RuntimeModeState(last_spawn_time=10.0),
        world_state=_world_state(()),
        level=_level(),
        current_time=13.0,
        params=RuntimeModeParams(spawn_absence_time=3.0),
    )

    assert not update.state.is_endgame_mode


def test_runtime_mode_prefers_rescue_over_endgame():
    state = RuntimeModeState(is_rescue_mode=True, is_endgame_mode=True)

    assert state.mode == RuntimeMode.RESCUE


def test_update_runtime_mode_state_ignores_entities_without_matching_track():
    update = update_runtime_mode_state(
        previous=initial_runtime_mode_state(current_time=10.0),
        world_state=_world_state((_entity(track_id=99, track_idx=100),)),
        level=_level(),
        current_time=20.0,
        params=RuntimeModeParams(spawn_absence_time=3.0),
    )

    assert not update.state.is_rescue_mode
    assert update.state.is_endgame_mode


def _level() -> LevelRuntimeAssets:
    topology = LevelTopology(
        level_id="test",
        frog_pivot=Point(x=0, y=0),
        tracks=(),
        treasure_points=(),
        source_path=Path("test.json"),
    )
    track = TrackGeometry(
        track_id=1,
        points=tuple(Point(x=float(idx), y=0.0) for idx in range(101)),
        cumulative_distances=tuple(float(idx) for idx in range(101)),
    )
    return LevelRuntimeAssets(
        level_id="test",
        topology=topology,
        geometry=LevelGeometry(level_id="test", tracks=(track,)),
        background=None,
    )


def _world_state(entities: tuple[BallEntity, ...]) -> WorldState:
    return WorldState(
        level_id="test",
        launcher=LauncherState(current_ball="red", next_ball="blue", next_position=None),
        entities=entities,
        clusters=(),
    )


def _entity(track_idx: int, track_id: int = 1) -> BallEntity:
    return BallEntity(
        x=float(track_idx),
        y=0.0,
        track_id=track_id,
        track_idx=track_idx,
        color="red",
    )
