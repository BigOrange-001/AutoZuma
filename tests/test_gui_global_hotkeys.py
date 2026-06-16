from autozuma.gui.global_hotkeys import GuiGlobalHotkeyPoller, _parse_shortcut
from autozuma.gui.settings import GuiHotkeySettings


def test_gui_global_hotkey_poller_reports_edges_only():
    reader = _Reader({"F1"})
    poller = GuiGlobalHotkeyPoller(reader)

    first = poller.poll()
    second = poller.poll()

    assert first.toggle_arm is True
    assert second.toggle_arm is False


def test_gui_global_hotkey_poller_maps_snapshot_and_safe():
    reader = _Reader({"F2", "F3"})
    poller = GuiGlobalHotkeyPoller(reader)

    events = poller.poll()

    assert events.toggle_debug_snapshots is True
    assert events.safe is True


def test_gui_global_hotkey_poller_updates_settings():
    reader = _Reader({"F4"})
    poller = GuiGlobalHotkeyPoller(reader)

    poller.update_settings(GuiHotkeySettings(toggle_arm="F4", snapshot="F5", safe="F6"))
    events = poller.poll()

    assert events.toggle_arm is True
    assert events.toggle_debug_snapshots is False
    assert events.safe is False


def test_parse_shortcut_supports_function_keys_and_modifiers():
    assert _parse_shortcut("F1") == (0x70,)
    assert _parse_shortcut("Ctrl+F2") == (0x11, 0x71)
    assert _parse_shortcut("Shift+Alt+F3") == (0x10, 0x12, 0x72)


def test_parse_shortcut_rejects_unknown_key():
    assert _parse_shortcut("NotAKey") is None


class _Reader:
    def __init__(self, pressed: set[str]) -> None:
        self.pressed = pressed

    def is_pressed(self, shortcut: str) -> bool:
        return shortcut in self.pressed
