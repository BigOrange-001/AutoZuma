from autozuma.core.models import BallEntity
from autozuma.vision.clusters import build_topological_clusters


def test_build_topological_clusters_returns_empty_tuple_for_empty_input():
    assert build_topological_clusters(()) == ()


def test_build_topological_clusters_groups_same_color_entities_on_same_track():
    entities = (
        _entity(track_id=0, track_idx=10, color="red"),
        _entity(track_id=0, track_idx=40, color="red"),
        _entity(track_id=0, track_idx=90, color="red"),
    )

    clusters = build_topological_clusters(entities)

    assert len(clusters) == 1
    assert clusters[0].track_id == 0
    assert clusters[0].color == "red"
    assert clusters[0].entities == entities
    assert clusters[0].size == 3
    assert clusters[0].start_idx == 10
    assert clusters[0].end_idx == 90


def test_build_topological_clusters_splits_when_color_changes():
    clusters = build_topological_clusters(
        (
            _entity(track_id=0, track_idx=10, color="red"),
            _entity(track_id=0, track_idx=40, color="blue"),
        )
    )

    assert [(cluster.color, cluster.size) for cluster in clusters] == [("red", 1), ("blue", 1)]


def test_build_topological_clusters_splits_when_track_changes():
    clusters = build_topological_clusters(
        (
            _entity(track_id=0, track_idx=10, color="red"),
            _entity(track_id=1, track_idx=40, color="red"),
        )
    )

    assert [(cluster.track_id, cluster.size) for cluster in clusters] == [(0, 1), (1, 1)]


def test_build_topological_clusters_uses_strict_track_index_gap_threshold():
    clusters = build_topological_clusters(
        (
            _entity(track_id=0, track_idx=10, color="red"),
            _entity(track_id=0, track_idx=94, color="red"),
            _entity(track_id=0, track_idx=179, color="red"),
        )
    )

    assert [(cluster.start_idx, cluster.end_idx, cluster.size) for cluster in clusters] == [
        (10, 94, 2),
        (179, 179, 1),
    ]


def _entity(track_id: int, track_idx: int, color: str) -> BallEntity:
    return BallEntity(
        x=float(track_idx),
        y=10.0,
        track_id=track_id,
        track_idx=track_idx,
        color=color,
    )
