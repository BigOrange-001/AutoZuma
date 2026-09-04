from autozuma.core.models import LauncherState, Point
from autozuma.vision.colors import UNKNOWN_COLOR
from autozuma.vision.launcher_stability import (
    LauncherColorStabilityParams,
    LauncherColorStabilityState,
    reset_launcher_color_stability,
    stabilize_launcher_colors,
)


def test_next_ball_requires_three_consecutive_matching_observations():
    state = LauncherColorStabilityState()
    params = LauncherColorStabilityParams(confirmation_frames=3)

    first = stabilize_launcher_colors(
        launcher=_launcher("blue"),
        state=state,
        params=params,
    )
    second = stabilize_launcher_colors(
        launcher=_launcher("blue"),
        state=first.state,
        params=params,
    )
    third = stabilize_launcher_colors(
        launcher=_launcher("blue"),
        state=second.state,
        params=params,
    )

    assert first.launcher.next_ball == UNKNOWN_COLOR
    assert second.launcher.next_ball == UNKNOWN_COLOR
    assert third.launcher.next_ball == "blue"
    assert third.state == LauncherColorStabilityState(
        candidate_next_ball="blue",
        candidate_frames=3,
        confirmed_next_ball="blue",
    )


def test_conflicting_or_unknown_observation_immediately_invalidates_confirmation():
    confirmed = LauncherColorStabilityState(
        candidate_next_ball="blue",
        candidate_frames=3,
        confirmed_next_ball="blue",
    )

    conflicting = stabilize_launcher_colors(
        launcher=_launcher("red"),
        state=confirmed,
    )
    unknown = stabilize_launcher_colors(
        launcher=_launcher(UNKNOWN_COLOR),
        state=confirmed,
    )

    assert conflicting.launcher.next_ball == UNKNOWN_COLOR
    assert conflicting.state == LauncherColorStabilityState(
        candidate_next_ball="red",
        candidate_frames=1,
        confirmed_next_ball=UNKNOWN_COLOR,
    )
    assert unknown.launcher.next_ball == UNKNOWN_COLOR
    assert unknown.state == LauncherColorStabilityState()


def test_reset_discards_pre_fire_next_ball_evidence():
    assert reset_launcher_color_stability() == LauncherColorStabilityState()


def _launcher(next_ball: str) -> LauncherState:
    return LauncherState(
        current_ball="red",
        next_ball=next_ball,
        next_position=Point(x=10.0, y=20.0),
        angle_degrees=45.0,
        confidence=0.9,
    )
