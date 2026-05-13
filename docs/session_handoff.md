# Session Handoff

This document is the quick entry point for continuing the AutoZuma Next refactor in a new conversation.

## Current Status

The original AutoZuma 2.0 prototype remains untouched as the behavior reference. A clean refactor target now exists at `AutoZumaNext/`.

The current refactor has completed the foundation layers:

- Project skeleton and local Python package.
- Migrated visual/topology assets.
- Asset inventory and migration documentation.
- Core data models.
- Topology JSON loader and asset validator.
- Local `.venv` with dev dependencies.
- Pure topology geometry generation.
- Runtime asset registry that loads topology, derived geometry, backgrounds, launcher template, and UI templates.
- Static level recognition for migrated static-background levels.

No live game automation, mouse execution, GUI, frame capture, ROI alignment, ball detection, launcher detection, or strategy migration has been done yet.

## Important Paths

- Refactor repo: `AutoZumaNext/`
- Source package: `AutoZumaNext/src/autozuma/`
- Tests: `AutoZumaNext/tests/`
- Migrated assets: `AutoZumaNext/assets/`
- Migration log: `AutoZumaNext/docs/migration_log.md`
- Asset notes: `AutoZumaNext/docs/assets.md`
- Topology notes: `AutoZumaNext/docs/topology.md`

Original project-level planning docs are still in the parent `docs/` directory:

- `docs/core_asset_inventory.md`
- `docs/current_pipeline.md`
- `docs/manual_review_points.md`

## Implemented Modules

### Core Models

File: `src/autozuma/core/models.py`

Current model groups:

- Asset/topology models: `Point`, `TrackControlPoint`, `LevelTopology`, `LevelAssetRef`
- Geometry models: `TrackGeometry`, `LevelGeometry`
- Runtime asset models: `ImageAsset`, `LevelRuntimeAssets`, `TemplateAssets`, `AssetRegistry`
- Perception result models: `LevelDetectionResult`
- Future gameplay skeletons: `BallEntity`, `Cluster`, `LauncherState`, `WorldState`, `TargetCandidate`, `Command`

### Asset Loading And Validation

Files:

- `src/autozuma/assets/paths.py`
- `src/autozuma/assets/loader.py`
- `src/autozuma/assets/validator.py`
- `src/autozuma/cli/validate_assets.py`

Behavior:

- Loads all topology JSON files into `LevelTopology`.
- Supports single-track `control_points` and multi-track `track_N.control_points`.
- Validates static background/topology matching.
- Treats `space` as a special dynamic-background level without static background.
- Validates launcher and UI template presence.

### Topology Geometry

File: `src/autozuma/topology/geometry.py`

Behavior:

- Builds dense Catmull-Rom sampled tracks from topology control points.
- Computes per-track cumulative distances.
- Keeps `LevelTopology` as raw decoded asset data and `LevelGeometry` as derived geometry.

### Runtime Asset Registry

Files:

- `src/autozuma/vision/image_io.py`
- `src/autozuma/assets/registry.py`

Behavior:

- Uses Unicode-safe OpenCV image loading.
- Loads static backgrounds as BGR and grayscale `ImageAsset`.
- Loads launcher and UI templates as BGR and grayscale `ImageAsset`.
- Combines topology, geometry, and images into `AssetRegistry`.
- Includes `space` with topology and geometry, but `background=None`.

### Static Level Recognition

File: `src/autozuma/vision/level_recognition.py`

Behavior:

- Detects static-background levels from a raw BGR frame using grayscale template matching.
- Uses `AssetRegistry` instead of prototype global `LEVEL_ASSETS`.
- Preserves the prototype confidence threshold of `0.25`.
- Returns `LevelDetectionResult(level_id, confidence, match_location)` or `None`.
- Skips `space` because it requires special dynamic-background detection.

## Migrated Assets

Current asset counts:

- Static backgrounds: 21
- Topology JSON files: 22
- Launcher templates: 1
- UI templates: 2

Special case:

- `space.json` has no static background because the original game has a dynamic background for that map. It is intentionally included and marked `requires_special_detection=True`.

## Verification Commands

Run from `AutoZumaNext/`:

```powershell
.\.venv\Scripts\python -m pytest
.\.venv\Scripts\python -m ruff check .
.\.venv\Scripts\python -m autozuma.cli.validate_assets
```

Last known results:

- `pytest`: 24 passed
- `ruff check`: all checks passed
- asset CLI: passed with the expected `space` note

## Next Recommended Step

The next clean step is to migrate ROI extraction/alignment for a detected static level.

Suggested scope:

- Add a clean version of prototype `vision/detector.py::extract_game_roi_ncc`.
- Use `LevelRuntimeAssets.background` from `AssetRegistry` instead of global background data.
- Keep static-level recognition and ROI alignment as separate functions.
- Return a structured result containing the cropped ROI and top-left offset.
- Add tests that embed a real migrated background inside a larger frame.

Do not migrate ball detection, launcher detection, UI handling, or strategy in the same step unless there is a specific reason.

## Design Rules To Preserve

- Preserve behavior first, then improve structure.
- Keep raw topology separate from derived geometry.
- Avoid reintroducing mutable global registries.
- Keep `space` special-case handling explicit.
- Add tests for each migrated behavior slice.
- Update `docs/migration_log.md` after each completed migration step.
