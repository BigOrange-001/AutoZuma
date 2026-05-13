"""Convert selected strategy targets into command objects."""

from __future__ import annotations

from autozuma.core.models import Command, CommandType, Point, TargetCandidate


def command_for_selected_target(target: TargetCandidate | None) -> Command:
    """Return a basic shoot command for a selected target, or no-op without one."""
    if target is None:
        return Command(command_type=CommandType.NO_OP)

    return Command(
        command_type=CommandType.SHOOT,
        primary_target=Point(x=target.x, y=target.y),
    )
