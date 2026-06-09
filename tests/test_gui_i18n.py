from autozuma.gui.i18n import SUPPORTED_LANGUAGES, translate


def test_gui_i18n_supports_english_and_chinese():
    assert SUPPORTED_LANGUAGES == ("en", "zh")
    assert translate("en", "controls") == "Controls"
    assert translate("zh", "controls") == "控制"


def test_gui_i18n_falls_back_to_english_then_key():
    assert translate("missing", "controls") == "Controls"
    assert translate("zh", "unknown_key") == "unknown_key"


def test_gui_i18n_has_button_tooltips():
    for key in (
        "tip_arm",
        "tip_safe",
        "tip_snapshot",
        "tip_load_ini",
        "tip_save_preset",
        "tip_reset_defaults",
    ):
        assert translate("en", key) != key
        assert translate("zh", key) != key
