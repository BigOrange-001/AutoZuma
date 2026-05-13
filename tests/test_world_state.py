from pathlib import Path

import numpy as np
import pytest

from autozuma.core.models import (
    BallEntity,
    Cluster,
    GameRoiResult,
    ImageAsset,
    LauncherState,
    LauncherTemplateSet,
    LevelGeometry,
    LevelRuntimeAssets,
    LevelTopology,
    Point,
    RoiExtractionError,
)
from autozuma.vision.image_io import to_gray
from autozuma.vision.world_state import detect_static_world_state


def test_detect_static_world_state_assembles_static_perception_pipeline(monkeypatch):
    raw_frame = np.zeros((20, 20, 3), dtype=np.uint8)
    roi_frame = np.full((10, 10, 3), 7, dtype=np.uint8)
    level = _level(background_bgr=np.zeros((10, 10, 3), dtype=np.uint8))
    template_set = LauncherTemplateSet(search_radius=5, step_degrees=5, templates={})
    launcher = LauncherState(
        current_ball="red",
        next_ball="blue",
        next_position=Point(x=2, y=3),
        angle_degrees=45.0,
        confidence=0.9,
    )
    entities = (
        BallEntity(x=4, y=5, track_id=0, track_idx=12, color="red"),
        BallEntity(x=8, y=5, track_id=0, track_idx=20, color="red"),
    )
    clusters = (
        Cluster(track_id=0, color="red", entities=entities, start_idx=12, end_idx=20),
    )
    calls = {}

    def fake_extract_game_roi(frame_bgr, runtime_level):
        calls["roi"] = (frame_bgr, runtime_level)
        return GameRoiResult(frame=roi_frame, offset=Point(x=1, y=2), confidence=1.0)

    def fake_detect_launcher_state(frame_roi_bgr, frog_pivot, template_set):
        calls["launcher"] = (frame_roi_bgr, frog_pivot, template_set)
        return launcher

    def fake_detect_level_entities(
        frame_roi_bgr,
        level,
        p_start_exclude,
        p_end_exclude,
    ):
        calls["entities"] = (frame_roi_bgr, level, p_start_exclude, p_end_exclude)
        return entities

    def fake_build_topological_clusters(detected_entities):
        calls["clusters"] = detected_entities
        return clusters

    monkeypatch.setattr("autozuma.vision.world_state.extract_game_roi", fake_extract_game_roi)
    monkeypatch.setattr(
        "autozuma.vision.world_state.detect_launcher_state",
        fake_detect_launcher_state,
    )
    monkeypatch.setattr(
        "autozuma.vision.world_state.detect_level_entities",
        fake_detect_level_entities,
    )
    monkeypatch.setattr(
        "autozuma.vision.world_state.build_topological_clusters",
        fake_build_topological_clusters,
    )

    state = detect_static_world_state(
        frame_bgr=raw_frame,
        level=level,
        launcher_templates=template_set,
        p_start_exclude=11.0,
        p_end_exclude=22.0,
    )

    assert state.level_id == "test"
    assert state.launcher == launcher
    assert state.entities == entities
    assert state.clusters == clusters
    assert calls["roi"] == (raw_frame, level)
    assert calls["launcher"] == (roi_frame, level.topology.frog_pivot, template_set)
    assert calls["entities"] == (roi_frame, level, 11.0, 22.0)
    assert calls["clusters"] == entities


def test_detect_static_world_state_rejects_level_without_static_background():
    level = _level(background_bgr=None)
    template_set = LauncherTemplateSet(search_radius=5, step_degrees=5, templates={})

    with pytest.raises(RoiExtractionError, match="no static background"):
        detect_static_world_state(
            frame_bgr=np.zeros((20, 20, 3), dtype=np.uint8),
            level=level,
            launcher_templates=template_set,
        )


def _level(background_bgr: np.ndarray | None) -> LevelRuntimeAssets:
    topology = LevelTopology(
        level_id="test",
        frog_pivot=Point(x=5, y=5),
        tracks=(),
        treasure_points=(),
        source_path=Path("test.json"),
        has_static_background=background_bgr is not None,
        requires_special_detection=background_bgr is None,
    )
    background = None
    if background_bgr is not None:
        background = ImageAsset(
            path=Path("test.png"),
            bgr=background_bgr,
            gray=to_gray(background_bgr),
        )
    return LevelRuntimeAssets(
        level_id="test",
        topology=topology,
        geometry=LevelGeometry(level_id="test", tracks=()),
        background=background,
        requires_special_detection=background_bgr is None,
    )
