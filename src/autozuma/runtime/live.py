"""Single-frame live static session adapter."""

from __future__ import annotations

from dataclasses import dataclass

from autozuma.assets.registry import load_asset_registry
from autozuma.control.capture import capture_window_frame
from autozuma.control.win32_executor import Win32CommandExecutor, find_game_window
from autozuma.core.models import AssetRegistry, LauncherTemplateSet
from autozuma.runtime.session import (
    StaticSessionFrameResult,
    StaticSessionParams,
    StaticSessionState,
    run_static_session_frame,
)
from autozuma.vision.launcher_templates import build_launcher_template_set


@dataclass(frozen=True)
class LiveStaticSessionParams:
    """Parameters for one live static-session frame."""

    session: StaticSessionParams
    window_title: str = "zuma deluxe"
    use_virtual_mouse: bool = False


@dataclass(frozen=True)
class LiveStaticSessionContext:
    """Loaded assets and templates shared across live frames."""

    registry: AssetRegistry
    launcher_templates: LauncherTemplateSet


def build_live_static_session_context() -> LiveStaticSessionContext:
    """Load assets and launcher templates for live static-session execution."""
    registry = load_asset_registry()
    return LiveStaticSessionContext(
        registry=registry,
        launcher_templates=build_launcher_template_set(registry.templates.launcher_frog),
    )


def run_live_static_session_frame(
    *,
    context: LiveStaticSessionContext,
    state: StaticSessionState,
    current_time: float,
    params: LiveStaticSessionParams,
) -> StaticSessionFrameResult:
    """Capture one game-window frame and run the static session adapter."""
    hwnd, rect = find_game_window(params.window_title)
    frame_bgr = capture_window_frame(rect)
    driver = Win32CommandExecutor(
        hwnd=hwnd,
        rect=rect,
        use_virtual=params.use_virtual_mouse,
    )
    return run_static_session_frame(
        frame_bgr=frame_bgr,
        registry=context.registry,
        launcher_templates=context.launcher_templates,
        state=state,
        current_time=current_time,
        params=params.session,
        driver=driver,
    )
