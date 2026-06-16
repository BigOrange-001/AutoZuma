from pathlib import Path

from autozuma.core.models import (
    BallEntity,
    Cluster,
    LauncherState,
    LevelGeometry,
    LevelRuntimeAssets,
    LevelTopology,
    Point,
    TrackGeometry,
    WorldState,
)
from autozuma.strategy.actions import ActionTrackerState, ClusterLock, Deadzone
from autozuma.strategy.targets import (
    COMBO_TARGET,
    ELIM_TARGET,
    PAIR_TARGET,
    ROLLBACK_ELIM_TARGET,
    TargetScoringParams,
    score_basic_targets,
    score_basic_targets_for_color,
)


def test_score_basic_targets_returns_empty_for_unknown_current_ball():
    world_state = _world_state(current_ball="unknown", clusters=(_cluster("red", 2, 30),))

    assert score_basic_targets(world_state, _level()) == ()


def test_score_basic_targets_ignores_clusters_with_different_color():
    world_state = _world_state(current_ball="red", clusters=(_cluster("blue", 2, 30),))

    assert score_basic_targets(world_state, _level()) == ()


def test_score_basic_targets_for_color_scores_next_ball_color():
    red_cluster = _cluster("red", 1, 30)
    blue_cluster = _cluster("blue", 2, 90)
    world_state = _world_state(current_ball="red", clusters=(red_cluster, blue_cluster))

    targets = score_basic_targets_for_color(
        world_state=world_state,
        level=_level(),
        target_color="blue",
        params=_params(),
    )

    assert len(targets) == 1
    assert targets[0].target_type == ELIM_TARGET
    assert targets[0].cluster_start_idx == 90


def test_score_basic_targets_scores_elimination_cluster():
    cluster = _cluster("red", 2, 30)
    world_state = _world_state(current_ball="red", clusters=(cluster,))

    targets = score_basic_targets(world_state, _level(), _params())

    assert len(targets) == 1
    assert targets[0].target_type == ELIM_TARGET
    assert targets[0].x == 32.0
    assert targets[0].y == 50.0
    assert targets[0].score > 0
    assert "size=2" in targets[0].reason
    assert "reachable=2" in targets[0].reason
    assert targets[0].track_id == 0
    assert targets[0].track_idx == 32
    assert targets[0].cluster_start_idx == 30
    assert targets[0].cluster_end_idx == 32


def test_score_basic_targets_scores_single_ball_as_pair_target():
    world_state = _world_state(current_ball="red", clusters=(_cluster("red", 1, 30),))

    targets = score_basic_targets(world_state, _level(), _params())

    assert len(targets) == 1
    assert targets[0].target_type == PAIR_TARGET


def test_score_basic_targets_sorts_candidates_by_score_descending():
    pair_cluster = _cluster("red", 1, 30)
    spacer_cluster = _cluster("blue", 1, 60)
    elim_cluster = _cluster("red", 2, 90)
    world_state = _world_state(
        current_ball="red",
        clusters=(pair_cluster, spacer_cluster, elim_cluster),
    )

    targets = score_basic_targets(world_state, _level(), _params())

    assert [target.target_type for target in targets] == [ELIM_TARGET, PAIR_TARGET]
    assert targets[0].score > targets[1].score


def test_score_basic_targets_skips_adjacent_same_color_clusters():
    left_cluster = _cluster("red", 1, 30)
    right_cluster = _cluster("red", 2, 90)
    world_state = _world_state(current_ball="red", clusters=(left_cluster, right_cluster))

    assert score_basic_targets(world_state, _level(), _params()) == ()


def test_score_basic_targets_scores_combo_when_neighbors_collapse():
    left_cluster = _cluster("blue", 2, 20)
    target_cluster = _cluster("red", 2, 50)
    right_cluster = _cluster("blue", 1, 80)
    world_state = _world_state(
        current_ball="red",
        clusters=(left_cluster, target_cluster, right_cluster),
    )

    targets = score_basic_targets(world_state, _level(), _params())

    assert len(targets) == 1
    assert targets[0].target_type == COMBO_TARGET
    assert targets[0].combo_depth == 1
    assert "combo_depth=1" in targets[0].reason


def test_score_basic_targets_scores_rollback_elimination():
    left_cluster = _cluster("blue", 1, 20)
    target_cluster = _cluster("red", 2, 50)
    right_cluster = _cluster("blue", 1, 80)
    world_state = _world_state(
        current_ball="red",
        clusters=(left_cluster, target_cluster, right_cluster),
    )

    targets = score_basic_targets(world_state, _level(), _params())

    assert len(targets) == 1
    assert targets[0].target_type == ROLLBACK_ELIM_TARGET
    assert targets[0].combo_depth == 0


def test_score_basic_targets_downgrades_when_nearby_combo_is_deeper():
    target_cluster = _cluster("red", 2, 10)
    combo_left = _cluster("yellow", 2, 35)
    combo_center = _cluster("blue", 2, 60)
    combo_right = _cluster("yellow", 1, 85)
    world_state = _world_state(
        current_ball="red",
        clusters=(target_cluster, combo_left, combo_center, combo_right),
    )

    targets = score_basic_targets(world_state, _level(), _params())

    assert len(targets) == 1
    assert targets[0].target_type == PAIR_TARGET
    assert targets[0].score < 100.0


def test_score_basic_targets_skips_unknown_clusters_when_scanning_neighbors():
    left_cluster = _cluster("blue", 2, 20)
    unknown_cluster = _cluster("unknown", 1, 40)
    target_cluster = _cluster("red", 2, 60)
    right_cluster = _cluster("blue", 1, 90)
    world_state = _world_state(
        current_ball="red",
        clusters=(left_cluster, unknown_cluster, target_cluster, right_cluster),
    )

    targets = score_basic_targets(world_state, _level(), _params())

    assert len(targets) == 1
    assert targets[0].target_type == COMBO_TARGET


def test_score_basic_targets_skips_cluster_inside_active_deadzone():
    cluster = _cluster("red", 2, 30)
    world_state = _world_state(current_ball="red", clusters=(cluster,))

    targets = score_basic_targets(
        world_state=world_state,
        level=_level(),
        params=TargetScoringParams(
            action_state=ActionTrackerState(
                deadzones=(Deadzone(point=Point(x=31.0, y=50.0), expires_at=12.0),)
            ),
            current_time=10.0,
            soft_lock_radius=35.0,
        ),
    )

    assert targets == ()


def test_score_basic_targets_ignores_expired_deadzone():
    cluster = _cluster("red", 2, 30)
    world_state = _world_state(current_ball="red", clusters=(cluster,))

    targets = score_basic_targets(
        world_state=world_state,
        level=_level(),
        params=TargetScoringParams(
            action_state=ActionTrackerState(
                deadzones=(Deadzone(point=Point(x=31.0, y=50.0), expires_at=10.0),)
            ),
            current_time=10.0,
            soft_lock_radius=35.0,
        ),
    )

    assert len(targets) == 1


def test_score_basic_targets_skips_cluster_inside_active_cluster_lock():
    cluster = _cluster("red", 2, 30)
    world_state = _world_state(current_ball="red", clusters=(cluster,))

    targets = score_basic_targets(
        world_state=world_state,
        level=_level(),
        params=TargetScoringParams(
            action_state=ActionTrackerState(
                cluster_locks=(
                    ClusterLock(track_id=0, start_idx=20, end_idx=40, expires_at=12.0),
                )
            ),
            current_time=10.0,
        ),
    )

    assert targets == ()


def test_score_basic_targets_uses_reachable_subset_for_aim_point():
    blocked = BallEntity(x=100.0, y=0.0, track_id=0, track_idx=100, color="red")
    also_blocked = BallEntity(x=110.0, y=0.0, track_id=0, track_idx=110, color="red")
    reachable_one = BallEntity(x=130.0, y=180.0, track_id=0, track_idx=130, color="red")
    reachable_two = BallEntity(x=140.0, y=180.0, track_id=0, track_idx=140, color="red")
    blocker_one = BallEntity(x=50.0, y=0.0, track_id=1, track_idx=50, color="blue")
    blocker_two = BallEntity(x=55.0, y=0.0, track_id=1, track_idx=55, color="blue")
    cluster = Cluster(
        track_id=0,
        color="red",
        entities=(blocked, also_blocked, reachable_one, reachable_two),
        start_idx=100,
        end_idx=140,
    )
    world_state = _world_state(current_ball="red", clusters=(cluster,))
    world_state = WorldState(
        level_id=world_state.level_id,
        launcher=world_state.launcher,
        entities=world_state.entities + (blocker_one, blocker_two),
        clusters=world_state.clusters,
    )

    targets = score_basic_targets(world_state, _horizontal_level(), _params())

    assert len(targets) == 1
    assert targets[0].x == 140.0
    assert targets[0].y == 180.0
    assert targets[0].track_idx == 140
    assert "reachable=2" in targets[0].reason


def test_score_basic_targets_ignores_same_track_entities_for_reachability():
    near = BallEntity(x=50.0, y=0.0, track_id=0, track_idx=50, color="red")
    far = BallEntity(x=100.0, y=0.0, track_id=0, track_idx=100, color="red")
    cluster = Cluster(
        track_id=0,
        color="red",
        entities=(near, far),
        start_idx=50,
        end_idx=100,
    )
    world_state = _world_state(current_ball="red", clusters=(cluster,))

    targets = score_basic_targets(world_state, _horizontal_level(), _params())

    assert len(targets) == 1
    assert "reachable=2" in targets[0].reason


def test_score_basic_targets_aims_odd_reachable_cluster_at_forward_ball_edge():
    entities = (
        BallEntity(x=30.0, y=0.0, track_id=0, track_idx=30, color="red"),
        BallEntity(x=50.0, y=0.0, track_id=0, track_idx=50, color="red"),
        BallEntity(x=70.0, y=0.0, track_id=0, track_idx=70, color="red"),
    )
    cluster = Cluster(
        track_id=0,
        color="red",
        entities=entities,
        start_idx=30,
        end_idx=70,
    )
    world_state = _world_state(current_ball="red", clusters=(cluster,))

    targets = score_basic_targets(world_state, _horizontal_level(), _params())

    assert len(targets) == 1
    assert targets[0].x == 66.0
    assert targets[0].y == 0.0
    assert targets[0].track_idx == 66
    assert "reachable=3" in targets[0].reason


def _params() -> TargetScoringParams:
    return TargetScoringParams(
        combo_priority=100.0,
        rollback_elim_priority=30.0,
        elim_priority=10.0,
        pair_priority=1.0,
    )


def _world_state(current_ball: str, clusters: tuple[Cluster, ...]) -> WorldState:
    return WorldState(
        level_id="test",
        launcher=LauncherState(
            current_ball=current_ball,
            next_ball="blue",
            next_position=None,
        ),
        entities=tuple(entity for cluster in clusters for entity in cluster.entities),
        clusters=clusters,
    )


def _cluster(color: str, size: int, start_idx: int) -> Cluster:
    entities = tuple(
        BallEntity(
            x=float(start_idx + offset * 2),
            y=50.0,
            track_id=0,
            track_idx=start_idx + offset * 2,
            color=color,
        )
        for offset in range(size)
    )
    return Cluster(
        track_id=0,
        color=color,
        entities=entities,
        start_idx=entities[0].track_idx,
        end_idx=entities[-1].track_idx,
    )


def _level() -> LevelRuntimeAssets:
    points = tuple(Point(x=float(index), y=50.0) for index in range(121))
    track = TrackGeometry(
        track_id=0,
        points=points,
        cumulative_distances=tuple(float(index) for index in range(len(points))),
    )
    topology = LevelTopology(
        level_id="test",
        frog_pivot=Point(x=60.0, y=0.0),
        tracks=(),
        treasure_points=(),
        source_path=Path("test.json"),
    )
    return LevelRuntimeAssets(
        level_id="test",
        topology=topology,
        geometry=LevelGeometry(level_id="test", tracks=(track,)),
        background=None,
    )


def _horizontal_level() -> LevelRuntimeAssets:
    points = tuple(Point(x=float(index), y=0.0) for index in range(201))
    track = TrackGeometry(
        track_id=0,
        points=points,
        cumulative_distances=tuple(float(index) for index in range(len(points))),
    )
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
        geometry=LevelGeometry(level_id="test", tracks=(track,)),
        background=None,
    )
