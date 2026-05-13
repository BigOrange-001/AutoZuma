"""Game ROI extraction and alignment."""

from __future__ import annotations

import cv2
import numpy as np

from autozuma.core.models import GameRoiResult, LevelRuntimeAssets, Point, RoiExtractionError
from autozuma.vision.image_io import to_gray


def extract_game_roi(frame_bgr: np.ndarray, level: LevelRuntimeAssets) -> GameRoiResult:
    """Locate and crop the static level background within a raw BGR frame."""
    if level.background is None:
        raise RoiExtractionError(f"Level {level.level_id!r} has no static background.")

    background = level.background
    background_height, background_width = background.gray.shape[:2]
    frame_height, frame_width = frame_bgr.shape[:2]

    if frame_height < background_height or frame_width < background_width:
        raise RoiExtractionError(
            "Frame is smaller than the level background "
            f"({frame_width}x{frame_height} < {background_width}x{background_height})."
        )

    match = cv2.matchTemplate(to_gray(frame_bgr), background.gray, cv2.TM_CCOEFF_NORMED)
    _, max_value, _, max_location = cv2.minMaxLoc(match)
    left, top = max_location
    roi = frame_bgr[top : top + background_height, left : left + background_width].copy()

    return GameRoiResult(
        frame=roi,
        offset=Point(x=float(left), y=float(top)),
        confidence=float(max_value),
    )
