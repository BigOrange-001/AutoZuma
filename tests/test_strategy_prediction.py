from pathlib import Path

from autozuma.core.models import (
    LevelGeometry,
    LevelRuntimeAssets,
    LevelTopology,
    Point,
    TargetCandidate,
    TrackGeometry,
)
from autozuma.strategy.prediction import TargetPredictionParams, predict_target, predict_targets


def test_predict_target_offsets_track_index_by_distance_multiplier():
    level = _level()
    target = _target(x=30, y=40, track_idx=10)

    predicted = predict_target(
        target=target,
        level=level,
        frog_pivot=Point(x=0, y=0),
        params=TargetPredictionParams(predict_multiplier=0.2),
    )

    assert predicted.x == 20
    assert predicted.y == 40
    assert predicted.track_idx == 20
    assert predicted.score == target.score
    assert predicted.target_type == target.target_type
    assert predicted.cluster_start_idx == target.cluster_start_idx
    assert predicted.cluster_end_idx == target.cluster_end_idx
    assert "offset_idx=10" in predicted.reason
    assert "predicted_idx=20" in predicted.reason


def test_predict_target_clamps_to_track_bounds():
    level = _level()
    target = _target(x=100, y=0, track_idx=95)

    predicted = predict_target(
        target=target,
        level=level,
        frog_pivot=Point(x=0, y=0),
        params=TargetPredictionParams(predict_multiplier=1.0),
    )

    assert predicted.x == 99
    assert predicted.y == 198
    assert predicted.track_idx == 99


def test_predict_target_supports_negative_offsets():
    level = _level()
    target = _target(x=30, y=40, track_idx=10)

    predicted = predict_target(
        target=target,
        level=level,
        frog_pivot=Point(x=0, y=0),
        params=TargetPredictionParams(predict_multiplier=-0.2),
    )

    assert predicted.x == 0
    assert predicted.y == 0
    assert predicted.track_idx == 0


def test_predict_target_leaves_target_without_topology_metadata_unchanged():
    level = _level()
    target = TargetCandidate(x=30, y=40, score=12.0, target_type="ELIM")

    predicted = predict_target(
        target=target,
        level=level,
        frog_pivot=Point(x=0, y=0),
        params=TargetPredictionParams(predict_multiplier=0.2),
    )

    assert predicted == target


def test_predict_targets_preserves_order():
    level = _level()
    targets = (
        _target(x=30, y=40, track_idx=10),
        _target(x=10, y=0, track_idx=20),
    )

    predicted = predict_targets(
        targets=targets,
        level=level,
        frog_pivot=Point(x=0, y=0),
        params=TargetPredictionParams(predict_multiplier=0.2),
    )

    assert tuple(target.track_idx for target in predicted) == (20, 22)


def _level() -> LevelRuntimeAssets:
    topology = LevelTopology(
        level_id="test",
        frog_pivot=Point(x=0, y=0),
        tracks=(),
        treasure_points=(),
        source_path=Path("test.json"),
    )
    track = TrackGeometry(
        track_id=0,
        points=tuple(Point(x=float(idx), y=float(idx * 2)) for idx in range(100)),
        cumulative_distances=tuple(float(idx) for idx in range(100)),
    )
    return LevelRuntimeAssets(
        level_id="test",
        topology=topology,
        geometry=LevelGeometry(level_id="test", tracks=(track,)),
        background=None,
    )


def _target(x: float, y: float, track_idx: int) -> TargetCandidate:
    return TargetCandidate(
        x=x,
        y=y,
        score=12.0,
        target_type="ELIM",
        reason="base",
        track_id=0,
        track_idx=track_idx,
        cluster_start_idx=8,
        cluster_end_idx=12,
    )
