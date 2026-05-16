"""Parameter schema reserved for the AutoZuma Next GUI."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from autozuma.runtime.config import DEFAULT_RUNTIME_VALUES


class GuiParameterMode(Enum):
    GENERAL = "general"
    NORMAL = "normal"
    RESCUE = "rescue"
    ENDGAME = "endgame"


class GuiParameterKind(Enum):
    FLOAT = "float"
    RANK = "rank"
    TOGGLE = "toggle"


@dataclass(frozen=True)
class GuiParameterDefinition:
    """Display metadata for one reserved runtime parameter."""

    key: str
    label: str
    section: str
    mode: GuiParameterMode
    kind: GuiParameterKind
    default: float
    minimum: float
    maximum: float
    step: float
    description: str


@dataclass(frozen=True)
class _BaseParameter:
    name: str
    label: str
    section: str
    kind: GuiParameterKind
    default: float
    minimum: float
    maximum: float
    step: float
    description: str


MODE_PREFIXES: tuple[tuple[str, GuiParameterMode], ...] = (
    ("n", GuiParameterMode.NORMAL),
    ("r", GuiParameterMode.RESCUE),
    ("e", GuiParameterMode.ENDGAME),
)


MODE_LABELS: dict[GuiParameterMode, str] = {
    GuiParameterMode.NORMAL: "Normal",
    GuiParameterMode.RESCUE: "Rescue",
    GuiParameterMode.ENDGAME: "Endgame",
}


MODE_SCOPED_PARAMETERS: tuple[_BaseParameter, ...] = (
    _BaseParameter(
        name="fire_cooldown",
        label="Fire cooldown",
        section="Timing",
        kind=GuiParameterKind.FLOAT,
        default=0.3,
        minimum=0.05,
        maximum=1.0,
        step=0.01,
        description="Minimum time between fired commands.",
    ),
    _BaseParameter(
        name="m_gap",
        label="Shot clearance",
        section="Geometry",
        kind=GuiParameterKind.FLOAT,
        default=22.0,
        minimum=10.0,
        maximum=40.0,
        step=0.5,
        description="Line-of-sight clearance threshold.",
    ),
    _BaseParameter(
        name="combo_hang_base",
        label="Combo hang base",
        section="Timing",
        kind=GuiParameterKind.FLOAT,
        default=0.8,
        minimum=0.2,
        maximum=2.0,
        step=0.05,
        description="Base hold time after combo shots.",
    ),
    _BaseParameter(
        name="combo_hang_mult",
        label="Combo depth hang",
        section="Timing",
        kind=GuiParameterKind.FLOAT,
        default=0.6,
        minimum=0.0,
        maximum=1.5,
        step=0.05,
        description="Additional hold time per combo depth.",
    ),
    _BaseParameter(
        name="soft_lock_ttl",
        label="Soft-lock TTL",
        section="Action Memory",
        kind=GuiParameterKind.FLOAT,
        default=0.6,
        minimum=0.1,
        maximum=2.0,
        step=0.05,
        description="Reserved: prototype soft-lock lifetime.",
    ),
    _BaseParameter(
        name="soft_lock_radius",
        label="Soft-lock radius",
        section="Action Memory",
        kind=GuiParameterKind.FLOAT,
        default=35.0,
        minimum=15.0,
        maximum=80.0,
        step=1.0,
        description="Radius for target deadzone lock checks.",
    ),
    _BaseParameter(
        name="predict_radius_th",
        label="Prediction radius",
        section="Prediction",
        kind=GuiParameterKind.FLOAT,
        default=200.0,
        minimum=50.0,
        maximum=400.0,
        step=5.0,
        description="Reserved: prototype distance threshold for prediction.",
    ),
    _BaseParameter(
        name="predict_mult",
        label="Prediction multiplier",
        section="Prediction",
        kind=GuiParameterKind.FLOAT,
        default=0.05,
        minimum=-0.3,
        maximum=0.3,
        step=0.005,
        description="Track-index prediction multiplier.",
    ),
    _BaseParameter(
        name="prio_coin",
        label="Coin priority",
        section="Priorities",
        kind=GuiParameterKind.RANK,
        default=1.0,
        minimum=1.0,
        maximum=6.0,
        step=1.0,
        description="Rank where 1 is highest priority.",
    ),
    _BaseParameter(
        name="prio_combo",
        label="Combo priority",
        section="Priorities",
        kind=GuiParameterKind.RANK,
        default=2.0,
        minimum=1.0,
        maximum=6.0,
        step=1.0,
        description="Rank where 1 is highest priority.",
    ),
    _BaseParameter(
        name="prio_rollback_elim",
        label="Rollback priority",
        section="Priorities",
        kind=GuiParameterKind.RANK,
        default=3.0,
        minimum=1.0,
        maximum=6.0,
        step=1.0,
        description="Rank for rollback elimination targets.",
    ),
    _BaseParameter(
        name="prio_elim",
        label="Elimination priority",
        section="Priorities",
        kind=GuiParameterKind.RANK,
        default=4.0,
        minimum=1.0,
        maximum=6.0,
        step=1.0,
        description="Rank for normal elimination targets.",
    ),
    _BaseParameter(
        name="prio_pair",
        label="Pair priority",
        section="Priorities",
        kind=GuiParameterKind.RANK,
        default=5.0,
        minimum=1.0,
        maximum=6.0,
        step=1.0,
        description="Rank for pair/insertion targets.",
    ),
)


GENERAL_PARAMETERS: tuple[GuiParameterDefinition, ...] = (
    GuiParameterDefinition(
        key="virtual_mouse",
        label="Virtual mouse",
        section="Control",
        mode=GuiParameterMode.GENERAL,
        kind=GuiParameterKind.TOGGLE,
        default=1.0,
        minimum=0.0,
        maximum=1.0,
        step=1.0,
        description="Use virtual/background click messages when enabled.",
    ),
    GuiParameterDefinition(
        key="detailed_analysis",
        label="Detailed analysis",
        section="Debug",
        mode=GuiParameterMode.GENERAL,
        kind=GuiParameterKind.TOGGLE,
        default=1.0,
        minimum=0.0,
        maximum=1.0,
        step=1.0,
        description="Reserved switch for per-shot analysis output.",
    ),
    GuiParameterDefinition(
        key="coin_break_delay",
        label="Coin break delay",
        section="Coins",
        mode=GuiParameterMode.GENERAL,
        kind=GuiParameterKind.FLOAT,
        default=0.25,
        minimum=0.05,
        maximum=1.0,
        step=0.01,
        description="Delay between breakthrough double-shot clicks.",
    ),
    GuiParameterDefinition(
        key="coin_hang_time",
        label="Coin hang time",
        section="Coins",
        mode=GuiParameterMode.GENERAL,
        kind=GuiParameterKind.FLOAT,
        default=0.3,
        minimum=0.1,
        maximum=1.0,
        step=0.01,
        description="Reserved hold time after breakthrough coin attempts.",
    ),
    GuiParameterDefinition(
        key="gap_priority_th",
        label="Gap priority threshold",
        section="Geometry",
        mode=GuiParameterMode.GENERAL,
        kind=GuiParameterKind.FLOAT,
        default=150.0,
        minimum=50.0,
        maximum=300.0,
        step=5.0,
        description="Reserved gap-priority distance threshold.",
    ),
    GuiParameterDefinition(
        key="rescue_th",
        label="Rescue threshold",
        section="Runtime Mode",
        mode=GuiParameterMode.GENERAL,
        kind=GuiParameterKind.FLOAT,
        default=400.0,
        minimum=100.0,
        maximum=1000.0,
        step=10.0,
        description="Distance to track end that triggers rescue mode.",
    ),
    GuiParameterDefinition(
        key="endgame_spawn_th",
        label="Endgame spawn threshold",
        section="Runtime Mode",
        mode=GuiParameterMode.GENERAL,
        kind=GuiParameterKind.FLOAT,
        default=150.0,
        minimum=50.0,
        maximum=400.0,
        step=5.0,
        description="Spawn-zone distance threshold for endgame mode.",
    ),
    GuiParameterDefinition(
        key="track_start_exclude",
        label="Track start exclude",
        section="Perception",
        mode=GuiParameterMode.GENERAL,
        kind=GuiParameterKind.FLOAT,
        default=80.0,
        minimum=0.0,
        maximum=300.0,
        step=5.0,
        description="Ignore detected entities too near track starts.",
    ),
    GuiParameterDefinition(
        key="track_end_exclude",
        label="Track end exclude",
        section="Perception",
        mode=GuiParameterMode.GENERAL,
        kind=GuiParameterKind.FLOAT,
        default=100.0,
        minimum=0.0,
        maximum=300.0,
        step=5.0,
        description="Ignore detected entities too near track ends.",
    ),
)


def build_gui_parameter_schema(
    values: dict[str, float] | None = None,
) -> tuple[GuiParameterDefinition, ...]:
    """Return parameter controls reserved for the GUI."""
    active_values = DEFAULT_RUNTIME_VALUES if values is None else values
    definitions: list[GuiParameterDefinition] = []

    for prefix, mode in MODE_PREFIXES:
        mode_label = MODE_LABELS[mode]
        for base in MODE_SCOPED_PARAMETERS:
            key = f"{prefix}_{base.name}"
            definitions.append(
                GuiParameterDefinition(
                    key=key,
                    label=f"{mode_label} {base.label}",
                    section=base.section,
                    mode=mode,
                    kind=base.kind,
                    default=float(active_values.get(key, base.default)),
                    minimum=base.minimum,
                    maximum=base.maximum,
                    step=base.step,
                    description=base.description,
                )
            )

    for parameter in GENERAL_PARAMETERS:
        definitions.append(
            GuiParameterDefinition(
                key=parameter.key,
                label=parameter.label,
                section=parameter.section,
                mode=parameter.mode,
                kind=parameter.kind,
                default=float(active_values.get(parameter.key, parameter.default)),
                minimum=parameter.minimum,
                maximum=parameter.maximum,
                step=parameter.step,
                description=parameter.description,
            )
        )

    return tuple(definitions)
