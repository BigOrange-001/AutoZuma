"""Image loading helpers that work with Unicode paths on Windows."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from autozuma.core.models import AssetLoadError, ImageAsset


def read_bgr_image(path: Path) -> np.ndarray:
    try:
        buffer = np.fromfile(path, dtype=np.uint8)
    except OSError as exc:
        raise AssetLoadError(f"Cannot read image file: {path}") from exc

    image = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
    if image is None or image.size == 0:
        raise AssetLoadError(f"Image file is empty or unsupported: {path}")
    return image


def to_gray(image_bgr: np.ndarray) -> np.ndarray:
    if image_bgr.ndim != 3 or image_bgr.shape[2] != 3:
        raise AssetLoadError("Expected a BGR image with 3 channels.")
    return cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)


def load_image_asset(path: Path) -> ImageAsset:
    bgr = read_bgr_image(path)
    return ImageAsset(path=path, bgr=bgr, gray=to_gray(bgr))
