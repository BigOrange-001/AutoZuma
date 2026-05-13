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
- Static ROI extraction/alignment for detected static levels.
- Launcher frog rotated template generation.
- Launcher state detection and HSV color classification.
- Stateless ball entity detection for static-background levels.
- Topological cluster building from detected ball entities.
- Static world-state perception assembly.
- Basic strategy target scoring.
- Strategy line-of-sight filtering.
- Strategy target selection.
- Basic strategy command generation.
- ROI-to-screen command coordinate mapping.

No live game automation, mouse execution, GUI, frame capture, UI state handling, full strategy migration, prediction, swaps, fallback discard, runtime cooldowns, or command execution has been done yet.

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
- Perception result models: `LevelDetectionResult`, `GameRoiResult`
- Launcher template models: `LauncherTemplate`, `LauncherTemplateSet`
- Future gameplay skeletons: `BallEntity`, `Cluster`, `LauncherState`, `WorldState`, `TargetCandidate`, `Command`

`TargetCandidate` now includes optional topology context fields for track id, target track index, and cluster start/end indices.

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

### Static ROI Extraction

File: `src/autozuma/vision/roi.py`

Behavior:

- Locates a static level background inside a raw BGR frame using grayscale template matching.
- Uses `LevelRuntimeAssets.background` instead of prototype global background data.
- Returns `GameRoiResult(frame, offset, confidence)`.
- Rejects frames smaller than the static background.
- Rejects `space` because it has no static background.

### Launcher Template Generation

File: `src/autozuma/vision/launcher_templates.py`

Behavior:

- Builds rotated launcher frog templates from `registry.templates.launcher_frog`.
- Uses explicit `LauncherTemplateSet` data instead of prototype global `FROG_TEMPLATES`.
- Preserves prototype defaults: search radius `50`, angle step `5`.
- Generates grayscale templates, match masks, and subtraction masks for angles `0..355`.

### Launcher State Detection

Files:

- `src/autozuma/vision/colors.py`
- `src/autozuma/vision/launcher_state.py`

Behavior:

- Detects launcher angle by comparing a frog-pivot ROI against `LauncherTemplateSet`.
- Uses migrated HSV color classification for current and next ball positions.
- Returns `LauncherState(current_ball, next_ball, next_position, angle_degrees, confidence)`.
- Returns unknown launcher state when templates are missing or the search ROI is clipped.

### Stateless Ball Entity Detection

File: `src/autozuma/vision/entities.py`

Behavior:

- Detects ball centers with static-background differencing, track masking, morphology, and distance-transform peaks.
- Projects candidates onto dense `TrackGeometry` points.
- Applies start/end exclusion distances.
- Classifies entity colors with the migrated HSV helper.
- Returns `BallEntity` tuples.

### Topological Cluster Building

File: `src/autozuma/vision/clusters.py`

Behavior:

- Consumes ordered `BallEntity` instances.
- Groups adjacent entities by same track, same color, and close track-index gap.
- Preserves the prototype strict threshold: `track_idx` gap must be less than `85`.
- Returns immutable `Cluster` instances.

### Static World-State Perception

File: `src/autozuma/vision/world_state.py`

Behavior:

- Combines static ROI extraction, launcher state detection, entity detection, and cluster building.
- Accepts explicit `LevelRuntimeAssets` and `LauncherTemplateSet` inputs.
- Returns `WorldState(level_id, launcher, entities, clusters)`.
- Currently supports only static-background levels; `space` remains a special detection gap.

### Basic Strategy Target Scoring

File: `src/autozuma/strategy/targets.py`

Behavior:

- Scores `WorldState` clusters that match the current launcher ball color.
- Produces `TargetCandidate` values for basic `ELIM` and `PAIR` targets.
- Keeps scoring pure and stateless with explicit `TargetScoringParams`.
- Uses distance, shot/track orthogonality, local straightness, and bad-geometry penalty terms from the prototype baseline.
- Does not yet handle combo depth, rollback, coins, line-of-sight, swaps, prediction, locks, or command generation.

### Strategy Line-Of-Sight

File: `src/autozuma/strategy/line_of_sight.py`

Behavior:

- Checks launcher-to-target ray clearance against detected `BallEntity` instances.
- Preserves prototype clearance rules, target-cluster exclusion, and same-track near-target tolerance.
- Returns `LineOfSightResult(is_clear, min_distance)`.
- Does not yet select targets or generate commands.

### Strategy Target Selection

File: `src/autozuma/strategy/selection.py`

Behavior:

- Sorts scored `TargetCandidate` values by score.
- Uses `check_line_of_sight()` to skip blocked candidates.
- Passes target topology metadata into line-of-sight filtering.
- Returns the best clear candidate or `None`.
- Does not yet handle prediction, cooldown, swaps, fallback discard, or command generation.

### Basic Strategy Command Generation

File: `src/autozuma/strategy/commands.py`

Behavior:

- Converts a selected `TargetCandidate` into a `CommandType.SHOOT` command at the ROI-local target point.
- Converts missing target selection into `CommandType.NO_OP`.
- Does not yet handle ROI-to-screen offsets, prediction, double shots, swaps, cooldowns, locks, fallback discard, or mouse execution.

### ROI-To-Screen Command Mapping

File: `src/autozuma/control/commands.py`

Behavior:

- Converts ROI-local `Command` target points into screen-frame coordinates using `GameRoiResult.offset`.
- Offsets both primary and secondary targets when present.
- Preserves command type and delay.
- Leaves targetless commands targetless.
- Does not execute mouse input or enforce runtime cooldowns.

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

- `pytest`: 69 passed
- `ruff check`: all checks passed
- asset CLI: passed with the expected `space` note

## Next Recommended Step

The next clean step is to add a static-frame decision pipeline that composes perception, scoring, selection, command generation, and ROI-to-screen mapping.

Suggested scope:

- Keep it pure and single-frame: no live capture, mouse execution, cooldowns, or locks.
- Accept a raw frame, level assets, launcher templates, and strategy parameters.
- Return a screen-frame `Command`.
- Add tests with mocked or synthetic perception outputs for target and no-target paths.

Do not migrate UI handling, mouse execution, runtime cooldowns, swaps, or fallback discard in the same step unless there is a specific reason.

## Design Rules To Preserve

- Preserve behavior first, then improve structure.
- Keep raw topology separate from derived geometry.
- Avoid reintroducing mutable global registries.
- Keep `space` special-case handling explicit.
- Add tests for each migrated behavior slice.
- Update `docs/migration_log.md` after each completed migration step.
