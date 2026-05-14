from autozuma.core.models import TargetCandidate
from autozuma.strategy.swap import SwapDecisionParams, choose_swap_candidates


def test_choose_swap_candidates_swaps_when_next_score_beats_ratio():
    current = (_target(score=100.0),)
    next_targets = (_target(score=120.0),)

    decision = choose_swap_candidates(
        current_candidates=current,
        next_candidates=next_targets,
        current_color="red",
        next_color="blue",
        params=SwapDecisionParams(swap_score_ratio=1.15),
    )

    assert decision.should_swap is True
    assert decision.candidates == next_targets
    assert decision.current_best_score == 100.0
    assert decision.next_best_score == 120.0


def test_choose_swap_candidates_stays_when_next_score_is_not_enough():
    current = (_target(score=100.0),)
    next_targets = (_target(score=114.0),)

    decision = choose_swap_candidates(
        current_candidates=current,
        next_candidates=next_targets,
        current_color="red",
        next_color="blue",
        params=SwapDecisionParams(swap_score_ratio=1.15),
    )

    assert decision.should_swap is False
    assert decision.candidates == current


def test_choose_swap_candidates_stays_when_next_ball_is_unknown():
    current = (_target(score=100.0),)
    next_targets = (_target(score=1000.0),)

    decision = choose_swap_candidates(
        current_candidates=current,
        next_candidates=next_targets,
        current_color="red",
        next_color="unknown",
    )

    assert decision.should_swap is False
    assert decision.candidates == current


def test_choose_swap_candidates_stays_when_next_ball_matches_current_ball():
    current = (_target(score=100.0),)
    next_targets = (_target(score=1000.0),)

    decision = choose_swap_candidates(
        current_candidates=current,
        next_candidates=next_targets,
        current_color="red",
        next_color="red",
    )

    assert decision.should_swap is False
    assert decision.candidates == current


def test_choose_swap_candidates_swaps_when_current_has_no_positive_target():
    next_targets = (_target(score=1.0),)

    decision = choose_swap_candidates(
        current_candidates=(),
        next_candidates=next_targets,
        current_color="red",
        next_color="blue",
    )

    assert decision.should_swap is True
    assert decision.candidates == next_targets


def _target(score: float) -> TargetCandidate:
    return TargetCandidate(x=1.0, y=2.0, score=score, target_type="ELIM")
