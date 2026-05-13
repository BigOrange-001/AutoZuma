"""Shared data models used across the refactored AutoZuma codebase."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any


class AutoZumaError(Exception):
    """Base exception for AutoZuma Next."""


class AssetLoadError(AutoZumaError):
    """Raised when an asset cannot be loaded."""


class InvalidTopologyError(AssetLoadError):
    """Raised when a topology JSON file does not match the expected shape."""


class RoiExtractionError(AutoZumaError):
    """Raised when a game ROI cannot be extracted from a frame."""


@dataclass(frozen=True)
class Point:
    x: float
    y: float


@dataclass(frozen=True)
class TrackControlPoint(Point):
    flag: int = 0


@dataclass(frozen=True)
class LevelTopology:
    level_id: str
    frog_pivot: Point
    tracks: tuple[tuple[TrackControlPoint, ...], ...]
    treasure_points: tuple[Point, ...]
    source_path: Path
    has_static_background: bool = True
    requires_special_detection: bool = False


@dataclass(frozen=True)
class LevelAssetRef:
    level_id: str
    topology_path: Path
    background_path: Path | None
    requires_special_detection: bool = False


@dataclass(frozen=True)
class TrackGeometry:
    track_id: int
    points: tuple[Point, ...]
    cumulative_distances: tuple[float, ...]


@dataclass(frozen=True)
class LevelGeometry:
    level_id: str
    tracks: tuple[TrackGeometry, ...]


@dataclass(frozen=True)
class ImageAsset:
    path: Path
    bgr: Any
    gray: Any


@dataclass(frozen=True)
class LevelRuntimeAssets:
    level_id: str
    topology: LevelTopology
    geometry: LevelGeometry
    background: ImageAsset | None
    requires_special_detection: bool = False


@dataclass(frozen=True)
class TemplateAssets:
    launcher_frog: ImageAsset
    ui: dict[str, ImageAsset]


@dataclass(frozen=True)
class AssetRegistry:
    levels: dict[str, LevelRuntimeAssets]
    templates: TemplateAssets


@dataclass(frozen=True)
class LevelDetectionResult:
    level_id: str
    confidence: float
    match_location: Point


@dataclass(frozen=True)
class GameRoiResult:
    frame: Any
    offset: Point
    confidence: float


@dataclass(frozen=True)
class BallEntity:
    x: float
    y: float
    track_id: int
    track_idx: int
    color: str


@dataclass(frozen=True)
class Cluster:
    track_id: int
    color: str
    entities: tuple[BallEntity, ...]
    start_idx: int
    end_idx: int

    @property
    def size(self) -> int:
        return len(self.entities)


@dataclass(frozen=True)
class LauncherState:
    current_ball: str
    next_ball: str
    next_position: Point | None
    angle_degrees: float | None = None
    confidence: float | None = None


@dataclass(frozen=True)
class WorldState:
    level_id: str
    launcher: LauncherState
    entities: tuple[BallEntity, ...]
    clusters: tuple[Cluster, ...]


@dataclass(frozen=True)
class TargetCandidate:
    x: float
    y: float
    score: float
    target_type: str
    reason: str = ""


class CommandType(Enum):
    NO_OP = "no_op"
    SHOOT = "shoot"
    DOUBLE_SHOOT = "double_shoot"
    UI_CLICK = "ui_click"
    SWAP_SHOOT = "swap_shoot"
    SWAP_DOUBLE_SHOOT = "swap_double_shoot"


@dataclass(frozen=True)
class Command:
    command_type: CommandType
    primary_target: Point | None = None
    secondary_target: Point | None = None
    delay_ms: int = 0
