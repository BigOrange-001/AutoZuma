"""Load migrated topology assets into explicit data models."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from autozuma.assets.paths import AssetPaths
from autozuma.core.models import InvalidTopologyError, LevelTopology, Point, TrackControlPoint

SPECIAL_DETECTION_LEVEL_IDS = frozenset({"space"})


def load_topology_file(path: Path) -> LevelTopology:
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except OSError as exc:
        raise InvalidTopologyError(f"Cannot read topology file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise InvalidTopologyError(f"Invalid JSON in topology file: {path}") from exc

    if not isinstance(data, dict):
        raise InvalidTopologyError(f"Topology root must be an object: {path}")

    level_id = path.stem
    requires_special_detection = level_id.lower() in SPECIAL_DETECTION_LEVEL_IDS
    return LevelTopology(
        level_id=level_id,
        frog_pivot=_parse_point(data.get("frog_pivot"), "frog_pivot", path),
        tracks=_parse_tracks(data, path),
        treasure_points=_parse_points(data.get("treasure_points", []), "treasure_points", path),
        source_path=path,
        has_static_background=not requires_special_detection,
        requires_special_detection=requires_special_detection,
    )


def load_all_topologies(paths: AssetPaths) -> dict[str, LevelTopology]:
    if not paths.level_topology.exists():
        raise InvalidTopologyError(f"Topology directory does not exist: {paths.level_topology}")

    topologies: dict[str, LevelTopology] = {}
    for path in sorted(paths.level_topology.glob("*.json")):
        topology = load_topology_file(path)
        key = topology.level_id.lower()
        if key in topologies:
            raise InvalidTopologyError(f"Duplicate topology level id: {topology.level_id}")
        topologies[key] = topology
    return topologies


def _parse_tracks(data: dict[str, Any], path: Path) -> tuple[tuple[TrackControlPoint, ...], ...]:
    track_keys = sorted(
        (key for key in data if re.fullmatch(r"track_\d+", key)),
        key=lambda key: int(key.split("_", 1)[1]),
    )

    if track_keys:
        tracks = tuple(
            _parse_control_points(data[key].get("control_points"), f"{key}.control_points", path)
            for key in track_keys
        )
    elif "control_points" in data:
        tracks = (_parse_control_points(data.get("control_points"), "control_points", path),)
    else:
        raise InvalidTopologyError(f"Topology has no control points: {path}")

    if not tracks:
        raise InvalidTopologyError(f"Topology has no tracks: {path}")
    return tracks


def _parse_control_points(value: Any, field: str, path: Path) -> tuple[TrackControlPoint, ...]:
    if not isinstance(value, list):
        raise InvalidTopologyError(f"{field} must be a list: {path}")

    points = []
    for index, item in enumerate(value):
        point = _parse_point(item, f"{field}[{index}]", path)
        flag = item.get("flag", 0) if isinstance(item, dict) else 0
        if not isinstance(flag, int):
            raise InvalidTopologyError(f"{field}[{index}].flag must be an integer: {path}")
        points.append(TrackControlPoint(x=point.x, y=point.y, flag=flag))

    if len(points) < 2:
        raise InvalidTopologyError(f"{field} must contain at least 2 points: {path}")
    return tuple(points)


def _parse_points(value: Any, field: str, path: Path) -> tuple[Point, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise InvalidTopologyError(f"{field} must be a list: {path}")
    return tuple(_parse_point(item, f"{field}[{index}]", path) for index, item in enumerate(value))


def _parse_point(value: Any, field: str, path: Path) -> Point:
    if not isinstance(value, dict):
        raise InvalidTopologyError(f"{field} must be an object: {path}")
    if "x" not in value or "y" not in value:
        raise InvalidTopologyError(f"{field} must contain x and y: {path}")
    x = value["x"]
    y = value["y"]
    if not isinstance(x, int | float) or not isinstance(y, int | float):
        raise InvalidTopologyError(f"{field}.x and {field}.y must be numeric: {path}")
    return Point(float(x), float(y))
