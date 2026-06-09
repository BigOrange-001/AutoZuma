"""Runtime configuration loading for live AutoZuma adapters."""

from __future__ import annotations

import configparser
from collections.abc import Mapping
from pathlib import Path

from autozuma.project_paths import project_path


DEFAULT_RUNTIME_VALUES: dict[str, float] = {
    "n_fire_cooldown": 0.44,
    "r_fire_cooldown": 0.59,
    "e_fire_cooldown": 0.6,
    "n_m_gap": 23.23,
    "r_m_gap": 22.0,
    "e_m_gap": 40.0,
    "n_combo_hang_base": 0.2,
    "r_combo_hang_base": 0.2,
    "e_combo_hang_base": 0.2,
    "n_combo_hang_mult": 0.0,
    "r_combo_hang_mult": 0.0,
    "e_combo_hang_mult": 0.0,
    "n_soft_lock_radius": 15.0,
    "r_soft_lock_radius": 15.0,
    "e_soft_lock_radius": 15.0,
    "n_predict_mult": 0.055,
    "r_predict_mult": 0.05,
    "e_predict_mult": 0.025,
    "n_prio_coin": 1.0,
    "r_prio_coin": 2.0,
    "e_prio_coin": 4.0,
    "n_prio_combo": 2.0,
    "r_prio_combo": 1.0,
    "e_prio_combo": 1.0,
    "n_prio_rollback_elim": 4.0,
    "r_prio_rollback_elim": 2.0,
    "e_prio_rollback_elim": 2.0,
    "n_prio_elim": 5.0,
    "r_prio_elim": 3.0,
    "e_prio_elim": 2.0,
    "n_prio_pair": 3.0,
    "r_prio_pair": 4.0,
    "e_prio_pair": 2.0,
    "virtual_mouse": 1.0,
    "detailed_analysis": 1.0,
    "coin_break_delay": 0.25,
    "coin_hang_time": 0.3,
    "gap_priority_th": 300.0,
    "rescue_th": 400.0,
    "endgame_spawn_th": 152.08,
    "track_start_exclude": 128.12,
    "track_end_exclude": 100.0,
}


def default_config_path() -> Path:
    """Return the bundled prototype-compatible strategy config path when present."""
    return project_path("config", "strategy_v1_plus.ini")


def load_runtime_values(
    path: Path | str | None = None,
    overrides: Mapping[str, float] | None = None,
) -> dict[str, float]:
    """Load prototype-style runtime values from defaults, optional INI, and overrides."""
    values = dict(DEFAULT_RUNTIME_VALUES)
    config_path = Path(path) if path is not None else default_config_path()
    if config_path.exists():
        values.update(load_runtime_values_from_ini(config_path))
    elif path is not None:
        raise FileNotFoundError(config_path)

    if overrides:
        values.update(_normalize_mapping(overrides))
    return values


def load_runtime_values_from_ini(path: Path | str) -> dict[str, float]:
    """Load numeric strategy values from a prototype-compatible INI file."""
    config = configparser.ConfigParser()
    config.optionxform = str.lower
    read_files = config.read(path, encoding="utf-8")
    if not read_files:
        raise FileNotFoundError(path)

    section_name = "strategy" if config.has_section("strategy") else "STRATEGY"
    if not config.has_section(section_name):
        return {}

    values: dict[str, float] = {}
    for key, raw_value in config.items(section_name):
        try:
            values[key.lower()] = float(raw_value)
        except ValueError as exc:
            raise ValueError(f"config value {key!r} must be numeric") from exc
    return values


def save_runtime_values_to_ini(path: Path | str, values: Mapping[str, float]) -> None:
    """Save numeric runtime values to a prototype-compatible strategy INI file."""
    config = configparser.ConfigParser()
    config.optionxform = str.lower
    config["STRATEGY"] = {
        key.lower(): str(float(value))
        for key, value in sorted(_normalize_mapping(values).items())
    }
    config_path = Path(path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with config_path.open("w", encoding="utf-8") as file:
        config.write(file)


def parse_runtime_overrides(items: list[str] | tuple[str, ...]) -> dict[str, float]:
    """Parse CLI KEY=VALUE runtime overrides."""
    overrides: dict[str, float] = {}
    for item in items:
        if "=" not in item:
            raise ValueError(f"override {item!r} must use KEY=VALUE")
        key, raw_value = item.split("=", 1)
        key = key.strip().lower()
        if not key:
            raise ValueError(f"override {item!r} has an empty key")
        try:
            overrides[key] = float(raw_value)
        except ValueError as exc:
            raise ValueError(f"override {key!r} must be numeric") from exc
    return overrides


def _normalize_mapping(values: Mapping[str, float]) -> dict[str, float]:
    return {key.lower(): float(value) for key, value in values.items()}
