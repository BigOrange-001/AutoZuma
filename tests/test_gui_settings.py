from autozuma.gui.settings import (
    GuiHotkeySettings,
    GuiSettings,
    load_gui_settings,
    save_gui_settings,
)


def test_load_gui_settings_returns_defaults_when_file_is_missing(tmp_path):
    settings = load_gui_settings(tmp_path / "missing.json")

    assert settings.language == "zh"
    assert settings.hotkeys == GuiHotkeySettings()


def test_save_and_load_gui_settings_round_trip(tmp_path):
    path = tmp_path / "gui.json"
    settings = GuiSettings(
        language="en",
        hotkeys=GuiHotkeySettings(
            toggle_arm="Ctrl+F1",
            snapshot="Ctrl+F2",
            safe="Ctrl+F3",
        )
    )

    save_gui_settings(settings, path)

    assert load_gui_settings(path) == settings


def test_load_gui_settings_rejects_unknown_language(tmp_path):
    path = tmp_path / "gui.json"
    path.write_text('{"language": "missing"}', encoding="utf-8")

    settings = load_gui_settings(path)

    assert settings.language == "zh"
