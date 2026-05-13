# Migration Log

## 2026-05-13

### Asset Migration Baseline

Created the first migrated asset layout under `AutoZumaNext/assets`.

Migrated:

- 21 static level background images from `assets/level_background/*.jpg` to `assets/levels/backgrounds`.
- 22 topology JSON files from `assets/decoded_tensors/*.json` to `assets/levels/topology`.
- `SMALLFROGonPAD.png` to `assets/templates/launcher`.
- `ui_ok.png` and `ui_continue.png` to `assets/templates/ui`.

Validation:

- Background count: 21.
- Topology count: 22.
- Launcher template count: 1.
- UI template count: 2.
- Static background and topology names match except for `space.json`.

Notes:

- `space.json` is intentionally migrated without a matching background image. It represents a dynamic-background special map and requires custom detection logic in a later migration step.
- Runtime screenshots, debug captures, `__pycache__`, and old source modules were not migrated.

### Asset Model And Validation Baseline

Added the first source-code layer for migrated asset handling.

Added:

- Core data models in `src/autozuma/core/models.py`.
- Asset path helpers in `src/autozuma/assets/paths.py`.
- Topology JSON loader in `src/autozuma/assets/loader.py`.
- Asset validation report and rules in `src/autozuma/assets/validator.py`.
- Asset validation CLI in `src/autozuma/cli/validate_assets.py`.
- Loader and validator tests in `tests/`.

Behavior:

- Single-track `control_points` and multi-track `track_N.control_points` files are normalized into `LevelTopology.tracks`.
- `space` is treated as a special-detection level and is allowed to have no static background.
- Missing static backgrounds for non-special levels are validation errors.
- Missing launcher/UI templates are validation errors.

Validation:

- `py -m autozuma.cli.validate_assets` passed from the `src` directory.
- CLI result: 21 backgrounds, 22 topologies, 22 levels.
- Expected note: `space` has no static background and requires special detection.
- `py -m compileall src tests` passed.
- `py -m pytest` could not run because `pytest` is not installed in the current environment.

### Local Development Environment

Created a local virtual environment at `.venv` and installed the project in editable mode with development dependencies.

Commands used:

- `py -m venv .venv`
- `.venv\Scripts\python -m pip install -e .[dev]`

Installed dev tools:

- `pytest`
- `ruff`

Post-install validation:

- `.venv\Scripts\python -m pytest` passed: 9 tests.
- `.venv\Scripts\python -m autozuma.cli.validate_assets` passed.
- CLI result remained 21 backgrounds, 22 topologies, 22 levels, with the expected `space` special-detection note.

### Topology Geometry Baseline

Added the first pure topology-geometry layer.

Added:

- `TrackGeometry` and `LevelGeometry` models.
- `src/autozuma/topology/geometry.py`.
- `docs/topology.md`.
- Geometry regression tests in `tests/test_topology_geometry.py`.

Behavior:

- Raw `LevelTopology` remains the source asset model and stores only decoded control points.
- `LevelGeometry` is derived from `LevelTopology`.
- Each source track is converted into a dense Catmull-Rom sampled track.
- Each dense track receives cumulative distances starting at `0.0`.
- The dynamic-background `space` topology can build geometry like all other levels.

Validation:

- `.venv\Scripts\python -m pytest` passed: 15 tests.
- `.venv\Scripts\python -m autozuma.cli.validate_assets` passed.

### Runtime Asset Registry Baseline

Added the first runtime-ready visual asset loading layer.

Added:

- `ImageAsset`, `LevelRuntimeAssets`, `TemplateAssets`, and `AssetRegistry` models.
- Unicode-safe OpenCV image loading in `src/autozuma/vision/image_io.py`.
- Runtime registry builder in `src/autozuma/assets/registry.py`.
- Registry tests in `tests/test_assets_registry.py`.

Behavior:

- `load_asset_registry()` combines topology, derived geometry, static backgrounds, launcher templates, and UI templates.
- Static level backgrounds are loaded as BGR and grayscale image pairs.
- Launcher and UI templates are loaded as BGR and grayscale image pairs.
- `space` is included in the registry with topology and geometry, but with `background=None` and `requires_special_detection=True`.
- Registry construction validates assets before loading image data.

Validation:

- `.venv\Scripts\python -m pytest` passed: 20 tests.
- `.venv\Scripts\python -m autozuma.cli.validate_assets` passed.
- `.venv\Scripts\python -m ruff check .` passed.

### Session Handoff

Added `docs/session_handoff.md` as the quick-start document for continuing the refactor in a new conversation.

The handoff records:

- Current completed layers.
- Important paths.
- Implemented modules.
- Migrated asset counts.
- Verification commands and last known results.
- Recommended next step: static level recognition migration.

Updated `README.md` with a link to the handoff document.

### Static Level Recognition Baseline

Migrated the first perception slice from prototype `vision/detector.py::auto_detect_level`.

Added:

- `LevelDetectionResult` model.
- `src/autozuma/vision/level_recognition.py`.
- Static level recognition tests in `tests/test_level_recognition.py`.

Behavior:

- Uses `AssetRegistry` instead of mutable global `LEVEL_ASSETS`.
- Matches raw BGR frames against migrated static background grayscale images with `cv2.TM_CCOEFF_NORMED`.
- Preserves the prototype confidence threshold of `0.25`.
- Returns `None` when no static level clears the threshold.
- Returns structured `LevelDetectionResult(level_id, confidence, match_location)`.
- Skips `space` and any future level marked `requires_special_detection`.

Validation:

- `.venv\Scripts\python -m pytest` passed: 24 tests.
- `.venv\Scripts\python -m ruff check .` passed.
- `.venv\Scripts\python -m autozuma.cli.validate_assets` passed with the expected `space` special-detection note.

### Static ROI Extraction Baseline

Migrated the next perception slice from prototype `vision/detector.py::extract_game_roi_ncc`.

Added:

- `GameRoiResult` model.
- `RoiExtractionError` domain exception.
- `src/autozuma/vision/roi.py`.
- ROI extraction tests in `tests/test_roi.py`.

Behavior:

- Uses `LevelRuntimeAssets.background` instead of prototype global background data.
- Locates a static level background inside a larger raw BGR frame with `cv2.TM_CCOEFF_NORMED`.
- Returns a copied ROI frame, top-left offset, and NCC confidence.
- Rejects frames smaller than the static background.
- Rejects `space` and other levels without a static background.

Validation:

- `.venv\Scripts\python -m pytest` passed: 28 tests.
- `.venv\Scripts\python -m ruff check .` passed.
- `.venv\Scripts\python -m autozuma.cli.validate_assets` passed with the expected `space` special-detection note.

### Launcher Template Generation Baseline

Migrated the launcher template generation slice from prototype `vision/detector.py::init_template_cache`.

Added:

- `LauncherTemplate` and `LauncherTemplateSet` models.
- `src/autozuma/vision/launcher_templates.py`.
- Launcher template generation tests in `tests/test_launcher_templates.py`.

Behavior:

- Uses `registry.templates.launcher_frog` instead of writing to global `FROG_TEMPLATES`.
- Preserves the prototype default search radius of `50`.
- Preserves the prototype default angle step of `5` degrees.
- Aligns the launcher frog asset into a `search_radius * 2` square ROI.
- Generates rotated grayscale templates, eroded match masks, and dilated subtraction masks for each angle.

Validation:

- `.venv\Scripts\python -m pytest` passed: 32 tests.
- `.venv\Scripts\python -m ruff check .` passed.
- `.venv\Scripts\python -m autozuma.cli.validate_assets` passed with the expected `space` special-detection note.

### Launcher State Detection Baseline

Migrated launcher state detection from prototype `vision/detector.py::detect_launcher_state_residual` and its required color helper.

Added:

- `src/autozuma/vision/colors.py`.
- `src/autozuma/vision/launcher_state.py`.
- Color classification tests in `tests/test_colors.py`.
- Launcher state tests in `tests/test_launcher_state.py`.

Behavior:

- Uses `LauncherTemplateSet` instead of prototype global `FROG_TEMPLATES`.
- Finds the best launcher angle by minimizing grayscale residual over each template match mask.
- Classifies current and next ball colors using the migrated HSV target-color logic.
- Returns `LauncherState` instead of a dictionary.
- Returns an explicit unknown state when templates are missing or the launcher search ROI is clipped.

Validation:

- `.venv\Scripts\python -m pytest` passed: 37 tests.
- `.venv\Scripts\python -m ruff check .` passed.
- `.venv\Scripts\python -m autozuma.cli.validate_assets` passed with the expected `space` special-detection note.

### Stateless Ball Entity Detection Baseline

Migrated ball-chain entity detection from prototype `vision/detector.py::detect_entities_stateless`.

Added:

- `src/autozuma/vision/entities.py`.
- Entity detection tests in `tests/test_entities.py`.

Behavior:

- Uses static background differencing to isolate foreground pixels.
- Gates foreground pixels with a dense track mask.
- Uses morphology and distance transform peaks to find ball centers.
- Projects each peak to the nearest dense track point.
- Applies start/end track exclusion distances.
- Classifies each detected ball with the migrated HSV color classifier.
- Returns `BallEntity` instances instead of dictionaries.

Validation:

- `.venv\Scripts\python -m pytest` passed: 41 tests.
- `.venv\Scripts\python -m ruff check .` passed.
- `.venv\Scripts\python -m autozuma.cli.validate_assets` passed with the expected `space` special-detection note.

### Topological Cluster Building Baseline

Migrated cluster construction from prototype `vision/detector.py::build_topological_clusters`.

Added:

- `src/autozuma/vision/clusters.py`.
- Cluster-building tests in `tests/test_clusters.py`.

Behavior:

- Consumes ordered `BallEntity` instances and returns immutable `Cluster` instances.
- Groups adjacent entities only when they remain on the same track, have the same color, and have a track-index gap less than `85`.
- Preserves the prototype's strict threshold behavior: a gap of `84` joins, while a gap of `85` starts a new cluster.
- Empty input returns an empty tuple.

Validation:

- `.venv\Scripts\python -m pytest` passed: 46 tests.
- `.venv\Scripts\python -m ruff check AutoZumaNext` passed from the parent workspace.
- `.venv\Scripts\python -m autozuma.cli.validate_assets` passed with the expected `space` special-detection note.

### Static World-State Perception Baseline

Added the first orchestration layer that assembles the already-migrated static perception slices.

Added:

- `src/autozuma/vision/world_state.py`.
- World-state orchestration tests in `tests/test_world_state.py`.

Behavior:

- Accepts an explicit raw BGR frame, `LevelRuntimeAssets`, and `LauncherTemplateSet`.
- Extracts the aligned static ROI.
- Detects launcher state from the aligned ROI and level frog pivot.
- Detects ball entities for all level tracks.
- Builds topological clusters from detected entities.
- Returns `WorldState(level_id, launcher, entities, clusters)`.
- Still rejects `space` and any level without a static background through the static ROI extraction path.

Validation:

- `.venv\Scripts\python -m pytest` passed: 48 tests.
- `.venv\Scripts\python -m ruff check AutoZumaNext` passed from the parent workspace.
- `.venv\Scripts\python -m autozuma.cli.validate_assets` passed with the expected `space` special-detection note.

### Basic Strategy Target Scoring Baseline

Started the new strategy layer with a pure target-scoring slice.

Added:

- `src/autozuma/strategy/__init__.py`.
- `src/autozuma/strategy/targets.py`.
- Basic strategy target tests in `tests/test_strategy_targets.py`.

Behavior:

- Consumes `WorldState`, `LevelRuntimeAssets`, and `TargetScoringParams`.
- Returns sorted `TargetCandidate` instances.
- Ignores unknown current-ball colors.
- Scores only clusters matching the current launcher ball color.
- Maps same-color clusters with size `>= 2` to `ELIM` targets.
- Maps same-color single-ball clusters to `PAIR` targets.
- Preserves the prototype's basic distance, shot/track orthogonality, local straightness, and bad-geometry penalty scoring terms.
- Does not yet include combo depth, rollback, coins, action locks, line-of-sight, swap decisions, prediction, or command generation.

Validation:

- `.venv\Scripts\python -m pytest` passed: 53 tests.
- `.venv\Scripts\python -m ruff check AutoZumaNext` passed from the parent workspace.
- `.venv\Scripts\python -m autozuma.cli.validate_assets` passed with the expected `space` special-detection note.

### Strategy Line-Of-Sight Baseline

Migrated the pure shot-clearance portion of prototype `logic/decision.py::check_line_of_sight_ext`.

Added:

- `src/autozuma/strategy/line_of_sight.py`.
- Line-of-sight tests in `tests/test_line_of_sight.py`.

Behavior:

- Checks whether the ray from launcher pivot to target point is blocked by detected `BallEntity` instances.
- Preserves the prototype physical clearance floor of `36` pixels.
- Applies caller-provided `min_gap` when it is larger than the physical clearance floor.
- Ignores entities too close to the target point.
- Ignores entities inside the selected target cluster's padded track-index range.
- Ignores same-track entities near the target to avoid false blockers on curved local track geometry.
- Returns structured `LineOfSightResult(is_clear, min_distance)`.

Validation:

- `.venv\Scripts\python -m pytest` passed: 59 tests.
- `.venv\Scripts\python -m ruff check AutoZumaNext` passed from the parent workspace.
- `.venv\Scripts\python -m autozuma.cli.validate_assets` passed with the expected `space` special-detection note.

### Strategy Target Selection Baseline

Added the first pure selector that combines scored targets with line-of-sight filtering.

Added:

- Optional topology context fields on `TargetCandidate`.
- `src/autozuma/strategy/selection.py`.
- Target-selection tests in `tests/test_target_selection.py`.

Behavior:

- `score_basic_targets()` now annotates targets with track id, center track index, and cluster start/end indices.
- `select_best_clear_target()` sorts candidates by score and returns the highest-scoring candidate whose launcher-to-target path is clear.
- Passes candidate topology metadata into line-of-sight filtering so target-cluster balls are not treated as blockers.
- Returns `None` when no candidate has a clear path.
- Still does not generate commands, apply prediction, inspect cooldowns, perform swaps, or run fallback discard logic.

Validation:

- `.venv\Scripts\python -m pytest` passed: 64 tests.
- `.venv\Scripts\python -m ruff check AutoZumaNext` passed from the parent workspace.
- `.venv\Scripts\python -m autozuma.cli.validate_assets` passed with the expected `space` special-detection note.

### Basic Strategy Command Generation Baseline

Added the first pure conversion from selected target to command object.

Added:

- `src/autozuma/strategy/commands.py`.
- Basic command generation tests in `tests/test_strategy_commands.py`.

Behavior:

- `command_for_selected_target(None)` returns `CommandType.NO_OP`.
- A selected `TargetCandidate` returns a single `CommandType.SHOOT` command at the candidate's ROI-local point.
- Does not yet apply ROI-to-screen offsets, prediction, double shots, swaps, cooldowns, action locks, virtual balls, fallback discard, or mouse execution.

Validation:

- `.venv\Scripts\python -m pytest` passed: 66 tests.
- `.venv\Scripts\python -m ruff check AutoZumaNext` passed from the parent workspace.
- `.venv\Scripts\python -m autozuma.cli.validate_assets` passed with the expected `space` special-detection note.

### ROI-To-Screen Command Mapping Baseline

Added the first control-layer transformation from ROI-local command coordinates to screen-frame command coordinates.

Added:

- `src/autozuma/control/__init__.py`.
- `src/autozuma/control/commands.py`.
- Control command mapping tests in `tests/test_control_commands.py`.

Behavior:

- `map_command_to_screen()` accepts a `Command` and `GameRoiResult`.
- Offsets primary and secondary command targets by `GameRoiResult.offset`.
- Preserves command type and delay.
- Leaves commands without targets as targetless commands.
- Does not execute mouse input, apply prediction, perform cooldown checks, handle swaps, or implement fallback discard.

Validation:

- `.venv\Scripts\python -m pytest` passed: 69 tests.
- `.venv\Scripts\python -m ruff check AutoZumaNext` passed from the parent workspace.
- `.venv\Scripts\python -m autozuma.cli.validate_assets` passed with the expected `space` special-detection note.
