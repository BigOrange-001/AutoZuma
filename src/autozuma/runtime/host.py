"""Host-facing single-frame static runtime execution adapter."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from autozuma.control.execution import (
    ExecutionDriver,
    ExecutionPlan,
    build_command_execution_plan,
    execute_plan,
)
from autozuma.core.models import LevelRuntimeAssets, LauncherTemplateSet
from autozuma.runtime.static_runtime import (
    StaticRuntimeFrameParams,
    StaticRuntimeFrameResult,
    StaticRuntimeState,
    run_static_runtime_frame,
)


@dataclass(frozen=True)
class StaticHostFrameParams:
    """Parameters for one host-executed static runtime frame."""

    runtime: StaticRuntimeFrameParams
    swap_delay_ms: int = 150
    execute_commands: bool = True


@dataclass(frozen=True)
class StaticHostFrameResult:
    """Combined pure runtime output and host execution plan."""

    runtime: StaticRuntimeFrameResult
    execution_plan: ExecutionPlan

    @property
    def state(self) -> StaticRuntimeState:
        return self.runtime.state


def run_static_host_frame(
    *,
    frame_bgr: np.ndarray,
    level: LevelRuntimeAssets,
    launcher_templates: LauncherTemplateSet,
    state: StaticRuntimeState,
    current_time: float,
    params: StaticHostFrameParams,
    driver: ExecutionDriver,
) -> StaticHostFrameResult:
    """Run one static runtime frame and optionally execute its screen command."""
    runtime_result = run_static_runtime_frame(
        frame_bgr=frame_bgr,
        level=level,
        launcher_templates=launcher_templates,
        state=state,
        current_time=current_time,
        params=params.runtime,
    )
    execution_plan = build_command_execution_plan(
        runtime_result.decision.decision.screen_command,
        swap_delay_ms=params.swap_delay_ms,
    )
    if params.execute_commands:
        execute_plan(execution_plan, driver)

    return StaticHostFrameResult(
        runtime=runtime_result,
        execution_plan=execution_plan,
    )
