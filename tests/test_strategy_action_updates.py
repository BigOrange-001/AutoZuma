from pathlib import Path
from types import MappingProxyType

import pytest

from autozuma.core.models import (
    BallEntity,
    Cluster,
    Command,
    CommandType,
    LevelGeometry,
    LevelRuntimeAssets,
    LevelTopology,
    LauncherState,
    Point,
    TargetCandidate,
    TrackGeometry,
    WorldState,
)
from autozuma.strategy.action_updates import (
    CommandOutcomeParams,
    CommandOutcomeState,
    apply_command_outcome,
)
from autozuma.strategy.actions import (
    ActionTrackerState,
    ClusterLock,
    Deadzone,
    VirtualBall,
)
from autozuma.strategy.coins import BREAKTHROUGH_COIN_TARGET, DIRECT_COIN_TARGET
from autozuma.strategy.targets import COMBO_TARGET, ELIM_TARGET, PAIR_TARGET, ROLLBACK_ELIM_TARGET
from autozuma.vision.coins import CoinLock, CoinTrackerState
from autozuma.vision.colors import UNKNOWN_COLOR


def test_apply_command_outcome_adds_combo_locks_and_cooldown():
    world_state = _world_state(
        clusters=(
            _cluster("red", track_id=1, start_idx=70, end_idx=75),
            _cluster("blue", track_id=1, start_idx=100, end_idx=120),
            _cluster("red", track_id=1, start_idx=150, end_idx=160),
        )
    )
    target = TargetCandidate(
        x=80.0,
        y=60.0,
        score=100.0,
        target_type=COMBO_TARGET,
        combo_depth=2,
        track_id=1,
        track_idx=110,
        cluster_start_idx=100,
        cluster_end_idx=120,
    )

    updated = apply_command_outcome(
        state=CommandOutcomeState(),
        command=Command(command_type=CommandType.SHOOT, primary_target=Point(x=80, y=60)),
        selected_target=target,
        world_state=world_state,
        level=_level(),
        current_time=10.0,
        params=CommandOutcomeParams(),
    )

    assert updated.action_tracker.deadzones == (
        Deadzone(point=Point(x=80.0, y=60.0), expires_at=11.025),
    )
    assert updated.action_tracker.cluster_locks == (
        ClusterLock(track_id=1, start_idx=70, end_idx=150, expires_at=11.025),
        ClusterLock(track_id=1, start_idx=70, end_idx=240, expires_at=11.025),
    )
    assert updated.next_fire_ready_time == 11.025
    assert updated.last_fire_time == 10.0


def test_apply_command_outcome_does_not_lock_combo_chain_across_unknown_cluster():
    world_state = _world_state(
        clusters=(
            _cluster("red", track_id=1, start_idx=50, end_idx=60),
            _cluster(UNKNOWN_COLOR, track_id=1, start_idx=70, end_idx=75),
            _cluster("blue", track_id=1, start_idx=100, end_idx=120),
            _cluster("red", track_id=1, start_idx=150, end_idx=160),
        )
    )
    target = TargetCandidate(
        x=80.0,
        y=60.0,
        score=100.0,
        target_type=COMBO_TARGET,
        combo_depth=2,
        track_id=1,
        track_idx=110,
        cluster_start_idx=100,
        cluster_end_idx=120,
    )

    updated = apply_command_outcome(
        state=CommandOutcomeState(),
        command=Command(command_type=CommandType.SHOOT, primary_target=Point(x=80, y=60)),
        selected_target=target,
        world_state=world_state,
        level=_level(),
        current_time=10.0,
    )

    assert updated.action_tracker.cluster_locks == (
        ClusterLock(track_id=1, start_idx=70, end_idx=150, expires_at=11.025),
    )


def test_apply_command_outcome_combo_locks_only_forward_predicted_chain():
    world_state = _world_state(
        clusters=(
            _cluster("red", track_id=1, start_idx=10, end_idx=20),
            _cluster("blue", track_id=1, start_idx=40, end_idx=50),
            _cluster("green", track_id=1, start_idx=70, end_idx=80),
            _cluster("blue", track_id=1, start_idx=100, end_idx=110),
            _cluster("red", track_id=1, start_idx=130, end_idx=140),
        )
    )
    target = TargetCandidate(
        x=0.0,
        y=80.0,
        score=100.0,
        target_type=COMBO_TARGET,
        combo_depth=2,
        track_id=1,
        track_idx=75,
        cluster_start_idx=70,
        cluster_end_idx=80,
    )

    updated = apply_command_outcome(
        state=CommandOutcomeState(),
        command=Command(command_type=CommandType.SHOOT, primary_target=Point(x=0, y=80)),
        selected_target=target,
        world_state=world_state,
        level=_level(),
        current_time=10.0,
    )

    locked_ranges = {
        (lock.start_idx, lock.end_idx)
        for lock in updated.action_tracker.cluster_locks
    }
    assert locked_ranges == {
        (40, 110),
        (20, 190),
        (50, 220),
    }


def test_apply_command_outcome_combo_adds_short_tail_lock_when_track_end_is_known():
    world_state = _world_state(
        clusters=(
            _cluster("blue", track_id=1, start_idx=20, end_idx=30),
            _cluster("red", track_id=1, start_idx=60, end_idx=70),
            _cluster("blue", track_id=1, start_idx=100, end_idx=110),
        )
    )
    target = TargetCandidate(
        x=0.0,
        y=80.0,
        score=100.0,
        target_type=COMBO_TARGET,
        combo_depth=1,
        track_id=1,
        track_idx=65,
        cluster_start_idx=60,
        cluster_end_idx=70,
    )

    updated = apply_command_outcome(
        state=CommandOutcomeState(),
        command=Command(command_type=CommandType.SHOOT, primary_target=Point(x=0, y=80)),
        selected_target=target,
        world_state=world_state,
        level=_level_with_track_end(201),
        current_time=10.0,
    )

    assert ClusterLock(track_id=1, start_idx=65, end_idx=200, expires_at=10.8) in (
        updated.action_tracker.cluster_locks
    )


def test_apply_command_outcome_combo_tail_lock_stops_at_occluded_region():
    world_state = _world_state(
        clusters=(
            _cluster("blue", track_id=1, start_idx=20, end_idx=30),
            _cluster("red", track_id=1, start_idx=60, end_idx=70),
            _cluster("blue", track_id=1, start_idx=100, end_idx=110),
        )
    )
    target = TargetCandidate(
        x=0.0,
        y=80.0,
        score=100.0,
        target_type=COMBO_TARGET,
        combo_depth=1,
        track_id=1,
        visibility_region=0,
        track_idx=65,
        cluster_start_idx=60,
        cluster_end_idx=70,
    )
    level = _level_with_track_end(201)
    track = level.geometry.tracks[0]
    visibility = tuple(0 if index <= 80 else -1 if index <= 119 else 1 for index in range(201))
    level = LevelRuntimeAssets(
        level_id=level.level_id,
        topology=level.topology,
        geometry=LevelGeometry(
            level_id=level.geometry.level_id,
            tracks=(
                TrackGeometry(
                    track_id=track.track_id,
                    points=track.points,
                    cumulative_distances=track.cumulative_distances,
                    visibility_region_ids=visibility,
                ),
            ),
        ),
        background=None,
    )

    updated = apply_command_outcome(
        state=CommandOutcomeState(),
        command=Command(command_type=CommandType.SHOOT, primary_target=Point(x=0, y=80)),
        selected_target=target,
        world_state=world_state,
        level=level,
        current_time=10.0,
    )

    assert ClusterLock(track_id=1, start_idx=65, end_idx=80, expires_at=10.8) in (
        updated.action_tracker.cluster_locks
    )
    assert ClusterLock(track_id=1, start_idx=30, end_idx=80, expires_at=10.8) in (
        updated.action_tracker.cluster_locks
    )
    assert all(lock.end_idx <= 80 for lock in updated.action_tracker.cluster_locks)


def test_apply_command_outcome_adds_pair_virtual_ball_with_swapped_color():
    world_state = _world_state(current_ball="red", next_ball="green")
    target = TargetCandidate(
        x=0.0,
        y=80.0,
        score=10.0,
        target_type=PAIR_TARGET,
        track_id=2,
        track_idx=55,
    )

    updated = apply_command_outcome(
        state=CommandOutcomeState(last_swap_time=4.0),
        command=Command(command_type=CommandType.SWAP_SHOOT, primary_target=Point(x=0, y=80)),
        selected_target=target,
        world_state=world_state,
        level=_level(),
        current_time=10.0,
        params=CommandOutcomeParams(),
    )

    assert updated.action_tracker.deadzones == (
        Deadzone(point=Point(x=0.0, y=80.0), expires_at=10.1),
    )
    assert updated.action_tracker.virtual_balls == (
        VirtualBall(track_id=2, track_idx=55, color="green", expires_at=10.1),
    )
    assert updated.last_swap_time == 10.0
    assert updated.next_fire_ready_time == pytest.approx(10.35)


def test_apply_command_outcome_locks_direct_coin_and_adds_travel_deadzone():
    target = TargetCandidate(
        x=0.0,
        y=80.0,
        score=100.0,
        target_type=DIRECT_COIN_TARGET,
        coin_x=10.0,
        coin_y=80.0,
    )

    updated = apply_command_outcome(
        state=CommandOutcomeState(),
        command=Command(command_type=CommandType.SHOOT, primary_target=Point(x=0, y=80)),
        selected_target=target,
        world_state=_world_state(),
        level=_level(),
        current_time=10.0,
        params=CommandOutcomeParams(),
    )

    assert updated.action_tracker.deadzones == (
        Deadzone(point=Point(x=0.0, y=80.0), expires_at=10.1),
    )
    assert updated.coin_tracker.locks == (
        CoinLock(point=Point(x=10.0, y=80.0), expires_at=11.0),
    )
    assert updated.next_fire_ready_time == 10.3


def test_apply_command_outcome_locks_breakthrough_coin_and_uses_double_shot_delay():
    target = TargetCandidate(
        x=0.0,
        y=80.0,
        score=100.0,
        target_type=BREAKTHROUGH_COIN_TARGET,
        secondary_x=200.0,
        secondary_y=10.0,
        coin_x=195.0,
        coin_y=10.0,
        delay_ms=250,
    )

    updated = apply_command_outcome(
        state=CommandOutcomeState(),
        command=Command(
            command_type=CommandType.SWAP_DOUBLE_SHOOT,
            primary_target=Point(x=0, y=80),
            secondary_target=Point(x=200, y=10),
            delay_ms=275,
        ),
        selected_target=target,
        world_state=_world_state(current_ball="red", next_ball="blue"),
        level=_level(),
        current_time=10.0,
        params=CommandOutcomeParams(),
    )

    assert updated.action_tracker.deadzones == (
        Deadzone(point=Point(x=0.0, y=80.0), expires_at=10.1),
    )
    assert updated.coin_tracker.locks == (
        CoinLock(point=Point(x=195.0, y=10.0), expires_at=12.0),
    )
    assert updated.last_swap_time == 10.0
    assert updated.next_fire_ready_time == pytest.approx(10.625)


def test_apply_command_outcome_prunes_without_mutating_on_no_op():
    state = CommandOutcomeState(
        action_tracker=ActionTrackerState(
            deadzones=(
                Deadzone(point=Point(x=1, y=1), expires_at=9.0),
                Deadzone(point=Point(x=2, y=2), expires_at=11.0),
            ),
        ),
        coin_tracker=CoinTrackerState(
            tracks=MappingProxyType({}),
            locks=(
                CoinLock(point=Point(x=1, y=1), expires_at=9.0),
                CoinLock(point=Point(x=2, y=2), expires_at=11.0),
            ),
        ),
        last_swap_time=4.0,
        next_fire_ready_time=9.5,
        last_fire_time=8.0,
    )

    updated = apply_command_outcome(
        state=state,
        command=Command(command_type=CommandType.NO_OP),
        selected_target=None,
        world_state=_world_state(),
        level=_level(),
        current_time=10.0,
    )

    assert updated.action_tracker.deadzones == (
        Deadzone(point=Point(x=2, y=2), expires_at=11.0),
    )
    assert updated.coin_tracker.locks == (
        CoinLock(point=Point(x=2, y=2), expires_at=11.0),
    )
    assert updated.last_swap_time == 4.0
    assert updated.next_fire_ready_time == 9.5
    assert updated.last_fire_time == 8.0


def test_apply_command_outcome_elim_uses_fire_cooldown_after_deadzone():
    target = TargetCandidate(
        x=0.0,
        y=80.0,
        score=10.0,
        target_type=ELIM_TARGET,
        track_id=1,
        track_idx=50,
    )

    updated = apply_command_outcome(
        state=CommandOutcomeState(),
        command=Command(command_type=CommandType.SHOOT, primary_target=Point(x=0, y=80)),
        selected_target=target,
        world_state=_world_state(),
        level=_level(),
        current_time=10.0,
    )

    assert updated.action_tracker.deadzones == (
        Deadzone(point=Point(x=0.0, y=80.0), expires_at=10.2),
    )
    assert updated.action_tracker.cluster_locks == (
        ClusterLock(track_id=1, start_idx=20, end_idx=80, expires_at=10.2),
    )
    assert updated.next_fire_ready_time == 10.3


def test_apply_command_outcome_rollback_locks_tail_near_track_end():
    target = TargetCandidate(
        x=0.0,
        y=80.0,
        score=10.0,
        target_type=ROLLBACK_ELIM_TARGET,
        track_id=1,
        track_idx=50,
        cluster_start_idx=45,
        cluster_end_idx=55,
    )

    updated = apply_command_outcome(
        state=CommandOutcomeState(),
        command=Command(command_type=CommandType.SHOOT, primary_target=Point(x=0, y=80)),
        selected_target=target,
        world_state=_world_state(),
        level=_level_with_track_end(201),
        current_time=10.0,
    )

    assert updated.action_tracker.cluster_locks == (
        ClusterLock(track_id=1, start_idx=15, end_idx=85, expires_at=10.2),
        ClusterLock(track_id=1, start_idx=30, end_idx=200, expires_at=10.4),
    )


def _world_state(
    *,
    clusters: tuple[Cluster, ...] = (),
    current_ball: str = "red",
    next_ball: str = "blue",
) -> WorldState:
    entities = tuple(entity for cluster in clusters for entity in cluster.entities)
    return WorldState(
        level_id="test",
        launcher=LauncherState(
            current_ball=current_ball,
            next_ball=next_ball,
            next_position=None,
        ),
        entities=entities,
        clusters=clusters,
    )


def _level() -> LevelRuntimeAssets:
    topology = LevelTopology(
        level_id="test",
        frog_pivot=Point(x=0.0, y=0.0),
        tracks=(),
        treasure_points=(),
        source_path=Path("test.json"),
    )
    return LevelRuntimeAssets(
        level_id="test",
        topology=topology,
        geometry=LevelGeometry(
            level_id="test",
            tracks=(TrackGeometry(track_id=1, points=(), cumulative_distances=()),),
        ),
        background=None,
    )


def _level_with_track_end(point_count: int) -> LevelRuntimeAssets:
    track = TrackGeometry(
        track_id=1,
        points=tuple(Point(x=float(index), y=0.0) for index in range(point_count)),
        cumulative_distances=tuple(float(index) for index in range(point_count)),
    )
    return LevelRuntimeAssets(
        level_id="test",
        topology=LevelTopology(
            level_id="test",
            frog_pivot=Point(x=0.0, y=0.0),
            tracks=(),
            treasure_points=(),
            source_path=Path("test.json"),
        ),
        geometry=LevelGeometry(level_id="test", tracks=(track,)),
        background=None,
    )


def _cluster(
    color: str,
    *,
    track_id: int,
    start_idx: int,
    end_idx: int,
) -> Cluster:
    entities = (
        BallEntity(
            x=float(start_idx),
            y=0.0,
            track_id=track_id,
            track_idx=start_idx,
            color=color,
        ),
        BallEntity(
            x=float(end_idx),
            y=0.0,
            track_id=track_id,
            track_idx=end_idx,
            color=color,
        ),
    )
    return Cluster(
        track_id=track_id,
        color=color,
        entities=entities,
        start_idx=start_idx,
        end_idx=end_idx,
    )
