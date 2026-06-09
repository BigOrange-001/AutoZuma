from pathlib import Path

from autozuma.assets.paths import default_asset_paths
from autozuma.gui.controller import GuiRuntimeSettings
from autozuma.gui.settings import default_gui_settings_path
from autozuma.project_paths import project_path, project_root
from autozuma.runtime.config import default_config_path


def test_project_root_is_independent_of_current_working_directory(monkeypatch, tmp_path):
    expected_root = Path(__file__).resolve().parents[1]

    monkeypatch.chdir(tmp_path)

    assert project_root() == expected_root
    assert default_config_path() == project_path("config", "strategy_v1_plus.ini")
    assert default_gui_settings_path() == project_path("config", "gui_settings.json")
    assert default_asset_paths().root == project_path("assets")
    assert GuiRuntimeSettings(raw_values={}).debug_dir == project_path("debug")
