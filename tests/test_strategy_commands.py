from autozuma.core.models import CommandType, TargetCandidate
from autozuma.strategy.commands import command_for_selected_target


def test_command_for_selected_target_returns_no_op_without_target():
    command = command_for_selected_target(None)

    assert command.command_type == CommandType.NO_OP
    assert command.primary_target is None
    assert command.secondary_target is None
    assert command.delay_ms == 0


def test_command_for_selected_target_returns_shoot_at_candidate_point():
    target = TargetCandidate(x=123.0, y=45.0, score=10.0, target_type="ELIM")

    command = command_for_selected_target(target)

    assert command.command_type == CommandType.SHOOT
    assert command.primary_target.x == 123.0
    assert command.primary_target.y == 45.0
    assert command.secondary_target is None
    assert command.delay_ms == 0


def test_command_for_selected_target_returns_swap_shoot_when_requested():
    target = TargetCandidate(x=123.0, y=45.0, score=10.0, target_type="ELIM")

    command = command_for_selected_target(target, swap=True)

    assert command.command_type == CommandType.SWAP_SHOOT
    assert command.primary_target.x == 123.0
    assert command.primary_target.y == 45.0


def test_command_for_selected_target_returns_double_shoot_with_secondary_target():
    target = TargetCandidate(
        x=123.0,
        y=45.0,
        score=10.0,
        target_type="breakthrough_coin",
        secondary_x=200.0,
        secondary_y=150.0,
        delay_ms=250,
    )

    command = command_for_selected_target(target)

    assert command.command_type == CommandType.DOUBLE_SHOOT
    assert command.primary_target.x == 123.0
    assert command.primary_target.y == 45.0
    assert command.secondary_target.x == 200.0
    assert command.secondary_target.y == 150.0
    assert command.delay_ms == 250


def test_command_for_selected_target_returns_swap_double_shoot_when_requested():
    target = TargetCandidate(
        x=123.0,
        y=45.0,
        score=10.0,
        target_type="breakthrough_coin",
        secondary_x=200.0,
        secondary_y=150.0,
        delay_ms=250,
    )

    command = command_for_selected_target(target, swap=True)

    assert command.command_type == CommandType.SWAP_DOUBLE_SHOOT
    assert command.primary_target.x == 123.0
    assert command.primary_target.y == 45.0
    assert command.secondary_target.x == 200.0
    assert command.secondary_target.y == 150.0
    assert command.delay_ms == 250


def test_command_for_selected_target_rejects_incomplete_secondary_target():
    target = TargetCandidate(
        x=123.0,
        y=45.0,
        score=10.0,
        target_type="breakthrough_coin",
        secondary_x=200.0,
    )

    try:
        command_for_selected_target(target)
    except ValueError as exc:
        assert str(exc) == "secondary target requires both secondary_x and secondary_y"
    else:
        raise AssertionError("expected incomplete secondary target to be rejected")
