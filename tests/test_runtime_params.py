from autozuma.runtime.modes import RuntimeMode, RuntimeModeState
from autozuma.runtime.params import (
    RuntimeParameterResolver,
    resolve_ranked_priority,
    resolve_runtime_parameter,
)


def test_resolve_runtime_parameter_uses_mode_prefix():
    resolver = RuntimeParameterResolver(
        {
            "N_FIRE_COOLDOWN": 0.3,
            "R_FIRE_COOLDOWN": 0.5,
            "E_FIRE_COOLDOWN": 0.2,
        }
    )

    assert resolver.get("FIRE_COOLDOWN", RuntimeMode.NORMAL) == 0.3
    assert resolver.get("FIRE_COOLDOWN", RuntimeMode.RESCUE) == 0.5
    assert resolver.get("FIRE_COOLDOWN", RuntimeMode.ENDGAME) == 0.2


def test_resolve_runtime_parameter_accepts_runtime_mode_state():
    state = RuntimeModeState(is_rescue_mode=True, is_endgame_mode=True)

    value = resolve_runtime_parameter(
        {"R_M_GAP": 22.0, "E_M_GAP": 40.0},
        "M_GAP",
        state,
    )

    assert value == 22.0


def test_resolve_runtime_parameter_falls_back_to_unscoped_key_then_zero():
    resolver = RuntimeParameterResolver({"COIN_BREAK_DELAY": 0.25})

    assert resolver.get("COIN_BREAK_DELAY", RuntimeMode.RESCUE) == 0.25
    assert resolver.get("MISSING", RuntimeMode.NORMAL) == 0.0


def test_resolve_runtime_parameter_is_case_insensitive_for_ini_style_keys():
    resolver = RuntimeParameterResolver({"n_predict_mult": 0.055})

    assert resolver.get("PREDICT_MULT", RuntimeMode.NORMAL) == 0.055


def test_resolve_ranked_priority_preserves_prototype_weight_formula():
    value = resolve_ranked_priority(
        {"N_PRIO_COIN": 1.0, "R_PRIO_COIN": 4.0},
        "PRIO_COIN",
        RuntimeMode.RESCUE,
    )

    assert value == 100.0


def test_resolve_ranked_priority_truncates_float_rank_like_prototype():
    value = resolve_ranked_priority(
        {"N_PRIO_PAIR": 3.9},
        "PRIO_PAIR",
        RuntimeMode.NORMAL,
    )

    assert value == 1000.0
