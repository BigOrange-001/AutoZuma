"""Pure mode-scoped runtime parameter resolution."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from autozuma.runtime.modes import RuntimeMode, RuntimeModeState


@dataclass(frozen=True)
class RuntimeParameterResolver:
    """Resolve prototype-style strategy parameters for the active runtime mode."""

    values: Mapping[str, float]

    def get(self, key: str, mode: RuntimeMode | RuntimeModeState) -> float:
        """Resolve a parameter using R/E/N prefixes with prototype fallback behavior."""
        active_mode = mode.mode if isinstance(mode, RuntimeModeState) else mode
        normalized = _normalize_values(self.values)
        normalized_key = key.upper()
        search_key = f"{_mode_prefix(active_mode)}_{normalized_key}"
        if search_key in normalized:
            return normalized[search_key]
        return normalized.get(normalized_key, 0.0)

    def ranked_priority(self, key: str, mode: RuntimeMode | RuntimeModeState) -> float:
        """Resolve a rank parameter into the prototype priority weight."""
        rank = int(self.get(key, mode))
        return float(10 ** (6 - rank))


def resolve_runtime_parameter(
    values: Mapping[str, float],
    key: str,
    mode: RuntimeMode | RuntimeModeState,
) -> float:
    """Resolve one prototype-style parameter from a mapping."""
    return RuntimeParameterResolver(values).get(key, mode)


def resolve_ranked_priority(
    values: Mapping[str, float],
    key: str,
    mode: RuntimeMode | RuntimeModeState,
) -> float:
    """Resolve one rank-style priority value from a mapping."""
    return RuntimeParameterResolver(values).ranked_priority(key, mode)


def _normalize_values(values: Mapping[str, float]) -> dict[str, float]:
    return {key.upper(): value for key, value in values.items()}


def _mode_prefix(mode: RuntimeMode) -> str:
    match mode:
        case RuntimeMode.RESCUE:
            return "R"
        case RuntimeMode.ENDGAME:
            return "E"
        case RuntimeMode.NORMAL:
            return "N"
