"""Small GUI localization table."""

from __future__ import annotations

SUPPORTED_LANGUAGES = ("en", "zh")


TEXT: dict[str, dict[str, str]] = {
    "en": {
        "app_title": "AutoZuma Next",
        "preview_status": "Tuning panel preview - not connected",
        "safe": "SAFE",
        "dry_run": "DRY RUN",
        "config_loaded": "CONFIG LOADED",
        "language": "Language",
        "controls": "Controls",
        "arm": "Arm",
        "safe_button": "Safe",
        "snapshot": "Snapshot",
        "runtime": "Runtime",
        "window": "Window",
        "state": "State",
        "level": "Level",
        "mode": "Mode",
        "command": "Command",
        "presets": "Presets",
        "load_ini": "Load INI",
        "save_preset": "Save Preset",
        "reset_defaults": "Reset Defaults",
        "hotkeys": "Hotkeys",
        "toggle_arm": "Toggle",
        "snapshot_key": "Snapshot",
        "safe_key": "Safe",
        "preview": "Preview",
        "preview_placeholder": "capture / overlay",
        "event_log": "Event Log",
        "log_config_loaded": "config loaded",
        "log_gui_idle": "gui controls idle",
        "log_disconnected": "live loop disconnected",
        "tab_general": "General",
        "tab_normal": "Normal",
        "tab_rescue": "Rescue",
        "tab_endgame": "Endgame",
    },
    "zh": {
        "app_title": "AutoZuma Next",
        "preview_status": "调参面板预览 - 尚未接入运行时",
        "safe": "安全",
        "dry_run": "演练模式",
        "config_loaded": "配置已载入",
        "language": "语言",
        "controls": "控制",
        "arm": "启动",
        "safe_button": "安全",
        "snapshot": "截图",
        "runtime": "运行状态",
        "window": "窗口",
        "state": "状态",
        "level": "地图",
        "mode": "模式",
        "command": "命令",
        "presets": "预设",
        "load_ini": "读取 INI",
        "save_preset": "保存预设",
        "reset_defaults": "恢复默认",
        "hotkeys": "快捷键",
        "toggle_arm": "开关",
        "snapshot_key": "截图",
        "safe_key": "安全",
        "preview": "预览",
        "preview_placeholder": "画面 / 标注预览",
        "event_log": "事件日志",
        "log_config_loaded": "配置已载入",
        "log_gui_idle": "GUI 控件空闲",
        "log_disconnected": "运行循环未接入",
        "tab_general": "通用",
        "tab_normal": "普通",
        "tab_rescue": "救场",
        "tab_endgame": "收尾",
    },
}


def translate(language: str, key: str) -> str:
    """Return localized GUI text."""
    table = TEXT.get(language, TEXT["en"])
    return table.get(key, TEXT["en"].get(key, key))
