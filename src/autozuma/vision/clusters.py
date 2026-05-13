"""Topological cluster building for detected ball entities."""

from __future__ import annotations

from collections.abc import Iterable

from autozuma.core.models import BallEntity, Cluster

MAX_CLUSTER_TRACK_IDX_GAP = 85


def build_topological_clusters(
    entities: Iterable[BallEntity],
    max_track_idx_gap: int = MAX_CLUSTER_TRACK_IDX_GAP,
) -> tuple[Cluster, ...]:
    """Group adjacent same-color entities on the same track into clusters."""
    ordered_entities = tuple(entities)
    if not ordered_entities:
        return ()

    clusters: list[Cluster] = []
    current_cluster: list[BallEntity] = [ordered_entities[0]]

    for entity in ordered_entities[1:]:
        previous = current_cluster[-1]
        if _belongs_to_cluster(entity, previous, max_track_idx_gap):
            current_cluster.append(entity)
            continue

        clusters.append(_build_cluster(current_cluster))
        current_cluster = [entity]

    clusters.append(_build_cluster(current_cluster))
    return tuple(clusters)


def _belongs_to_cluster(
    entity: BallEntity,
    previous: BallEntity,
    max_track_idx_gap: int,
) -> bool:
    return (
        entity.track_id == previous.track_id
        and entity.color == previous.color
        and entity.track_idx - previous.track_idx < max_track_idx_gap
    )


def _build_cluster(entities: list[BallEntity]) -> Cluster:
    return Cluster(
        track_id=entities[0].track_id,
        color=entities[0].color,
        entities=tuple(entities),
        start_idx=entities[0].track_idx,
        end_idx=entities[-1].track_idx,
    )
