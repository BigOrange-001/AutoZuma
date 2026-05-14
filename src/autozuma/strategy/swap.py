"""Pure swap decision logic for current-ball versus next-ball targets."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from autozuma.core.models import TargetCandidate
from autozuma.vision.colors import UNKNOWN_COLOR


@dataclass(frozen=True)
class SwapDecisionParams:
    """Parameters for score-only swap decisions."""

    swap_score_ratio: float = 1.15


@dataclass(frozen=True)
class SwapDecision:
    """Selected target set and swap flag for a single decision frame."""

    should_swap: bool
    candidates: tuple[TargetCandidate, ...]
    current_best_score: float
    next_best_score: float
    reason: str


def choose_swap_candidates(
    current_candidates: Iterable[TargetCandidate],
    next_candidates: Iterable[TargetCandidate],
    current_color: str,
    next_color: str,
    params: SwapDecisionParams = SwapDecisionParams(),
) -> SwapDecision:
    """Choose whether to use current-ball or next-ball candidates."""
    current_tuple = tuple(current_candidates)
    next_tuple = tuple(next_candidates)
    current_best = _best_positive_score(current_tuple)
    next_best = _best_positive_score(next_tuple)

    if next_color == UNKNOWN_COLOR:
        return _stay(current_tuple, current_best, next_best, "next ball is unknown")
    if next_color == current_color:
        return _stay(current_tuple, current_best, next_best, "next ball matches current ball")

    should_swap = next_best >= current_best * params.swap_score_ratio and next_best > 0.0
    if should_swap:
        return SwapDecision(
            should_swap=True,
            candidates=next_tuple,
            current_best_score=current_best,
            next_best_score=next_best,
            reason=(
                f"next score {next_best:.3f} >= current score {current_best:.3f} "
                f"* ratio {params.swap_score_ratio:.3f}"
            ),
        )
    return _stay(
        current_tuple,
        current_best,
        next_best,
        (
            f"next score {next_best:.3f} < current score {current_best:.3f} "
            f"* ratio {params.swap_score_ratio:.3f}"
        ),
    )


def _best_positive_score(candidates: tuple[TargetCandidate, ...]) -> float:
    if not candidates:
        return 0.0
    return max(0.0, max(candidate.score for candidate in candidates))


def _stay(
    candidates: tuple[TargetCandidate, ...],
    current_best_score: float,
    next_best_score: float,
    reason: str,
) -> SwapDecision:
    return SwapDecision(
        should_swap=False,
        candidates=candidates,
        current_best_score=current_best_score,
        next_best_score=next_best_score,
        reason=reason,
    )
