from pathlib import Path

import numpy as np

from autozuma.core.models import (
    BallEntity,
    Cluster,
    CommandType,
    GameRoiResult,
    LauncherState,
    LauncherTemplateSet,
    LevelGeometry,
    LevelRuntimeAssets,
    LevelTopology,
    Point,
    TargetCandidate,
    TrackGeometry,
    WorldState,
)
from autozuma.decision.static_frame import StaticFrameDecisionParams, decide_static_frame_command
from autozuma.strategy.coins import CoinScoringParams
from autozuma.strategy.discard import DiscardParams
from autozuma.strategy.prediction import TargetPredictionParams
from autozuma.strategy.selection import TargetSelectionParams
from autozuma.strategy.swap import SwapDecisionParams
from autozuma.strategy.targets import TargetScoringParams


def test_decide_static_frame_command_returns_screen_shoot_for_clear_target(monkeypatch):
    raw_frame = np.zeros((30, 30, 3), dtype=np.uint8)
    roi_frame = np.full((20, 20, 3), 9, dtype=np.uint8)
    level = _level()
    template_set = LauncherTemplateSet(search_radius=5, step_degrees=5, templates={})
    roi_result = GameRoiResult(frame=roi_frame, offset=Point(x=10, y=20), confidence=1.0)
    world_state = _world_state(current_color="red")
    calls = {}

    def fake_extract_game_roi(frame_bgr, runtime_level):
        calls["roi"] = (frame_bgr, runtime_level)
        return roi_result

    def fake_detect_static_world_state_from_roi(
        frame_roi_bgr,
        level,
        launcher_templates,
        p_start_exclude,
        p_end_exclude,
    ):
        calls["world"] = (
            frame_roi_bgr,
            level,
            launcher_templates,
            p_start_exclude,
            p_end_exclude,
        )
        return world_state

    monkeypatch.setattr(
        "autozuma.decision.static_frame.extract_game_roi",
        fake_extract_game_roi,
    )
    monkeypatch.setattr(
        "autozuma.decision.static_frame.detect_static_world_state_from_roi",
        fake_detect_static_world_state_from_roi,
    )

    command = decide_static_frame_command(
        frame_bgr=raw_frame,
        level=level,
        launcher_templates=template_set,
        params=StaticFrameDecisionParams(p_start_exclude=11.0, p_end_exclude=22.0),
    )

    assert command.command_type == CommandType.SHOOT
    assert command.primary_target == Point(x=110.0, y=137.0)
    assert command.secondary_target is None
    assert calls["roi"] == (raw_frame, level)
    assert calls["world"] == (roi_frame, level, template_set, 11.0, 22.0)


def test_decide_static_frame_command_returns_screen_no_op_without_target(monkeypatch):
    raw_frame = np.zeros((30, 30, 3), dtype=np.uint8)
    roi_frame = np.full((20, 20, 3), 9, dtype=np.uint8)
    level = _level()
    template_set = LauncherTemplateSet(search_radius=5, step_degrees=5, templates={})
    roi_result = GameRoiResult(frame=roi_frame, offset=Point(x=10, y=20), confidence=1.0)
    world_state = _world_state(current_color="blue")

    monkeypatch.setattr(
        "autozuma.decision.static_frame.extract_game_roi",
        lambda frame_bgr, level: roi_result,
    )
    monkeypatch.setattr(
        "autozuma.decision.static_frame.detect_static_world_state_from_roi",
        lambda **kwargs: world_state,
    )

    command = decide_static_frame_command(
        frame_bgr=raw_frame,
        level=level,
        launcher_templates=template_set,
        params=StaticFrameDecisionParams(fallback_discard=DiscardParams(enabled=False)),
    )

    assert command.command_type == CommandType.NO_OP
    assert command.primary_target is None
    assert command.secondary_target is None


def test_decide_static_frame_command_discards_when_no_target_is_selected(monkeypatch):
    raw_frame = np.zeros((30, 30, 3), dtype=np.uint8)
    roi_frame = np.full((20, 20, 3), 9, dtype=np.uint8)
    level = _level()
    template_set = LauncherTemplateSet(search_radius=5, step_degrees=5, templates={})
    roi_result = GameRoiResult(frame=roi_frame, offset=Point(x=10, y=20), confidence=1.0)

    monkeypatch.setattr(
        "autozuma.decision.static_frame.extract_game_roi",
        lambda frame_bgr, level: roi_result,
    )
    monkeypatch.setattr(
        "autozuma.decision.static_frame.detect_static_world_state_from_roi",
        lambda **kwargs: _world_state(current_color="red"),
    )
    monkeypatch.setattr(
        "autozuma.decision.static_frame.score_basic_targets",
        lambda **kwargs: (),
    )
    monkeypatch.setattr(
        "autozuma.decision.static_frame.score_basic_targets_for_color",
        lambda **kwargs: (),
    )
    monkeypatch.setattr(
        "autozuma.decision.static_frame.discard_target",
        lambda **kwargs: _target_candidate(x=3.0, y=4.0, score=0.0, track_idx=3),
    )

    command = decide_static_frame_command(
        frame_bgr=raw_frame,
        level=level,
        launcher_templates=template_set,
    )

    assert command.command_type == CommandType.SHOOT
    assert command.primary_target == Point(x=13.0, y=24.0)


def test_decide_static_frame_command_returns_swap_shoot_for_better_next_target(monkeypatch):
    raw_frame = np.zeros((30, 30, 3), dtype=np.uint8)
    roi_frame = np.full((20, 20, 3), 9, dtype=np.uint8)
    level = _level()
    template_set = LauncherTemplateSet(search_radius=5, step_degrees=5, templates={})
    roi_result = GameRoiResult(frame=roi_frame, offset=Point(x=10, y=20), confidence=1.0)
    world_state = WorldState(
        level_id="test",
        launcher=LauncherState(
            current_ball="red",
            next_ball="yellow",
            next_position=None,
        ),
        entities=(),
        clusters=(),
    )

    monkeypatch.setattr(
        "autozuma.decision.static_frame.extract_game_roi",
        lambda frame_bgr, level: roi_result,
    )
    monkeypatch.setattr(
        "autozuma.decision.static_frame.detect_static_world_state_from_roi",
        lambda **kwargs: world_state,
    )
    monkeypatch.setattr(
        "autozuma.decision.static_frame.score_basic_targets",
        lambda **kwargs: (
            _target_candidate(x=20.0, y=20.0, score=10.0, track_idx=20),
        ),
    )
    monkeypatch.setattr(
        "autozuma.decision.static_frame.score_basic_targets_for_color",
        lambda **kwargs: (
            _target_candidate(x=100.0, y=100.0, score=20.0, track_idx=100),
        ),
    )

    command = decide_static_frame_command(
        frame_bgr=raw_frame,
        level=level,
        launcher_templates=template_set,
        params=StaticFrameDecisionParams(
            target_swap=SwapDecisionParams(swap_score_ratio=1.15),
            target_prediction=TargetPredictionParams(predict_multiplier=0.05),
        ),
    )

    assert command.command_type == CommandType.SWAP_SHOOT
    assert command.primary_target == Point(x=110.0, y=127.0)
    assert command.secondary_target is None


def test_decide_static_frame_command_maps_double_shoot_targets_to_screen(monkeypatch):
    raw_frame = np.zeros((30, 30, 3), dtype=np.uint8)
    roi_frame = np.full((20, 20, 3), 9, dtype=np.uint8)
    level = _level()
    template_set = LauncherTemplateSet(search_radius=5, step_degrees=5, templates={})
    roi_result = GameRoiResult(frame=roi_frame, offset=Point(x=10, y=20), confidence=1.0)
    target = TargetCandidate(
        x=3.0,
        y=4.0,
        score=100.0,
        target_type="breakthrough_coin",
        secondary_x=13.0,
        secondary_y=14.0,
        delay_ms=250,
    )

    monkeypatch.setattr(
        "autozuma.decision.static_frame.extract_game_roi",
        lambda frame_bgr, level: roi_result,
    )
    monkeypatch.setattr(
        "autozuma.decision.static_frame.detect_static_world_state_from_roi",
        lambda **kwargs: _world_state(current_color="red"),
    )
    monkeypatch.setattr(
        "autozuma.decision.static_frame.score_basic_targets",
        lambda **kwargs: (target,),
    )
    monkeypatch.setattr(
        "autozuma.decision.static_frame.score_basic_targets_for_color",
        lambda **kwargs: (),
    )
    monkeypatch.setattr(
        "autozuma.decision.static_frame.select_best_clear_target",
        lambda world_state, candidates, frog_pivot, params: tuple(candidates)[0],
    )

    command = decide_static_frame_command(
        frame_bgr=raw_frame,
        level=level,
        launcher_templates=template_set,
    )

    assert command.command_type == CommandType.DOUBLE_SHOOT
    assert command.primary_target == Point(x=13.0, y=24.0)
    assert command.secondary_target == Point(x=23.0, y=34.0)
    assert command.delay_ms == 250


def test_decide_static_frame_command_scores_active_breakthrough_coin(monkeypatch):
    raw_frame = np.zeros((30, 30, 3), dtype=np.uint8)
    roi_frame = np.full((20, 20, 3), 9, dtype=np.uint8)
    level = _level()
    template_set = LauncherTemplateSet(search_radius=5, step_degrees=5, templates={})
    roi_result = GameRoiResult(frame=roi_frame, offset=Point(x=10, y=20), confidence=1.0)

    monkeypatch.setattr(
        "autozuma.decision.static_frame.extract_game_roi",
        lambda frame_bgr, level: roi_result,
    )
    monkeypatch.setattr(
        "autozuma.decision.static_frame.detect_static_world_state_from_roi",
        lambda **kwargs: _world_state(current_color="red"),
    )

    command = decide_static_frame_command(
        frame_bgr=raw_frame,
        level=level,
        launcher_templates=template_set,
        params=StaticFrameDecisionParams(
            coin_scoring=CoinScoringParams(
                coin_priority=100000.0,
                breakthrough_delay_ms=250,
            ),
            active_coins=(Point(x=100.0, y=150.0),),
        ),
    )

    assert command.command_type == CommandType.DOUBLE_SHOOT
    assert command.primary_target == Point(x=110.0, y=145.0)
    assert command.secondary_target == Point(x=110.0, y=170.0)
    assert command.delay_ms == 250


def test_decide_static_frame_command_passes_strategy_params(monkeypatch):
    raw_frame = np.zeros((30, 30, 3), dtype=np.uint8)
    roi_frame = np.full((20, 20, 3), 9, dtype=np.uint8)
    level = _level()
    template_set = LauncherTemplateSet(search_radius=5, step_degrees=5, templates={})
    scoring_params = TargetScoringParams(elim_priority=123.0)
    swap_params = SwapDecisionParams(swap_score_ratio=1.5)
    prediction_params = TargetPredictionParams(predict_multiplier=0.25)
    selection_params = TargetSelectionParams(min_gap=44.0)
    coin_params = CoinScoringParams(coin_priority=777.0)
    active_coins = (Point(x=1.0, y=2.0),)
    calls = {}

    monkeypatch.setattr(
        "autozuma.decision.static_frame.extract_game_roi",
        lambda frame_bgr, level: GameRoiResult(
            frame=roi_frame,
            offset=Point(x=0, y=0),
            confidence=1.0,
        ),
    )
    monkeypatch.setattr(
        "autozuma.decision.static_frame.detect_static_world_state_from_roi",
        lambda **kwargs: _world_state(current_color="red"),
    )

    def fake_score_basic_targets(world_state, level, params):
        calls["score"] = params
        return ()

    def fake_predict_targets(targets, level, frog_pivot, params):
        calls["predict"] = params
        return targets

    def fake_score_coin_targets_for_color(
        world_state,
        level,
        active_coins,
        target_color,
        params,
    ):
        calls.setdefault("coins", []).append((active_coins, target_color, params))
        return ()

    def fake_choose_swap_candidates(
        current_candidates,
        next_candidates,
        current_color,
        next_color,
        params,
    ):
        calls["swap"] = params
        return type(
            "FakeSwapDecision",
            (),
            {"should_swap": False, "candidates": tuple(current_candidates)},
        )()

    def fake_select_best_clear_target(world_state, candidates, frog_pivot, params):
        calls["select"] = params
        return None

    monkeypatch.setattr(
        "autozuma.decision.static_frame.score_basic_targets",
        fake_score_basic_targets,
    )
    monkeypatch.setattr(
        "autozuma.decision.static_frame.predict_targets",
        fake_predict_targets,
    )
    monkeypatch.setattr(
        "autozuma.decision.static_frame.score_coin_targets_for_color",
        fake_score_coin_targets_for_color,
    )
    monkeypatch.setattr(
        "autozuma.decision.static_frame.choose_swap_candidates",
        fake_choose_swap_candidates,
    )
    monkeypatch.setattr(
        "autozuma.decision.static_frame.select_best_clear_target",
        fake_select_best_clear_target,
    )

    decide_static_frame_command(
        frame_bgr=raw_frame,
        level=level,
        launcher_templates=template_set,
        params=StaticFrameDecisionParams(
            target_scoring=scoring_params,
            target_swap=swap_params,
            target_prediction=prediction_params,
            target_selection=selection_params,
            coin_scoring=coin_params,
            active_coins=active_coins,
        ),
    )

    assert calls["score"] == scoring_params
    assert calls["coins"] == [
        (active_coins, "red", coin_params),
        (active_coins, "yellow", coin_params),
    ]
    assert calls["swap"] == swap_params
    assert calls["predict"] == prediction_params
    assert calls["select"] == selection_params


def _level() -> LevelRuntimeAssets:
    topology = LevelTopology(
        level_id="test",
        frog_pivot=Point(x=0, y=0),
        tracks=(),
        treasure_points=(),
        source_path=Path("test.json"),
    )
    track = TrackGeometry(
        track_id=0,
        points=tuple(Point(x=100, y=y) for y in range(200)),
        cumulative_distances=tuple(float(y) for y in range(200)),
    )
    return LevelRuntimeAssets(
        level_id="test",
        topology=topology,
        geometry=LevelGeometry(level_id="test", tracks=(track,)),
        background=None,
    )


def _world_state(current_color: str) -> WorldState:
    entities = (
        BallEntity(x=100, y=100, track_id=0, track_idx=100, color="red"),
        BallEntity(x=100, y=110, track_id=0, track_idx=110, color="red"),
    )
    return WorldState(
        level_id="test",
        launcher=LauncherState(
            current_ball=current_color,
            next_ball="yellow",
            next_position=None,
        ),
        entities=entities,
        clusters=(
            Cluster(
                track_id=0,
                color="red",
                entities=entities,
                start_idx=100,
                end_idx=110,
            ),
        ),
    )


def _target_candidate(x: float, y: float, score: float, track_idx: int) -> TargetCandidate:
    return TargetCandidate(
        x=x,
        y=y,
        score=score,
        target_type="ELIM",
        track_id=0,
        track_idx=track_idx,
        cluster_start_idx=track_idx - 5,
        cluster_end_idx=track_idx + 5,
    )
