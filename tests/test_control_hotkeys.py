from autozuma.control.hotkeys import Hotkey, HotkeyControlState, poll_hotkeys


def test_poll_hotkeys_toggles_arm_on_f1_rising_edge():
    reader = _Reader({Hotkey.F1: True})

    result = poll_hotkeys(HotkeyControlState(), reader)

    assert result.state.is_armed is True
    assert result.events.toggled_arm is True
    assert result.events.armed_reset_requested is True


def test_poll_hotkeys_does_not_repeat_while_key_is_held():
    reader = _Reader({Hotkey.F1: True})
    state = HotkeyControlState(is_armed=True, previous_f1=True)

    result = poll_hotkeys(state, reader)

    assert result.state.is_armed is True
    assert result.events.toggled_arm is False
    assert result.events.armed_reset_requested is False


def test_poll_hotkeys_reports_debug_request_on_f2_edge():
    reader = _Reader({Hotkey.F2: True})

    result = poll_hotkeys(HotkeyControlState(is_armed=True), reader)

    assert result.state.is_armed is True
    assert result.events.debug_requested is True


def test_poll_hotkeys_forces_safe_on_f3_edge():
    reader = _Reader({Hotkey.F3: True})

    result = poll_hotkeys(HotkeyControlState(is_armed=True), reader)

    assert result.state.is_armed is False
    assert result.events.forced_safe is True


class _Reader:
    def __init__(self, pressed=None):
        self.pressed = pressed or {}

    def is_pressed(self, hotkey):
        return self.pressed.get(hotkey, False)
