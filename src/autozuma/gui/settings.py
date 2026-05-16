"""Persistent GUI-only settings."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class GuiHotkeySettings:
    """Configurable GUI shortcut keys."""

    toggle_arm: str = "F1"
    snapshot: str = "F2"
    safe: str = "F3"


@dataclass(frozen=True)
class GuiSettings:
    """Settings that are not part of strategy runtime values."""

    hotkeys: GuiHotkeySettings = GuiHotkeySettings()


def default_gui_settings_path() -> Path:
    """Return the default local GUI settings path."""
    return Path(__file__).resolve().parents[3] / "config" / "gui_settings.json"


def load_gui_settings(path: Path | str | None = None) -> GuiSettings:
    """Load GUI settings, returning defaults when no settings file exists."""
    settings_path = Path(path) if path is not None else default_gui_settings_path()
    if not settings_path.exists():
        return GuiSettings()

    data = json.loads(settings_path.read_text(encoding="utf-8"))
    hotkey_data = data.get("hotkeys", {})
    defaults = GuiHotkeySettings()
    return GuiSettings(
        hotkeys=GuiHotkeySettings(
            toggle_arm=str(hotkey_data.get("toggle_arm", defaults.toggle_arm)),
            snapshot=str(hotkey_data.get("snapshot", defaults.snapshot)),
            safe=str(hotkey_data.get("safe", defaults.safe)),
        )
    )


def save_gui_settings(settings: GuiSettings, path: Path | str | None = None) -> None:
    """Save GUI settings as JSON."""
    settings_path = Path(path) if path is not None else default_gui_settings_path()
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(
        json.dumps(asdict(settings), indent=2),
        encoding="utf-8",
    )
