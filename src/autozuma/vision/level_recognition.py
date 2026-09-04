"""Static level recognition using migrated background assets."""

from __future__ import annotations

import cv2
import numpy as np

from autozuma.core.models import AssetRegistry, LevelDetectionResult, Point
from autozuma.vision.image_io import to_gray
from autozuma.vision.space_level import SPACE_LEVEL_ID, detect_space_level

STATIC_LEVEL_MATCH_THRESHOLD = 0.25


def detect_static_level(
    frame_bgr: np.ndarray,
    registry: AssetRegistry,
    min_confidence: float = STATIC_LEVEL_MATCH_THRESHOLD,
) -> LevelDetectionResult | None:
    """Detect a supported level from a raw BGR frame."""
    space_level = registry.levels.get(SPACE_LEVEL_ID)
    if space_level is not None and space_level.requires_special_detection:
        space_result = detect_space_level(frame_bgr)
        if space_result is not None and space_result.confidence >= min_confidence:
            return space_result

    gray_frame = to_gray(frame_bgr)

    best_result: LevelDetectionResult | None = None
    for level_id, level in registry.levels.items():
        if level.requires_special_detection or level.background is None:
            continue
        if not _can_match(gray_frame, level.background.gray):
            continue

        match = cv2.matchTemplate(gray_frame, level.background.gray, cv2.TM_CCOEFF_NORMED)
        _, max_value, _, max_location = cv2.minMaxLoc(match)
        if best_result is None or max_value > best_result.confidence:
            best_result = LevelDetectionResult(
                level_id=level_id,
                confidence=float(max_value),
                match_location=Point(x=float(max_location[0]), y=float(max_location[1])),
            )

    if best_result is None or best_result.confidence < min_confidence:
        return None
    return best_result


def _can_match(frame_gray: np.ndarray, template_gray: np.ndarray) -> bool:
    frame_height, frame_width = frame_gray.shape[:2]
    template_height, template_width = template_gray.shape[:2]
    return frame_height >= template_height and frame_width >= template_width
