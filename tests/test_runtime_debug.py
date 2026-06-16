import json
from types import SimpleNamespace

import numpy as np

from autozuma.control.execution import ExecutionPlan, ExecutionStep, ExecutionStepType
from autozuma.core.models import (
    BallEntity,
    Cluster,
    Command,
    CommandType,
    GameRoiResult,
    LauncherState,
    Point,
    TargetCandidate,
    WorldState,
)
from autozuma.decision.static_frame import StaticFrameDecisionResult
from autozuma.runtime.debug import (
    FileDebugOutputSink,
    build_debug_summary,
    render_static_decision_overlay,
    render_static_session_overlay,
)
from autozuma.runtime.modes import RuntimeModeUpdate, initial_runtime_mode_state
from autozuma.runtime.session import StaticSessionFrameResult, StaticSessionPhase, StaticSessionState


def test_file_debug_output_writes_only_overlay_in_debug_root_for_detection_state(tmp_path):
    frame = np.zeros((4, 5, 3), dtype=np.uint8)
    result = StaticSessionFrameResult(
        state=StaticSessionState(phase=StaticSessionPhase.DETECTING),
    )

    output = FileDebugOutputSink(tmp_path).write(
        frame_bgr=frame,
        session_result=result,
        current_time=10.25,
    )

    assert output.output_dir == tmp_path
    assert output.overlay_path.parent == tmp_path
    assert output.overlay_path.exists()
    assert output.overlay_path.name.endswith("_detecting_overlay.png")
    assert not any(path.is_dir() for path in tmp_path.iterdir())
    assert [path.suffix for path in tmp_path.iterdir()] == [".png"]


def test_file_debug_output_writes_session_overlay_for_decision_state(tmp_path):
    frame = np.zeros((30, 40, 3), dtype=np.uint8)
    session_result = _playing_session_result()

    output = FileDebugOutputSink(tmp_path).write(
        frame_bgr=frame,
        session_result=session_result,
        current_time=12.0,
    )

    assert output.output_dir == tmp_path
    assert output.overlay_path.parent == tmp_path
    assert output.overlay_path.exists()
    assert output.overlay_path.name.endswith("_spiral_overlay.png")
    assert len(tuple(tmp_path.iterdir())) == 1


def test_build_debug_summary_stays_json_serializable():
    summary = build_debug_summary(_playing_session_result(), current_time=12.0)

    json.dumps(summary)


def test_render_static_session_overlay_pastes_roi_overlay_into_full_frame():
    frame = np.zeros((30, 40, 3), dtype=np.uint8)

    overlay = render_static_session_overlay(frame, _playing_session_result())

    assert overlay.shape == frame.shape
    assert int(overlay.sum()) > 0


def test_render_static_decision_overlay_marks_playable_cluster_and_aim_point():
    decision = _playing_session_result().host_result.runtime.decision.decision

    overlay = render_static_decision_overlay(decision)

    assert tuple(int(channel) for channel in overlay[14, 5]) == (0, 0, 255)
    aim_pixel = tuple(int(channel) for channel in overlay[13, 12])
    assert aim_pixel[0] == 0
    assert aim_pixel[1] == 0
    assert 0 < aim_pixel[2] < 255


def _playing_session_result():
    roi = np.zeros((20, 20, 3), dtype=np.uint8)
    target = TargetCandidate(
        x=12,
        y=13,
        score=10,
        target_type="ELIM",
        reason="test",
        track_id=0,
        track_idx=7,
        cluster_start_idx=5,
        cluster_end_idx=9,
    )
    command = Command(CommandType.SHOOT, primary_target=Point(x=12, y=13))
    decision = StaticFrameDecisionResult(
        roi_result=GameRoiResult(frame=roi, offset=Point(x=3, y=4), confidence=0.95),
        world_state=WorldState(
            level_id="spiral",
            launcher=LauncherState(
                current_ball="red",
                next_ball="blue",
                next_position=Point(x=10, y=10),
            ),
            entities=(BallEntity(x=5, y=14, track_id=0, track_idx=6, color="red"),),
            clusters=(
                Cluster(
                    track_id=0,
                    color="red",
                    entities=(BallEntity(x=5, y=14, track_id=0, track_idx=6, color="red"),),
                    start_idx=5,
                    end_idx=9,
                ),
            ),
        ),
        current_candidates=(target,),
        next_candidates=(),
        swap_decision=SimpleNamespace(
            reason="stay",
            should_swap=False,
        ),
        aim_candidates=(target,),
        selected_target=target,
        roi_command=command,
        screen_command=Command(CommandType.SHOOT, primary_target=Point(x=15, y=17)),
    )
    host_result = SimpleNamespace(
        runtime=SimpleNamespace(
            decision=SimpleNamespace(decision=decision, can_fire=True, can_swap=True),
            mode_update=RuntimeModeUpdate(
                state=initial_runtime_mode_state(12.0),
                spawn_detected=False,
            ),
            coin_update=SimpleNamespace(active_coins=(Point(x=1, y=2),)),
        ),
        execution_plan=ExecutionPlan(
            steps=(
                ExecutionStep(
                    ExecutionStepType.LEFT_CLICK,
                    target=Point(x=15, y=17),
                ),
            )
        ),
    )
    return StaticSessionFrameResult(
        state=StaticSessionState(
            phase=StaticSessionPhase.PLAYING,
            level_id="spiral",
            last_map_detect_time=11.0,
        ),
        host_result=host_result,
    )
