from autozuma.assets.loader import load_all_topologies
from autozuma.assets.paths import default_asset_paths


def test_loads_all_migrated_topologies():
    topologies = load_all_topologies(default_asset_paths())

    assert len(topologies) == 22
    assert "space" in topologies
    assert "spiral" in topologies


def test_space_is_marked_for_special_detection():
    topology = load_all_topologies(default_asset_paths())["space"]

    assert topology.requires_special_detection is True
    assert topology.has_static_background is False


def test_all_topologies_have_frog_pivot_and_tracks():
    topologies = load_all_topologies(default_asset_paths())

    for topology in topologies.values():
        assert topology.frog_pivot is not None
        assert len(topology.tracks) >= 1
        for track in topology.tracks:
            assert len(track) >= 2


def test_multi_track_topologies_are_normalized_to_tracks_tuple():
    topologies = load_all_topologies(default_asset_paths())
    multi_track_topologies = [
        topology for topology in topologies.values() if len(topology.tracks) > 1
    ]

    assert multi_track_topologies
    for topology in multi_track_topologies:
        assert isinstance(topology.tracks, tuple)
        assert all(isinstance(track, tuple) for track in topology.tracks)
