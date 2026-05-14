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
from autozuma.strategy.discard import DISCARD_TARGET, DiscardParams, discard_target


def test_discard_target_returns_none_for_unknown_current_ball():
    state = _world_state(current_ball="unknown", clusters=())

    assert discard_target(state, _level(), (100, 100)) is None


def test_discard_target_chooses_nearest_clear_edge_point():
    state = _world_state(current_ball="red", clusters=())

    target = discard_target(
        world_state=state,
        level=_level(frog_pivot=Point(x=50, y=50)),
        roi_size=(100, 100),
        params=DiscardParams(edge_step=50, edge_margin=5),
    )

    assert target is not None
    assert target.target_type == DISCARD_TARGET
    assert target.x == 50
    assert target.y == 5
    assert "edge" in target.reason


def test_discard_target_chooses_reachable_gap_when_edges_blocked(monkeypatch):
    state = _world_state(
        current_ball="red",
        clusters=(
            _cluster("blue", 1, 10),
            _cluster("yellow", 1, 40),
            _cluster("red", 1, 80),
        ),
    )

    def fake_check_line_of_sight(frog_pivot, target, entities, min_gap, **kwargs):
        return type("Result", (), {"is_clear": target.x == 25.0})()

    monkeypatch.setattr(
        "autozuma.strategy.discard.check_line_of_sight",
        fake_check_line_of_sight,
    )

    target = discard_target(
        world_state=state,
        level=_level(),
        roi_size=(100, 100),
        params=DiscardParams(edge_step=50, edge_margin=5),
    )

    assert target is not None
    assert target.track_idx == 25
    assert target.x == 25
    assert "gap" in target.reason


def test_discard_target_prefers_gap_near_same_color_cluster(monkeypatch):
    state = _world_state(
        current_ball="red",
        clusters=(
            _cluster("blue", 1, 10),
            _cluster("yellow", 1, 40),
            _cluster("green", 1, 60),
            _cluster("purple", 1, 70),
            _cluster("red", 1, 75),
        ),
    )

    monkeypatch.setattr(
        "autozuma.strategy.discard.check_line_of_sight",
        lambda **kwargs: type("Result", (), {"is_clear": kwargs["target"].x not in {0.0, 5.0, 50.0, 95.0}})(),
    )

    target = discard_target(
        world_state=state,
        level=_level(),
        roi_size=(100, 100),
        params=DiscardParams(edge_step=50, edge_margin=5),
    )

    assert target is not None
    assert target.track_idx == 72
    assert target.x == 72


def test_discard_target_falls_back_to_size_one_cluster_when_edges_and_gaps_blocked(monkeypatch):
    state = _world_state(
        current_ball="red",
        clusters=(
            _cluster("blue", 2, 20),
            _cluster("red", 1, 60),
        ),
    )

    monkeypatch.setattr(
        "autozuma.strategy.discard.check_line_of_sight",
        lambda **kwargs: type("Result", (), {"is_clear": False})(),
    )

    target = discard_target(state, _level(), (100, 100))

    assert target is not None
    assert target.track_idx == 60
    assert "size-1" in target.reason


def test_discard_target_falls_back_to_earliest_known_cluster(monkeypatch):
    state = _world_state(
        current_ball="red",
        clusters=(
            _cluster("blue", 2, 30),
            _cluster("yellow", 2, 60),
        ),
    )

    monkeypatch.setattr(
        "autozuma.strategy.discard.check_line_of_sight",
        lambda **kwargs: type("Result", (), {"is_clear": False})(),
    )

    target = discard_target(state, _level(), (100, 100))

    assert target is not None
    assert target.track_idx == 30
    assert "earliest" in target.reason


def test_discard_target_falls_back_upward_without_clusters(monkeypatch):
    state = _world_state(current_ball="red", clusters=())

    monkeypatch.setattr(
        "autozuma.strategy.discard.check_line_of_sight",
        lambda **kwargs: type("Result", (), {"is_clear": False})(),
    )

    target = discard_target(
        state,
        _level(frog_pivot=Point(x=50, y=50)),
        (100, 100),
        DiscardParams(fallback_up_distance=80),
    )

    assert target is not None
    assert target.x == 50
    assert target.y == -30
    assert "upward" in target.reason


def _world_state(current_ball: str, clusters: tuple[Cluster, ...]) -> WorldState:
    return WorldState(
        level_id="test",
        launcher=LauncherState(current_ball=current_ball, next_ball="blue", next_position=None),
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


def _level(frog_pivot: Point = Point(x=0, y=0)) -> LevelRuntimeAssets:
    track = TrackGeometry(
        track_id=0,
        points=tuple(Point(x=float(idx), y=50.0) for idx in range(101)),
        cumulative_distances=tuple(float(idx) for idx in range(101)),
    )
    topology = LevelTopology(
        level_id="test",
        frog_pivot=frog_pivot,
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
