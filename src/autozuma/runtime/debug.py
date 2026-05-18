"""Debug evidence output for live static-session frames."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol

import cv2
import numpy as np

from autozuma.control.execution import ExecutionPlan
from autozuma.core.models import Command, LevelDetectionResult, Point, TargetCandidate
from autozuma.decision.static_frame import StaticFrameDecisionResult
from autozuma.runtime.session import StaticSessionFrameResult, StaticSessionPhase


class DebugOutputSink(Protocol):
    """Side-effect boundary for writing one requested debug snapshot."""

    def write(
        self,
        *,
        frame_bgr: np.ndarray,
        session_result: StaticSessionFrameResult,
        current_time: float,
    ) -> "DebugOutputResult":
        """Write debug evidence for one captured frame."""


@dataclass(frozen=True)
class DebugOutputResult:
    """Files produced for one debug snapshot."""

    output_dir: Path
    frame_path: Path
    summary_path: Path
    roi_path: Path | None = None
    overlay_path: Path | None = None


@dataclass(frozen=True)
class FileDebugOutputSink:
    """Write debug evidence files under a root directory."""

    root: Path

    def write(
        self,
        *,
        frame_bgr: np.ndarray,
        session_result: StaticSessionFrameResult,
        current_time: float,
    ) -> DebugOutputResult:
        output_dir = _unique_output_dir(
            root=self.root,
            current_time=current_time,
            level_id=session_result.state.level_id,
        )
        output_dir.mkdir(parents=True, exist_ok=False)

        frame_path = output_dir / "frame.png"
        _write_bgr_image(frame_path, frame_bgr)

        roi_path: Path | None = None
        overlay_path: Path | None = None
        decision = _decision_result(session_result)
        if decision is not None:
            roi_path = output_dir / "roi.png"
            overlay_path = output_dir / "roi_overlay.png"
            _write_bgr_image(roi_path, decision.roi_result.frame)
            _write_bgr_image(overlay_path, render_static_decision_overlay(decision))

        summary_path = output_dir / "summary.json"
        summary_path.write_text(
            json.dumps(build_debug_summary(session_result, current_time), indent=2),
            encoding="utf-8",
        )

        return DebugOutputResult(
            output_dir=output_dir,
            frame_path=frame_path,
            summary_path=summary_path,
            roi_path=roi_path,
            overlay_path=overlay_path,
        )


def build_debug_summary(
    session_result: StaticSessionFrameResult,
    current_time: float,
) -> dict[str, object]:
    """Return JSON-serializable evidence for one static-session frame."""
    summary: dict[str, object] = {
        "current_time": float(current_time),
        "session": {
            "phase": session_result.state.phase.value,
            "level_id": session_result.state.level_id,
            "level_changed": session_result.level_changed,
            "last_map_detect_time": session_result.state.last_map_detect_time,
        },
        "detection": _detection_summary(session_result.detection_result),
        "ui": _ui_summary(session_result),
    }
    if session_result.host_result is not None:
        summary["host"] = _host_summary(session_result)
    return summary


def render_static_decision_overlay(decision: StaticFrameDecisionResult) -> np.ndarray:
    """Render a compact ROI-local overlay from a rich static-frame decision result."""
    overlay = decision.roi_result.frame.copy()
    frog = decision.world_state.launcher
    for entity in decision.world_state.entities:
        cv2.circle(
            overlay,
            (int(round(entity.x)), int(round(entity.y))),
            5,
            _color_for_entity(entity.color),
            1,
            lineType=cv2.LINE_AA,
        )

    selected = decision.selected_target
    if selected is not None:
        target = (int(round(selected.x)), int(round(selected.y)))
        cv2.circle(overlay, target, 9, (0, 255, 255), 2, lineType=cv2.LINE_AA)
        cv2.putText(
            overlay,
            selected.target_type,
            (target[0] + 10, target[1] - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (0, 255, 255),
            1,
            cv2.LINE_AA,
        )
        if selected.secondary_x is not None and selected.secondary_y is not None:
            secondary = (int(round(selected.secondary_x)), int(round(selected.secondary_y)))
            cv2.circle(overlay, secondary, 7, (255, 0, 255), 2, lineType=cv2.LINE_AA)

    if frog.next_position is not None:
        next_pos = (int(round(frog.next_position.x)), int(round(frog.next_position.y)))
        cv2.circle(overlay, next_pos, 6, (255, 255, 255), 1, lineType=cv2.LINE_AA)

    return overlay


def render_static_session_overlay(
    frame_bgr: np.ndarray,
    session_result: StaticSessionFrameResult,
) -> np.ndarray:
    """Render a full captured-frame overlay for live preview."""
    overlay = frame_bgr.copy()
    decision = _decision_result(session_result)
    if decision is not None:
        _paste_decision_roi_overlay(overlay, decision)
        _draw_command_targets(overlay, decision.screen_command)

    if session_result.ui_result is not None:
        detection = session_result.ui_result.automation.detection_result
        if detection is not None:
            target = (int(round(detection.target.x)), int(round(detection.target.y)))
            cv2.circle(overlay, target, 12, (0, 165, 255), 2, lineType=cv2.LINE_AA)
            cv2.putText(
                overlay,
                detection.template_id,
                (target[0] + 12, target[1] - 12),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (0, 165, 255),
                1,
                cv2.LINE_AA,
            )

    if session_result.detection_result is not None:
        detection = session_result.detection_result
        cv2.putText(
            overlay,
            f"{detection.level_id} {detection.confidence:.2f}",
            (12, 24),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (0, 255, 255),
            2,
            cv2.LINE_AA,
        )
    return overlay


def _host_summary(session_result: StaticSessionFrameResult) -> dict[str, object]:
    host_result = session_result.host_result
    if host_result is None:
        return {}

    runtime = host_result.runtime
    stateful = runtime.decision
    decision = stateful.decision
    return {
        "mode": runtime.mode_update.state.mode.value,
        "spawn_detected": runtime.mode_update.spawn_detected,
        "active_coins": [_point_summary(point) for point in runtime.coin_update.active_coins],
        "can_fire": stateful.can_fire,
        "can_swap": stateful.can_swap,
        "world": {
            "level_id": decision.world_state.level_id,
            "current_ball": decision.world_state.launcher.current_ball,
            "next_ball": decision.world_state.launcher.next_ball,
            "entity_count": len(decision.world_state.entities),
            "cluster_count": len(decision.world_state.clusters),
        },
        "candidates": {
            "current_count": len(decision.current_candidates),
            "next_count": len(decision.next_candidates),
            "predicted_count": len(decision.predicted_candidates),
            "swap_reason": decision.swap_decision.reason,
            "swap_selected": decision.swap_decision.should_swap,
        },
        "selected_target": _target_summary(decision.selected_target),
        "used_fallback": decision.used_fallback,
        "roi_command": _command_summary(decision.roi_command),
        "screen_command": _command_summary(decision.screen_command),
        "execution_plan": _execution_plan_summary(host_result.execution_plan),
    }


def _ui_summary(session_result: StaticSessionFrameResult) -> dict[str, object] | None:
    if session_result.ui_result is None:
        return None
    automation = session_result.ui_result.automation
    return {
        "state": {
            "last_poll_time": automation.state.last_poll_time,
            "click_count": automation.state.click_count,
            "next_click_time": automation.state.next_click_time,
        },
        "detection": (
            None
            if automation.detection_result is None
            else {
                "template_id": automation.detection_result.template_id,
                "confidence": automation.detection_result.confidence,
                "match_location": _point_summary(automation.detection_result.match_location),
                "target": _point_summary(automation.detection_result.target),
            }
        ),
        "command": _command_summary(automation.command),
        "should_skip_gameplay": automation.should_skip_gameplay,
        "reset_session": automation.reset_session,
        "execution_plan": _execution_plan_summary(session_result.ui_result.execution_plan),
    }


def _decision_result(session_result: StaticSessionFrameResult) -> StaticFrameDecisionResult | None:
    if session_result.host_result is None:
        return None
    return session_result.host_result.runtime.decision.decision


def _detection_summary(detection: LevelDetectionResult | None) -> dict[str, object] | None:
    if detection is None:
        return None
    return {
        "level_id": detection.level_id,
        "confidence": float(detection.confidence),
        "match_location": _point_summary(detection.match_location),
    }


def _target_summary(target: TargetCandidate | None) -> dict[str, object] | None:
    if target is None:
        return None
    return {
        "x": float(target.x),
        "y": float(target.y),
        "score": float(target.score),
        "target_type": target.target_type,
        "reason": target.reason,
        "combo_depth": target.combo_depth,
        "track_id": target.track_id,
        "track_idx": target.track_idx,
        "cluster_start_idx": target.cluster_start_idx,
        "cluster_end_idx": target.cluster_end_idx,
        "secondary": (
            None
            if target.secondary_x is None or target.secondary_y is None
            else {"x": float(target.secondary_x), "y": float(target.secondary_y)}
        ),
        "delay_ms": target.delay_ms,
    }


def _command_summary(command: Command) -> dict[str, object]:
    return {
        "type": command.command_type.value,
        "primary_target": _point_summary(command.primary_target),
        "secondary_target": _point_summary(command.secondary_target),
        "delay_ms": command.delay_ms,
    }


def _execution_plan_summary(plan: ExecutionPlan) -> list[dict[str, object]]:
    return [
        {
            "type": step.step_type.value,
            "target": _point_summary(step.target),
            "delay_ms": step.delay_ms,
        }
        for step in plan.steps
    ]


def _point_summary(point: Point | None) -> dict[str, float] | None:
    if point is None:
        return None
    return {"x": float(point.x), "y": float(point.y)}


def _paste_decision_roi_overlay(
    frame_overlay: np.ndarray,
    decision: StaticFrameDecisionResult,
) -> None:
    roi_overlay = render_static_decision_overlay(decision)
    offset = decision.roi_result.offset
    left = int(round(offset.x))
    top = int(round(offset.y))
    height, width = roi_overlay.shape[:2]
    frame_height, frame_width = frame_overlay.shape[:2]

    x1 = max(0, left)
    y1 = max(0, top)
    x2 = min(frame_width, left + width)
    y2 = min(frame_height, top + height)
    if x1 >= x2 or y1 >= y2:
        return

    roi_x1 = x1 - left
    roi_y1 = y1 - top
    roi_x2 = roi_x1 + (x2 - x1)
    roi_y2 = roi_y1 + (y2 - y1)
    frame_overlay[y1:y2, x1:x2] = roi_overlay[roi_y1:roi_y2, roi_x1:roi_x2]
    cv2.rectangle(
        frame_overlay,
        (x1, y1),
        (x2 - 1, y2 - 1),
        (0, 255, 255),
        1,
        lineType=cv2.LINE_AA,
    )


def _draw_command_targets(overlay: np.ndarray, command: Command) -> None:
    if command.primary_target is not None:
        _draw_crosshair(overlay, command.primary_target, (0, 0, 255))
    if command.secondary_target is not None:
        _draw_crosshair(overlay, command.secondary_target, (255, 0, 255))


def _draw_crosshair(overlay: np.ndarray, point: Point, color: tuple[int, int, int]) -> None:
    x = int(round(point.x))
    y = int(round(point.y))
    cv2.circle(overlay, (x, y), 11, color, 2, lineType=cv2.LINE_AA)
    cv2.line(overlay, (x - 16, y), (x + 16, y), color, 1, lineType=cv2.LINE_AA)
    cv2.line(overlay, (x, y - 16), (x, y + 16), color, 1, lineType=cv2.LINE_AA)


def _write_bgr_image(path: Path, image_bgr: np.ndarray) -> None:
    ok, buffer = cv2.imencode(path.suffix, image_bgr)
    if not ok:
        raise ValueError(f"Could not encode debug image: {path}")
    buffer.tofile(path)


def _unique_output_dir(root: Path, current_time: float, level_id: str | None) -> Path:
    base_name = _output_dir_name(current_time, level_id)
    candidate = root / base_name
    suffix = 1
    while candidate.exists():
        candidate = root / f"{base_name}_{suffix:02d}"
        suffix += 1
    return candidate


def _output_dir_name(current_time: float, level_id: str | None) -> str:
    timestamp = datetime.fromtimestamp(current_time).strftime("%Y%m%d_%H%M%S")
    milliseconds = int((current_time % 1.0) * 1000)
    level = _safe_path_token(level_id or StaticSessionPhase.DETECTING.value)
    return f"{timestamp}_{milliseconds:03d}_{level}"


def _safe_path_token(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_") or "unknown"


def _color_for_entity(color: str) -> tuple[int, int, int]:
    return {
        "red": (0, 0, 255),
        "yellow": (0, 255, 255),
        "green": (0, 220, 0),
        "blue": (255, 0, 0),
        "purple": (255, 0, 255),
        "white": (255, 255, 255),
    }.get(color, (180, 180, 180))
