from autozuma.core.models import BallEntity, Cluster, Point
from autozuma.strategy.actions import (
    ActionTrackerState,
    ClusterLock,
    Deadzone,
    VirtualBall,
    active_virtual_balls,
    add_cluster_lock,
    add_deadzone,
    add_virtual_ball,
    apply_virtual_balls_to_clusters,
    is_cluster_locked,
    is_deadzone_locked,
    prune_action_tracker_state,
)


def test_add_deadzone_adds_expiring_point_and_prunes_old_entries():
    state = ActionTrackerState(
        deadzones=(
            Deadzone(point=Point(x=1, y=1), expires_at=9.0),
            Deadzone(point=Point(x=2, y=2), expires_at=12.0),
        )
    )

    updated = add_deadzone(
        state=state,
        point=Point(x=20, y=30),
        current_time=10.0,
        duration=2.5,
    )

    assert updated.deadzones == (
        Deadzone(point=Point(x=2, y=2), expires_at=12.0),
        Deadzone(point=Point(x=20, y=30), expires_at=12.5),
    )


def test_is_deadzone_locked_uses_strict_radius_squared_check():
    state = ActionTrackerState(
        deadzones=(Deadzone(point=Point(x=10, y=10), expires_at=12.0),)
    )

    assert is_deadzone_locked(
        state=state,
        point=Point(x=13, y=14),
        radius=6.0,
        current_time=10.0,
    )
    assert not is_deadzone_locked(
        state=state,
        point=Point(x=16, y=10),
        radius=6.0,
        current_time=10.0,
    )


def test_is_deadzone_locked_ignores_expired_deadzones():
    state = ActionTrackerState(
        deadzones=(Deadzone(point=Point(x=10, y=10), expires_at=10.0),)
    )

    assert not is_deadzone_locked(
        state=state,
        point=Point(x=10, y=10),
        radius=6.0,
        current_time=10.0,
    )


def test_add_cluster_lock_adds_expiring_track_range():
    state = ActionTrackerState()

    updated = add_cluster_lock(
        state=state,
        track_id=2,
        start_idx=100,
        end_idx=140,
        current_time=10.0,
        duration=1.5,
    )

    assert updated.cluster_locks == (
        ClusterLock(track_id=2, start_idx=100, end_idx=140, expires_at=11.5),
    )


def test_is_cluster_locked_uses_track_id_and_default_padding():
    state = ActionTrackerState(
        cluster_locks=(
            ClusterLock(track_id=2, start_idx=100, end_idx=140, expires_at=12.0),
        )
    )

    assert is_cluster_locked(state, track_id=2, track_idx=95, current_time=10.0)
    assert is_cluster_locked(state, track_id=2, track_idx=145, current_time=10.0)
    assert not is_cluster_locked(state, track_id=2, track_idx=94, current_time=10.0)
    assert not is_cluster_locked(state, track_id=3, track_idx=120, current_time=10.0)


def test_is_cluster_locked_ignores_expired_locks():
    state = ActionTrackerState(
        cluster_locks=(
            ClusterLock(track_id=2, start_idx=100, end_idx=140, expires_at=10.0),
        )
    )

    assert not is_cluster_locked(state, track_id=2, track_idx=120, current_time=10.0)


def test_add_virtual_ball_adds_expiring_virtual_entity():
    state = ActionTrackerState()

    updated = add_virtual_ball(
        state=state,
        track_id=1,
        track_idx=80,
        color="red",
        current_time=10.0,
        duration=0.75,
    )

    assert updated.virtual_balls == (
        VirtualBall(track_id=1, track_idx=80, color="red", expires_at=10.75),
    )


def test_active_virtual_balls_returns_only_non_expired_entries():
    state = ActionTrackerState(
        virtual_balls=(
            VirtualBall(track_id=1, track_idx=80, color="red", expires_at=10.0),
            VirtualBall(track_id=2, track_idx=90, color="blue", expires_at=11.0),
        )
    )

    virtual_balls = active_virtual_balls(state, current_time=10.0)

    assert virtual_balls == (
        VirtualBall(track_id=2, track_idx=90, color="blue", expires_at=11.0),
    )


def test_prune_action_tracker_state_removes_all_expired_memory():
    state = ActionTrackerState(
        deadzones=(
            Deadzone(point=Point(x=1, y=1), expires_at=9.0),
            Deadzone(point=Point(x=2, y=2), expires_at=11.0),
        ),
        cluster_locks=(
            ClusterLock(track_id=1, start_idx=0, end_idx=10, expires_at=9.0),
            ClusterLock(track_id=2, start_idx=20, end_idx=30, expires_at=11.0),
        ),
        virtual_balls=(
            VirtualBall(track_id=1, track_idx=5, color="red", expires_at=9.0),
            VirtualBall(track_id=2, track_idx=25, color="blue", expires_at=11.0),
        ),
    )

    pruned = prune_action_tracker_state(state, current_time=10.0)

    assert pruned == ActionTrackerState(
        deadzones=(Deadzone(point=Point(x=2, y=2), expires_at=11.0),),
        cluster_locks=(ClusterLock(track_id=2, start_idx=20, end_idx=30, expires_at=11.0),),
        virtual_balls=(VirtualBall(track_id=2, track_idx=25, color="blue", expires_at=11.0),),
    )


def test_apply_virtual_balls_to_clusters_adds_matching_virtual_size_bonus():
    red_cluster = _cluster("red", track_id=1, start_idx=100)
    blue_cluster = _cluster("blue", track_id=1, start_idx=130)
    state = ActionTrackerState(
        virtual_balls=(
            VirtualBall(track_id=1, track_idx=115, color="red", expires_at=12.0),
            VirtualBall(track_id=1, track_idx=115, color="blue", expires_at=12.0),
            VirtualBall(track_id=1, track_idx=115, color="red", expires_at=10.0),
            VirtualBall(track_id=2, track_idx=115, color="red", expires_at=12.0),
        )
    )

    clusters = apply_virtual_balls_to_clusters(
        clusters=(red_cluster, blue_cluster),
        state=state,
        current_time=10.0,
        track_idx_padding=30,
    )

    assert clusters[0].virtual_size_bonus == 1
    assert clusters[0].size == 2
    assert clusters[1].virtual_size_bonus == 1
    assert clusters[1].size == 2


def test_apply_virtual_balls_to_clusters_returns_original_clusters_without_matches():
    cluster = _cluster("red", track_id=1, start_idx=100)
    state = ActionTrackerState(
        virtual_balls=(VirtualBall(track_id=1, track_idx=200, color="red", expires_at=12.0),)
    )

    clusters = apply_virtual_balls_to_clusters(
        clusters=(cluster,),
        state=state,
        current_time=10.0,
        track_idx_padding=30,
    )

    assert clusters == (cluster,)


def _cluster(color: str, track_id: int, start_idx: int) -> Cluster:
    entity = BallEntity(
        x=float(start_idx),
        y=50.0,
        track_id=track_id,
        track_idx=start_idx,
        color=color,
    )
    return Cluster(
        track_id=track_id,
        color=color,
        entities=(entity,),
        start_idx=start_idx,
        end_idx=start_idx,
    )
