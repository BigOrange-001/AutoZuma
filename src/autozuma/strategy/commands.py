"""Convert selected strategy targets into command objects."""

from __future__ import annotations

from autozuma.core.models import Command, CommandType, Point, TargetCandidate


def command_for_selected_target(target: TargetCandidate | None, swap: bool = False) -> Command:
    """Return a shoot command for a selected target, or no-op without one."""
    if target is None:
        return Command(command_type=CommandType.NO_OP)

    secondary_target = _secondary_target(target)
    if secondary_target is not None:
        command_type = CommandType.SWAP_DOUBLE_SHOOT if swap else CommandType.DOUBLE_SHOOT
    else:
        command_type = CommandType.SWAP_SHOOT if swap else CommandType.SHOOT

    return Command(
        command_type=command_type,
        primary_target=Point(x=target.x, y=target.y),
        secondary_target=secondary_target,
        delay_ms=target.delay_ms if secondary_target is not None else 0,
    )


def _secondary_target(target: TargetCandidate) -> Point | None:
    if target.secondary_x is None and target.secondary_y is None:
        return None
    if target.secondary_x is None or target.secondary_y is None:
        raise ValueError("secondary target requires both secondary_x and secondary_y")
    return Point(x=target.secondary_x, y=target.secondary_y)
