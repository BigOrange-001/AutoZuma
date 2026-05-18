"""Pure command execution planning and driver dispatch."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from autozuma.core.models import Command, CommandType, Point


class CommandExecutionError(ValueError):
    """Raised when a command cannot be converted into executable actions."""


class ExecutionStepType(Enum):
    LEFT_CLICK = "left_click"
    UI_CLICK = "ui_click"
    RIGHT_CLICK = "right_click"
    WAIT = "wait"


@dataclass(frozen=True)
class ExecutionStep:
    step_type: ExecutionStepType
    target: Point | None = None
    delay_ms: int = 0


@dataclass(frozen=True)
class ExecutionPlan:
    steps: tuple[ExecutionStep, ...]


class ExecutionDriver(Protocol):
    """Side-effect boundary consumed by execution plans."""

    def left_click(self, target: Point) -> None:
        """Shoot/click the game field at a captured-frame target."""

    def ui_click(self, target: Point) -> None:
        """Click a UI element at a captured-frame target."""

    def right_click(self) -> None:
        """Trigger the launcher swap action."""

    def wait(self, delay_ms: int) -> None:
        """Block for the requested command timing delay."""


def build_command_execution_plan(command: Command, swap_delay_ms: int = 150) -> ExecutionPlan:
    """Convert a pure command into ordered execution steps."""
    if swap_delay_ms < 0:
        raise CommandExecutionError("swap_delay_ms cannot be negative")
    if command.delay_ms < 0:
        raise CommandExecutionError("command delay_ms cannot be negative")

    match command.command_type:
        case CommandType.NO_OP:
            return ExecutionPlan(steps=())
        case CommandType.SHOOT:
            return ExecutionPlan(steps=(_left_click(command),))
        case CommandType.DOUBLE_SHOOT:
            return ExecutionPlan(
                steps=(
                    _left_click(command),
                    ExecutionStep(ExecutionStepType.WAIT, delay_ms=command.delay_ms),
                    _secondary_left_click(command),
                )
            )
        case CommandType.UI_CLICK:
            return ExecutionPlan(steps=(_ui_click(command),))
        case CommandType.SWAP_SHOOT:
            return ExecutionPlan(
                steps=(
                    ExecutionStep(ExecutionStepType.RIGHT_CLICK),
                    ExecutionStep(ExecutionStepType.WAIT, delay_ms=swap_delay_ms),
                    _left_click(command),
                )
            )
        case CommandType.SWAP_DOUBLE_SHOOT:
            return ExecutionPlan(
                steps=(
                    ExecutionStep(ExecutionStepType.RIGHT_CLICK),
                    ExecutionStep(ExecutionStepType.WAIT, delay_ms=swap_delay_ms),
                    _left_click(command),
                    ExecutionStep(ExecutionStepType.WAIT, delay_ms=command.delay_ms),
                    _secondary_left_click(command),
                )
            )


def execute_plan(plan: ExecutionPlan, driver: ExecutionDriver) -> None:
    """Run an execution plan through an explicit side-effect driver."""
    for step in plan.steps:
        match step.step_type:
            case ExecutionStepType.LEFT_CLICK:
                driver.left_click(_require_step_target(step))
            case ExecutionStepType.UI_CLICK:
                driver.ui_click(_require_step_target(step))
            case ExecutionStepType.RIGHT_CLICK:
                driver.right_click()
            case ExecutionStepType.WAIT:
                driver.wait(step.delay_ms)


def _left_click(command: Command) -> ExecutionStep:
    return ExecutionStep(ExecutionStepType.LEFT_CLICK, target=_require_primary(command))


def _secondary_left_click(command: Command) -> ExecutionStep:
    return ExecutionStep(ExecutionStepType.LEFT_CLICK, target=_require_secondary(command))


def _ui_click(command: Command) -> ExecutionStep:
    return ExecutionStep(ExecutionStepType.UI_CLICK, target=_require_primary(command))


def _require_primary(command: Command) -> Point:
    if command.primary_target is None:
        raise CommandExecutionError(f"{command.command_type.value} requires a primary target")
    return command.primary_target


def _require_secondary(command: Command) -> Point:
    if command.secondary_target is None:
        raise CommandExecutionError(f"{command.command_type.value} requires a secondary target")
    return command.secondary_target


def _require_step_target(step: ExecutionStep) -> Point:
    if step.target is None:
        raise CommandExecutionError(f"{step.step_type.value} step requires a target")
    return step.target
