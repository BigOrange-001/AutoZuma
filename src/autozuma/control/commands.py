"""Command coordinate mapping utilities."""

from __future__ import annotations

from autozuma.core.models import Command, GameRoiResult, Point


def map_command_to_screen(command: Command, roi_result: GameRoiResult) -> Command:
    """Convert ROI-local command target points into screen-frame coordinates."""
    return Command(
        command_type=command.command_type,
        primary_target=_offset_point(command.primary_target, roi_result.offset),
        secondary_target=_offset_point(command.secondary_target, roi_result.offset),
        delay_ms=command.delay_ms,
    )


def _offset_point(point: Point | None, offset: Point) -> Point | None:
    if point is None:
        return None
    return Point(x=point.x + offset.x, y=point.y + offset.y)
