from autozuma.core.models import BallEntity, LauncherState, Point, TargetCandidate, WorldState
from autozuma.strategy.selection import TargetSelectionParams, select_best_clear_target


def test_select_best_clear_target_returns_none_without_candidates():
    world_state = _world_state(entities=())

    assert select_best_clear_target(world_state, (), Point(x=0, y=0)) is None


def test_select_best_clear_target_returns_highest_scoring_clear_candidate():
    low_score = _candidate(x=0, y=100, score=10)
    high_score = _candidate(x=100, y=0, score=20)
    world_state = _world_state(entities=())

    selected = select_best_clear_target(
        world_state=world_state,
        candidates=(low_score, high_score),
        frog_pivot=Point(x=0, y=0),
    )

    assert selected == high_score


def test_select_best_clear_target_skips_blocked_candidates():
    blocked = _candidate(x=100, y=0, score=20)
    clear = _candidate(x=0, y=100, score=10)
    world_state = _world_state(
        entities=(_entity(x=50, y=0, track_id=1, track_idx=50),),
    )

    selected = select_best_clear_target(
        world_state=world_state,
        candidates=(blocked, clear),
        frog_pivot=Point(x=0, y=0),
        params=TargetSelectionParams(min_gap=36),
    )

    assert selected == clear


def test_select_best_clear_target_returns_none_when_all_candidates_are_blocked():
    candidate = _candidate(x=100, y=0, score=20)
    world_state = _world_state(
        entities=(_entity(x=50, y=0, track_id=1, track_idx=50),),
    )

    selected = select_best_clear_target(
        world_state=world_state,
        candidates=(candidate,),
        frog_pivot=Point(x=0, y=0),
    )

    assert selected is None


def test_select_best_clear_target_uses_candidate_cluster_metadata():
    candidate = _candidate(
        x=100,
        y=0,
        score=20,
        track_id=0,
        track_idx=50,
        cluster_start_idx=40,
        cluster_end_idx=60,
    )
    world_state = _world_state(
        entities=(_entity(x=50, y=0, track_id=0, track_idx=50),),
    )

    selected = select_best_clear_target(
        world_state=world_state,
        candidates=(candidate,),
        frog_pivot=Point(x=0, y=0),
    )

    assert selected == candidate


def test_select_best_clear_target_blocks_same_track_entities_outside_candidate_neighborhood():
    candidate = _candidate(
        x=100,
        y=0,
        score=20,
        track_id=0,
        track_idx=200,
        cluster_start_idx=180,
        cluster_end_idx=220,
    )
    world_state = _world_state(
        entities=(_entity(x=50, y=0, track_id=0, track_idx=50),),
    )

    selected = select_best_clear_target(
        world_state=world_state,
        candidates=(candidate,),
        frog_pivot=Point(x=0, y=0),
    )

    assert selected is None


def _world_state(entities: tuple[BallEntity, ...]) -> WorldState:
    return WorldState(
        level_id="test",
        launcher=LauncherState(current_ball="red", next_ball="blue", next_position=None),
        entities=entities,
        clusters=(),
    )


def _candidate(
    x: float,
    y: float,
    score: float,
    track_id: int | None = None,
    track_idx: int | None = None,
    cluster_start_idx: int | None = None,
    cluster_end_idx: int | None = None,
) -> TargetCandidate:
    return TargetCandidate(
        x=x,
        y=y,
        score=score,
        target_type="ELIM",
        track_id=track_id,
        track_idx=track_idx,
        cluster_start_idx=cluster_start_idx,
        cluster_end_idx=cluster_end_idx,
    )


def _entity(x: float, y: float, track_id: int, track_idx: int) -> BallEntity:
    return BallEntity(x=x, y=y, track_id=track_id, track_idx=track_idx, color="red")
