"""Runtime controller used by the GUI shell."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from time import time

import numpy as np

from autozuma.runtime.debug import (
    DebugOutputResult,
    FileDebugOutputSink,
    render_static_session_overlay,
)
from autozuma.runtime.host import StaticHostFrameParams
from autozuma.runtime.live import (
    LiveStaticSessionContext,
    LiveStaticSessionParams,
    build_live_static_session_context,
    run_live_static_session_frame,
)
from autozuma.runtime.session import StaticSessionParams
from autozuma.runtime.static_runtime import StaticRuntimeFrameParams
from autozuma.runtime.loop import LiveLoopState, initial_live_loop_state


@dataclass(frozen=True)
class GuiRuntimeSettings:
    """Settings supplied by the GUI for live control."""

    raw_values: Mapping[str, float]
    execute_commands: bool = False
    window_title: str = "zuma deluxe"
    fps: float = 10.0
    map_redetect_interval: float = 4.0
    level_min_confidence: float = 0.25
    debug_dir: Path = Path("debug")


@dataclass(frozen=True)
class GuiRuntimeStep:
    """Summary of one GUI-triggered runtime step."""

    state: LiveLoopState
    level_id: str | None
    command_type: str
    message: str
    commands_enabled: bool = False
    mouse_mode: str = "virtual"
    mode: str | None = None
    preview_bgr: np.ndarray | None = None


class GuiRuntimeController:
    """Small bridge from GUI controls to the existing live static adapter."""

    def __init__(
        self,
        *,
        context_factory: Callable[[], LiveStaticSessionContext] = build_live_static_session_context,
        frame_runner: Callable[..., object] = run_live_static_session_frame,
        clock: Callable[[], float] = time,
    ) -> None:
        self._context_factory = context_factory
        self._frame_runner = frame_runner
        self._clock = clock
        self._context: LiveStaticSessionContext | None = None
        self.state = initial_live_loop_state()
        self.is_armed = False

    def arm(self) -> None:
        """Arm frame processing and reset session detection state."""
        self.is_armed = True
        self.state = replace(initial_live_loop_state(), hotkeys=self.state.hotkeys)

    def safe(self) -> None:
        """Stop GUI-triggered frame processing."""
        self.is_armed = False

    def step(
        self,
        settings: GuiRuntimeSettings,
        *,
        debug_snapshot: bool = False,
    ) -> GuiRuntimeStep:
        """Run one live frame when armed."""
        if not self.is_armed and not debug_snapshot:
            return GuiRuntimeStep(
                state=self.state,
                level_id=self.state.session.level_id,
                command_type="NO_OP",
                message="safe",
            )

        if self._context is None:
            self._context = self._context_factory()

        preview_sink = _GuiPreviewSink(
            file_sink=FileDebugOutputSink(settings.debug_dir) if debug_snapshot else None
        )
        commands_enabled = settings.execute_commands and self.is_armed and not debug_snapshot
        result = self._frame_runner(
            context=self._context,
            state=self.state.session,
            current_time=self._clock(),
            params=_live_params(settings, execute_commands=commands_enabled),
            debug_output=preview_sink,
        )
        self.state = LiveLoopState(session=result.state, hotkeys=self.state.hotkeys)
        command_type = _command_type_from_result(result)
        return GuiRuntimeStep(
            state=self.state,
            level_id=result.state.level_id,
            command_type=command_type,
            message="snapshot" if debug_snapshot else "frame",
            commands_enabled=commands_enabled,
            mouse_mode="virtual" if bool(settings.raw_values.get("virtual_mouse", 0.0)) else "physical",
            mode=_mode_from_result(result),
            preview_bgr=preview_sink.preview_bgr,
        )


def _live_params(
    settings: GuiRuntimeSettings,
    *,
    execute_commands: bool,
) -> LiveStaticSessionParams:
    return LiveStaticSessionParams(
        session=StaticSessionParams(
            host=StaticHostFrameParams(
                runtime=StaticRuntimeFrameParams(raw_values=settings.raw_values),
                execute_commands=execute_commands,
            ),
            level_min_confidence=settings.level_min_confidence,
            map_redetect_interval=settings.map_redetect_interval,
        ),
        window_title=settings.window_title,
        use_virtual_mouse=bool(settings.raw_values.get("virtual_mouse", 0.0)),
    )


def _command_type_from_result(result: object) -> str:
    host_result = getattr(result, "host_result", None)
    if host_result is not None:
        return host_result.runtime.decision.decision.screen_command.command_type.value

    ui_result = getattr(result, "ui_result", None)
    if ui_result is not None:
        return ui_result.automation.command.command_type.value

    return "NO_OP"


def _mode_from_result(result: object) -> str | None:
    host_result = getattr(result, "host_result", None)
    if host_result is None:
        state = getattr(result, "state", None)
        phase = getattr(state, "phase", None)
        return getattr(phase, "value", None)

    mode_update = getattr(host_result.runtime, "mode_update", None)
    mode_state = getattr(mode_update, "state", None)
    mode = getattr(mode_state, "mode", None)
    return getattr(mode, "value", None)


class _GuiPreviewSink:
    def __init__(self, file_sink: FileDebugOutputSink | None = None) -> None:
        self._file_sink = file_sink
        self.preview_bgr: np.ndarray | None = None

    def write(
        self,
        *,
        frame_bgr: np.ndarray,
        session_result: object,
        current_time: float,
    ) -> DebugOutputResult | None:
        self.preview_bgr = render_static_session_overlay(frame_bgr, session_result)
        if self._file_sink is None:
            return None
        return self._file_sink.write(
            frame_bgr=frame_bgr,
            session_result=session_result,
            current_time=current_time,
        )
