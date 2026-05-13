import cv2
import numpy as np

from autozuma.core.models import LauncherTemplate, LauncherTemplateSet, Point
from autozuma.vision.colors import COLOR_PROFILES_BGR, UNKNOWN_COLOR
from autozuma.vision.launcher_state import detect_launcher_state


def test_detects_launcher_angle_and_ball_colors_from_controlled_roi():
    frame = np.zeros((120, 120, 3), dtype=np.uint8)
    pivot = Point(x=60, y=60)
    template_set = _controlled_template_set(search_radius=20)
    cv2.circle(frame, (60, 88), 13, COLOR_PROFILES_BGR["red"][0], -1)
    cv2.circle(frame, (60, 35), 8, COLOR_PROFILES_BGR["blue"][0], -1)

    state = detect_launcher_state(frame, pivot, template_set)

    assert state.angle_degrees == 0
    assert state.confidence == 1.0
    assert state.current_ball == "red"
    assert state.next_ball == "blue"
    assert state.next_position == Point(x=60, y=35)


def test_launcher_state_returns_unknown_when_search_roi_is_clipped():
    frame = np.zeros((60, 60, 3), dtype=np.uint8)
    pivot = Point(x=10, y=10)

    state = detect_launcher_state(frame, pivot, _controlled_template_set(search_radius=20))

    assert state.current_ball == UNKNOWN_COLOR
    assert state.next_ball == UNKNOWN_COLOR
    assert state.next_position is None
    assert state.angle_degrees is None
    assert state.confidence is None


def test_launcher_state_returns_unknown_without_valid_templates():
    frame = np.zeros((120, 120, 3), dtype=np.uint8)
    pivot = Point(x=60, y=60)
    template_set = LauncherTemplateSet(search_radius=20, step_degrees=5, templates={})

    state = detect_launcher_state(frame, pivot, template_set)

    assert state.current_ball == UNKNOWN_COLOR
    assert state.next_ball == UNKNOWN_COLOR
    assert state.next_position is None
    assert state.angle_degrees is None
    assert state.confidence is None


def _controlled_template_set(search_radius: int) -> LauncherTemplateSet:
    shape = (search_radius * 2, search_radius * 2)
    match_mask = np.zeros(shape, dtype=np.uint8)
    match_mask[0:5, 0:5] = 255
    return LauncherTemplateSet(
        search_radius=search_radius,
        step_degrees=90,
        templates={
            0: LauncherTemplate(
                angle_degrees=0,
                gray=np.zeros(shape, dtype=np.uint8),
                match_mask=match_mask,
                sub_mask=np.zeros(shape, dtype=np.uint8),
            ),
            90: LauncherTemplate(
                angle_degrees=90,
                gray=np.full(shape, 255, dtype=np.uint8),
                match_mask=match_mask,
                sub_mask=np.zeros(shape, dtype=np.uint8),
            ),
        },
    )
