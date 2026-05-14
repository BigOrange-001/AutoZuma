import pytest

from autozuma.control.execution import (
    CommandExecutionError,
    ExecutionStep,
    ExecutionStepType,
    build_command_execution_plan,
    execute_plan,
)
from autozuma.core.models import Command, CommandType, Point


def test_build_plan_for_no_op_has_no_steps():
    plan = build_command_execution_plan(Command(command_type=CommandType.NO_OP))

    assert plan.steps == ()


def test_build_plan_for_shoot_clicks_primary_target():
    target = Point(x=12, y=34)

    plan = build_command_execution_plan(
        Command(command_type=CommandType.SHOOT, primary_target=target)
    )

    assert plan.steps == (ExecutionStep(ExecutionStepType.LEFT_CLICK, target=target),)


def test_build_plan_for_double_shoot_preserves_order_and_delay():
    primary = Point(x=10, y=20)
    secondary = Point(x=30, y=40)

    plan = build_command_execution_plan(
        Command(
            command_type=CommandType.DOUBLE_SHOOT,
            primary_target=primary,
            secondary_target=secondary,
            delay_ms=250,
        )
    )

    assert plan.steps == (
        ExecutionStep(ExecutionStepType.LEFT_CLICK, target=primary),
        ExecutionStep(ExecutionStepType.WAIT, delay_ms=250),
        ExecutionStep(ExecutionStepType.LEFT_CLICK, target=secondary),
    )


def test_build_plan_for_ui_click_uses_ui_click_step():
    target = Point(x=100, y=200)

    plan = build_command_execution_plan(
        Command(command_type=CommandType.UI_CLICK, primary_target=target)
    )

    assert plan.steps == (ExecutionStep(ExecutionStepType.UI_CLICK, target=target),)


def test_build_plan_for_swap_shoot_right_clicks_before_primary_target():
    target = Point(x=100, y=200)

    plan = build_command_execution_plan(
        Command(command_type=CommandType.SWAP_SHOOT, primary_target=target)
    )

    assert plan.steps == (
        ExecutionStep(ExecutionStepType.RIGHT_CLICK),
        ExecutionStep(ExecutionStepType.WAIT, delay_ms=150),
        ExecutionStep(ExecutionStepType.LEFT_CLICK, target=target),
    )


def test_build_plan_for_swap_double_shoot_preserves_all_prototype_timing():
    primary = Point(x=10, y=20)
    secondary = Point(x=30, y=40)

    plan = build_command_execution_plan(
        Command(
            command_type=CommandType.SWAP_DOUBLE_SHOOT,
            primary_target=primary,
            secondary_target=secondary,
            delay_ms=275,
        ),
        swap_delay_ms=125,
    )

    assert plan.steps == (
        ExecutionStep(ExecutionStepType.RIGHT_CLICK),
        ExecutionStep(ExecutionStepType.WAIT, delay_ms=125),
        ExecutionStep(ExecutionStepType.LEFT_CLICK, target=primary),
        ExecutionStep(ExecutionStepType.WAIT, delay_ms=275),
        ExecutionStep(ExecutionStepType.LEFT_CLICK, target=secondary),
    )


def test_build_plan_rejects_missing_required_targets():
    with pytest.raises(CommandExecutionError, match="primary target"):
        build_command_execution_plan(Command(command_type=CommandType.SHOOT))

    with pytest.raises(CommandExecutionError, match="secondary target"):
        build_command_execution_plan(
            Command(command_type=CommandType.DOUBLE_SHOOT, primary_target=Point(x=1, y=2))
        )


def test_execute_plan_dispatches_steps_to_driver():
    driver = _RecordingDriver()
    primary = Point(x=10, y=20)
    secondary = Point(x=30, y=40)
    plan = build_command_execution_plan(
        Command(
            command_type=CommandType.SWAP_DOUBLE_SHOOT,
            primary_target=primary,
            secondary_target=secondary,
            delay_ms=250,
        )
    )

    execute_plan(plan, driver)

    assert driver.calls == [
        ("right_click", None),
        ("wait", 150),
        ("left_click", primary),
        ("wait", 250),
        ("left_click", secondary),
    ]


class _RecordingDriver:
    def __init__(self):
        self.calls = []

    def left_click(self, target):
        self.calls.append(("left_click", target))

    def ui_click(self, target):
        self.calls.append(("ui_click", target))

    def right_click(self):
        self.calls.append(("right_click", None))

    def wait(self, delay_ms):
        self.calls.append(("wait", delay_ms))
