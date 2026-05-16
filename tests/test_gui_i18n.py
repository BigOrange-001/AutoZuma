from autozuma.gui.i18n import SUPPORTED_LANGUAGES, translate


def test_gui_i18n_supports_english_and_chinese():
    assert SUPPORTED_LANGUAGES == ("en", "zh")
    assert translate("en", "controls") == "Controls"
    assert translate("zh", "controls") == "控制"


def test_gui_i18n_falls_back_to_english_then_key():
    assert translate("missing", "controls") == "Controls"
    assert translate("zh", "unknown_key") == "unknown_key"
