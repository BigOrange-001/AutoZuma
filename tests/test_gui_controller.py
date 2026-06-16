from types import SimpleNamespace

import numpy as np

from autozuma.core.models import CommandType
from autozuma.gui.controller import GuiRuntimeController, GuiRuntimeSettings
from autozuma.runtime.session import StaticSessionFrameResult, StaticSessionState


def test_gui_controller_stays_idle_while_safe():
    controller = GuiRuntimeController(
        context_factory=lambda: (_ for _ in ()).throw(AssertionError("context should not load")),
    )

    result = controller.step(GuiRuntimeSettings(raw_values={}))

    assert result.level_id is None
    assert result.command_type == "NO_OP"
    assert result.message == "safe"


def test_gui_controller_executes_frame_when_armed():
    calls = {}
    frame_result = SimpleNamespace(
        state=StaticSessionState(level_id="spiral"),
        host_result=SimpleNamespace(
            runtime=SimpleNamespace(
                decision=SimpleNamespace(
                    decision=SimpleNamespace(
                        screen_command=SimpleNamespace(command_type=CommandType.SHOOT)
                    )
                )
            )
        ),
        ui_result=None,
    )

    def frame_runner(**kwargs):
        calls["frame"] = kwargs
        return frame_result

    controller = GuiRuntimeController(
        context_factory=lambda: "context",
        frame_runner=frame_runner,
        clock=lambda: 42.0,
    )
    controller.arm()

    result = controller.step(GuiRuntimeSettings(raw_values={"virtual_mouse": 1.0}))

    assert calls["frame"]["context"] == "context"
    assert calls["frame"]["current_time"] == 42.0
    assert calls["frame"]["params"].session.host.execute_commands is True
    assert calls["frame"]["params"].use_virtual_mouse is True
    assert result.level_id == "spiral"
    assert result.command_type == "shoot"
    assert result.commands_enabled is True
    assert result.mouse_mode == "virtual"


def test_gui_controller_toggles_debug_snapshots_without_running_frame():
    controller = GuiRuntimeController(
        context_factory=lambda: (_ for _ in ()).throw(AssertionError("context should not load")),
        clock=lambda: 10.0,
    )

    assert controller.toggle_debug_snapshots() is True
    assert controller.debug_snapshots_enabled is True
    assert controller.toggle_debug_snapshots() is False
    assert controller.debug_snapshots_enabled is False


def test_gui_controller_periodic_debug_snapshot_waits_for_interval(tmp_path):
    calls = {}
    clock = {"now": 0.0}
    frame_result = StaticSessionFrameResult(state=StaticSessionState(level_id=None))

    def frame_runner(**kwargs):
        calls.setdefault("frames", []).append(kwargs)
        kwargs["debug_output"].write(
            frame_bgr=np.zeros((4, 5, 3), dtype=np.uint8),
            session_result=frame_result,
            current_time=kwargs["current_time"],
        )
        return frame_result

    controller = GuiRuntimeController(
        context_factory=lambda: "context",
        frame_runner=frame_runner,
        clock=lambda: clock["now"],
    )
    controller.arm()
    assert controller.toggle_debug_snapshots() is True

    clock["now"] = 9.9
    result = controller.step(GuiRuntimeSettings(raw_values={}, debug_dir=tmp_path))
    assert result.debug_snapshots_enabled is True
    assert result.debug_snapshot_saved is False
    assert result.message == "frame"

    clock["now"] = 10.0
    result = controller.step(GuiRuntimeSettings(raw_values={}, debug_dir=tmp_path))
    assert result.debug_snapshot_saved is True
    assert result.message == "frame+debug"
    assert any(tmp_path.iterdir())
    assert calls["frames"][-1]["params"].session.host.execute_commands is True
    assert result.commands_enabled is True


def test_gui_controller_periodic_debug_snapshot_does_not_run_while_safe():
    controller = GuiRuntimeController(
        context_factory=lambda: (_ for _ in ()).throw(AssertionError("context should not load")),
        clock=lambda: 0.0,
    )
    assert controller.toggle_debug_snapshots() is True

    result = controller.step(GuiRuntimeSettings(raw_values={}))

    assert result.commands_enabled is False
    assert result.debug_snapshots_enabled is True
    assert result.debug_snapshot_saved is False
    assert result.message == "safe"


def test_gui_controller_periodic_debug_snapshot_stops_after_toggle_off(tmp_path):
    clock = {"now": 0.0}
    frame_result = StaticSessionFrameResult(state=StaticSessionState(level_id=None))

    def frame_runner(**kwargs):
        kwargs["debug_output"].write(
            frame_bgr=np.zeros((4, 5, 3), dtype=np.uint8),
            session_result=frame_result,
            current_time=kwargs["current_time"],
        )
        return frame_result

    controller = GuiRuntimeController(
        context_factory=lambda: "context",
        frame_runner=frame_runner,
        clock=lambda: clock["now"],
    )
    controller.arm()
    controller.toggle_debug_snapshots()
    controller.toggle_debug_snapshots()

    clock["now"] = 20.0
    result = controller.step(GuiRuntimeSettings(raw_values={}, debug_dir=tmp_path))

    assert result.debug_snapshots_enabled is False
    assert result.debug_snapshot_saved is False
    assert not any(tmp_path.iterdir())


def test_gui_controller_returns_live_preview_frame():
    frame = np.full((4, 5, 3), 9, dtype=np.uint8)
    frame_result = StaticSessionFrameResult(state=StaticSessionState(level_id=None))

    def frame_runner(**kwargs):
        kwargs["debug_output"].write(
            frame_bgr=frame,
            session_result=frame_result,
            current_time=10.0,
        )
        return frame_result

    controller = GuiRuntimeController(
        context_factory=lambda: "context",
        frame_runner=frame_runner,
    )
    controller.arm()

    result = controller.step(GuiRuntimeSettings(raw_values={}))

    assert result.preview_bgr is not None
    assert np.array_equal(result.preview_bgr, frame)


def test_gui_controller_passes_preview_sink_for_frame():
    calls = {}
    frame_result = SimpleNamespace(
        state=StaticSessionState(level_id=None),
        host_result=None,
        ui_result=None,
    )

    def frame_runner(**kwargs):
        calls["debug_output"] = kwargs["debug_output"]
        return frame_result

    controller = GuiRuntimeController(
        context_factory=lambda: "context",
        frame_runner=frame_runner,
    )

    controller.arm()
    result = controller.step(GuiRuntimeSettings(raw_values={}))

    assert calls["debug_output"] is not None
    assert result.message == "frame"
