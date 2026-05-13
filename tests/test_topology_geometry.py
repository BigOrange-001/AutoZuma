import math

from autozuma.assets.loader import load_all_topologies
from autozuma.assets.paths import default_asset_paths
from autozuma.topology.geometry import build_level_geometry


def test_all_topologies_build_geometry():
    topologies = load_all_topologies(default_asset_paths())

    for topology in topologies.values():
        geometry = build_level_geometry(topology)

        assert geometry.level_id == topology.level_id
        assert len(geometry.tracks) == len(topology.tracks)


def test_dense_tracks_are_larger_than_control_tracks():
    topologies = load_all_topologies(default_asset_paths())

    for topology in topologies.values():
        geometry = build_level_geometry(topology)
        for source_track, geometry_track in zip(topology.tracks, geometry.tracks):
            assert len(geometry_track.points) > len(source_track)
            assert len(geometry_track.cumulative_distances) == len(geometry_track.points)


def test_cumulative_distances_are_monotonic():
    topologies = load_all_topologies(default_asset_paths())

    for topology in topologies.values():
        geometry = build_level_geometry(topology)
        for track in geometry.tracks:
            distances = track.cumulative_distances
            assert distances[0] == 0.0
            assert distances[-1] > 0.0
            assert all(current >= previous for previous, current in zip(distances, distances[1:]))


def test_dense_track_endpoints_match_control_endpoints():
    topologies = load_all_topologies(default_asset_paths())

    for topology in topologies.values():
        geometry = build_level_geometry(topology)
        for source_track, geometry_track in zip(topology.tracks, geometry.tracks):
            assert _distance(geometry_track.points[0], source_track[0]) < 1e-6
            assert _distance(geometry_track.points[-1], source_track[-1]) < 1e-6


def test_multi_track_count_is_preserved():
    topologies = load_all_topologies(default_asset_paths())
    multi_track_topologies = [
        topology for topology in topologies.values() if len(topology.tracks) > 1
    ]

    assert multi_track_topologies
    for topology in multi_track_topologies:
        geometry = build_level_geometry(topology)
        assert len(geometry.tracks) == len(topology.tracks)


def test_space_builds_geometry_even_without_static_background():
    topology = load_all_topologies(default_asset_paths())["space"]
    geometry = build_level_geometry(topology)

    assert topology.requires_special_detection is True
    assert geometry.level_id == "space"
    assert len(geometry.tracks) == len(topology.tracks)


def _distance(a, b):
    return math.hypot(a.x - b.x, a.y - b.y)
