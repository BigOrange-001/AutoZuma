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
PROJECTION_CONFLICT_DISTANCE = 12.0
PROJECTION_SUPPORT_TRACK_IDX_GAP = 85
SPACE_FOREGROUND_VALUE_THRESHOLD = 150
SPACE_BALL_RADIUS = 18.0
SPACE_TRACK_GATING_EPSILON = 18.0
SPACE_DISTANCE_PEAK_THRESHOLD = 3.5
SPACE_CLOSE_KERNEL_SIZE = 11


def detect_level_entities(
    frame_roi_bgr: np.ndarray,
    level: LevelRuntimeAssets,
    p_start_exclude: float = 0.0,
    p_end_exclude: float = 0.0,
) -> tuple[BallEntity, ...]:
    """Detect ball entities for every track in a supported level."""
    if level.background is None:
        if not level.requires_special_detection or level.level_id != "space":
            return ()
        entities: list[BallEntity] = []
        for track in level.geometry.tracks:
            entities.extend(
                detect_space_track_entities(
                    frame_roi_bgr=frame_roi_bgr,
                    track=track,
                    p_start_exclude=p_start_exclude,
                    p_end_exclude=p_end_exclude,
                )
            )
        return tuple(_resolve_projection_conflicts(entities, level.geometry.tracks))

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
    return tuple(_resolve_projection_conflicts(entities, level.geometry.tracks))


def detect_space_track_entities(
    frame_roi_bgr: np.ndarray,
    track: TrackGeometry,
    p_start_exclude: float = 0.0,
    p_end_exclude: float = 0.0,
) -> tuple[BallEntity, ...]:
    """Detect bright ball bodies along a known track over the animated space backdrop."""
    if not track.points:
        return ()

    track_points = _track_points_array(track)
    track_mask = _build_track_mask(
        frame_roi_bgr.shape[:2],
        track_points,
        SPACE_BALL_RADIUS,
    )
    foreground_mask = _build_space_foreground_mask(frame_roi_bgr)
    roi_mask = cv2.bitwise_and(foreground_mask, track_mask)
    morph_mask = cv2.morphologyEx(
        roi_mask,
        cv2.MORPH_CLOSE,
        cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE,
            (SPACE_CLOSE_KERNEL_SIZE, SPACE_CLOSE_KERNEL_SIZE),
        ),
    )
    morph_mask = cv2.morphologyEx(
        morph_mask,
        cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)),
    )
    peak_xs, peak_ys = _find_distance_transform_peaks(
        morph_mask,
        threshold=SPACE_DISTANCE_PEAK_THRESHOLD,
    )
    entities = _project_peaks_to_track(
        frame_roi_bgr=frame_roi_bgr,
        peak_xs=peak_xs,
        peak_ys=peak_ys,
        track=track,
        track_points=track_points,
        p_start_exclude=p_start_exclude,
        p_end_exclude=p_end_exclude,
        track_gating_epsilon=SPACE_TRACK_GATING_EPSILON,
    )
    return tuple(_deduplicate_entities(entities))


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


def _build_space_foreground_mask(frame_roi_bgr: np.ndarray) -> np.ndarray:
    value = cv2.cvtColor(frame_roi_bgr, cv2.COLOR_BGR2HSV)[:, :, 2]
    return np.where(value >= SPACE_FOREGROUND_VALUE_THRESHOLD, 255, 0).astype(np.uint8)


def _find_distance_transform_peaks(
    mask: np.ndarray,
    threshold: float = DISTANCE_PEAK_THRESHOLD,
) -> tuple[np.ndarray, np.ndarray]:
    distance_transform = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
    local_max = cv2.dilate(distance_transform, np.ones((13, 13), np.uint8))
    peak_ys, peak_xs = np.where(
        (distance_transform == local_max) & (distance_transform > threshold)
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
    visible_indices = _visible_track_indices(track)
    if visible_indices.size == 0:
        return entities
    visible_track_points = track_points[visible_indices]

    for x, y in zip(peak_xs, peak_ys):
        point = np.array([x, y])
        distances = np.linalg.norm(visible_track_points - point, axis=1)
        visible_offset = int(np.argmin(distances))
        if distances[visible_offset] > track_gating_epsilon:
            continue
        track_index = int(visible_indices[visible_offset])

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
                visibility_region=_visibility_region(track, track_index),
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


def _visible_track_indices(track: TrackGeometry) -> np.ndarray:
    if len(track.visibility_region_ids) != len(track.points):
        return np.arange(len(track.points), dtype=np.int64)
    return np.flatnonzero(np.asarray(track.visibility_region_ids) >= 0)


def _visibility_region(track: TrackGeometry, track_idx: int) -> int:
    if len(track.visibility_region_ids) != len(track.points):
        return 0
    return track.visibility_region_ids[track_idx]


def _resolve_projection_conflicts(
    entities: list[BallEntity],
    tracks: tuple[TrackGeometry, ...],
) -> list[BallEntity]:
    """Keep one topological assignment for each spatially indistinguishable ball."""
    if len(entities) < 2:
        return entities

    groups: list[list[BallEntity]] = []
    for entity in entities:
        group = next(
            (
                candidate_group
                for candidate_group in groups
                if any(
                    math.hypot(entity.x - other.x, entity.y - other.y)
                    <= PROJECTION_CONFLICT_DISTANCE
                    for other in candidate_group
                )
            ),
            None,
        )
        if group is None:
            groups.append([entity])
        else:
            group.append(entity)

    track_by_id = {track.track_id: track for track in tracks}
    selected: list[BallEntity] = []
    for group in groups:
        track_ids = {entity.track_id for entity in group}
        if len(group) == 1 or len(track_ids) == 1:
            selected.extend(group)
            continue
        conflict_ids = {id(entity) for entity in group}
        selected.append(
            max(
                group,
                key=lambda entity: _projection_support_key(
                    entity,
                    entities,
                    conflict_ids,
                    track_by_id,
                ),
            )
        )

    selected.sort(key=lambda entity: (entity.track_id, entity.track_idx))
    return selected


def _projection_support_key(
    entity: BallEntity,
    entities: list[BallEntity],
    conflict_ids: set[int],
    track_by_id: dict[int, TrackGeometry],
) -> tuple[int, int, int, float, int, int]:
    neighbors = [
        other
        for other in entities
        if id(other) not in conflict_ids
        and other.track_id == entity.track_id
        and other.visibility_region == entity.visibility_region
        and 0
        < abs(other.track_idx - entity.track_idx)
        < PROJECTION_SUPPORT_TRACK_IDX_GAP
    ]
    has_previous = any(other.track_idx < entity.track_idx for other in neighbors)
    has_next = any(other.track_idx > entity.track_idx for other in neighbors)
    matching_color_count = sum(other.color == entity.color for other in neighbors)
    projection_error = _projection_error(entity, track_by_id.get(entity.track_id))
    return (
        int(has_previous) + int(has_next),
        len(neighbors),
        matching_color_count,
        -projection_error,
        -entity.track_id,
        -entity.track_idx,
    )


def _projection_error(entity: BallEntity, track: TrackGeometry | None) -> float:
    if track is None or not 0 <= entity.track_idx < len(track.points):
        return float("inf")
    point = track.points[entity.track_idx]
    return math.hypot(entity.x - point.x, entity.y - point.y)
