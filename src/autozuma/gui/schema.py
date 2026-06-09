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
    label_zh: str
    section: str
    mode: GuiParameterMode
    kind: GuiParameterKind
    default: float
    minimum: float
    maximum: float
    step: float
    description: str
    description_zh: str

    def display_label(self, language: str) -> str:
        return self.label_zh if language == "zh" else self.label

    def display_description(self, language: str) -> str:
        return self.description_zh if language == "zh" else self.description


@dataclass(frozen=True)
class _BaseParameter:
    name: str
    label: str
    label_zh: str
    section: str
    kind: GuiParameterKind
    default: float
    minimum: float
    maximum: float
    step: float
    description: str
    description_zh: str


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

MODE_LABELS_ZH: dict[GuiParameterMode, str] = {
    GuiParameterMode.NORMAL: "普通",
    GuiParameterMode.RESCUE: "救场",
    GuiParameterMode.ENDGAME: "收尾",
}


MODE_SCOPED_PARAMETERS: tuple[_BaseParameter, ...] = (
    _BaseParameter(
        name="fire_cooldown",
        label="Fire cooldown",
        label_zh="发射冷却时间",
        section="Timing",
        kind=GuiParameterKind.FLOAT,
        default=0.3,
        minimum=0.05,
        maximum=1.0,
        step=0.01,
        description="Minimum time between fired commands.",
        description_zh="两次发射命令之间的最短间隔。",
    ),
    _BaseParameter(
        name="m_gap",
        label="Shot clearance",
        label_zh="射线路径安全间距",
        section="Geometry",
        kind=GuiParameterKind.FLOAT,
        default=22.0,
        minimum=10.0,
        maximum=40.0,
        step=0.5,
        description="Line-of-sight clearance threshold.",
        description_zh="判断射线路径是否可通行的安全间距阈值。",
    ),
    _BaseParameter(
        name="combo_hang_base",
        label="Combo hang base",
        label_zh="连击基础等待时间",
        section="Timing",
        kind=GuiParameterKind.FLOAT,
        default=0.8,
        minimum=0.2,
        maximum=2.0,
        step=0.05,
        description="Base hold time after combo shots.",
        description_zh="连击射击后的基础等待时间。",
    ),
    _BaseParameter(
        name="combo_hang_mult",
        label="Combo depth hang",
        label_zh="连击深度等待倍率",
        section="Timing",
        kind=GuiParameterKind.FLOAT,
        default=0.6,
        minimum=0.0,
        maximum=1.5,
        step=0.05,
        description="Additional hold time per combo depth.",
        description_zh="每增加一层连击深度时追加的等待时间。",
    ),
    _BaseParameter(
        name="soft_lock_ttl",
        label="Soft-lock TTL",
        label_zh="软锁定持续时间",
        section="Action Memory",
        kind=GuiParameterKind.FLOAT,
        default=0.6,
        minimum=0.1,
        maximum=2.0,
        step=0.05,
        description="Reserved: prototype soft-lock lifetime.",
        description_zh="保留参数：原型软锁定目标的有效持续时间。",
    ),
    _BaseParameter(
        name="soft_lock_radius",
        label="Soft-lock radius",
        label_zh="软锁定半径",
        section="Action Memory",
        kind=GuiParameterKind.FLOAT,
        default=35.0,
        minimum=15.0,
        maximum=80.0,
        step=1.0,
        description="Radius for target deadzone lock checks.",
        description_zh="目标死区锁定检查使用的半径。",
    ),
    _BaseParameter(
        name="predict_radius_th",
        label="Prediction radius",
        label_zh="预测半径阈值",
        section="Prediction",
        kind=GuiParameterKind.FLOAT,
        default=200.0,
        minimum=50.0,
        maximum=400.0,
        step=5.0,
        description="Reserved: prototype distance threshold for prediction.",
        description_zh="保留参数：原型预测逻辑使用的距离阈值。",
    ),
    _BaseParameter(
        name="predict_mult",
        label="Prediction multiplier",
        label_zh="预测倍率",
        section="Prediction",
        kind=GuiParameterKind.FLOAT,
        default=0.05,
        minimum=-0.3,
        maximum=0.3,
        step=0.005,
        description="Track-index prediction multiplier.",
        description_zh="按轨道索引推算目标位置时使用的预测倍率。",
    ),
    _BaseParameter(
        name="prio_coin",
        label="Coin priority",
        label_zh="硬币目标优先级",
        section="Priorities",
        kind=GuiParameterKind.RANK,
        default=1.0,
        minimum=1.0,
        maximum=6.0,
        step=1.0,
        description="Rank where 1 is highest priority.",
        description_zh="目标排序优先级，1 表示最高优先级。",
    ),
    _BaseParameter(
        name="prio_combo",
        label="Combo priority",
        label_zh="连击目标优先级",
        section="Priorities",
        kind=GuiParameterKind.RANK,
        default=2.0,
        minimum=1.0,
        maximum=6.0,
        step=1.0,
        description="Rank where 1 is highest priority.",
        description_zh="目标排序优先级，1 表示最高优先级。",
    ),
    _BaseParameter(
        name="prio_rollback_elim",
        label="Rollback priority",
        label_zh="回滚消除优先级",
        section="Priorities",
        kind=GuiParameterKind.RANK,
        default=3.0,
        minimum=1.0,
        maximum=6.0,
        step=1.0,
        description="Rank for rollback elimination targets.",
        description_zh="回滚消除目标的排序优先级。",
    ),
    _BaseParameter(
        name="prio_elim",
        label="Elimination priority",
        label_zh="普通消除优先级",
        section="Priorities",
        kind=GuiParameterKind.RANK,
        default=4.0,
        minimum=1.0,
        maximum=6.0,
        step=1.0,
        description="Rank for normal elimination targets.",
        description_zh="普通消除目标的排序优先级。",
    ),
    _BaseParameter(
        name="prio_pair",
        label="Pair priority",
        label_zh="配对插入优先级",
        section="Priorities",
        kind=GuiParameterKind.RANK,
        default=5.0,
        minimum=1.0,
        maximum=6.0,
        step=1.0,
        description="Rank for pair/insertion targets.",
        description_zh="配对或插入目标的排序优先级。",
    ),
)


GENERAL_PARAMETERS: tuple[GuiParameterDefinition, ...] = (
    GuiParameterDefinition(
        key="virtual_mouse",
        label="Virtual mouse",
        label_zh="后台虚拟鼠标",
        section="Control",
        mode=GuiParameterMode.GENERAL,
        kind=GuiParameterKind.TOGGLE,
        default=1.0,
        minimum=0.0,
        maximum=1.0,
        step=1.0,
        description="Use virtual/background click messages when enabled.",
        description_zh="启用后使用后台虚拟点击消息，而不是直接前台物理点击。",
    ),
    GuiParameterDefinition(
        key="detailed_analysis",
        label="Detailed analysis",
        label_zh="详细分析输出",
        section="Debug",
        mode=GuiParameterMode.GENERAL,
        kind=GuiParameterKind.TOGGLE,
        default=1.0,
        minimum=0.0,
        maximum=1.0,
        step=1.0,
        description="Reserved switch for per-shot analysis output.",
        description_zh="保留开关：用于控制每次射击的详细分析输出。",
    ),
    GuiParameterDefinition(
        key="coin_break_delay",
        label="Coin break delay",
        label_zh="硬币突破模式双发延迟",
        section="Coins",
        mode=GuiParameterMode.GENERAL,
        kind=GuiParameterKind.FLOAT,
        default=0.25,
        minimum=0.05,
        maximum=1.0,
        step=0.01,
        description="Delay between breakthrough double-shot clicks.",
        description_zh="硬币突破模式中两次连续点击之间的延迟。",
    ),
    GuiParameterDefinition(
        key="coin_hang_time",
        label="Coin hang time",
        label_zh="硬币突破后等待时间",
        section="Coins",
        mode=GuiParameterMode.GENERAL,
        kind=GuiParameterKind.FLOAT,
        default=0.3,
        minimum=0.1,
        maximum=1.0,
        step=0.01,
        description="Reserved hold time after breakthrough coin attempts.",
        description_zh="保留参数：尝试硬币突破后的等待时间。",
    ),
    GuiParameterDefinition(
        key="gap_priority_th",
        label="Gap priority threshold",
        label_zh="空隙优先距离阈值",
        section="Geometry",
        mode=GuiParameterMode.GENERAL,
        kind=GuiParameterKind.FLOAT,
        default=150.0,
        minimum=50.0,
        maximum=300.0,
        step=5.0,
        description="Reserved gap-priority distance threshold.",
        description_zh="保留参数：空隙目标优先级使用的距离阈值。",
    ),
    GuiParameterDefinition(
        key="rescue_th",
        label="Rescue threshold",
        label_zh="救场触发阈值",
        section="Runtime Mode",
        mode=GuiParameterMode.GENERAL,
        kind=GuiParameterKind.FLOAT,
        default=400.0,
        minimum=100.0,
        maximum=1000.0,
        step=10.0,
        description="Distance to track end that triggers rescue mode.",
        description_zh="球链距离轨道终点低于该值时触发救场模式。",
    ),
    GuiParameterDefinition(
        key="endgame_spawn_th",
        label="Endgame spawn threshold",
        label_zh="收尾出生区阈值",
        section="Runtime Mode",
        mode=GuiParameterMode.GENERAL,
        kind=GuiParameterKind.FLOAT,
        default=150.0,
        minimum=50.0,
        maximum=400.0,
        step=5.0,
        description="Spawn-zone distance threshold for endgame mode.",
        description_zh="用于判断收尾模式的出生区距离阈值。",
    ),
    GuiParameterDefinition(
        key="track_start_exclude",
        label="Track start exclude",
        label_zh="轨道起点忽略距离",
        section="Perception",
        mode=GuiParameterMode.GENERAL,
        kind=GuiParameterKind.FLOAT,
        default=80.0,
        minimum=0.0,
        maximum=300.0,
        step=5.0,
        description="Ignore detected entities too near track starts.",
        description_zh="忽略距离轨道起点过近的检测目标。",
    ),
    GuiParameterDefinition(
        key="track_end_exclude",
        label="Track end exclude",
        label_zh="轨道终点忽略距离",
        section="Perception",
        mode=GuiParameterMode.GENERAL,
        kind=GuiParameterKind.FLOAT,
        default=100.0,
        minimum=0.0,
        maximum=300.0,
        step=5.0,
        description="Ignore detected entities too near track ends.",
        description_zh="忽略距离轨道终点过近的检测目标。",
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
        mode_label_zh = MODE_LABELS_ZH[mode]
        for base in MODE_SCOPED_PARAMETERS:
            key = f"{prefix}_{base.name}"
            definitions.append(
                GuiParameterDefinition(
                    key=key,
                    label=f"{mode_label} {base.label}",
                    label_zh=f"{mode_label_zh}{base.label_zh}",
                    section=base.section,
                    mode=mode,
                    kind=base.kind,
                    default=float(active_values.get(key, base.default)),
                    minimum=base.minimum,
                    maximum=base.maximum,
                    step=base.step,
                    description=base.description,
                    description_zh=base.description_zh,
                )
            )

    for parameter in GENERAL_PARAMETERS:
        definitions.append(
            GuiParameterDefinition(
                key=parameter.key,
                label=parameter.label,
                label_zh=parameter.label_zh,
                section=parameter.section,
                mode=parameter.mode,
                kind=parameter.kind,
                default=float(active_values.get(parameter.key, parameter.default)),
                minimum=parameter.minimum,
                maximum=parameter.maximum,
                step=parameter.step,
                description=parameter.description,
                description_zh=parameter.description_zh,
            )
        )

    return tuple(definitions)
