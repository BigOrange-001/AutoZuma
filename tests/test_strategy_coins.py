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
from autozuma.strategy.coins import (
    BREAKTHROUGH_COIN_TARGET,
    DIRECT_COIN_TARGET,
    CoinScoringParams,
    score_coin_targets,
    score_coin_targets_for_color,
)


def test_score_coin_targets_returns_empty_for_unknown_current_ball():
    world_state = _world_state(current_ball="unknown", clusters=(_cluster("red", (40, 42), y=0),))

    targets = score_coin_targets(world_state, _level(), active_coins=(Point(x=100, y=0),))

    assert targets == ()


def test_score_coin_targets_returns_empty_without_entities():
    world_state = _world_state(current_ball="red", clusters=())

    targets = score_coin_targets(world_state, _level(), active_coins=(Point(x=100, y=0),))

    assert targets == ()


def test_score_coin_targets_scores_direct_coin_when_no_cluster_blocks_line():
    world_state = _world_state(current_ball="red", clusters=(_cluster("blue", (40,), y=50),))
    params = CoinScoringParams(coin_priority=100.0, min_gap=36.0)

    targets = score_coin_targets(
        world_state=world_state,
        level=_level(),
        active_coins=(Point(x=100, y=0),),
        params=params,
    )

    assert len(targets) == 1
    assert targets[0].target_type == DIRECT_COIN_TARGET
    assert targets[0].x == 100
    assert targets[0].y == 0
    assert targets[0].score == 200.0
    assert targets[0].secondary_x is None
    assert targets[0].secondary_y is None


def test_score_coin_targets_scores_breakthrough_coin_for_one_matching_blocker():
    world_state = _world_state(current_ball="red", clusters=(_cluster("red", (40, 42), y=0),))
    params = CoinScoringParams(
        coin_priority=100.0,
        min_gap=36.0,
        breakthrough_aim_offset_idx=15,
        breakthrough_delay_ms=250,
    )

    targets = score_coin_targets(
        world_state=world_state,
        level=_level(),
        active_coins=(Point(x=100, y=0),),
        params=params,
    )

    assert len(targets) == 1
    assert targets[0].target_type == BREAKTHROUGH_COIN_TARGET
    assert targets[0].x == 57
    assert targets[0].y == 0
    assert targets[0].score == 150.0
    assert targets[0].track_id == 0
    assert targets[0].track_idx == 57
    assert targets[0].cluster_start_idx == 40
    assert targets[0].cluster_end_idx == 42
    assert targets[0].secondary_x == 100
    assert targets[0].secondary_y == 0
    assert targets[0].delay_ms == 250


def test_score_coin_targets_for_color_uses_requested_ball_color():
    world_state = _world_state(current_ball="red", clusters=(_cluster("blue", (40, 42), y=0),))

    targets = score_coin_targets_for_color(
        world_state=world_state,
        level=_level(),
        active_coins=(Point(x=100, y=0),),
        target_color="blue",
        params=CoinScoringParams(coin_priority=100.0),
    )

    assert len(targets) == 1
    assert targets[0].target_type == BREAKTHROUGH_COIN_TARGET


def test_score_coin_targets_ignores_breakthrough_with_wrong_color_blocker():
    world_state = _world_state(current_ball="red", clusters=(_cluster("blue", (40, 42), y=0),))

    targets = score_coin_targets(world_state, _level(), active_coins=(Point(x=100, y=0),))

    assert targets == ()


def test_score_coin_targets_ignores_breakthrough_with_single_ball_blocker():
    world_state = _world_state(current_ball="red", clusters=(_cluster("red", (40,), y=0),))

    targets = score_coin_targets(world_state, _level(), active_coins=(Point(x=100, y=0),))

    assert targets == ()


def test_score_coin_targets_ignores_coin_with_multiple_blockers():
    world_state = _world_state(
        current_ball="red",
        clusters=(
            _cluster("red", (40, 42), y=0),
            _cluster("red", (70, 72), y=0),
        ),
    )

    targets = score_coin_targets(world_state, _level(), active_coins=(Point(x=100, y=0),))

    assert targets == ()


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


def _cluster(color: str, track_indices: tuple[int, ...], y: float) -> Cluster:
    entities = tuple(
        BallEntity(
            x=float(track_idx),
            y=y,
            track_id=0,
            track_idx=track_idx,
            color=color,
        )
        for track_idx in track_indices
    )
    return Cluster(
        track_id=0,
        color=color,
        entities=entities,
        start_idx=entities[0].track_idx,
        end_idx=entities[-1].track_idx,
    )


def _level() -> LevelRuntimeAssets:
    points = tuple(Point(x=float(index), y=0.0) for index in range(121))
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
