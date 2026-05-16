from pathlib import Path
from types import SimpleNamespace

import numpy as np

from autozuma.core.models import (
    AssetRegistry,
    Command,
    CommandType,
    ImageAsset,
    LauncherTemplateSet,
    LevelDetectionResult,
    LevelGeometry,
    LevelRuntimeAssets,
    LevelTopology,
    Point,
    TemplateAssets,
)
from autozuma.runtime.ui import UiAutomationFrameResult, UiAutomationState
from autozuma.runtime.host import StaticHostFrameParams
from autozuma.runtime.session import (
    StaticSessionParams,
    StaticSessionPhase,
    StaticSessionState,
    initial_static_session_state,
    run_static_session_frame,
)
from autozuma.runtime.static_runtime import StaticRuntimeFrameParams, initial_static_runtime_state


def test_initial_static_session_state_starts_detecting():
    state = initial_static_session_state()

    assert state.phase == StaticSessionPhase.DETECTING
    assert state.level_id is None
    assert state.runtime_state is None


def test_detecting_state_initializes_level_without_running_host(monkeypatch):
    frame = np.zeros((10, 10, 3), dtype=np.uint8)
    registry = _registry("spiral")

    monkeypatch.setattr(
        "autozuma.runtime.session.detect_static_level",
        lambda frame_bgr, registry, min_confidence: LevelDetectionResult(
            level_id="spiral",
            confidence=0.99,
            match_location=Point(x=0, y=0),
        ),
    )
    monkeypatch.setattr(
        "autozuma.runtime.session.run_static_host_frame",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("host should not run")),
    )

    result = run_static_session_frame(
        frame_bgr=frame,
        registry=registry,
        launcher_templates=_launcher_templates(),
        state=initial_static_session_state(),
        current_time=10.0,
        params=_params(),
        driver=_Driver(),
    )

    assert result.state.phase == StaticSessionPhase.PLAYING
    assert result.state.level_id == "spiral"
    assert result.state.runtime_state == initial_static_runtime_state(10.0)
    assert result.state.last_map_detect_time == 10.0
    assert result.detection_result.level_id == "spiral"
    assert result.host_result is None
    assert result.level_changed is True


def test_detecting_state_stays_detecting_without_match(monkeypatch):
    monkeypatch.setattr(
        "autozuma.runtime.session.detect_static_level",
        lambda frame_bgr, registry, min_confidence: None,
    )
    state = initial_static_session_state()

    result = run_static_session_frame(
        frame_bgr=np.zeros((10, 10, 3), dtype=np.uint8),
        registry=_registry("spiral"),
        launcher_templates=_launcher_templates(),
        state=state,
        current_time=10.0,
        params=_params(),
        driver=_Driver(),
    )

    assert result.state == state
    assert result.detection_result is None
    assert result.host_result is None
    assert result.level_changed is False


def test_playing_state_runs_host_without_redetect_before_interval(monkeypatch):
    runtime_state = initial_static_runtime_state(1.0)
    host_result = SimpleNamespace(state=initial_static_runtime_state(12.0))
    calls = {}

    monkeypatch.setattr(
        "autozuma.runtime.session.detect_static_level",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("redetect should not run")),
    )

    def fake_run_static_host_frame(**kwargs):
        calls["host"] = kwargs
        return host_result

    monkeypatch.setattr("autozuma.runtime.session.run_static_host_frame", fake_run_static_host_frame)

    result = run_static_session_frame(
        frame_bgr=np.zeros((10, 10, 3), dtype=np.uint8),
        registry=_registry("spiral"),
        launcher_templates=_launcher_templates(),
        state=StaticSessionState(
            phase=StaticSessionPhase.PLAYING,
            level_id="spiral",
            runtime_state=runtime_state,
            last_map_detect_time=10.0,
        ),
        current_time=13.0,
        params=_params(),
        driver=_Driver(),
    )

    assert calls["host"]["level"].level_id == "spiral"
    assert calls["host"]["state"] == runtime_state
    assert result.host_result is host_result
    assert result.state.runtime_state == host_result.state
    assert result.state.last_map_detect_time == 10.0
    assert result.level_changed is False


def test_playing_state_redetects_and_resets_when_level_changes(monkeypatch):
    new_runtime_state = initial_static_runtime_state(20.0)
    host_result = SimpleNamespace(state=new_runtime_state)
    calls = {}

    monkeypatch.setattr(
        "autozuma.runtime.session.detect_static_level",
        lambda frame_bgr, registry, min_confidence: LevelDetectionResult(
            level_id="coaster",
            confidence=0.99,
            match_location=Point(x=0, y=0),
        ),
    )

    def fake_run_static_host_frame(**kwargs):
        calls["host"] = kwargs
        return host_result

    monkeypatch.setattr("autozuma.runtime.session.run_static_host_frame", fake_run_static_host_frame)

    result = run_static_session_frame(
        frame_bgr=np.zeros((10, 10, 3), dtype=np.uint8),
        registry=_registry("spiral", "coaster"),
        launcher_templates=_launcher_templates(),
        state=StaticSessionState(
            phase=StaticSessionPhase.PLAYING,
            level_id="spiral",
            runtime_state=initial_static_runtime_state(1.0),
            last_map_detect_time=10.0,
        ),
        current_time=20.0,
        params=_params(),
        driver=_Driver(),
    )

    assert calls["host"]["level"].level_id == "coaster"
    assert calls["host"]["state"] == initial_static_runtime_state(20.0)
    assert result.state.level_id == "coaster"
    assert result.state.runtime_state == new_runtime_state
    assert result.state.last_map_detect_time == 20.0
    assert result.level_changed is True


def test_playing_state_refreshes_detection_time_when_same_level_is_seen(monkeypatch):
    host_result = SimpleNamespace(state=initial_static_runtime_state(20.0))
    monkeypatch.setattr(
        "autozuma.runtime.session.detect_static_level",
        lambda frame_bgr, registry, min_confidence: LevelDetectionResult(
            level_id="spiral",
            confidence=0.99,
            match_location=Point(x=0, y=0),
        ),
    )
    monkeypatch.setattr(
        "autozuma.runtime.session.run_static_host_frame",
        lambda **kwargs: host_result,
    )

    result = run_static_session_frame(
        frame_bgr=np.zeros((10, 10, 3), dtype=np.uint8),
        registry=_registry("spiral"),
        launcher_templates=_launcher_templates(),
        state=StaticSessionState(
            phase=StaticSessionPhase.PLAYING,
            level_id="spiral",
            runtime_state=initial_static_runtime_state(1.0),
            last_map_detect_time=10.0,
        ),
        current_time=20.0,
        params=_params(),
        driver=_Driver(),
    )

    assert result.state.level_id == "spiral"
    assert result.state.last_map_detect_time == 20.0
    assert result.level_changed is False


def test_ui_click_skips_gameplay_and_uses_ui_execution_plan(monkeypatch):
    frame = np.zeros((10, 10, 3), dtype=np.uint8)
    driver = _Driver()
    ui_state = UiAutomationState(last_poll_time=12.0, click_count=4, next_click_time=13.0)

    monkeypatch.setattr(
        "autozuma.runtime.session.run_ui_automation_frame",
        lambda **kwargs: UiAutomationFrameResult(
            state=ui_state,
            command=Command(CommandType.UI_CLICK, primary_target=Point(x=5, y=6)),
            should_skip_gameplay=True,
        ),
    )
    monkeypatch.setattr(
        "autozuma.runtime.session.detect_static_level",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("level detection should not run")),
    )
    monkeypatch.setattr(
        "autozuma.runtime.session.run_static_host_frame",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("host should not run")),
    )

    result = run_static_session_frame(
        frame_bgr=frame,
        registry=_registry("spiral"),
        launcher_templates=_launcher_templates(),
        state=StaticSessionState(
            phase=StaticSessionPhase.PLAYING,
            level_id="spiral",
            runtime_state=initial_static_runtime_state(1.0),
        ),
        current_time=13.0,
        params=_params(execute_commands=True),
        driver=driver,
    )

    assert result.host_result is None
    assert result.ui_result is not None
    assert result.ui_result.execution_plan.steps[0].target == Point(x=5, y=6)
    assert result.state.ui_state == ui_state
    assert driver.calls == [("ui_click", Point(x=5, y=6))]


def test_ui_automation_reset_returns_to_detecting_without_gameplay(monkeypatch):
    monkeypatch.setattr(
        "autozuma.runtime.session.run_ui_automation_frame",
        lambda **kwargs: UiAutomationFrameResult(
            state=UiAutomationState(last_poll_time=12.0),
            should_skip_gameplay=True,
            reset_session=True,
        ),
    )

    result = run_static_session_frame(
        frame_bgr=np.zeros((10, 10, 3), dtype=np.uint8),
        registry=_registry("spiral"),
        launcher_templates=_launcher_templates(),
        state=StaticSessionState(
            phase=StaticSessionPhase.PLAYING,
            level_id="spiral",
            runtime_state=initial_static_runtime_state(1.0),
        ),
        current_time=13.0,
        params=_params(),
        driver=_Driver(),
    )

    assert result.state.phase == StaticSessionPhase.DETECTING
    assert result.state.level_id is None
    assert result.state.runtime_state is None
    assert result.state.ui_state.last_poll_time == 12.0
    assert result.host_result is None


def _params(execute_commands=False) -> StaticSessionParams:
    return StaticSessionParams(
        host=StaticHostFrameParams(
            runtime=StaticRuntimeFrameParams(raw_values={}),
            execute_commands=execute_commands,
        )
    )


def _registry(*level_ids: str) -> AssetRegistry:
    return AssetRegistry(
        levels={level_id: _level(level_id) for level_id in level_ids},
        templates=TemplateAssets(
            launcher_frog=ImageAsset(path=Path("frog.png"), bgr=None, gray=None),
            ui={},
        ),
    )


def _level(level_id: str) -> LevelRuntimeAssets:
    return LevelRuntimeAssets(
        level_id=level_id,
        topology=LevelTopology(
            level_id=level_id,
            frog_pivot=Point(x=0, y=0),
            tracks=(),
            treasure_points=(),
            source_path=Path(f"{level_id}.json"),
        ),
        geometry=LevelGeometry(level_id=level_id, tracks=()),
        background=None,
    )


def _launcher_templates() -> LauncherTemplateSet:
    return LauncherTemplateSet(search_radius=1, step_degrees=5, templates={})


class _Driver:
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
