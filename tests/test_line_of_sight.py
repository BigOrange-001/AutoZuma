import math

from autozuma.core.models import BallEntity, Point
from autozuma.strategy.line_of_sight import check_line_of_sight


def test_check_line_of_sight_is_clear_without_entities():
    result = check_line_of_sight(
        frog_pivot=Point(x=0, y=0),
        target=Point(x=100, y=0),
        entities=(),
        min_gap=20,
    )

    assert result.is_clear is True
    assert math.isinf(result.min_distance)


def test_check_line_of_sight_detects_blocker_on_ray():
    result = check_line_of_sight(
        frog_pivot=Point(x=0, y=0),
        target=Point(x=100, y=0),
        entities=(_entity(x=50, y=0, track_id=1, track_idx=50),),
        min_gap=20,
    )

    assert result.is_clear is False
    assert result.min_distance == 0


def test_check_line_of_sight_allows_off_ray_entities_outside_clearance():
    result = check_line_of_sight(
        frog_pivot=Point(x=0, y=0),
        target=Point(x=100, y=0),
        entities=(_entity(x=50, y=50, track_id=1, track_idx=50),),
        min_gap=20,
    )

    assert result.is_clear is True
    assert result.min_distance == 50


def test_check_line_of_sight_respects_requested_min_gap_above_physical_limit():
    result = check_line_of_sight(
        frog_pivot=Point(x=0, y=0),
        target=Point(x=100, y=0),
        entities=(_entity(x=50, y=40, track_id=1, track_idx=50),),
        min_gap=45,
    )

    assert result.is_clear is False
    assert result.min_distance == 40


def test_check_line_of_sight_ignores_entities_inside_target_cluster_bounds():
    result = check_line_of_sight(
        frog_pivot=Point(x=0, y=0),
        target=Point(x=100, y=0),
        entities=(_entity(x=50, y=0, track_id=0, track_idx=50),),
        min_gap=20,
        target_track_id=0,
        cluster_start_idx=40,
        cluster_end_idx=60,
    )

    assert result.is_clear is True
    assert math.isinf(result.min_distance)


def test_check_line_of_sight_ignores_same_track_entities_near_target():
    result = check_line_of_sight(
        frog_pivot=Point(x=0, y=0),
        target=Point(x=100, y=0),
        entities=(_entity(x=55, y=0, track_id=0, track_idx=55),),
        min_gap=20,
        target_track_id=0,
    )

    assert result.is_clear is True
    assert math.isinf(result.min_distance)


def _entity(x: float, y: float, track_id: int, track_idx: int) -> BallEntity:
    return BallEntity(
        x=x,
        y=y,
        track_id=track_id,
        track_idx=track_idx,
        color="red",
    )
