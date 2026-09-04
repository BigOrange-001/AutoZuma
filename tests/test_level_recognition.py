import cv2
import numpy as np

from autozuma.assets.registry import load_asset_registry
from autozuma.vision.level_recognition import detect_static_level
from autozuma.vision.space_level import detect_space_level


def test_detects_exact_static_level_background():
    registry = load_asset_registry()
    level = registry.levels["spiral"]

    result = detect_static_level(level.background.bgr, registry)

    assert result is not None
    assert result.level_id == "spiral"
    assert result.confidence >= 0.99
    assert result.match_location.x == 0
    assert result.match_location.y == 0


def test_detected_groovefest_id_can_index_the_registry():
    registry = load_asset_registry()
    level = registry.levels["groovefest"]

    result = detect_static_level(level.background.bgr, registry)

    assert result is not None
    assert result.level_id == "groovefest"
    assert registry.levels[result.level_id] is level


def test_detects_static_level_inside_larger_frame():
    registry = load_asset_registry()
    level = registry.levels["coaster"]
    background = level.background.bgr
    top, left = 7, 13
    frame = np.zeros(
        (background.shape[0] + top + 9, background.shape[1] + left + 11, 3),
        dtype=background.dtype,
    )
    frame[top : top + background.shape[0], left : left + background.shape[1]] = background

    result = detect_static_level(frame, registry)

    assert result is not None
    assert result.level_id == "coaster"
    assert result.confidence >= 0.99
    assert result.match_location.x == left
    assert result.match_location.y == top


def test_static_recognition_returns_none_below_threshold():
    registry = load_asset_registry()
    shape = registry.levels["spiral"].background.bgr.shape
    rng = np.random.default_rng(0)
    frame = rng.integers(0, 256, size=shape, dtype=np.uint8)

    assert detect_static_level(frame, registry) is None


def test_static_background_is_not_misclassified_as_space():
    registry = load_asset_registry()

    assert registry.levels["space"].requires_special_detection is True
    assert registry.levels["space"].background is None
    assert detect_static_level(registry.levels["spiral"].background.bgr, registry).level_id != "space"


def test_detects_dynamic_space_palette_without_a_background_template():
    registry = load_asset_registry()
    frame = _space_signature_frame()

    result = detect_static_level(frame, registry)

    assert result is not None
    assert result.level_id == "space"
    assert result.match_location.x == 0
    assert result.match_location.y == 0


def test_space_palette_rejects_dimmed_pause_frame_and_static_backgrounds():
    registry = load_asset_registry()
    paused = (_space_signature_frame().astype(np.float32) * 0.25).astype(np.uint8)

    assert detect_space_level(paused) is None
    for level in registry.levels.values():
        if level.background is not None:
            assert detect_space_level(level.background.bgr) is None


def _space_signature_frame() -> np.ndarray:
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    bright_purple_hsv = np.full((415, 380, 3), (145, 210, 90), dtype=np.uint8)
    frame[45:460, 18:398] = cv2.cvtColor(
        bright_purple_hsv,
        cv2.COLOR_HSV2BGR,
    )
    return frame
