from pathlib import Path

import pytest

from autozuma.runtime.config import (
    DEFAULT_RUNTIME_VALUES,
    load_runtime_values,
    load_runtime_values_from_ini,
    parse_runtime_overrides,
)


def test_load_runtime_values_from_ini_reads_strategy_section_case_insensitively(tmp_path):
    config_path = tmp_path / "strategy.ini"
    config_path.write_text(
        "[STRATEGY]\nN_FIRE_COOLDOWN = 0.12\nvirtual_mouse = 0\n",
        encoding="utf-8",
    )

    values = load_runtime_values_from_ini(config_path)

    assert values["n_fire_cooldown"] == 0.12
    assert values["virtual_mouse"] == 0.0


def test_load_runtime_values_merges_defaults_ini_and_overrides(tmp_path):
    config_path = tmp_path / "strategy.ini"
    config_path.write_text(
        "[STRATEGY]\nn_fire_cooldown = 0.12\n",
        encoding="utf-8",
    )

    values = load_runtime_values(
        config_path,
        overrides={"N_FIRE_COOLDOWN": 0.5, "custom": 2.0},
    )

    assert values["n_fire_cooldown"] == 0.5
    assert values["custom"] == 2.0
    assert values["r_fire_cooldown"] == DEFAULT_RUNTIME_VALUES["r_fire_cooldown"]


def test_load_runtime_values_raises_for_missing_explicit_path(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_runtime_values(tmp_path / "missing.ini")


def test_load_runtime_values_rejects_non_numeric_ini_value(tmp_path):
    config_path = tmp_path / "strategy.ini"
    config_path.write_text("[STRATEGY]\nn_fire_cooldown = fast\n", encoding="utf-8")

    with pytest.raises(ValueError, match="n_fire_cooldown"):
        load_runtime_values_from_ini(config_path)


def test_parse_runtime_overrides_normalizes_keys_and_values():
    assert parse_runtime_overrides(["N_FIRE_COOLDOWN=0.3", "custom = 4"]) == {
        "n_fire_cooldown": 0.3,
        "custom": 4.0,
    }


def test_parse_runtime_overrides_rejects_bad_shape():
    with pytest.raises(ValueError, match="KEY=VALUE"):
        parse_runtime_overrides(["n_fire_cooldown"])


def test_default_runtime_values_match_bundled_strategy_file():
    bundled_path = Path(__file__).resolve().parents[1] / "config" / "strategy_v1_plus.ini"
    if not bundled_path.exists():
        return

    values = load_runtime_values_from_ini(bundled_path)

    assert values["n_fire_cooldown"] == DEFAULT_RUNTIME_VALUES["n_fire_cooldown"]
