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


def test_optional_vote_thresholds_reject_sparse_or_mixed_color_samples():
    sparse = np.zeros((40, 40, 3), dtype=np.uint8)
    sparse[18:22, 18:22] = COLOR_PROFILES_BGR["red"][0]

    assert (
        classify_entity_color(
            sparse,
            20,
            20,
            radius=8,
            min_value=64.0,
            min_valid_fraction=0.20,
            min_dominant_fraction=0.60,
        )
        == UNKNOWN_COLOR
    )

    mixed = np.zeros((40, 40, 3), dtype=np.uint8)
    mixed[12:28, 12:20] = COLOR_PROFILES_BGR["red"][0]
    mixed[12:28, 20:28] = COLOR_PROFILES_BGR["blue"][0]

    assert (
        classify_entity_color(
            mixed,
            20,
            20,
            radius=8,
            min_value=64.0,
            min_valid_fraction=0.20,
            min_dominant_fraction=0.60,
        )
        == UNKNOWN_COLOR
    )
