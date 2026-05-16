from autozuma.gui.settings import (
    GuiHotkeySettings,
    GuiSettings,
    load_gui_settings,
    save_gui_settings,
)


def test_load_gui_settings_returns_defaults_when_file_is_missing(tmp_path):
    settings = load_gui_settings(tmp_path / "missing.json")

    assert settings.hotkeys == GuiHotkeySettings()


def test_save_and_load_gui_settings_round_trip(tmp_path):
    path = tmp_path / "gui.json"
    settings = GuiSettings(
        hotkeys=GuiHotkeySettings(
            toggle_arm="Ctrl+F1",
            snapshot="Ctrl+F2",
            safe="Ctrl+F3",
        )
    )

    save_gui_settings(settings, path)

    assert load_gui_settings(path) == settings
