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


def test_gui_controller_runs_dry_run_frame_when_armed():
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
    assert calls["frame"]["params"].session.host.execute_commands is False
    assert calls["frame"]["params"].use_virtual_mouse is True
    assert result.level_id == "spiral"
    assert result.command_type == "shoot"
    assert result.commands_enabled is False
    assert result.mouse_mode == "virtual"


def test_gui_controller_can_enable_command_execution():
    calls = {}
    frame_result = SimpleNamespace(
        state=StaticSessionState(level_id=None),
        host_result=None,
        ui_result=None,
    )

    def frame_runner(**kwargs):
        calls["frame"] = kwargs
        return frame_result

    controller = GuiRuntimeController(
        context_factory=lambda: "context",
        frame_runner=frame_runner,
    )
    controller.arm()

    controller.step(GuiRuntimeSettings(raw_values={}, execute_commands=True))

    assert calls["frame"]["params"].session.host.execute_commands is True


def test_gui_controller_snapshot_forces_dry_run_even_when_execution_is_enabled():
    calls = {}
    frame_result = SimpleNamespace(
        state=StaticSessionState(level_id=None),
        host_result=None,
        ui_result=None,
    )

    def frame_runner(**kwargs):
        calls["frame"] = kwargs
        return frame_result

    controller = GuiRuntimeController(
        context_factory=lambda: "context",
        frame_runner=frame_runner,
    )
    controller.arm()

    result = controller.step(
        GuiRuntimeSettings(raw_values={}, execute_commands=True),
        debug_snapshot=True,
    )

    assert calls["frame"]["params"].session.host.execute_commands is False
    assert result.commands_enabled is False
    assert result.message == "snapshot"


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


def test_gui_controller_passes_debug_sink_for_snapshot():
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

    result = controller.step(GuiRuntimeSettings(raw_values={}), debug_snapshot=True)

    assert calls["debug_output"] is not None
    assert result.message == "snapshot"
