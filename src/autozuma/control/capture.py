"""Screen capture helpers for host adapters."""

from __future__ import annotations

from typing import Any, Protocol

import numpy as np

from autozuma.control.win32_executor import WindowRect


class ScreenGrabber(Protocol):
    """Subset of the mss API used by capture helpers."""

    def grab(self, monitor: dict[str, int]) -> Any:
        """Capture the requested monitor rectangle."""


def capture_window_frame(rect: WindowRect, grabber: ScreenGrabber | None = None) -> np.ndarray:
    """Capture a client-window rectangle and return a BGR frame."""
    if grabber is not None:
        return _capture_with_grabber(rect, grabber)

    import mss

    with mss.mss() as screen:
        return _capture_with_grabber(rect, screen)


def _capture_with_grabber(rect: WindowRect, grabber: ScreenGrabber) -> np.ndarray:
    raw = np.asarray(
        grabber.grab(
            {
                "left": rect.left,
                "top": rect.top,
                "width": rect.width,
                "height": rect.height,
            }
        )
    )
    if raw.ndim != 3 or raw.shape[2] < 3:
        raise ValueError("captured frame must have at least three color channels")
    return raw[:, :, :3].copy()
