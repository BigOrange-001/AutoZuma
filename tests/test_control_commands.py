import numpy as np

from autozuma.control.commands import map_command_to_screen
from autozuma.core.models import Command, CommandType, GameRoiResult, Point


def test_map_command_to_screen_preserves_no_op_without_targets():
    command = Command(command_type=CommandType.NO_OP)
    roi_result = _roi_result(offset=Point(x=20, y=30))

    mapped = map_command_to_screen(command, roi_result)

    assert mapped.command_type == CommandType.NO_OP
    assert mapped.primary_target is None
    assert mapped.secondary_target is None
    assert mapped.delay_ms == 0


def test_map_command_to_screen_offsets_primary_target():
    command = Command(
        command_type=CommandType.SHOOT,
        primary_target=Point(x=12, y=34),
        delay_ms=25,
    )
    roi_result = _roi_result(offset=Point(x=100, y=200))

    mapped = map_command_to_screen(command, roi_result)

    assert mapped.command_type == CommandType.SHOOT
    assert mapped.primary_target == Point(x=112, y=234)
    assert mapped.secondary_target is None
    assert mapped.delay_ms == 25


def test_map_command_to_screen_offsets_secondary_target():
    command = Command(
        command_type=CommandType.DOUBLE_SHOOT,
        primary_target=Point(x=10, y=20),
        secondary_target=Point(x=30, y=40),
        delay_ms=150,
    )
    roi_result = _roi_result(offset=Point(x=5, y=7))

    mapped = map_command_to_screen(command, roi_result)

    assert mapped.command_type == CommandType.DOUBLE_SHOOT
    assert mapped.primary_target == Point(x=15, y=27)
    assert mapped.secondary_target == Point(x=35, y=47)
    assert mapped.delay_ms == 150


def _roi_result(offset: Point) -> GameRoiResult:
    return GameRoiResult(
        frame=np.zeros((10, 10, 3), dtype=np.uint8),
        offset=offset,
        confidence=1.0,
    )
