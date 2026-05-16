from autozuma.gui.schema import (
    GuiParameterKind,
    GuiParameterMode,
    build_gui_parameter_schema,
)
from autozuma.runtime.config import load_runtime_values


def test_gui_schema_reserves_all_runtime_config_keys():
    values = load_runtime_values()
    schema = build_gui_parameter_schema(values)
    schema_keys = {parameter.key for parameter in schema}

    assert set(values).issubset(schema_keys)


def test_gui_schema_groups_mode_scoped_parameters():
    schema = build_gui_parameter_schema()
    by_mode = {
        mode: [parameter for parameter in schema if parameter.mode is mode]
        for mode in (GuiParameterMode.NORMAL, GuiParameterMode.RESCUE, GuiParameterMode.ENDGAME)
    }

    assert len(by_mode[GuiParameterMode.NORMAL]) == len(by_mode[GuiParameterMode.RESCUE])
    assert len(by_mode[GuiParameterMode.RESCUE]) == len(by_mode[GuiParameterMode.ENDGAME])
    assert any(parameter.key == "n_fire_cooldown" for parameter in by_mode[GuiParameterMode.NORMAL])
    assert any(parameter.key == "r_prio_combo" for parameter in by_mode[GuiParameterMode.RESCUE])
    assert any(parameter.key == "e_predict_radius_th" for parameter in by_mode[GuiParameterMode.ENDGAME])


def test_gui_schema_marks_toggles_and_ranks_for_appropriate_controls():
    schema = {parameter.key: parameter for parameter in build_gui_parameter_schema()}

    assert schema["virtual_mouse"].kind is GuiParameterKind.TOGGLE
    assert schema["detailed_analysis"].kind is GuiParameterKind.TOGGLE
    assert schema["n_prio_coin"].kind is GuiParameterKind.RANK
    assert schema["n_fire_cooldown"].kind is GuiParameterKind.FLOAT
