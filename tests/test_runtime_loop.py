from types import SimpleNamespace

import pytest

from autozuma.control.hotkeys import Hotkey, HotkeyControlState
from autozuma.runtime.live import LiveStaticSessionParams
from autozuma.runtime.loop import (
    LiveLoopParams,
    LiveLoopState,
    initial_live_loop_state,
    run_live_loop,
    run_live_loop_iteration,
)
from autozuma.runtime.session import StaticSessionParams, StaticSessionState
from autozuma.runtime.static_runtime import StaticRuntimeFrameParams
from autozuma.runtime.host import StaticHostFrameParams


def test_initial_live_loop_state_starts_safe_and_detecting():
    state = initial_live_loop_state()

    assert state.hotkeys == HotkeyControlState()
    assert state.session == StaticSessionState()


def test_iteration_sleeps_idle_when_not_armed(monkeypatch):
    calls = {}
    monkeypatch.setattr(
        "autozuma.runtime.loop.run_live_static_session_frame",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("live frame should not run")),
    )
    clock = _Clock()

    result = run_live_loop_iteration(
        context=object(),
        state=initial_live_loop_state(),
        params=_params(),
        hotkey_reader=_Reader({}),
        clock=clock,
    )

    assert calls == {}
    assert result.frame_result is None
    assert clock.sleeps == [0.001]
    assert result.state.hotkeys.is_armed is False


def test_iteration_arms_resets_session_and_runs_live_frame(monkeypatch):
    frame_result = SimpleNamespace(state=StaticSessionState(level_id="spiral"))
    calls = {}

    def fake_run_live_static_session_frame(**kwargs):
        calls["live"] = kwargs
        return frame_result

    monkeypatch.setattr(
        "autozuma.runtime.loop.run_live_static_session_frame",
        fake_run_live_static_session_frame,
    )
    stale_session = StaticSessionState(level_id="old")

    result = run_live_loop_iteration(
        context="context",
        state=LiveLoopState(session=stale_session),
        params=_params(),
        hotkey_reader=_Reader({Hotkey.F1: True}),
        clock=_Clock(wall_time=42.0),
    )

    assert calls["live"]["context"] == "context"
    assert calls["live"]["state"] == StaticSessionState()
    assert calls["live"]["current_time"] == 42.0
    assert result.frame_result is frame_result
    assert result.state.session == frame_result.state
    assert result.state.hotkeys.is_armed is True
    assert result.hotkey_events.armed_reset_requested is True


def test_iteration_forced_safe_stops_running_live_frame(monkeypatch):
    monkeypatch.setattr(
        "autozuma.runtime.loop.run_live_static_session_frame",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("live frame should not run")),
    )

    result = run_live_loop_iteration(
        context=object(),
        state=LiveLoopState(session=StaticSessionState(level_id="spiral"), hotkeys=HotkeyControlState(is_armed=True)),
        params=_params(),
        hotkey_reader=_Reader({Hotkey.F3: True}),
        clock=_Clock(),
    )

    assert result.state.hotkeys.is_armed is False
    assert result.state.session.level_id == "spiral"
    assert result.hotkey_events.forced_safe is True


def test_iteration_passes_debug_sink_to_live_frame_on_f2_edge(monkeypatch):
    debug_output = object()
    frame_result = SimpleNamespace(state=StaticSessionState(level_id="spiral"))
    calls = {}

    def fake_run_live_static_session_frame(**kwargs):
        calls["live"] = kwargs
        return frame_result

    monkeypatch.setattr(
        "autozuma.runtime.loop.run_live_static_session_frame",
        fake_run_live_static_session_frame,
    )

    result = run_live_loop_iteration(
        context="context",
        state=LiveLoopState(
            session=StaticSessionState(level_id="spiral"),
            hotkeys=HotkeyControlState(is_armed=True),
        ),
        params=_params(debug_output=debug_output),
        hotkey_reader=_Reader({Hotkey.F2: True}),
        clock=_Clock(wall_time=42.0),
    )

    assert calls["live"]["debug_output"] is debug_output
    assert result.hotkey_events.debug_requested is True


def test_run_live_loop_paces_iterations_and_returns_last_frame(monkeypatch):
    results = [
        SimpleNamespace(state=StaticSessionState(level_id="one")),
        SimpleNamespace(state=StaticSessionState(level_id="two")),
    ]
    calls = []

    def fake_run_live_static_session_frame(**kwargs):
        calls.append(kwargs)
        return results[len(calls) - 1]

    monkeypatch.setattr(
        "autozuma.runtime.loop.run_live_static_session_frame",
        fake_run_live_static_session_frame,
    )
    clock = _Clock(perf_times=[0.0, 0.02, 0.1, 0.11])

    result = run_live_loop(
        context="context",
        params=_params(target_fps=10.0),
        initial_state=LiveLoopState(session=StaticSessionState(), hotkeys=HotkeyControlState(is_armed=True)),
        hotkey_reader=_Reader({}),
        clock=clock,
        max_iterations=2,
    )

    assert result.iterations == 2
    assert result.last_frame_result is results[-1]
    assert result.state.session == results[-1].state
    assert len(calls) == 2
    assert clock.sleeps == pytest.approx([0.08, 0.09])


def test_run_live_loop_rejects_invalid_target_fps():
    with pytest.raises(ValueError, match="target_fps"):
        run_live_loop(
            context=object(),
            params=_params(target_fps=0),
            hotkey_reader=_Reader({}),
            clock=_Clock(),
            max_iterations=0,
        )


def _params(target_fps=10.0, debug_output=None) -> LiveLoopParams:
    return LiveLoopParams(
        live=LiveStaticSessionParams(
            session=StaticSessionParams(
                host=StaticHostFrameParams(
                    runtime=StaticRuntimeFrameParams(raw_values={}),
                    execute_commands=False,
                )
            )
        ),
        target_fps=target_fps,
        debug_output=debug_output,
    )


class _Reader:
    def __init__(self, pressed):
        self.pressed = pressed

    def is_pressed(self, hotkey):
        return self.pressed.get(hotkey, False)


class _Clock:
    def __init__(self, wall_time=1.0, perf_times=None):
        self.wall_time = wall_time
        self.perf_times = list(perf_times or [0.0, 0.0])
        self.sleeps = []

    def time(self):
        return self.wall_time

    def perf_counter(self):
        if self.perf_times:
            return self.perf_times.pop(0)
        return 0.0

    def sleep(self, seconds):
        self.sleeps.append(seconds)
