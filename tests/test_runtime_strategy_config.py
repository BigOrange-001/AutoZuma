from autozuma.core.models import Point
from autozuma.runtime.modes import RuntimeModeState
from autozuma.runtime.strategy_config import build_runtime_strategy_config


def test_build_runtime_strategy_config_maps_normal_mode_values():
    config = build_runtime_strategy_config(
        _params(),
        RuntimeModeState(),
        active_coins=(Point(x=10.0, y=20.0),),
    )

    frame = config.frame_decision
    assert config.mode_params.rescue_distance_threshold == 410.0
    assert config.mode_params.endgame_spawn_distance_threshold == 155.0
    assert frame.target_selection.min_gap == 23.0
    assert frame.fallback_discard.min_gap == 23.0
    assert frame.target_prediction.predict_multiplier == 0.055
    assert frame.target_scoring.soft_lock_radius == 16.0
    assert frame.p_start_exclude == 128.0
    assert frame.p_end_exclude == 101.0
    assert frame.active_coins == (Point(x=10.0, y=20.0),)

    assert frame.coin_scoring.breakthrough_delay_ms == 250
    assert frame.coin_scoring.min_gap == 23.0
    assert frame.coin_scoring.coin_priority == 100000.0
    assert frame.target_scoring.combo_priority == 10000.0
    assert frame.target_scoring.rollback_elim_priority == 1000.0
    assert frame.target_scoring.elim_priority == 100.0
    assert frame.target_scoring.pair_priority == 10.0

    assert config.stateful_decision.outcome.fire_cooldown == 0.44
    assert config.stateful_decision.outcome.combo_hang_base == 0.2
    assert config.stateful_decision.outcome.combo_hang_mult == 0.0
    assert config.stateful_decision.outcome.breakthrough_delay == 0.25
    assert config.stateful_decision.swap_cooldown == 0.5


def test_build_runtime_strategy_config_uses_rescue_values_when_rescue_mode():
    config = build_runtime_strategy_config(
        _params(),
        RuntimeModeState(is_rescue_mode=True, is_endgame_mode=True),
    )

    frame = config.frame_decision
    assert frame.target_selection.min_gap == 22.0
    assert frame.target_prediction.predict_multiplier == 0.05
    assert frame.target_scoring.combo_priority == 100000.0
    assert frame.target_scoring.rollback_elim_priority == 10000.0
    assert frame.target_scoring.elim_priority == 1000.0
    assert frame.target_scoring.pair_priority == 100.0
    assert config.stateful_decision.outcome.fire_cooldown == 0.59


def test_build_runtime_strategy_config_uses_endgame_values_when_endgame_mode():
    config = build_runtime_strategy_config(
        _params(),
        RuntimeModeState(is_endgame_mode=True),
    )

    frame = config.frame_decision
    assert frame.target_selection.min_gap == 40.0
    assert frame.target_prediction.predict_multiplier == 0.025
    assert frame.target_scoring.combo_priority == 100000.0
    assert frame.target_scoring.rollback_elim_priority == 10000.0
    assert frame.target_scoring.elim_priority == 10000.0
    assert frame.target_scoring.pair_priority == 10000.0
    assert config.stateful_decision.outcome.fire_cooldown == 0.6


def test_build_runtime_strategy_config_falls_back_for_unscoped_general_values():
    values = _params() | {
        "coin_break_delay": 0.375,
        "rescue_th": 500.0,
        "endgame_spawn_th": 175.0,
        "track_start_exclude": 90.0,
        "track_end_exclude": 110.0,
    }

    config = build_runtime_strategy_config(values, RuntimeModeState(is_endgame_mode=True))

    assert config.mode_params.rescue_distance_threshold == 500.0
    assert config.mode_params.endgame_spawn_distance_threshold == 175.0
    assert config.frame_decision.p_start_exclude == 90.0
    assert config.frame_decision.p_end_exclude == 110.0
    assert config.frame_decision.coin_scoring.breakthrough_delay_ms == 375
    assert config.stateful_decision.outcome.breakthrough_delay == 0.375


def _params() -> dict[str, float]:
    return {
        "n_fire_cooldown": 0.44,
        "r_fire_cooldown": 0.59,
        "e_fire_cooldown": 0.6,
        "n_m_gap": 23.0,
        "r_m_gap": 22.0,
        "e_m_gap": 40.0,
        "n_combo_hang_base": 0.2,
        "r_combo_hang_base": 0.2,
        "e_combo_hang_base": 0.2,
        "n_combo_hang_mult": 0.0,
        "r_combo_hang_mult": 0.0,
        "e_combo_hang_mult": 0.0,
        "n_soft_lock_radius": 16.0,
        "r_soft_lock_radius": 17.0,
        "e_soft_lock_radius": 18.0,
        "n_predict_mult": 0.055,
        "r_predict_mult": 0.05,
        "e_predict_mult": 0.025,
        "n_prio_coin": 1.0,
        "r_prio_coin": 2.0,
        "e_prio_coin": 4.0,
        "n_prio_combo": 2.0,
        "r_prio_combo": 1.0,
        "e_prio_combo": 1.0,
        "n_prio_rollback_elim": 3.0,
        "r_prio_rollback_elim": 2.0,
        "e_prio_rollback_elim": 2.0,
        "n_prio_elim": 4.0,
        "r_prio_elim": 3.0,
        "e_prio_elim": 2.0,
        "n_prio_pair": 5.0,
        "r_prio_pair": 4.0,
        "e_prio_pair": 2.0,
        "coin_break_delay": 0.25,
        "rescue_th": 410.0,
        "endgame_spawn_th": 155.0,
        "track_start_exclude": 128.0,
        "track_end_exclude": 101.0,
    }
