"""Build dense geometry from decoded level topology control points."""

from __future__ import annotations

import math

from autozuma.core.models import (
    LevelGeometry,
    LevelTopology,
    Point,
    TrackControlPoint,
    TrackGeometry,
)


def centripetal_catmull_rom(
    p0: Point,
    p1: Point,
    p2: Point,
    p3: Point,
    samples: int = 100,
) -> tuple[Point, ...]:
    """Interpolate a Catmull-Rom segment from p1 to p2."""

    if samples < 2:
        raise ValueError("samples must be at least 2")

    t0 = 0.0
    t1 = _next_t(t0, p0, p1)
    t2 = _next_t(t1, p1, p2)
    t3 = _next_t(t2, p2, p3)

    return tuple(
        _catmull_rom_point(p0, p1, p2, p3, t0, t1, t2, t3, t)
        for t in _linspace(t1, t2, samples)
    )


def build_track_geometry(
    track_id: int,
    control_points: tuple[TrackControlPoint, ...],
    samples_per_segment: int = 100,
) -> TrackGeometry:
    if len(control_points) < 2:
        raise ValueError("control_points must contain at least 2 points")

    extended = _extend_endpoints(control_points)
    dense_points: list[Point] = []
    for index in range(len(extended) - 3):
        segment = centripetal_catmull_rom(
            extended[index],
            extended[index + 1],
            extended[index + 2],
            extended[index + 3],
            samples=samples_per_segment,
        )
        dense_points.extend(segment)

    points = tuple(dense_points)
    return TrackGeometry(
        track_id=track_id,
        points=points,
        cumulative_distances=_cumulative_distances(points),
    )


def build_level_geometry(
    topology: LevelTopology,
    samples_per_segment: int = 100,
) -> LevelGeometry:
    return LevelGeometry(
        level_id=topology.level_id,
        tracks=tuple(
            build_track_geometry(track_id, track, samples_per_segment=samples_per_segment)
            for track_id, track in enumerate(topology.tracks)
        ),
    )


def _next_t(t_start: float, p_start: Point, p_end: Point) -> float:
    return t_start + math.sqrt(_distance(p_start, p_end))


def _distance(a: Point, b: Point) -> float:
    return math.hypot(b.x - a.x, b.y - a.y)


def _linspace(start: float, stop: float, count: int) -> tuple[float, ...]:
    if count == 1:
        return (start,)
    step = (stop - start) / (count - 1)
    return tuple(start + step * index for index in range(count))


def _catmull_rom_point(
    p0: Point,
    p1: Point,
    p2: Point,
    p3: Point,
    t0: float,
    t1: float,
    t2: float,
    t3: float,
    t: float,
) -> Point:
    a1 = _interpolate_point(p0, p1, t0, t1, t)
    a2 = _interpolate_point(p1, p2, t1, t2, t)
    a3 = _interpolate_point(p2, p3, t2, t3, t)
    b1 = _interpolate_point(a1, a2, t0, t2, t)
    b2 = _interpolate_point(a2, a3, t1, t3, t)
    return _interpolate_point(b1, b2, t1, t2, t)


def _interpolate_point(a: Point, b: Point, t_a: float, t_b: float, t: float) -> Point:
    denominator = t_b - t_a
    if abs(denominator) < 1e-9:
        return Point(a.x, a.y)
    left = (t_b - t) / denominator
    right = (t - t_a) / denominator
    return Point(left * a.x + right * b.x, left * a.y + right * b.y)


def _extend_endpoints(control_points: tuple[TrackControlPoint, ...]) -> tuple[Point, ...]:
    first = control_points[0]
    second = control_points[1]
    before_first = Point(2 * first.x - second.x, 2 * first.y - second.y)

    last = control_points[-1]
    before_last = control_points[-2]
    after_last = Point(2 * last.x - before_last.x, 2 * last.y - before_last.y)

    return (before_first, *control_points, after_last)


def _cumulative_distances(points: tuple[Point, ...]) -> tuple[float, ...]:
    if not points:
        return ()

    distances = [0.0]
    total = 0.0
    for previous, current in zip(points, points[1:]):
        total += _distance(previous, current)
        distances.append(total)
    return tuple(distances)
