"""Stateless ball-chain detection from an aligned game ROI."""

from __future__ import annotations

import math

import cv2
import numpy as np

from autozuma.core.models import BallEntity, LevelRuntimeAssets, TrackGeometry
from autozuma.vision.colors import classify_entity_color
from autozuma.vision.image_io import to_gray

BALL_RADIUS = 15.0
TRACK_GATING_EPSILON = 12.0
FOREGROUND_THRESHOLD = 20
DISTANCE_PEAK_THRESHOLD = 9.5
ENTITY_DEDUP_DISTANCE = 24.0


def detect_level_entities(
    frame_roi_bgr: np.ndarray,
    level: LevelRuntimeAssets,
    p_start_exclude: float = 0.0,
    p_end_exclude: float = 0.0,
) -> tuple[BallEntity, ...]:
    """Detect ball entities for every track in a static-background level."""
    if level.background is None:
        return ()

    entities: list[BallEntity] = []
    for track in level.geometry.tracks:
        entities.extend(
            detect_track_entities(
                frame_roi_bgr=frame_roi_bgr,
                background_bgr=level.background.bgr,
                track=track,
                p_start_exclude=p_start_exclude,
                p_end_exclude=p_end_exclude,
            )
        )
    return tuple(entities)


def detect_track_entities(
    frame_roi_bgr: np.ndarray,
    background_bgr: np.ndarray,
    track: TrackGeometry,
    p_start_exclude: float = 0.0,
    p_end_exclude: float = 0.0,
    ball_radius: float = BALL_RADIUS,
    track_gating_epsilon: float = TRACK_GATING_EPSILON,
) -> tuple[BallEntity, ...]:
    """Detect ball entities near a single dense track geometry."""
    if not track.points:
        return ()

    track_points = _track_points_array(track)
    track_mask = _build_track_mask(frame_roi_bgr.shape[:2], track_points, ball_radius)
    foreground_mask = _build_foreground_mask(frame_roi_bgr, background_bgr)
    roi_mask = cv2.bitwise_and(foreground_mask, track_mask)

    morph_mask = cv2.morphologyEx(
        roi_mask,
        cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)),
    )
    morph_mask = cv2.morphologyEx(
        morph_mask,
        cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)),
    )

    peak_xs, peak_ys = _find_distance_transform_peaks(morph_mask)
    entities = _project_peaks_to_track(
        frame_roi_bgr=frame_roi_bgr,
        peak_xs=peak_xs,
        peak_ys=peak_ys,
        track=track,
        track_points=track_points,
        p_start_exclude=p_start_exclude,
        p_end_exclude=p_end_exclude,
        track_gating_epsilon=track_gating_epsilon,
    )
    return tuple(_deduplicate_entities(entities))


def _track_points_array(track: TrackGeometry) -> np.ndarray:
    return np.array([(point.x, point.y) for point in track.points], dtype=np.float64)


def _build_track_mask(
    shape: tuple[int, int],
    track_points: np.ndarray,
    ball_radius: float,
) -> np.ndarray:
    mask = np.zeros(shape, dtype=np.uint8)
    polyline_points = np.int32(track_points).reshape((-1, 1, 2))
    cv2.polylines(
        mask,
        [polyline_points],
        isClosed=False,
        color=255,
        thickness=int(ball_radius * 2 - 4),
    )
    return mask


def _build_foreground_mask(frame_roi_bgr: np.ndarray, background_bgr: np.ndarray) -> np.ndarray:
    diff = cv2.absdiff(to_gray(frame_roi_bgr), to_gray(background_bgr))
    _, foreground_mask = cv2.threshold(diff, FOREGROUND_THRESHOLD, 255, cv2.THRESH_BINARY)
    return foreground_mask


def _find_distance_transform_peaks(mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    distance_transform = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
    local_max = cv2.dilate(distance_transform, np.ones((13, 13), np.uint8))
    peak_ys, peak_xs = np.where(
        (distance_transform == local_max) & (distance_transform > DISTANCE_PEAK_THRESHOLD)
    )
    return peak_xs, peak_ys


def _project_peaks_to_track(
    frame_roi_bgr: np.ndarray,
    peak_xs: np.ndarray,
    peak_ys: np.ndarray,
    track: TrackGeometry,
    track_points: np.ndarray,
    p_start_exclude: float,
    p_end_exclude: float,
    track_gating_epsilon: float,
) -> list[BallEntity]:
    entities: list[BallEntity] = []
    total_track_length = track.cumulative_distances[-1]

    for x, y in zip(peak_xs, peak_ys):
        point = np.array([x, y])
        distances = np.linalg.norm(track_points - point, axis=1)
        track_index = int(np.argmin(distances))
        if distances[track_index] > track_gating_epsilon:
            continue

        distance_along_path = track.cumulative_distances[track_index]
        if distance_along_path < p_start_exclude:
            continue
        if total_track_length - distance_along_path < p_end_exclude:
            continue

        entities.append(
            BallEntity(
                x=float(x),
                y=float(y),
                track_id=track.track_id,
                track_idx=track_index,
                color=classify_entity_color(frame_roi_bgr, x, y),
            )
        )

    entities.sort(key=lambda entity: entity.track_idx)
    return entities


def _deduplicate_entities(entities: list[BallEntity]) -> list[BallEntity]:
    filtered: list[BallEntity] = []
    for entity in entities:
        if not filtered:
            filtered.append(entity)
            continue
        previous = filtered[-1]
        if math.hypot(entity.x - previous.x, entity.y - previous.y) > ENTITY_DEDUP_DISTANCE:
            filtered.append(entity)
    return filtered
