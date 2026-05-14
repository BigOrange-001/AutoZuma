from types import SimpleNamespace

import numpy as np

from autozuma.control.execution import ExecutionStep, ExecutionStepType
from autozuma.core.models import Command, CommandType, Point
from autozuma.runtime.host import (
    StaticHostFrameParams,
    run_static_host_frame,
)
from autozuma.runtime.static_runtime import StaticRuntimeFrameParams


def test_run_static_host_frame_executes_runtime_screen_command(monkeypatch):
    frame = np.zeros((10, 10, 3), dtype=np.uint8)
    level = object()
    launcher_templates = object()
    state = object()
    runtime_params = StaticRuntimeFrameParams(raw_values={"n_fire_cooldown": 0.3})
    runtime_result = _runtime_result(
        state="next-state",
        command=Command(
            command_type=CommandType.SWAP_DOUBLE_SHOOT,
            primary_target=Point(x=10, y=20),
            secondary_target=Point(x=30, y=40),
            delay_ms=275,
        ),
    )
    calls = {}

    def fake_run_static_runtime_frame(**kwargs):
        calls["runtime"] = kwargs
        return runtime_result

    monkeypatch.setattr(
        "autozuma.runtime.host.run_static_runtime_frame",
        fake_run_static_runtime_frame,
    )
    driver = _RecordingDriver()

    result = run_static_host_frame(
        frame_bgr=frame,
        level=level,
        launcher_templates=launcher_templates,
        state=state,
        current_time=12.5,
        params=StaticHostFrameParams(
            runtime=runtime_params,
            swap_delay_ms=125,
        ),
        driver=driver,
    )

    assert calls["runtime"] == {
        "frame_bgr": frame,
        "level": level,
        "launcher_templates": launcher_templates,
        "state": state,
        "current_time": 12.5,
        "params": runtime_params,
    }
    assert result.runtime is runtime_result
    assert result.state == "next-state"
    assert result.execution_plan.steps == (
        ExecutionStep(ExecutionStepType.RIGHT_CLICK),
        ExecutionStep(ExecutionStepType.WAIT, delay_ms=125),
        ExecutionStep(ExecutionStepType.LEFT_CLICK, target=Point(x=10, y=20)),
        ExecutionStep(ExecutionStepType.WAIT, delay_ms=275),
        ExecutionStep(ExecutionStepType.LEFT_CLICK, target=Point(x=30, y=40)),
    )
    assert driver.calls == [
        ("right_click", None),
        ("wait", 125),
        ("left_click", Point(x=10, y=20)),
        ("wait", 275),
        ("left_click", Point(x=30, y=40)),
    ]


def test_run_static_host_frame_can_plan_without_executing(monkeypatch):
    runtime_result = _runtime_result(
        state="next-state",
        command=Command(command_type=CommandType.SHOOT, primary_target=Point(x=4, y=5)),
    )
    monkeypatch.setattr(
        "autozuma.runtime.host.run_static_runtime_frame",
        lambda **kwargs: runtime_result,
    )
    driver = _RecordingDriver()

    result = run_static_host_frame(
        frame_bgr=np.zeros((10, 10, 3), dtype=np.uint8),
        level=object(),
        launcher_templates=object(),
        state=object(),
        current_time=1.0,
        params=StaticHostFrameParams(
            runtime=StaticRuntimeFrameParams(raw_values={}),
            execute_commands=False,
        ),
        driver=driver,
    )

    assert result.execution_plan.steps == (
        ExecutionStep(ExecutionStepType.LEFT_CLICK, target=Point(x=4, y=5)),
    )
    assert driver.calls == []


def _runtime_result(state, command):
    return SimpleNamespace(
        state=state,
        decision=SimpleNamespace(
            decision=SimpleNamespace(screen_command=command),
        ),
    )


class _RecordingDriver:
    def __init__(self):
        self.calls = []

    def left_click(self, target):
        self.calls.append(("left_click", target))

    def ui_click(self, target):
        self.calls.append(("ui_click", target))

    def right_click(self):
        self.calls.append(("right_click", None))

    def wait(self, delay_ms):
        self.calls.append(("wait", delay_ms))
