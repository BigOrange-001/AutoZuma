from autozuma.core.models import BallEntity, Point, TrackGeometry
from autozuma.strategy.aiming import aim_at_ball_entities, forward_track_index


def test_single_ball_aim_moves_forward_by_ball_radius():
    track = _track()
    entity = _entity(track_idx=30)

    aim = aim_at_ball_entities((entity,), track, forward_distance=16.0)

    assert aim is not None
    assert aim.context_entity == entity
    assert aim.track_idx == 46
    assert aim.point == Point(x=46.0, y=0.0)


def test_even_reachable_sequence_uses_endpoint_side_middle_ball():
    track = _track()
    entities = (_entity(track_idx=20), _entity(track_idx=40))

    aim = aim_at_ball_entities(entities, track)

    assert aim is not None
    assert aim.context_entity == entities[1]
    assert aim.track_idx == 40
    assert aim.point == Point(x=40.0, y=0.0)


def test_forward_track_index_stops_at_visible_region_boundary():
    base = _track()
    track = TrackGeometry(
        track_id=base.track_id,
        points=base.points,
        cumulative_distances=base.cumulative_distances,
        visibility_region_ids=tuple(
            0 if index <= 40 else -1 if index <= 60 else 1
            for index in range(len(base.points))
        ),
    )

    assert forward_track_index(35, track, 16.0) == 40


def _entity(track_idx: int) -> BallEntity:
    return BallEntity(
        x=float(track_idx),
        y=0.0,
        track_id=0,
        track_idx=track_idx,
        color="red",
    )


def _track() -> TrackGeometry:
    points = tuple(Point(x=float(index), y=0.0) for index in range(101))
    return TrackGeometry(
        track_id=0,
        points=points,
        cumulative_distances=tuple(float(index) for index in range(len(points))),
    )
