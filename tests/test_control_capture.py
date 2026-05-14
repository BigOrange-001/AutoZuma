import numpy as np
import pytest

from autozuma.control.capture import capture_window_frame
from autozuma.control.win32_executor import WindowRect


def test_capture_window_frame_returns_bgr_copy_and_uses_rect_monitor():
    raw = np.zeros((4, 5, 4), dtype=np.uint8)
    raw[:, :, 0] = 10
    raw[:, :, 1] = 20
    raw[:, :, 2] = 30
    raw[:, :, 3] = 255
    grabber = _FakeGrabber(raw)

    frame = capture_window_frame(
        WindowRect(left=11, top=22, width=5, height=4),
        grabber=grabber,
    )

    assert grabber.monitors == [{"left": 11, "top": 22, "width": 5, "height": 4}]
    assert frame.shape == (4, 5, 3)
    assert np.array_equal(frame, raw[:, :, :3])
    assert not np.shares_memory(frame, raw)


def test_capture_window_frame_rejects_invalid_channel_shape():
    grabber = _FakeGrabber(np.zeros((4, 5), dtype=np.uint8))

    with pytest.raises(ValueError, match="at least three color channels"):
        capture_window_frame(WindowRect(left=0, top=0, width=5, height=4), grabber=grabber)


class _FakeGrabber:
    def __init__(self, frame):
        self.frame = frame
        self.monitors = []

    def grab(self, monitor):
        self.monitors.append(monitor)
        return self.frame
