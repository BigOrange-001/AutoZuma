"""Static-level world-state perception orchestration."""

from __future__ import annotations

import numpy as np

from autozuma.core.models import LevelRuntimeAssets, LauncherTemplateSet, WorldState
from autozuma.vision.clusters import build_topological_clusters
from autozuma.vision.entities import detect_level_entities
from autozuma.vision.launcher_state import detect_launcher_state
from autozuma.vision.roi import extract_game_roi


def detect_static_world_state(
    frame_bgr: np.ndarray,
    level: LevelRuntimeAssets,
    launcher_templates: LauncherTemplateSet,
    p_start_exclude: float = 0.0,
    p_end_exclude: float = 0.0,
) -> WorldState:
    """Detect the playable world state for a static-background level."""
    roi_result = extract_game_roi(frame_bgr, level)
    launcher = detect_launcher_state(
        frame_roi_bgr=roi_result.frame,
        frog_pivot=level.topology.frog_pivot,
        template_set=launcher_templates,
    )
    entities = detect_level_entities(
        frame_roi_bgr=roi_result.frame,
        level=level,
        p_start_exclude=p_start_exclude,
        p_end_exclude=p_end_exclude,
    )
    clusters = build_topological_clusters(entities)

    return WorldState(
        level_id=level.level_id,
        launcher=launcher,
        entities=entities,
        clusters=clusters,
    )
