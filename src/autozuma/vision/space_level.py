"""Low-cost recognition helpers for the dynamic-background space level."""

from __future__ import annotations

import cv2
import numpy as np

from autozuma.core.models import LevelDetectionResult, Point

SPACE_LEVEL_ID = "space"
SPACE_FRAME_WIDTH = 640
SPACE_FRAME_HEIGHT = 480

# Exclude the decorative frame and HUD, then sample only one pixel in every 4x4
# block. The animated nebula moves, but its black/purple palette remains stable.
SPACE_SAMPLE_LEFT = 18
SPACE_SAMPLE_RIGHT = 622
SPACE_SAMPLE_TOP = 45
SPACE_SAMPLE_BOTTOM = 460
SPACE_SAMPLE_STRIDE = 4

SPACE_PURPLE_HUE_MIN = 125
SPACE_PURPLE_HUE_MAX = 165
SPACE_PURPLE_MIN_SATURATION = 80
SPACE_PURPLE_MIN_VALUE = 25
SPACE_BRIGHT_PURPLE_MIN_SATURATION = 100
SPACE_BRIGHT_PURPLE_MIN_VALUE = 55
SPACE_DARK_MAX_VALUE = 34

SPACE_MIN_PURPLE_FRACTION = 0.35
SPACE_MIN_BRIGHT_PURPLE_FRACTION = 0.25
SPACE_MIN_DARK_FRACTION = 0.10


def detect_space_level(frame_bgr: np.ndarray) -> LevelDetectionResult | None:
    """Recognize an active unscaled space-level client frame by palette ratios."""
    if frame_bgr.shape[:2] != (SPACE_FRAME_HEIGHT, SPACE_FRAME_WIDTH):
        return None

    sample = frame_bgr[
        SPACE_SAMPLE_TOP:SPACE_SAMPLE_BOTTOM:SPACE_SAMPLE_STRIDE,
        SPACE_SAMPLE_LEFT:SPACE_SAMPLE_RIGHT:SPACE_SAMPLE_STRIDE,
    ]
    if sample.size == 0:
        return None

    hsv = cv2.cvtColor(sample, cv2.COLOR_BGR2HSV)
    hue = hsv[:, :, 0]
    saturation = hsv[:, :, 1]
    value = hsv[:, :, 2]
    purple_hue = (hue >= SPACE_PURPLE_HUE_MIN) & (hue <= SPACE_PURPLE_HUE_MAX)
    purple_fraction = float(
        np.mean(
            purple_hue
            & (saturation >= SPACE_PURPLE_MIN_SATURATION)
            & (value >= SPACE_PURPLE_MIN_VALUE)
        )
    )
    bright_purple_fraction = float(
        np.mean(
            purple_hue
            & (saturation >= SPACE_BRIGHT_PURPLE_MIN_SATURATION)
            & (value >= SPACE_BRIGHT_PURPLE_MIN_VALUE)
        )
    )
    dark_fraction = float(np.mean(value <= SPACE_DARK_MAX_VALUE))

    if (
        purple_fraction < SPACE_MIN_PURPLE_FRACTION
        or bright_purple_fraction < SPACE_MIN_BRIGHT_PURPLE_FRACTION
        or dark_fraction < SPACE_MIN_DARK_FRACTION
    ):
        return None

    confidence = min(
        1.0,
        purple_fraction / 0.60,
        bright_purple_fraction / 0.45,
        dark_fraction / 0.20,
    )
    return LevelDetectionResult(
        level_id=SPACE_LEVEL_ID,
        confidence=confidence,
        match_location=Point(x=0.0, y=0.0),
    )
