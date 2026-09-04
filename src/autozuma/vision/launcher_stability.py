"""Lightweight temporal confirmation for visually recognized launcher colors."""

from __future__ import annotations

from dataclasses import dataclass, replace

from autozuma.core.models import LauncherState
from autozuma.vision.colors import UNKNOWN_COLOR


@dataclass(frozen=True)
class LauncherColorStabilityState:
    """Consecutive-frame evidence retained for the next launcher ball."""

    candidate_next_ball: str = UNKNOWN_COLOR
    candidate_frames: int = 0
    confirmed_next_ball: str = UNKNOWN_COLOR


@dataclass(frozen=True)
class LauncherColorStabilityParams:
    """Required temporal evidence before next-ball decisions may use a color."""

    confirmation_frames: int = 3


@dataclass(frozen=True)
class LauncherColorStabilityUpdate:
    """Updated evidence plus the launcher state safe for strategy use."""

    state: LauncherColorStabilityState
    launcher: LauncherState


def stabilize_launcher_colors(
    *,
    launcher: LauncherState,
    state: LauncherColorStabilityState,
    params: LauncherColorStabilityParams = LauncherColorStabilityParams(),
) -> LauncherColorStabilityUpdate:
    """Require repeated next-ball observations and reject stale/conflicting colors."""
    if params.confirmation_frames < 1:
        raise ValueError("confirmation_frames must be positive")

    observed = launcher.next_ball
    if observed == UNKNOWN_COLOR:
        updated_state = LauncherColorStabilityState()
    else:
        candidate_frames = (
            min(state.candidate_frames + 1, params.confirmation_frames)
            if observed == state.candidate_next_ball
            else 1
        )
        confirmed = (
            observed
            if candidate_frames >= params.confirmation_frames
            else UNKNOWN_COLOR
        )
        updated_state = LauncherColorStabilityState(
            candidate_next_ball=observed,
            candidate_frames=candidate_frames,
            confirmed_next_ball=confirmed,
        )

    return LauncherColorStabilityUpdate(
        state=updated_state,
        launcher=replace(launcher, next_ball=updated_state.confirmed_next_ball),
    )


def reset_launcher_color_stability() -> LauncherColorStabilityState:
    """Discard pre-fire next-ball evidence after the launcher queue advances."""
    return LauncherColorStabilityState()
