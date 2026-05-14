from types import MappingProxyType

import numpy as np

from autozuma.core.models import Point
from autozuma.vision.coins import (
    CoinDetectionParams,
    CoinLock,
    CoinPresence,
    CoinTrackerState,
    CoinTrack,
    CoinTrackingParams,
    detect_coin_presence,
    lock_coin,
    update_active_coins_from_frame,
    update_coin_tracker_state,
)


def test_detect_coin_presence_returns_empty_without_treasure_points():
    frame = np.zeros((40, 40), dtype=np.uint8)

    presences = detect_coin_presence(frame, frame.copy(), ())

    assert presences == ()


def test_detect_coin_presence_detects_foreground_near_treasure_point():
    background = np.zeros((40, 40), dtype=np.uint8)
    frame = background.copy()
    frame[15:24, 15:24] = 255

    presences = detect_coin_presence(
        frame_gray=frame,
        background_gray=background,
        treasure_points=(Point(x=20, y=20),),
        params=CoinDetectionParams(roi_radius=12, diff_threshold=40, min_active_pixels=55),
    )

    assert len(presences) == 1
    assert presences[0].treasure_index == 0
    assert presences[0].point == Point(x=20, y=20)
    assert presences[0].active_pixels == 81


def test_detect_coin_presence_requires_pixels_above_threshold():
    background = np.zeros((40, 40), dtype=np.uint8)
    frame = background.copy()
    frame[15:20, 15:20] = 255

    presences = detect_coin_presence(
        frame_gray=frame,
        background_gray=background,
        treasure_points=(Point(x=20, y=20),),
        params=CoinDetectionParams(roi_radius=12, diff_threshold=40, min_active_pixels=55),
    )

    assert presences == ()


def test_detect_coin_presence_rejects_mismatched_frame_shapes():
    frame = np.zeros((40, 40), dtype=np.uint8)
    background = np.zeros((41, 40), dtype=np.uint8)

    try:
        detect_coin_presence(frame, background, (Point(x=20, y=20),))
    except ValueError as exc:
        assert str(exc) == "frame_gray and background_gray must have the same shape"
    else:
        raise AssertionError("expected mismatched frame shapes to be rejected")


def test_update_coin_tracker_state_records_first_seen_before_activation_window():
    state = CoinTrackerState()
    presence = CoinPresence(treasure_index=0, point=Point(x=20, y=20), active_pixels=81)

    update = update_coin_tracker_state(
        state=state,
        presences=(presence,),
        treasure_points=(Point(x=20, y=20),),
        current_time=10.0,
    )

    assert update.active_coins == ()
    assert update.state.tracks[0] == CoinTrack(first_seen=10.0, last_seen=10.0)


def test_update_coin_tracker_state_promotes_coin_after_min_lifetime():
    state = CoinTrackerState(
        tracks=MappingProxyType({0: CoinTrack(first_seen=10.0, last_seen=10.0)})
    )
    presence = CoinPresence(treasure_index=0, point=Point(x=20, y=20), active_pixels=81)

    update = update_coin_tracker_state(
        state=state,
        presences=(presence,),
        treasure_points=(Point(x=20, y=20),),
        current_time=10.6,
    )

    assert update.active_coins == (Point(x=20, y=20),)
    assert update.state.tracks[0] == CoinTrack(first_seen=10.0, last_seen=10.6)


def test_update_coin_tracker_state_does_not_promote_coin_at_exact_min_lifetime():
    state = CoinTrackerState(
        tracks=MappingProxyType({0: CoinTrack(first_seen=10.0, last_seen=10.0)})
    )
    presence = CoinPresence(treasure_index=0, point=Point(x=20, y=20), active_pixels=81)

    update = update_coin_tracker_state(
        state=state,
        presences=(presence,),
        treasure_points=(Point(x=20, y=20),),
        current_time=10.5,
    )

    assert update.active_coins == ()


def test_update_coin_tracker_state_does_not_promote_coin_after_max_lifetime():
    state = CoinTrackerState(
        tracks=MappingProxyType({0: CoinTrack(first_seen=10.0, last_seen=16.9)})
    )
    presence = CoinPresence(treasure_index=0, point=Point(x=20, y=20), active_pixels=81)

    update = update_coin_tracker_state(
        state=state,
        presences=(presence,),
        treasure_points=(Point(x=20, y=20),),
        current_time=17.0,
    )

    assert update.active_coins == ()
    assert 0 in update.state.tracks


def test_update_coin_tracker_state_keeps_absent_track_until_stale_timeout():
    state = CoinTrackerState(
        tracks=MappingProxyType({0: CoinTrack(first_seen=10.0, last_seen=10.0)})
    )

    update = update_coin_tracker_state(
        state=state,
        presences=(),
        treasure_points=(Point(x=20, y=20),),
        current_time=10.4,
    )

    assert update.active_coins == ()
    assert 0 in update.state.tracks


def test_update_coin_tracker_state_drops_absent_track_after_stale_timeout():
    state = CoinTrackerState(
        tracks=MappingProxyType({0: CoinTrack(first_seen=10.0, last_seen=10.0)})
    )

    update = update_coin_tracker_state(
        state=state,
        presences=(),
        treasure_points=(Point(x=20, y=20),),
        current_time=10.401,
    )

    assert update.active_coins == ()
    assert update.state.tracks == {}


def test_update_coin_tracker_state_skips_locked_coin_and_expires_old_locks():
    state = CoinTrackerState(
        tracks=MappingProxyType({0: CoinTrack(first_seen=10.0, last_seen=10.0)}),
        locks=(
            CoinLock(point=Point(x=25, y=25), expires_at=11.0),
            CoinLock(point=Point(x=100, y=100), expires_at=10.0),
        ),
    )
    presence = CoinPresence(treasure_index=0, point=Point(x=20, y=20), active_pixels=81)

    update = update_coin_tracker_state(
        state=state,
        presences=(presence,),
        treasure_points=(Point(x=20, y=20),),
        current_time=10.6,
        params=CoinTrackingParams(lock_radius=15.0),
    )

    assert update.active_coins == ()
    assert update.state.locks == (CoinLock(point=Point(x=25, y=25), expires_at=11.0),)


def test_lock_coin_adds_lock_with_explicit_time_and_prunes_expired_locks():
    state = CoinTrackerState(
        locks=(
            CoinLock(point=Point(x=1, y=1), expires_at=9.0),
            CoinLock(point=Point(x=2, y=2), expires_at=12.0),
        )
    )

    updated = lock_coin(
        state=state,
        point=Point(x=20, y=20),
        current_time=10.0,
        duration=2.0,
    )

    assert updated.locks == (
        CoinLock(point=Point(x=2, y=2), expires_at=12.0),
        CoinLock(point=Point(x=20, y=20), expires_at=12.0),
    )


def test_update_active_coins_from_frame_detects_and_updates_tracker_state():
    background = np.zeros((40, 40), dtype=np.uint8)
    frame = background.copy()
    frame[15:24, 15:24] = 255
    state = CoinTrackerState(
        tracks=MappingProxyType({0: CoinTrack(first_seen=10.0, last_seen=10.0)})
    )

    update = update_active_coins_from_frame(
        frame_gray=frame,
        background_gray=background,
        treasure_points=(Point(x=20, y=20),),
        state=state,
        current_time=10.6,
        detection_params=CoinDetectionParams(
            roi_radius=12,
            diff_threshold=40,
            min_active_pixels=55,
        ),
    )

    assert update.active_coins == (Point(x=20, y=20),)
    assert update.state.tracks[0] == CoinTrack(first_seen=10.0, last_seen=10.6)
