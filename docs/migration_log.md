# Migration Log

## 2026-05-14

### Strategy Command Variants Baseline

Migrated the pure command-object representation for prototype double-shot command variants.

Added:

- Secondary target and delay metadata on `TargetCandidate`.
- `DOUBLE_SHOOT` and `SWAP_DOUBLE_SHOOT` generation in `src/autozuma/strategy/commands.py`.
- Command variant tests in `tests/test_strategy_commands.py`.
- Static-frame command mapping coverage in `tests/test_static_frame_decision.py`.

Behavior:

- A selected target without a secondary target still emits `SHOOT` or `SWAP_SHOOT`.
- A selected target with both `secondary_x` and `secondary_y` emits `DOUBLE_SHOOT`.
- A swapped selected target with a secondary target emits `SWAP_DOUBLE_SHOOT`.
- Double-shot commands carry the target-specific inter-shot delay in milliseconds.
- Incomplete secondary target metadata is rejected instead of producing a partial command.
- The static-frame decision pipeline maps both primary and secondary ROI-local targets into screen-frame coordinates.
- Keeps command generation pure and stateless: no mouse execution, swap cooldown, coin tracking, runtime locks, or UI handling.

Validation:

- `.venv\Scripts\python -m pytest tests\test_strategy_commands.py tests\test_control_commands.py tests\test_static_frame_decision.py` passed: 15 tests.
- `.venv\Scripts\python -m pytest` passed: 102 tests.
- `.venv\Scripts\python -m ruff check .` passed.
- `.venv\Scripts\python -m autozuma.cli.validate_assets` passed with the expected `space` special-detection note.

### Strategy Coin Target Scoring Baseline

Migrated the pure coin target-scoring portion of the prototype strategy loop.

Added:

- `src/autozuma/strategy/coins.py`.
- `CoinScoringParams` on `StaticFrameDecisionParams`.
- Explicit `active_coins` input on `StaticFrameDecisionParams`.
- Coin scoring tests in `tests/test_strategy_coins.py`.
- Static-frame active coin coverage in `tests/test_static_frame_decision.py`.

Behavior:

- Scores already-detected active coin points without owning coin tracking state.
- Preserves prototype direct coin scoring: clear coin line of sight emits `direct_coin` with `coin_priority * 2.0`.
- Preserves prototype breakthrough coin scoring: exactly one blocking same-color cluster with size at least 2 emits `breakthrough_coin` with `coin_priority * 1.5`.
- Uses the prototype breakthrough aim offset of `+15` dense track indices.
- Uses the prototype breakthrough double-shot delay default of `250 ms`.
- Breakthrough coin targets carry secondary target metadata so command generation emits `DOUBLE_SHOOT` or `SWAP_DOUBLE_SHOOT`.
- Current-ball and next-ball coin candidates are both scored before the existing pure swap decision.
- Prediction leaves double-shot targets unchanged so breakthrough aim points are not moved a second time.
- Keeps the slice pure and single-frame: no live capture, coin lifetime tracking, coin locks, mouse execution, runtime cooldowns, or action locks.

Validation:

- `.venv\Scripts\python -m pytest tests\test_strategy_coins.py tests\test_strategy_prediction.py tests\test_strategy_commands.py tests\test_static_frame_decision.py` passed: 27 tests.
- `.venv\Scripts\python -m pytest` passed: 112 tests.
- `.venv\Scripts\python -m ruff check .` passed.
- `.venv\Scripts\python -m autozuma.cli.validate_assets` passed with the expected `space` special-detection note.

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

### Static Frame Decision Pipeline Baseline

Added the first pure single-frame decision pipeline for static-background levels.

Added:

- `src/autozuma/decision/__init__.py`.
- `src/autozuma/decision/static_frame.py`.
- `detect_static_world_state_from_roi()` in `src/autozuma/vision/world_state.py`.
- Static-frame decision tests in `tests/test_static_frame_decision.py`.

Behavior:

- Accepts one raw BGR frame, explicit `LevelRuntimeAssets`, `LauncherTemplateSet`, and decision params.
- Extracts the aligned static game ROI once.
- Builds `WorldState` from the aligned ROI.
- Scores basic targets, filters by line of sight, converts the selected target into a command, and maps ROI-local target coordinates back to screen-frame coordinates.
- Returns `CommandType.NO_OP` when no target is selected.
- Remains pure and single-frame: no live capture, mouse execution, cooldowns, locks, swaps, fallback discard, or UI handling.

Validation:

- `.venv\Scripts\python -m pytest` passed: 72 tests.
- `.venv\Scripts\python -m ruff check AutoZumaNext` passed from the parent workspace.
- `.venv\Scripts\python -m autozuma.cli.validate_assets` passed with the expected `space` special-detection note.

### Strategy Prediction Baseline

Migrated the pure target-coordinate prediction slice from the prototype command-selection loop.

Added:

- `src/autozuma/strategy/prediction.py`.
- Prediction parameters on `StaticFrameDecisionParams`.
- Prediction tests in `tests/test_strategy_prediction.py`.

Behavior:

- Uses the prototype prediction formula: `offset_idx = int(PREDICT_MULT * distance_to_frog)`.
- Preserves the prototype default `PREDICT_MULT` value of `0.05`.
- Clamps predicted track indices to the dense track bounds.
- Replaces candidate coordinates with the dense track point at the predicted index.
- Updates candidate `track_idx` so line-of-sight filtering checks the predicted shot point.
- Leaves candidates without topology metadata unchanged.
- Keeps prediction pure and stateless: no bullet travel time, cooldowns, virtual balls, mouse execution, swaps, fallback discard, or runtime memory.

Validation:

- `.venv\Scripts\python -m pytest` passed: 77 tests.
- `.venv\Scripts\python -m ruff check AutoZumaNext` passed from the parent workspace.
- `.venv\Scripts\python -m autozuma.cli.validate_assets` passed with the expected `space` special-detection note.

### Strategy Swap Decision Baseline

Migrated the pure score-comparison portion of the prototype swap decision.

Added:

- `src/autozuma/strategy/swap.py`.
- `score_basic_targets_for_color()` in `src/autozuma/strategy/targets.py`.
- Swap parameters on `StaticFrameDecisionParams`.
- Swap command support in `src/autozuma/strategy/commands.py`.
- Swap tests in `tests/test_strategy_swap.py`.

Behavior:

- Scores current-ball candidates and next-ball candidates separately.
- Uses the prototype swap comparison threshold: `next_best_score >= current_best_score * 1.15`.
- Requires next-ball score to be positive.
- Does not swap when the next ball is unknown or matches the current ball.
- Selects the next-ball candidate set when swapping, then applies existing prediction and line-of-sight selection.
- Emits `CommandType.SWAP_SHOOT` when a swapped target is selected.
- Keeps swap logic pure and stateless: no swap cooldown, right-click execution, mouse input, runtime locks, or UI handling.

Validation:

- `.venv\Scripts\python -m pytest` passed: 85 tests.
- `.venv\Scripts\python -m ruff check AutoZumaNext` passed from the parent workspace.
- `.venv\Scripts\python -m autozuma.cli.validate_assets` passed with the expected `space` special-detection note.

### Strategy Combo And Rollback Scoring Baseline

Migrated the pure combo/rollback target-classification portion of prototype greedy scoring.

Added:

- `COMBO` and `ROLLBACK_ELIM` target types in `src/autozuma/strategy/targets.py`.
- Combo and rollback priorities on `TargetScoringParams`.
- `combo_depth` metadata on `TargetCandidate`.
- Combo/rollback scoring tests in `tests/test_strategy_targets.py`.

Behavior:

- Scores same-color clusters as `COMBO` when removing the target cluster would connect same-track, same-color neighbor clusters with combined size at least 3.
- Preserves the prototype combo-depth scan, including skipping `unknown` clusters while looking left and right.
- Adds the prototype depth bonus term, capped at `2.0`.
- Scores `ROLLBACK_ELIM` when the immediate non-unknown neighbors on both sides are same-track, same-color, and not the fired color.
- Preserves the prototype behavior that skips targets adjacent to another same-color cluster on the same track.
- Preserves the prototype downgrade behavior where an elimination target near a deeper combo is scored with pair priority.
- Keeps scoring pure and stateless: no action tracker, virtual balls, locks, cooldowns, or execution behavior.

Validation:

- `.venv\Scripts\python -m pytest` passed: 90 tests.
- `.venv\Scripts\python -m ruff check AutoZumaNext` passed from the parent workspace.
- `.venv\Scripts\python -m autozuma.cli.validate_assets` passed with the expected `space` special-detection note.

### Fallback Discard Baseline

Migrated the pure fallback discard target-selection portion of the prototype decision loop.

Added:

- `src/autozuma/strategy/discard.py`.
- `DiscardParams` on `StaticFrameDecisionParams`.
- Fallback discard tests in `tests/test_strategy_discard.py`.
- Static-frame fallback coverage in `tests/test_static_frame_decision.py`.

Behavior:

- Runs fallback only when no selected clear target exists and the current launcher ball is known.
- Preserves the prototype fallback order:
  - nearest clear edge point;
  - reachable gap between nearby different-color clusters;
  - size-1 cluster;
  - earliest known cluster;
  - upward shot from the frog pivot.
- Uses line-of-sight checks for edge and reachable-gap candidates.
- Prefers reachable gaps near same-color clusters when possible.
- Emits a normal `SHOOT` command for fallback, not a swap command.
- Keeps fallback pure and stateless: no fire cooldown, mouse execution, action tracker, virtual balls, or locks.

Validation:

- `.venv\Scripts\python -m pytest` passed: 98 tests.
- `.venv\Scripts\python -m ruff check AutoZumaNext` passed from the parent workspace.
- `.venv\Scripts\python -m autozuma.cli.validate_assets` passed with the expected `space` special-detection note.
