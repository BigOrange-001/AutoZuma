"""Explicit action-memory state used by strategy decisions."""

from __future__ import annotations

from dataclasses import dataclass, replace

from autozuma.core.models import Cluster, Point


@dataclass(frozen=True)
class Deadzone:
    point: Point
    expires_at: float


@dataclass(frozen=True)
class ClusterLock:
    track_id: int
    start_idx: int
    end_idx: int
    expires_at: float


@dataclass(frozen=True)
class VirtualBall:
    track_id: int
    track_idx: int
    color: str
    expires_at: float


@dataclass(frozen=True)
class ActionTrackerState:
    deadzones: tuple[Deadzone, ...] = ()
    cluster_locks: tuple[ClusterLock, ...] = ()
    virtual_balls: tuple[VirtualBall, ...] = ()


def add_deadzone(
    state: ActionTrackerState,
    point: Point,
    current_time: float,
    duration: float,
) -> ActionTrackerState:
    """Return state with an added temporary deadzone."""
    state = prune_action_tracker_state(state, current_time)
    return ActionTrackerState(
        deadzones=state.deadzones + (Deadzone(point=point, expires_at=current_time + duration),),
        cluster_locks=state.cluster_locks,
        virtual_balls=state.virtual_balls,
    )


def add_cluster_lock(
    state: ActionTrackerState,
    track_id: int,
    start_idx: int,
    end_idx: int,
    current_time: float,
    duration: float,
) -> ActionTrackerState:
    """Return state with an added temporary cluster-index lock."""
    state = prune_action_tracker_state(state, current_time)
    return ActionTrackerState(
        deadzones=state.deadzones,
        cluster_locks=state.cluster_locks
        + (
            ClusterLock(
                track_id=track_id,
                start_idx=start_idx,
                end_idx=end_idx,
                expires_at=current_time + duration,
            ),
        ),
        virtual_balls=state.virtual_balls,
    )


def add_virtual_ball(
    state: ActionTrackerState,
    track_id: int,
    track_idx: int,
    color: str,
    current_time: float,
    duration: float,
) -> ActionTrackerState:
    """Return state with an added temporary virtual ball."""
    state = prune_action_tracker_state(state, current_time)
    return ActionTrackerState(
        deadzones=state.deadzones,
        cluster_locks=state.cluster_locks,
        virtual_balls=state.virtual_balls
        + (
            VirtualBall(
                track_id=track_id,
                track_idx=track_idx,
                color=color,
                expires_at=current_time + duration,
            ),
        ),
    )


def active_virtual_balls(
    state: ActionTrackerState,
    current_time: float,
) -> tuple[VirtualBall, ...]:
    """Return non-expired virtual balls."""
    return tuple(virtual for virtual in state.virtual_balls if virtual.expires_at > current_time)


def apply_virtual_balls_to_clusters(
    clusters: tuple[Cluster, ...],
    state: ActionTrackerState,
    current_time: float,
    track_idx_padding: int = 30,
) -> tuple[Cluster, ...]:
    """Return clusters with active virtual balls counted into matching cluster sizes."""
    virtual_balls = active_virtual_balls(state, current_time)
    if not virtual_balls or not clusters:
        return clusters

    bonuses = [0 for _ in clusters]
    for virtual in virtual_balls:
        for cluster_idx, cluster in enumerate(clusters):
            if (
                cluster.track_id == virtual.track_id
                and cluster.color == virtual.color
                and cluster.start_idx - track_idx_padding
                <= virtual.track_idx
                <= cluster.end_idx + track_idx_padding
            ):
                bonuses[cluster_idx] += 1
                break

    return tuple(
        replace(cluster, virtual_size_bonus=cluster.virtual_size_bonus + bonuses[idx])
        if bonuses[idx]
        else cluster
        for idx, cluster in enumerate(clusters)
    )


def is_deadzone_locked(
    state: ActionTrackerState,
    point: Point,
    radius: float,
    current_time: float,
) -> bool:
    """Return whether a point falls inside an active deadzone."""
    radius_squared = radius * radius
    for deadzone in state.deadzones:
        if deadzone.expires_at <= current_time:
            continue
        dx = point.x - deadzone.point.x
        dy = point.y - deadzone.point.y
        if dx * dx + dy * dy < radius_squared:
            return True
    return False


def is_cluster_locked(
    state: ActionTrackerState,
    track_id: int,
    track_idx: int,
    current_time: float,
    padding: int = 5,
) -> bool:
    """Return whether a track index falls inside an active cluster lock."""
    for lock in state.cluster_locks:
        if lock.expires_at <= current_time:
            continue
        if (
            lock.track_id == track_id
            and lock.start_idx - padding <= track_idx <= lock.end_idx + padding
        ):
            return True
    return False


def prune_action_tracker_state(
    state: ActionTrackerState,
    current_time: float,
) -> ActionTrackerState:
    """Drop expired action-memory entries."""
    return ActionTrackerState(
        deadzones=tuple(
            deadzone for deadzone in state.deadzones if deadzone.expires_at > current_time
        ),
        cluster_locks=tuple(
            lock for lock in state.cluster_locks if lock.expires_at > current_time
        ),
        virtual_balls=active_virtual_balls(state, current_time),
    )
