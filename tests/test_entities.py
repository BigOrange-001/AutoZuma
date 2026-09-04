import numpy as np

from autozuma.core.models import LevelRuntimeAssets, Point, TrackGeometry
from autozuma.vision.colors import COLOR_PROFILES_BGR
from autozuma.vision.entities import detect_level_entities, detect_track_entities


def test_detect_track_entities_finds_colored_balls_on_track():
    background = np.zeros((120, 160, 3), dtype=np.uint8)
    frame = background.copy()
    track = _horizontal_track(track_id=0, y=60, x_start=20, x_end=140)
    frame[60, 40] = COLOR_PROFILES_BGR["red"][0]
    frame[60, 90] = COLOR_PROFILES_BGR["blue"][0]
    _draw_ball(frame, 40, 60, "red")
    _draw_ball(frame, 90, 60, "blue")

    entities = detect_track_entities(frame, background, track)

    assert [entity.color for entity in entities] == ["red", "blue"]
    assert [entity.track_id for entity in entities] == [0, 0]
    assert entities[0].track_idx < entities[1].track_idx
    assert abs(entities[0].x - 40) <= 1
    assert abs(entities[1].x - 90) <= 1


def test_detect_track_entities_filters_off_track_foreground():
    background = np.zeros((120, 160, 3), dtype=np.uint8)
    frame = background.copy()
    track = _horizontal_track(track_id=0, y=60, x_start=20, x_end=140)
    _draw_ball(frame, 90, 25, "green")

    assert detect_track_entities(frame, background, track) == ()


def test_detect_track_entities_applies_start_and_end_exclusion():
    background = np.zeros((120, 160, 3), dtype=np.uint8)
    frame = background.copy()
    track = _horizontal_track(track_id=0, y=60, x_start=20, x_end=140)
    _draw_ball(frame, 30, 60, "yellow")
    _draw_ball(frame, 130, 60, "purple")

    assert (
        detect_track_entities(
            frame,
            background,
            track,
            p_start_exclude=25,
            p_end_exclude=25,
        )
        == ()
    )


def test_detect_level_entities_uses_all_tracks():
    background = np.zeros((140, 180, 3), dtype=np.uint8)
    frame = background.copy()
    track_0 = _horizontal_track(track_id=0, y=50, x_start=20, x_end=160)
    track_1 = _horizontal_track(track_id=1, y=95, x_start=20, x_end=160)
    _draw_ball(frame, 60, 50, "red")
    _draw_ball(frame, 120, 95, "blue")
    level = LevelRuntimeAssets(
        level_id="test",
        topology=None,
        geometry=type("Geometry", (), {"tracks": (track_0, track_1)})(),
        background=type("Background", (), {"bgr": background})(),
    )

    entities = detect_level_entities(frame, level)

    assert [(entity.track_id, entity.color) for entity in entities] == [(0, "red"), (1, "blue")]


def test_detect_track_entities_ignores_occluded_region_and_preserves_visible_regions():
    background = np.zeros((120, 180, 3), dtype=np.uint8)
    frame = background.copy()
    track = _horizontal_track(track_id=0, y=60, x_start=20, x_end=160)
    visibility = tuple(
        0 if point.x < 65 else -1 if point.x <= 115 else 1
        for point in track.points
    )
    track = TrackGeometry(
        track_id=track.track_id,
        points=track.points,
        cumulative_distances=track.cumulative_distances,
        visibility_region_ids=visibility,
    )
    _draw_ball(frame, 45, 60, "red")
    _draw_ball(frame, 90, 60, "yellow")
    _draw_ball(frame, 135, 60, "blue")

    entities = detect_track_entities(frame, background, track)

    assert [(entity.color, entity.visibility_region) for entity in entities] == [
        ("red", 0),
        ("blue", 1),
    ]


def test_detect_level_entities_assigns_crossing_ball_to_supported_track_once():
    background = np.zeros((180, 180, 3), dtype=np.uint8)
    frame = background.copy()
    horizontal = _horizontal_track(track_id=0, y=90, x_start=20, x_end=160)
    vertical = _vertical_track(track_id=1, x=90, y_start=20, y_end=160)
    _draw_ball(frame, 90, 50, "blue")
    _draw_ball(frame, 90, 90, "blue")
    _draw_ball(frame, 90, 130, "blue")
    level = LevelRuntimeAssets(
        level_id="crossing",
        topology=None,
        geometry=type("Geometry", (), {"tracks": (horizontal, vertical)})(),
        background=type("Background", (), {"bgr": background})(),
    )

    entities = detect_level_entities(frame, level)

    assert len(entities) == 3
    assert {entity.track_id for entity in entities} == {1}


def test_detect_level_entities_supports_dynamic_space_background():
    frame = np.full((120, 160, 3), (45, 8, 30), dtype=np.uint8)
    track = _horizontal_track(track_id=0, y=60, x_start=20, x_end=140)
    _draw_ball(frame, 40, 60, "purple")
    _draw_ball(frame, 100, 60, "white")
    frame[60, 70] = 255  # A star-like point is too small to survive morphology.
    level = LevelRuntimeAssets(
        level_id="space",
        topology=None,
        geometry=type("Geometry", (), {"tracks": (track,)})(),
        background=None,
        requires_special_detection=True,
    )

    entities = detect_level_entities(frame, level)

    assert [entity.color for entity in entities] == ["purple", "white"]
    assert abs(entities[0].x - 40) <= 1
    assert abs(entities[1].x - 100) <= 1


def _horizontal_track(track_id: int, y: int, x_start: int, x_end: int) -> TrackGeometry:
    points = tuple(Point(x=float(x), y=float(y)) for x in range(x_start, x_end + 1))
    cumulative_distances = tuple(float(index) for index in range(len(points)))
    return TrackGeometry(
        track_id=track_id,
        points=points,
        cumulative_distances=cumulative_distances,
    )


def _vertical_track(track_id: int, x: int, y_start: int, y_end: int) -> TrackGeometry:
    points = tuple(Point(x=float(x), y=float(y)) for y in range(y_start, y_end + 1))
    cumulative_distances = tuple(float(index) for index in range(len(points)))
    return TrackGeometry(
        track_id=track_id,
        points=points,
        cumulative_distances=cumulative_distances,
    )


def _draw_ball(frame: np.ndarray, x: int, y: int, color: str) -> None:
    yy, xx = np.ogrid[: frame.shape[0], : frame.shape[1]]
    mask = (xx - x) ** 2 + (yy - y) ** 2 <= 13**2
    frame[mask] = COLOR_PROFILES_BGR[color][0]
