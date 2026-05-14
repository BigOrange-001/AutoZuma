from types import SimpleNamespace

from autozuma.control.win32_executor import WindowRect
from autozuma.runtime.live import (
    LiveStaticSessionContext,
    LiveStaticSessionParams,
    run_live_static_session_frame,
)
from autozuma.runtime.session import StaticSessionParams
from autozuma.runtime.static_runtime import StaticRuntimeFrameParams
from autozuma.runtime.host import StaticHostFrameParams


def test_run_live_static_session_frame_captures_window_and_runs_session(monkeypatch):
    context = LiveStaticSessionContext(registry=object(), launcher_templates=object())
    state = object()
    frame = object()
    session_result = object()
    calls = {}
    rect = WindowRect(left=1, top=2, width=3, height=4)

    monkeypatch.setattr(
        "autozuma.runtime.live.find_game_window",
        lambda title: (99, rect),
    )
    monkeypatch.setattr(
        "autozuma.runtime.live.capture_window_frame",
        lambda capture_rect: frame,
    )

    class FakeExecutor:
        def __init__(self, hwnd, rect, use_virtual):
            calls["executor"] = (hwnd, rect, use_virtual)

    def fake_run_static_session_frame(**kwargs):
        calls["session"] = kwargs
        return session_result

    monkeypatch.setattr("autozuma.runtime.live.Win32CommandExecutor", FakeExecutor)
    monkeypatch.setattr("autozuma.runtime.live.run_static_session_frame", fake_run_static_session_frame)

    params = LiveStaticSessionParams(
        session=StaticSessionParams(
            host=StaticHostFrameParams(runtime=StaticRuntimeFrameParams(raw_values={}))
        ),
        window_title="zuma deluxe",
        use_virtual_mouse=True,
    )

    result = run_live_static_session_frame(
        context=context,
        state=state,
        current_time=10.0,
        params=params,
    )

    assert result is session_result
    assert calls["executor"] == (99, rect, True)
    assert calls["session"] == {
        "frame_bgr": frame,
        "registry": context.registry,
        "launcher_templates": context.launcher_templates,
        "state": state,
        "current_time": 10.0,
        "params": params.session,
        "driver": None,
    } | {"driver": calls["session"]["driver"]}
    assert isinstance(calls["session"]["driver"], FakeExecutor)


def test_build_live_static_session_context_loads_registry_and_templates(monkeypatch):
    registry = SimpleNamespace(templates=SimpleNamespace(launcher_frog=object()))
    template_set = object()

    monkeypatch.setattr("autozuma.runtime.live.load_asset_registry", lambda: registry)
    monkeypatch.setattr(
        "autozuma.runtime.live.build_launcher_template_set",
        lambda launcher_frog: template_set,
    )

    from autozuma.runtime.live import build_live_static_session_context

    context = build_live_static_session_context()

    assert context.registry is registry
    assert context.launcher_templates is template_set
