"""Long-running live loop scaffolding for static AutoZuma sessions."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from autozuma.control.hotkeys import (
    HotkeyControlState,
    HotkeyEvents,
    HotkeyReader,
    Win32HotkeyReader,
    poll_hotkeys,
)
from autozuma.runtime.live import (
    LiveStaticSessionContext,
    LiveStaticSessionParams,
    run_live_static_session_frame,
)
from autozuma.runtime.session import (
    StaticSessionFrameResult,
    StaticSessionState,
    initial_static_session_state,
)


class LoopClock(Protocol):
    """Clock operations used by the live loop."""

    def time(self) -> float:
        """Return wall-clock seconds."""

    def perf_counter(self) -> float:
        """Return monotonic timing seconds for frame pacing."""

    def sleep(self, seconds: float) -> None:
        """Sleep for the requested number of seconds."""


@dataclass(frozen=True)
class SystemClock:
    """Default clock backed by Python's time module."""

    def time(self) -> float:
        return time.time()

    def perf_counter(self) -> float:
        return time.perf_counter()

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)


@dataclass(frozen=True)
class LiveLoopParams:
    """Parameters for the long-running static live loop."""

    live: LiveStaticSessionParams
    target_fps: float = 10.0
    idle_sleep_seconds: float = 0.001


@dataclass(frozen=True)
class LiveLoopState:
    """Mutable-at-the-edge state threaded through the live loop."""

    session: StaticSessionState
    hotkeys: HotkeyControlState = HotkeyControlState()


@dataclass(frozen=True)
class LiveLoopIterationResult:
    """Result for one loop iteration."""

    state: LiveLoopState
    hotkey_events: HotkeyEvents
    frame_result: StaticSessionFrameResult | None = None


@dataclass(frozen=True)
class LiveLoopRunResult:
    """Summary returned when a bounded loop run exits."""

    state: LiveLoopState
    iterations: int
    last_frame_result: StaticSessionFrameResult | None = None


def initial_live_loop_state() -> LiveLoopState:
    """Return loop state equivalent to a safe, not-yet-detected prototype session."""
    return LiveLoopState(session=initial_static_session_state())


def run_live_loop_iteration(
    *,
    context: LiveStaticSessionContext,
    state: LiveLoopState,
    params: LiveLoopParams,
    hotkey_reader: HotkeyReader,
    clock: LoopClock,
) -> LiveLoopIterationResult:
    """Run one paced live loop iteration."""
    poll_result = poll_hotkeys(state.hotkeys, hotkey_reader)
    session_state = state.session
    if poll_result.events.armed_reset_requested:
        session_state = initial_static_session_state()

    frame_result: StaticSessionFrameResult | None = None
    if poll_result.state.is_armed:
        frame_result = run_live_static_session_frame(
            context=context,
            state=session_state,
            current_time=clock.time(),
            params=params.live,
        )
        session_state = frame_result.state
    else:
        clock.sleep(params.idle_sleep_seconds)

    return LiveLoopIterationResult(
        state=LiveLoopState(session=session_state, hotkeys=poll_result.state),
        hotkey_events=poll_result.events,
        frame_result=frame_result,
    )


def run_live_loop(
    *,
    context: LiveStaticSessionContext,
    params: LiveLoopParams,
    initial_state: LiveLoopState | None = None,
    hotkey_reader: HotkeyReader | None = None,
    clock: LoopClock | None = None,
    max_iterations: int | None = None,
    should_stop: Callable[[LiveLoopIterationResult], bool] | None = None,
) -> LiveLoopRunResult:
    """Run the static live loop until a bound or stop predicate exits."""
    if params.target_fps <= 0:
        raise ValueError("target_fps must be positive")
    if max_iterations is not None and max_iterations < 0:
        raise ValueError("max_iterations cannot be negative")

    active_state = initial_state or initial_live_loop_state()
    active_hotkeys = hotkey_reader or Win32HotkeyReader()
    active_clock = clock or SystemClock()
    frame_delay = 1.0 / params.target_fps
    iterations = 0
    last_frame_result: StaticSessionFrameResult | None = None

    while max_iterations is None or iterations < max_iterations:
        start_time = active_clock.perf_counter()
        iteration_result = run_live_loop_iteration(
            context=context,
            state=active_state,
            params=params,
            hotkey_reader=active_hotkeys,
            clock=active_clock,
        )
        active_state = iteration_result.state
        if iteration_result.frame_result is not None:
            last_frame_result = iteration_result.frame_result
        iterations += 1

        elapsed = active_clock.perf_counter() - start_time
        active_clock.sleep(max(0.001, frame_delay - elapsed))

        if should_stop is not None and should_stop(iteration_result):
            break

    return LiveLoopRunResult(
        state=active_state,
        iterations=iterations,
        last_frame_result=last_frame_result,
    )
