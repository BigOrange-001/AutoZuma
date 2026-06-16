from pathlib import Path
from types import MappingProxyType

import numpy as np

from autozuma.core.models import (
    BallEntity,
    Cluster,
    CommandType,
    GameRoiResult,
    ImageAsset,
    LauncherState,
    LauncherTemplateSet,
    LevelGeometry,
    LevelRuntimeAssets,
    LevelTopology,
    Point,
    TrackGeometry,
    WorldState,
)
from autozuma.runtime.modes import RuntimeMode, RuntimeModeState
from autozuma.runtime.static_runtime import (
    StaticRuntimeFrameParams,
    StaticRuntimeState,
    initial_static_runtime_state,
    run_static_runtime_frame,
)
from autozuma.strategy.action_updates import CommandOutcomeState
from autozuma.vision.coins import CoinTrack, CoinTrackerState


def test_initial_static_runtime_state_resets_mode_and_command_state():
    state = initial_static_runtime_state(current_time=10.0)

    assert state.mode_state == RuntimeModeState(last_spawn_time=10.0)
    assert state.command_outcome == CommandOutcomeState()


def test_run_static_runtime_frame_threads_coin_mode_and_decision_state(monkeypatch):
    raw_frame = np.zeros((60, 60, 3), dtype=np.uint8)
    roi_frame = np.zeros((40, 40, 3), dtype=np.uint8)
    roi_frame[10:30, 10:30] = 255
    level = _level(background_gray=np.zeros((40, 40), dtype=np.uint8))
    roi_result = GameRoiResult(frame=roi_frame, offset=Point(x=5.0, y=7.0), confidence=1.0)
    world_state = _world_state(track_idx=96)
    calls = {}

    def fake_extract_game_roi(frame_bgr, runtime_level):
        calls["roi"] = (frame_bgr, runtime_level)
        return roi_result

    def fake_detect_static_world_state_from_roi(
        frame_roi_bgr,
        level,
        launcher_templates,
        p_start_exclude,
        p_end_exclude,
    ):
        calls["world"] = (
            frame_roi_bgr,
            level,
            launcher_templates,
            p_start_exclude,
            p_end_exclude,
        )
        return world_state

    monkeypatch.setattr(
        "autozuma.runtime.static_runtime.extract_game_roi",
        fake_extract_game_roi,
    )
    monkeypatch.setattr(
        "autozuma.runtime.static_runtime.detect_static_world_state_from_roi",
        fake_detect_static_world_state_from_roi,
    )

    state = StaticRuntimeState(
        mode_state=RuntimeModeState(last_spawn_time=9.0),
        command_outcome=CommandOutcomeState(
            coin_tracker=CoinTrackerState(
                tracks=MappingProxyType({0: CoinTrack(first_seen=9.0, last_seen=9.0)})
            )
        ),
    )

    result = run_static_runtime_frame(
        frame_bgr=raw_frame,
        level=level,
        launcher_templates=LauncherTemplateSet(search_radius=5, step_degrees=5, templates={}),
        state=state,
        current_time=10.0,
        params=StaticRuntimeFrameParams(raw_values=_params()),
    )

    assert calls["roi"] == (raw_frame, level)
    assert calls["world"][0] is roi_frame
    assert calls["world"][3:] == (128.0, 101.0)
    assert result.coin_update.active_coins == (Point(x=20.0, y=20.0),)
    assert result.mode_update.state.is_rescue_mode
    assert result.state.mode_state.mode == RuntimeMode.RESCUE

    assert result.strategy_config.frame_decision.active_coins == (Point(x=20.0, y=20.0),)
    assert result.strategy_config.frame_decision.target_selection.min_gap == 0.0
    assert result.decision.decision.roi_result == roi_result
    assert result.decision.decision.world_state == world_state
    assert result.decision.decision.screen_command.command_type == CommandType.SHOOT
    assert result.state.command_outcome.last_fire_time == 10.0
    assert result.state.command_outcome.coin_tracker.tracks[0] == CoinTrack(
        first_seen=9.0,
        last_seen=10.0,
    )


def test_run_static_runtime_frame_prunes_coin_state_without_static_background(monkeypatch):
    raw_frame = np.zeros((60, 60, 3), dtype=np.uint8)
    roi_frame = np.zeros((40, 40, 3), dtype=np.uint8)
    level = _level(background_gray=None)
    roi_result = GameRoiResult(frame=roi_frame, offset=Point(x=0.0, y=0.0), confidence=1.0)

    monkeypatch.setattr(
        "autozuma.runtime.static_runtime.extract_game_roi",
        lambda frame_bgr, level: roi_result,
    )
    monkeypatch.setattr(
        "autozuma.runtime.static_runtime.detect_static_world_state_from_roi",
        lambda **kwargs: _world_state(track_idx=50),
    )

    state = StaticRuntimeState(
        mode_state=RuntimeModeState(last_spawn_time=9.0),
        command_outcome=CommandOutcomeState(
            coin_tracker=CoinTrackerState(
                tracks=MappingProxyType({0: CoinTrack(first_seen=8.0, last_seen=8.0)})
            )
        ),
    )

    result = run_static_runtime_frame(
        frame_bgr=raw_frame,
        level=level,
        launcher_templates=LauncherTemplateSet(search_radius=5, step_degrees=5, templates={}),
        state=state,
        current_time=10.0,
        params=StaticRuntimeFrameParams(raw_values=_params()),
    )

    assert result.coin_update.active_coins == ()
    assert result.coin_update.state.tracks == {}


def _level(background_gray: np.ndarray | None) -> LevelRuntimeAssets:
    topology = LevelTopology(
        level_id="test",
        frog_pivot=Point(x=0.0, y=0.0),
        tracks=(),
        treasure_points=(Point(x=20.0, y=20.0),),
        source_path=Path("test.json"),
    )
    track = TrackGeometry(
        track_id=1,
        points=tuple(Point(x=float(idx), y=50.0) for idx in range(101)),
        cumulative_distances=tuple(float(idx) for idx in range(101)),
    )
    background = None
    if background_gray is not None:
        background = ImageAsset(
            path=Path("background.png"),
            bgr=np.zeros((*background_gray.shape, 3), dtype=np.uint8),
            gray=background_gray,
        )
    return LevelRuntimeAssets(
        level_id="test",
        topology=topology,
        geometry=LevelGeometry(level_id="test", tracks=(track,)),
        background=background,
    )


def _world_state(track_idx: int) -> WorldState:
    entities = (
        BallEntity(x=float(track_idx), y=50.0, track_id=1, track_idx=track_idx, color="red"),
        BallEntity(
            x=float(track_idx + 1),
            y=50.0,
            track_id=1,
            track_idx=track_idx + 1,
            color="red",
        ),
    )
    return WorldState(
        level_id="test",
        launcher=LauncherState(current_ball="red", next_ball="blue", next_position=None),
        entities=entities,
        clusters=(
            Cluster(
                track_id=1,
                color="red",
                entities=entities,
                start_idx=track_idx,
                end_idx=track_idx + 1,
            ),
        ),
    )


def _params() -> dict[str, float]:
    return {
        "n_fire_cooldown": 0.44,
        "r_fire_cooldown": 0.59,
        "e_fire_cooldown": 0.6,
        "n_m_gap": 23.0,
        "r_m_gap": 22.0,
        "e_m_gap": 40.0,
        "n_combo_hang_base": 0.2,
        "r_combo_hang_base": 0.2,
        "e_combo_hang_base": 0.2,
        "n_combo_hang_mult": 0.0,
        "r_combo_hang_mult": 0.0,
        "e_combo_hang_mult": 0.0,
        "n_soft_lock_radius": 16.0,
        "r_soft_lock_radius": 17.0,
        "e_soft_lock_radius": 18.0,
        "n_prio_coin": 1.0,
        "r_prio_coin": 2.0,
        "e_prio_coin": 4.0,
        "n_prio_combo": 2.0,
        "r_prio_combo": 1.0,
        "e_prio_combo": 1.0,
        "n_prio_rollback_elim": 3.0,
        "r_prio_rollback_elim": 2.0,
        "e_prio_rollback_elim": 2.0,
        "n_prio_elim": 4.0,
        "r_prio_elim": 3.0,
        "e_prio_elim": 2.0,
        "n_prio_pair": 5.0,
        "r_prio_pair": 4.0,
        "e_prio_pair": 2.0,
        "coin_break_delay": 0.25,
        "rescue_th": 10.0,
        "endgame_spawn_th": 15.0,
        "track_start_exclude": 128.0,
        "track_end_exclude": 101.0,
    }
