"""Validation for migrated visual and topology assets."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from autozuma.assets.loader import SPECIAL_DETECTION_LEVEL_IDS, load_topology_file
from autozuma.assets.paths import AssetPaths
from autozuma.core.models import InvalidTopologyError, LevelAssetRef

Severity = Literal["error", "warning", "note"]

BACKGROUND_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png"})
REQUIRED_LAUNCHER_TEMPLATES = ("SMALLFROGonPAD.png",)
REQUIRED_UI_TEMPLATES = ("ui_ok.png", "ui_continue.png")


@dataclass(frozen=True)
class AssetValidationIssue:
    severity: Severity
    code: str
    message: str
    path: Path | None = None


@dataclass(frozen=True)
class AssetValidationReport:
    topology_count: int
    background_count: int
    level_refs: tuple[LevelAssetRef, ...]
    issues: tuple[AssetValidationIssue, ...]

    @property
    def ok(self) -> bool:
        return all(issue.severity != "error" for issue in self.issues)

    @property
    def errors(self) -> tuple[AssetValidationIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "error")

    @property
    def warnings(self) -> tuple[AssetValidationIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "warning")

    @property
    def notes(self) -> tuple[AssetValidationIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "note")


def validate_assets(paths: AssetPaths) -> AssetValidationReport:
    issues: list[AssetValidationIssue] = []

    topology_files = _list_files(paths.level_topology, "*.json", issues, "missing_topology_dir")
    background_files = _list_backgrounds(paths.level_backgrounds, issues)

    background_by_id = _index_by_stem(background_files, "duplicate_background", issues)
    topology_by_id: dict[str, Path] = {}
    level_refs: list[LevelAssetRef] = []

    for topology_path in topology_files:
        key = topology_path.stem.lower()
        if key in topology_by_id:
            issues.append(
                AssetValidationIssue(
                    "error",
                    "duplicate_topology",
                    f"Duplicate topology level id: {topology_path.stem}",
                    topology_path,
                )
            )
            continue
        topology_by_id[key] = topology_path

        try:
            topology = load_topology_file(topology_path)
        except InvalidTopologyError as exc:
            issues.append(
                AssetValidationIssue("error", "invalid_topology", str(exc), topology_path)
            )
            continue

        background_path = background_by_id.get(key)
        requires_special_detection = key in SPECIAL_DETECTION_LEVEL_IDS
        if background_path is None and requires_special_detection:
            issues.append(
                AssetValidationIssue(
                    "note",
                    "special_detection_no_background",
                    f"{topology.level_id} has no static background and requires special detection.",
                    topology_path,
                )
            )
        elif background_path is None:
            issues.append(
                AssetValidationIssue(
                    "error",
                    "missing_background",
                    f"{topology.level_id} has no matching static background.",
                    topology_path,
                )
            )

        level_refs.append(
            LevelAssetRef(
                level_id=topology.level_id,
                topology_path=topology.source_path,
                background_path=background_path,
                requires_special_detection=requires_special_detection,
            )
        )

    for key, background_path in sorted(background_by_id.items()):
        if key not in topology_by_id:
            issues.append(
                AssetValidationIssue(
                    "warning",
                    "background_without_topology",
                    f"{background_path.name} has no matching topology JSON.",
                    background_path,
                )
            )

    _validate_required_files(paths.launcher_templates, REQUIRED_LAUNCHER_TEMPLATES, issues)
    _validate_required_files(paths.ui_templates, REQUIRED_UI_TEMPLATES, issues)

    return AssetValidationReport(
        topology_count=len(topology_files),
        background_count=len(background_files),
        level_refs=tuple(sorted(level_refs, key=lambda ref: ref.level_id.lower())),
        issues=tuple(issues),
    )


def _list_files(
    directory: Path,
    pattern: str,
    issues: list[AssetValidationIssue],
    missing_code: str,
) -> tuple[Path, ...]:
    if not directory.exists():
        issues.append(
            AssetValidationIssue("error", missing_code, f"Directory does not exist: {directory}")
        )
        return ()
    if not directory.is_dir():
        issues.append(
            AssetValidationIssue("error", missing_code, f"Path is not a directory: {directory}")
        )
        return ()
    return tuple(sorted(directory.glob(pattern)))


def _list_backgrounds(
    directory: Path,
    issues: list[AssetValidationIssue],
) -> tuple[Path, ...]:
    if not directory.exists():
        issues.append(
            AssetValidationIssue(
                "error",
                "missing_background_dir",
                f"Directory does not exist: {directory}",
            )
        )
        return ()
    if not directory.is_dir():
        issues.append(
            AssetValidationIssue(
                "error",
                "missing_background_dir",
                f"Path is not a directory: {directory}",
            )
        )
        return ()
    return tuple(
        sorted(path for path in directory.iterdir() if path.suffix.lower() in BACKGROUND_EXTENSIONS)
    )


def _index_by_stem(
    files: tuple[Path, ...],
    duplicate_code: str,
    issues: list[AssetValidationIssue],
) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for path in files:
        key = path.stem.lower()
        if key in result:
            issues.append(
                AssetValidationIssue(
                    "error",
                    duplicate_code,
                    f"Duplicate asset id: {path.stem}",
                    path,
                )
            )
            continue
        result[key] = path
    return result


def _validate_required_files(
    directory: Path,
    required_names: tuple[str, ...],
    issues: list[AssetValidationIssue],
) -> None:
    if not directory.exists() or not directory.is_dir():
        issues.append(
            AssetValidationIssue(
                "error",
                "missing_template_dir",
                f"Template directory does not exist: {directory}",
            )
        )
        return

    existing = {path.name.lower() for path in directory.iterdir() if path.is_file()}
    for name in required_names:
        if name.lower() not in existing:
            issues.append(
                AssetValidationIssue(
                    "error",
                    "missing_template",
                    f"Required template is missing: {name}",
                    directory / name,
                )
            )
