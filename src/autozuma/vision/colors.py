"""Color classification helpers for launcher and ball perception."""

from __future__ import annotations

from collections import Counter

import cv2
import numpy as np

UNKNOWN_COLOR = "unknown"


def _hex_to_bgr(hex_color: str) -> tuple[int, int, int]:
    rgb = tuple(int(hex_color.lstrip("#")[index : index + 2], 16) for index in (0, 2, 4))
    return rgb[::-1]


COLOR_PROFILES_BGR: dict[str, tuple[tuple[int, int, int], ...]] = {
    "red": (_hex_to_bgr("#d8040d"), _hex_to_bgr("#ee131c")),
    "yellow": (_hex_to_bgr("#ffff28"), _hex_to_bgr("#bc9518")),
    "green": (_hex_to_bgr("#38ff4c"), _hex_to_bgr("#367946")),
    "blue": (_hex_to_bgr("#36e2ff"), _hex_to_bgr("#32208d")),
    "purple": (_hex_to_bgr("#fb8df7"), _hex_to_bgr("#9e16a4")),
    "white": (_hex_to_bgr("#cec0ad"),),
}

TARGET_COLORS_BGR: list[tuple[int, int, int]] = []
TARGET_LABELS: list[str] = []
for label, colors in COLOR_PROFILES_BGR.items():
    for color in colors:
        TARGET_COLORS_BGR.append(color)
        TARGET_LABELS.append(label)

TARGET_HSV = cv2.cvtColor(np.array([TARGET_COLORS_BGR], dtype=np.uint8), cv2.COLOR_BGR2HSV)[
    0
].astype(np.float32)


def classify_entity_color(frame_bgr: np.ndarray, cx: float, cy: float, radius: int = 11) -> str:
    """Classify the dominant Zuma ball color around a circular sample region."""
    height, width = frame_bgr.shape[:2]
    y1 = max(0, int(cy) - radius)
    y2 = min(height, int(cy) + radius)
    x1 = max(0, int(cx) - radius)
    x2 = min(width, int(cx) + radius)
    roi = frame_bgr[y1:y2, x1:x2]
    if roi.size == 0:
        return UNKNOWN_COLOR

    y_grid, x_grid = np.ogrid[: y2 - y1, : x2 - x1]
    mask = (x_grid - (cx - x1)) ** 2 + (y_grid - (cy - y1)) ** 2 <= radius**2
    pixels = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)[mask].astype(np.float32)
    if pixels.size == 0:
        return UNKNOWN_COLOR

    diff_h = np.abs(pixels[:, np.newaxis, 0] - TARGET_HSV[np.newaxis, :, 0])
    diff_h = np.minimum(diff_h, 180.0 - diff_h)
    diff_s = pixels[:, np.newaxis, 1] - TARGET_HSV[np.newaxis, :, 1]
    diff_v = pixels[:, np.newaxis, 2] - TARGET_HSV[np.newaxis, :, 2]
    distances = np.sqrt((2.0 * diff_h) ** 2 + diff_s**2 + (0.2 * diff_v) ** 2)
    nearest_target_indexes = np.argmin(distances, axis=1)
    valid_indexes = nearest_target_indexes[np.min(distances, axis=1) < 90.0]
    if len(valid_indexes) < 5:
        return UNKNOWN_COLOR

    return Counter(TARGET_LABELS[index] for index in valid_indexes).most_common(1)[0][0]
