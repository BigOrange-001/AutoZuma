import numpy as np
import pytest

from autozuma.assets.registry import load_asset_registry
from autozuma.core.models import RoiExtractionError
from autozuma.vision.roi import extract_game_roi


def test_extracts_exact_background_as_zero_offset_roi():
    registry = load_asset_registry()
    level = registry.levels["spiral"]
    background = level.background.bgr

    result = extract_game_roi(background, level)

    assert result.offset.x == 0
    assert result.offset.y == 0
    assert result.confidence >= 0.99
    assert result.frame.shape == background.shape
    assert np.array_equal(result.frame, background)


def test_extracts_background_from_larger_frame():
    registry = load_asset_registry()
    level = registry.levels["triangle"]
    background = level.background.bgr
    top, left = 19, 31
    frame = np.zeros(
        (background.shape[0] + top + 17, background.shape[1] + left + 23, 3),
        dtype=background.dtype,
    )
    frame[top : top + background.shape[0], left : left + background.shape[1]] = background

    result = extract_game_roi(frame, level)

    assert result.offset.x == left
    assert result.offset.y == top
    assert result.confidence >= 0.99
    assert np.array_equal(result.frame, background)


def test_extract_game_roi_rejects_frame_smaller_than_background():
    registry = load_asset_registry()
    level = registry.levels["spiral"]
    background = level.background.bgr

    with pytest.raises(RoiExtractionError, match="Frame is smaller"):
        extract_game_roi(background[:-1, :, :], level)


def test_extract_game_roi_supports_unscaled_dynamic_space_frame():
    registry = load_asset_registry()
    space = registry.levels["space"]
    frame = np.zeros((480, 640, 3), dtype=np.uint8)

    result = extract_game_roi(frame, space)

    assert result.offset.x == 0
    assert result.offset.y == 0
    assert result.confidence == 1.0
    assert np.array_equal(result.frame, frame)


def test_extract_game_roi_rejects_scaled_dynamic_space_frame():
    registry = load_asset_registry()
    space = registry.levels["space"]

    with pytest.raises(RoiExtractionError, match="requires an unscaled 640x480"):
        extract_game_roi(np.zeros((481, 640, 3), dtype=np.uint8), space)
