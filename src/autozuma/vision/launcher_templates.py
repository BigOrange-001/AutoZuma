"""Launcher frog template generation."""

from __future__ import annotations

import cv2
import numpy as np

from autozuma.core.models import ImageAsset, LauncherTemplate, LauncherTemplateSet
from autozuma.vision.image_io import to_gray

DEFAULT_LAUNCHER_SEARCH_RADIUS = 50
DEFAULT_LAUNCHER_TEMPLATE_STEP_DEGREES = 5


def build_launcher_template_set(
    launcher_frog: ImageAsset,
    search_radius: int = DEFAULT_LAUNCHER_SEARCH_RADIUS,
    step_degrees: int = DEFAULT_LAUNCHER_TEMPLATE_STEP_DEGREES,
) -> LauncherTemplateSet:
    """Build rotated launcher templates from the migrated frog asset."""
    if search_radius <= 0:
        raise ValueError("search_radius must be positive.")
    if step_degrees <= 0 or 360 % step_degrees != 0:
        raise ValueError("step_degrees must be a positive divisor of 360.")

    roi_size = search_radius * 2
    aligned_gray = _align_launcher_to_roi(launcher_frog.bgr, roi_size, search_radius)
    _, base_mask = cv2.threshold(aligned_gray, 10, 255, cv2.THRESH_BINARY)
    erode_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    dilate_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))

    templates: dict[int, LauncherTemplate] = {}
    for angle in range(0, 360, step_degrees):
        rotation = cv2.getRotationMatrix2D((search_radius, search_radius), angle, 1.0)
        rotated_gray = cv2.warpAffine(aligned_gray, rotation, (roi_size, roi_size))
        rotated_mask = cv2.warpAffine(base_mask, rotation, (roi_size, roi_size))
        templates[angle] = LauncherTemplate(
            angle_degrees=angle,
            gray=rotated_gray,
            match_mask=cv2.erode(rotated_mask, erode_kernel, iterations=1),
            sub_mask=cv2.dilate(rotated_mask, dilate_kernel, iterations=1),
        )

    return LauncherTemplateSet(
        search_radius=search_radius,
        step_degrees=step_degrees,
        templates=templates,
    )


def _align_launcher_to_roi(
    launcher_frog_bgr: np.ndarray,
    roi_size: int,
    search_radius: int,
) -> np.ndarray:
    asset_height, asset_width = launcher_frog_bgr.shape[:2]
    translate_x = search_radius - asset_width // 2
    translate_y = search_radius - asset_height // 2
    alignment = np.float32([[1, 0, translate_x], [0, 1, translate_y]])
    aligned_bgr = cv2.warpAffine(launcher_frog_bgr, alignment, (roi_size, roi_size))
    return to_gray(aligned_bgr)
