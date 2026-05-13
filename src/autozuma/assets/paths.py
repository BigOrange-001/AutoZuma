"""Path helpers for migrated AutoZuma assets."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AssetPaths:
    root: Path
    level_backgrounds: Path
    level_topology: Path
    launcher_templates: Path
    ui_templates: Path


def default_asset_paths() -> AssetPaths:
    repo_root = Path(__file__).resolve().parents[3]
    asset_root = repo_root / "assets"
    return AssetPaths(
        root=asset_root,
        level_backgrounds=asset_root / "levels" / "backgrounds",
        level_topology=asset_root / "levels" / "topology",
        launcher_templates=asset_root / "templates" / "launcher",
        ui_templates=asset_root / "templates" / "ui",
    )
