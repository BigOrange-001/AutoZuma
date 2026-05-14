"""Coin presence detection and explicit active-coin tracking state."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType

import cv2
import numpy as np

from autozuma.core.models import Point

FLOAT_EPSILON = 1e-9


@dataclass(frozen=True)
class CoinDetectionParams:
    """Parameters for detecting coin presence at known treasure points."""

    roi_radius: int = 12
    diff_threshold: int = 40
    min_active_pixels: int = 55


@dataclass(frozen=True)
class CoinTrackingParams:
    """Parameters for promoting detected coin presence into active coin points."""

    min_active_lifetime: float = 0.5
    max_active_lifetime: float = 7.0
    stale_timeout: float = 0.4
    lock_radius: float = 15.0


@dataclass(frozen=True)
class CoinPresence:
    treasure_index: int
    point: Point
    active_pixels: int


@dataclass(frozen=True)
class CoinTrack:
    first_seen: float
    last_seen: float


@dataclass(frozen=True)
class CoinLock:
    point: Point
    expires_at: float


@dataclass(frozen=True)
class CoinTrackerState:
    tracks: MappingProxyType[int, CoinTrack] = field(
        default_factory=lambda: MappingProxyType({})
    )
    locks: tuple[CoinLock, ...] = ()


@dataclass(frozen=True)
class CoinTrackerUpdate:
    state: CoinTrackerState
    active_coins: tuple[Point, ...]


def detect_coin_presence(
    frame_gray: np.ndarray,
    background_gray: np.ndarray,
    treasure_points: tuple[Point, ...],
    params: CoinDetectionParams = CoinDetectionParams(),
) -> tuple[CoinPresence, ...]:
    """Return treasure points whose local foreground difference suggests a coin."""
    if frame_gray.shape != background_gray.shape:
        raise ValueError("frame_gray and background_gray must have the same shape")
    if not treasure_points:
        return ()

    diff = cv2.absdiff(frame_gray, background_gray)
    _, thresholded = cv2.threshold(diff, params.diff_threshold, 255, cv2.THRESH_BINARY)
    height, width = thresholded.shape

    presences: list[CoinPresence] = []
    for index, point in enumerate(treasure_points):
        active_pixels = _active_pixels_near_point(
            thresholded=thresholded,
            point=point,
            width=width,
            height=height,
            radius=params.roi_radius,
        )
        if active_pixels > params.min_active_pixels:
            presences.append(
                CoinPresence(
                    treasure_index=index,
                    point=point,
                    active_pixels=active_pixels,
                )
            )
    return tuple(presences)


def update_coin_tracker_state(
    state: CoinTrackerState,
    presences: tuple[CoinPresence, ...],
    treasure_points: tuple[Point, ...],
    current_time: float,
    params: CoinTrackingParams = CoinTrackingParams(),
) -> CoinTrackerUpdate:
    """Advance coin lifetime state and return currently actionable active coins."""
    active_indices = {presence.treasure_index for presence in presences}
    presence_by_index = {presence.treasure_index: presence for presence in presences}
    locks = tuple(lock for lock in state.locks if lock.expires_at > current_time)
    tracks: dict[int, CoinTrack] = {}
    active_coins: list[Point] = []

    for index, track in state.tracks.items():
        if index in active_indices:
            tracks[index] = CoinTrack(first_seen=track.first_seen, last_seen=current_time)
        elif current_time - track.last_seen <= params.stale_timeout + FLOAT_EPSILON:
            tracks[index] = track

    for index, presence in presence_by_index.items():
        if index not in tracks:
            tracks[index] = CoinTrack(first_seen=current_time, last_seen=current_time)
            continue

        track = tracks[index]
        alive_time = current_time - track.first_seen
        point = _treasure_point_for_index(index, presence.point, treasure_points)
        if (
            params.min_active_lifetime < alive_time < params.max_active_lifetime
            and not _is_locked(point, locks, params.lock_radius)
        ):
            active_coins.append(point)

    return CoinTrackerUpdate(
        state=CoinTrackerState(
            tracks=MappingProxyType(tracks),
            locks=locks,
        ),
        active_coins=tuple(active_coins),
    )


def update_active_coins_from_frame(
    frame_gray: np.ndarray,
    background_gray: np.ndarray,
    treasure_points: tuple[Point, ...],
    state: CoinTrackerState,
    current_time: float,
    detection_params: CoinDetectionParams = CoinDetectionParams(),
    tracking_params: CoinTrackingParams = CoinTrackingParams(),
) -> CoinTrackerUpdate:
    """Detect coin presence from a frame pair, then update active coin state."""
    presences = detect_coin_presence(
        frame_gray=frame_gray,
        background_gray=background_gray,
        treasure_points=treasure_points,
        params=detection_params,
    )
    return update_coin_tracker_state(
        state=state,
        presences=presences,
        treasure_points=treasure_points,
        current_time=current_time,
        params=tracking_params,
    )


def lock_coin(
    state: CoinTrackerState,
    point: Point,
    current_time: float,
    duration: float = 1.0,
) -> CoinTrackerState:
    """Return state with an explicit temporary lock for a coin point."""
    active_locks = tuple(lock for lock in state.locks if lock.expires_at > current_time)
    return CoinTrackerState(
        tracks=state.tracks,
        locks=active_locks + (CoinLock(point=point, expires_at=current_time + duration),),
    )


def _active_pixels_near_point(
    thresholded: np.ndarray,
    point: Point,
    width: int,
    height: int,
    radius: int,
) -> int:
    center_x = int(point.x)
    center_y = int(point.y)
    y1 = max(0, center_y - radius)
    y2 = min(height, center_y + radius)
    x1 = max(0, center_x - radius)
    x2 = min(width, center_x + radius)
    roi = thresholded[y1:y2, x1:x2]
    if roi.size == 0:
        return 0
    return int(np.count_nonzero(roi))


def _treasure_point_for_index(
    index: int,
    fallback: Point,
    treasure_points: tuple[Point, ...],
) -> Point:
    if 0 <= index < len(treasure_points):
        return treasure_points[index]
    return fallback


def _is_locked(point: Point, locks: tuple[CoinLock, ...], lock_radius: float) -> bool:
    for lock in locks:
        if (
            abs(point.x - lock.point.x) < lock_radius
            and abs(point.y - lock.point.y) < lock_radius
        ):
            return True
    return False
