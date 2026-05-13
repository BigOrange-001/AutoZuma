import numpy as np

from autozuma.vision.colors import COLOR_PROFILES_BGR, UNKNOWN_COLOR, classify_entity_color


def test_classifies_known_color_samples():
    frame = np.zeros((80, 80, 3), dtype=np.uint8)
    frame[20:60, 20:60] = COLOR_PROFILES_BGR["red"][0]

    assert classify_entity_color(frame, 40, 40, radius=11) == "red"


def test_returns_unknown_for_empty_or_weak_color_samples():
    frame = np.zeros((20, 20, 3), dtype=np.uint8)

    assert classify_entity_color(frame, -10, -10, radius=3) == UNKNOWN_COLOR
    assert classify_entity_color(frame, 10, 10, radius=0) == UNKNOWN_COLOR
