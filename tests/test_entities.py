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


def _horizontal_track(track_id: int, y: int, x_start: int, x_end: int) -> TrackGeometry:
    points = tuple(Point(x=float(x), y=float(y)) for x in range(x_start, x_end + 1))
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
