import json
from types import SimpleNamespace

import numpy as np

from autozuma.control.execution import ExecutionPlan, ExecutionStep, ExecutionStepType
from autozuma.core.models import (
    BallEntity,
    Command,
    CommandType,
    GameRoiResult,
    LauncherState,
    Point,
    TargetCandidate,
    WorldState,
)
from autozuma.decision.static_frame import StaticFrameDecisionResult
from autozuma.runtime.debug import FileDebugOutputSink, build_debug_summary
from autozuma.runtime.modes import RuntimeModeUpdate, initial_runtime_mode_state
from autozuma.runtime.session import StaticSessionFrameResult, StaticSessionPhase, StaticSessionState


def test_file_debug_output_writes_frame_and_summary_for_detection_state(tmp_path):
    frame = np.zeros((4, 5, 3), dtype=np.uint8)
    result = StaticSessionFrameResult(
        state=StaticSessionState(phase=StaticSessionPhase.DETECTING),
    )

    output = FileDebugOutputSink(tmp_path).write(
        frame_bgr=frame,
        session_result=result,
        current_time=10.25,
    )

    assert output.output_dir.exists()
    assert output.frame_path.exists()
    assert output.summary_path.exists()
    assert output.roi_path is None
    assert output.overlay_path is None
    summary = json.loads(output.summary_path.read_text(encoding="utf-8"))
    assert summary["current_time"] == 10.25
    assert summary["session"]["phase"] == "detecting"
    assert "host" not in summary


def test_file_debug_output_writes_roi_overlay_and_decision_summary(tmp_path):
    frame = np.zeros((30, 40, 3), dtype=np.uint8)
    session_result = _playing_session_result()

    output = FileDebugOutputSink(tmp_path).write(
        frame_bgr=frame,
        session_result=session_result,
        current_time=12.0,
    )

    assert output.roi_path is not None and output.roi_path.exists()
    assert output.overlay_path is not None and output.overlay_path.exists()
    summary = json.loads(output.summary_path.read_text(encoding="utf-8"))
    assert summary["host"]["mode"] == "normal"
    assert summary["host"]["world"]["entity_count"] == 1
    assert summary["host"]["selected_target"]["target_type"] == "ELIM"
    assert summary["host"]["screen_command"]["type"] == "shoot"
    assert summary["host"]["execution_plan"][0]["type"] == "left_click"


def test_build_debug_summary_stays_json_serializable():
    summary = build_debug_summary(_playing_session_result(), current_time=12.0)

    json.dumps(summary)


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
            entities=(BallEntity(x=8, y=9, track_id=0, track_idx=6, color="red"),),
            clusters=(),
        ),
        current_candidates=(target,),
        next_candidates=(),
        swap_decision=SimpleNamespace(
            reason="stay",
            should_swap=False,
        ),
        predicted_candidates=(target,),
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
