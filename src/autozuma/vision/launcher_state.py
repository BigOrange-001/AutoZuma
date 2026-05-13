"""Launcher state detection from an aligned game ROI."""

from __future__ import annotations

import math

import cv2
import numpy as np

from autozuma.core.models import LauncherState, LauncherTemplateSet, Point
from autozuma.vision.colors import UNKNOWN_COLOR, classify_entity_color
from autozuma.vision.image_io import to_gray

CURRENT_BALL_DISTANCE = 28
NEXT_BALL_DISTANCE = 25


def detect_launcher_state(
    frame_roi_bgr: np.ndarray,
    frog_pivot: Point,
    template_set: LauncherTemplateSet,
) -> LauncherState:
    """Detect launcher angle and visible ball colors from a game ROI."""
    live_roi = _extract_launcher_search_roi(frame_roi_bgr, frog_pivot, template_set.search_radius)
    if live_roi is None or not template_set.templates:
        return _unknown_launcher_state()

    live_gray = to_gray(live_roi)
    best_angle, min_error = _find_best_launcher_angle(live_gray, template_set)
    if best_angle is None or min_error is None:
        return _unknown_launcher_state()

    angle_radians = math.radians(best_angle)
    current_x = int(frog_pivot.x + CURRENT_BALL_DISTANCE * math.sin(angle_radians))
    current_y = int(frog_pivot.y + CURRENT_BALL_DISTANCE * math.cos(angle_radians))
    next_x = int(frog_pivot.x - NEXT_BALL_DISTANCE * math.sin(angle_radians))
    next_y = int(frog_pivot.y - NEXT_BALL_DISTANCE * math.cos(angle_radians))

    return LauncherState(
        current_ball=classify_entity_color(frame_roi_bgr, current_x, current_y, radius=13),
        next_ball=classify_entity_color(frame_roi_bgr, next_x, next_y, radius=8),
        next_position=Point(x=float(next_x), y=float(next_y)),
        angle_degrees=float(best_angle),
        confidence=max(0.0, 1.0 - min_error / 255.0),
    )


def _extract_launcher_search_roi(
    frame_roi_bgr: np.ndarray,
    frog_pivot: Point,
    search_radius: int,
) -> np.ndarray | None:
    expected_size = search_radius * 2
    height, width = frame_roi_bgr.shape[:2]
    y1 = max(0, int(frog_pivot.y) - search_radius)
    y2 = min(height, int(frog_pivot.y) + search_radius)
    x1 = max(0, int(frog_pivot.x) - search_radius)
    x2 = min(width, int(frog_pivot.x) + search_radius)
    live_roi = frame_roi_bgr[y1:y2, x1:x2].copy()
    if live_roi.size == 0 or live_roi.shape[:2] != (expected_size, expected_size):
        return None
    return live_roi


def _find_best_launcher_angle(
    live_gray: np.ndarray,
    template_set: LauncherTemplateSet,
) -> tuple[int | None, float | None]:
    min_error = float("inf")
    best_angle: int | None = None
    for angle, template in template_set.templates.items():
        if template.gray.shape != live_gray.shape:
            continue
        valid_pixels = template.match_mask > 0
        valid_count = np.count_nonzero(valid_pixels)
        if valid_count == 0:
            continue

        diff = cv2.absdiff(live_gray, template.gray)
        error = float(np.sum(diff[valid_pixels]) / valid_count)
        if error < min_error:
            min_error = error
            best_angle = angle

    if best_angle is None:
        return None, None
    return best_angle, min_error


def _unknown_launcher_state() -> LauncherState:
    return LauncherState(
        current_ball=UNKNOWN_COLOR,
        next_ball=UNKNOWN_COLOR,
        next_position=None,
        angle_degrees=None,
        confidence=None,
    )
