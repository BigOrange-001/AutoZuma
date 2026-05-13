"""Build runtime asset registries from migrated assets."""

from __future__ import annotations

from pathlib import Path

from autozuma.assets.loader import load_all_topologies
from autozuma.assets.paths import AssetPaths, default_asset_paths
from autozuma.assets.validator import validate_assets
from autozuma.core.models import (
    AssetLoadError,
    AssetRegistry,
    ImageAsset,
    LevelRuntimeAssets,
    TemplateAssets,
)
from autozuma.topology.geometry import build_level_geometry
from autozuma.vision.image_io import load_image_asset

UI_TEMPLATE_NAMES = {
    "ok": "ui_ok.png",
    "continue": "ui_continue.png",
}
LAUNCHER_FROG_TEMPLATE = "SMALLFROGonPAD.png"


def load_asset_registry(paths: AssetPaths | None = None) -> AssetRegistry:
    paths = paths or default_asset_paths()
    report = validate_assets(paths)
    if not report.ok:
        details = "; ".join(issue.message for issue in report.errors)
        raise AssetLoadError(f"Asset validation failed: {details}")

    background_by_id = _index_backgrounds(paths.level_backgrounds)
    topologies = load_all_topologies(paths)

    levels: dict[str, LevelRuntimeAssets] = {}
    for key, topology in topologies.items():
        background_path = background_by_id.get(key)
        background = load_image_asset(background_path) if background_path else None
        levels[key] = LevelRuntimeAssets(
            level_id=topology.level_id,
            topology=topology,
            geometry=build_level_geometry(topology),
            background=background,
            requires_special_detection=topology.requires_special_detection,
        )

    return AssetRegistry(
        levels=levels,
        templates=TemplateAssets(
            launcher_frog=load_image_asset(paths.launcher_templates / LAUNCHER_FROG_TEMPLATE),
            ui=_load_ui_templates(paths.ui_templates),
        ),
    )


def _load_ui_templates(directory: Path) -> dict[str, ImageAsset]:
    return {
        template_id: load_image_asset(directory / filename)
        for template_id, filename in UI_TEMPLATE_NAMES.items()
    }


def _index_backgrounds(directory: Path) -> dict[str, Path]:
    return {
        path.stem.lower(): path
        for path in directory.iterdir()
        if path.suffix.lower() in {".jpg", ".jpeg", ".png"}
    }
