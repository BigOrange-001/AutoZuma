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
- Strategy target scoring with basic, combo, and rollback target classes.
- Strategy line-of-sight filtering.
- Strategy target selection.
- Basic strategy command generation.
- ROI-to-screen command coordinate mapping.
- Pure static-frame decision pipeline for static-background levels.
- Pure target-coordinate prediction along dense track geometry.
- Pure swap decision based on current-ball versus next-ball target scores.
- Pure fallback discard target selection.
- Pure command variants for `DOUBLE_SHOOT` and `SWAP_DOUBLE_SHOOT`.
- Pure coin target scoring for direct and breakthrough coin shots.
- Active coin detection/tracking with explicit state and locks.
- Action tracker state for deadzones, cluster locks, and virtual balls.
- Lock-aware target scoring using action deadzones and cluster locks.
- Pure virtual-ball cluster-size injection.
- Pure command-result action updates and cooldown planning.
- Rich static-frame decision results and pure stateful static-frame fire/swap gating.
- Pure runtime rescue/endgame mode detection and mode-scoped parameter resolution.
- Pure runtime strategy-parameter adapter from raw/shared params into pipeline params.

No live game automation, mouse execution, GUI, frame capture, UI state handling, swap execution, or command execution has been done yet.

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

`TargetCandidate` now includes optional combo depth, topology context fields for track id, target track index, and cluster start/end indices, plus optional secondary target coordinates and delay metadata for double-shot command variants.

`Cluster` now includes `virtual_size_bonus`; `Cluster.size` is detected entity count plus virtual size bonus.

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
- Also exposes `detect_static_world_state_from_roi()` for callers that have already extracted an aligned ROI and need the ROI offset for downstream coordinate mapping.
- Accepts explicit `LevelRuntimeAssets` and `LauncherTemplateSet` inputs.
- Returns `WorldState(level_id, launcher, entities, clusters)`.
- Currently supports only static-background levels; `space` remains a special detection gap.

### Active Coin Detection And Tracking

File: `src/autozuma/vision/coins.py`

Behavior:

- Detects coin presence from aligned grayscale ROI and background frames at known topology treasure points.
- Preserves prototype detection thresholds: ROI radius `12`, diff threshold `40`, active pixel count `>55`.
- Uses explicit immutable `CoinTrackerState` instead of hidden mutable state.
- Preserves prototype active lifetime window: alive time must be greater than `0.5s` and less than `7.0s`.
- Preserves prototype stale timeout: missing coin tracks are dropped only after more than `0.4s`.
- Preserves prototype lock radius `15` with explicit `CoinLock` values.
- `update_active_coins_from_frame()` returns active coin `Point` values ready to pass into `StaticFrameDecisionParams.active_coins`.
- Uses explicit `current_time`; no `time.time()` calls or live loop ownership.
- Does not score coin targets, execute commands, enforce fire cooldowns, or perform mouse input.

### Strategy Target Scoring

File: `src/autozuma/strategy/targets.py`

Behavior:

- Scores `WorldState` clusters that match the current launcher ball color.
- Produces `TargetCandidate` values for `COMBO`, `ROLLBACK_ELIM`, `ELIM`, and `PAIR` targets.
- Keeps scoring pure and stateless with explicit `TargetScoringParams`.
- Uses distance, shot/track orthogonality, local straightness, and bad-geometry penalty terms from the prototype baseline.
- Preserves prototype combo-depth scanning, rollback classification, same-color adjacent-cluster skipping, and nearby deeper-combo downgrade behavior.
- Coin target scoring is handled separately in `src/autozuma/strategy/coins.py`.
- Does not yet handle line-of-sight selection, locks, or command generation directly.

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
- Does not yet handle cooldown, swaps, or command generation.

### Strategy Prediction

File: `src/autozuma/strategy/prediction.py`

Behavior:

- Applies the prototype target prediction formula to scored `TargetCandidate` values.
- Computes `offset_idx = int(predict_multiplier * distance_to_frog)`.
- Preserves the prototype default `predict_multiplier=0.05`.
- Clamps predicted indices to dense track bounds.
- Replaces target coordinates with the predicted dense track point and updates `track_idx` for downstream line-of-sight filtering.
- Leaves targets without topology metadata unchanged.
- Leaves double-shot targets unchanged so breakthrough coin aim points are not re-predicted.
- Does not compute travel time, update virtual balls, enforce cooldowns, perform swaps, or execute commands.

### Strategy Swap Decision

File: `src/autozuma/strategy/swap.py`

Behavior:

- Compares current-ball and next-ball target candidate sets.
- Preserves the prototype threshold: swap when `next_best_score >= current_best_score * 1.15` and the next score is positive.
- Does not swap when the next ball is unknown or the same color as the current ball.
- Returns a pure `SwapDecision` with `should_swap`, selected candidates, best scores, and a reason.
- Does not handle swap cooldown, right-click execution, runtime state, or UI handling.

### Fallback Discard

File: `src/autozuma/strategy/discard.py`

Behavior:

- Produces a pure `DISCARD` target when no selected clear target exists and the current launcher ball is known.
- Preserves prototype fallback order: nearest clear edge point, reachable gap, size-1 cluster, earliest known cluster, then upward shot.
- Uses line-of-sight for edge and reachable-gap fallback candidates.
- Prefers reachable gaps near same-color clusters.
- Emits normal `SHOOT` through the static-frame decision pipeline.
- Does not handle fire cooldown, mouse execution, action tracker, virtual balls, or locks.

### Strategy Coin Target Scoring

File: `src/autozuma/strategy/coins.py`

Behavior:

- Scores explicitly supplied active coin points; it does not detect or track active coins.
- Preserves prototype direct coin scoring when coin line of sight is clear: `direct_coin` with `coin_priority * 2.0`.
- Preserves prototype breakthrough scoring when exactly one blocking cluster matches the evaluated ball color and has size at least 2: `breakthrough_coin` with `coin_priority * 1.5`.
- Preserves prototype breakthrough aim offset: center entity track index `+15`, clamped to the dense track.
- Preserves prototype breakthrough double-shot delay default: `250 ms`.
- Adds secondary target metadata to breakthrough coin targets so command generation emits `DOUBLE_SHOOT` or `SWAP_DOUBLE_SHOOT`.
- Supports scoring current-ball and next-ball coin targets before the existing pure swap decision.
- Keeps the slice pure and stateless: no coin lifetime tracking, coin locks, frame differencing, cooldowns, action tracker, or mouse execution.

### Action Tracker State

File: `src/autozuma/strategy/actions.py`

Behavior:

- Represents deadzones, cluster locks, and virtual balls as explicit immutable state.
- Uses caller-supplied `current_time`; no hidden `time.time()` reads.
- Provides pure helpers to add deadzones, cluster locks, and virtual balls.
- Provides pure queries for deadzone locks and cluster locks.
- Preserves prototype deadzone behavior: squared distance must be strictly less than `radius ** 2`.
- Preserves prototype cluster lock behavior: same track and default `5` index padding around the locked range.
- Preserves prototype virtual ball expiry behavior: active while `expires_at > current_time`.
- Provides pure virtual-ball cluster-size injection.
- Preserves prototype virtual-ball injection rule: same track, same color, and `cluster.start_idx - 30 <= virtual.track_idx <= cluster.end_idx + 30`.
- Applies each active virtual ball to the first matching cluster, matching the prototype's `break` behavior.
- Provides pruning of expired action-memory entries.
- Command-result updates are handled separately in `src/autozuma/strategy/action_updates.py`.

### Command Outcome Action Updates

File: `src/autozuma/strategy/action_updates.py`

Behavior:

- Represents post-command runtime planning with explicit immutable `CommandOutcomeState`.
- Carries `ActionTrackerState`, `CoinTrackerState`, `last_swap_time`, `next_fire_ready_time`, and `last_fire_time`.
- Uses explicit `current_time`; no hidden `time.time()` reads.
- Preserves prototype bullet speed default `800.0`, fire cooldown default `0.3s`, swap extra fire delay `0.05s`, combo hang defaults `0.8s + combo_depth * 0.6s`, direct coin lock `1.0s`, and breakthrough coin lock `2.0s`.
- `NO_OP` and `UI_CLICK` prune expired state but do not advance fire or swap timestamps.
- `direct_coin` locks the coin, adds a travel-time deadzone, and plans normal fire cooldown.
- `breakthrough_coin` locks the secondary coin, adds a travel-time deadzone at the breakthrough aim point, and plans next fire after double-shot delay plus fire cooldown.
- `COMBO` adds the prototype long target cluster lock, target deadzone, and adjacent non-unknown cluster locks.
- `ELIM` and `ROLLBACK_ELIM` add only a travel-time deadzone and normal fire cooldown.
- `PAIR` adds a travel-time deadzone and virtual ball using the actually fired ball color, including next-ball color for swapped shots.
- `DISCARD` advances only normal fire cooldown.
- Does not sleep, execute mouse input, enforce fire readiness, enforce swap cooldown, or own live-loop state transitions.

### Lock-Aware Target Scoring

File: `src/autozuma/strategy/targets.py`

Behavior:

- `TargetScoringParams` can optionally carry `ActionTrackerState`, `current_time`, and `soft_lock_radius`.
- Target scoring skips a candidate when the candidate center is inside an active deadzone.
- Target scoring skips a candidate when the candidate center track index is inside an active cluster lock.
- Expired action-memory entries are ignored.
- Existing callers keep previous behavior when no action state is supplied.

### Basic Strategy Command Generation

File: `src/autozuma/strategy/commands.py`

Behavior:

- Converts a selected `TargetCandidate` into a `CommandType.SHOOT` command at the ROI-local target point.
- Converts a selected swapped target into `CommandType.SWAP_SHOOT`.
- Converts selected targets with complete secondary target metadata into `CommandType.DOUBLE_SHOOT`.
- Converts swapped selected targets with complete secondary target metadata into `CommandType.SWAP_DOUBLE_SHOOT`.
- Carries target-specific double-shot delays in `Command.delay_ms`.
- Converts missing target selection into `CommandType.NO_OP`.
- Rejects incomplete secondary target metadata.
- Does not yet handle cooldowns, locks, or mouse execution.

### ROI-To-Screen Command Mapping

File: `src/autozuma/control/commands.py`

Behavior:

- Converts ROI-local `Command` target points into screen-frame coordinates using `GameRoiResult.offset`.
- Offsets both primary and secondary targets when present.
- Preserves command type and delay.
- Leaves targetless commands targetless.
- Does not execute mouse input or enforce runtime cooldowns.

### Static Frame Decision Pipeline

File: `src/autozuma/decision/static_frame.py`

Behavior:

- Accepts a raw BGR frame, `LevelRuntimeAssets`, `LauncherTemplateSet`, and `StaticFrameDecisionParams`.
- Extracts the static ROI once, detects world state from that ROI, scores basic targets, selects the best clear target, generates a ROI-local command, and maps it back to screen-frame coordinates.
- Scores both current-ball and next-ball basic/coin targets and applies pure swap decision before prediction.
- Accepts explicit `active_coins` in `StaticFrameDecisionParams`; active coin detection/tracking is not part of this pipeline yet.
- Applies pure target prediction between scoring and line-of-sight selection.
- Returns a screen-frame `Command`.
- Preserves and maps secondary targets for double-shot command variants.
- Returns fallback `CommandType.SHOOT` when no target is selected but discard is available.
- Returns `CommandType.NO_OP` when no target is selected and discard is disabled or unavailable.
- Also exposes `decide_static_frame()` with `StaticFrameDecisionResult` for detailed ROI/world/candidate/swap/target/command output.
- Also exposes `decide_static_frame_from_world()` for already-extracted ROI and perceived world-state callers.
- Also exposes `decide_stateful_static_frame()` with `StatefulStaticFrameDecisionResult`.
- Stateful static-frame decision injects action state into target scoring, applies active virtual balls to clusters, gates swap with the prototype `0.5s` cooldown, gates fire readiness with `next_fire_ready_time`, and calls command-outcome updates only for emitted shoot commands.
- Remains pure and single-frame: no live capture, mouse execution, sleeping, swap execution, or UI handling.

### Runtime Mode Detection

File: `src/autozuma/runtime/modes.py`

Behavior:

- Represents runtime mode as explicit immutable `RuntimeModeState`.
- Provides `initial_runtime_mode_state(current_time)` for prototype-equivalent level reset state.
- Computes rescue mode from entity distance to dense-track end using `TrackGeometry.cumulative_distances`.
- Preserves prototype strict rescue check: `total_length - dist_along_path < rescue_distance_threshold`.
- Computes spawn presence from strict start-distance check: `dist_along_path < endgame_spawn_distance_threshold`.
- Preserves prototype timing windows: sustained spawn for more than `2.0s` clears endgame; missing spawn for more than `3.0s` enters endgame.
- `RuntimeModeState.mode` prioritizes rescue over endgame over normal.
- Keeps live capture, level switching, UI state, and parameter mutation outside this slice.

### Runtime Parameter Resolution

File: `src/autozuma/runtime/params.py`

Behavior:

- Resolves prototype `N_*`, `R_*`, and `E_*` scoped values through `RuntimeParameterResolver`.
- Accepts either `RuntimeMode` or `RuntimeModeState`.
- Uses rescue parameters before endgame parameters when both flags are true, matching runtime mode priority.
- Falls back to an unscoped key, then `0.0`, matching prototype `get_p()`.
- Treats keys case-insensitively so lower-case INI names and upper-case GUI/shared-param names both work.
- Preserves prototype rank-to-weight mapping: `int(rank)`, then `10 ** (6 - rank)`.
- Does not load INI files, own GUI state, or mutate shared params.

### Runtime Strategy Parameter Adapter

File: `src/autozuma/runtime/strategy_config.py`

Behavior:

- Builds concrete `RuntimeStrategyConfig` from a raw mapping plus `RuntimeModeState`.
- Produces `RuntimeModeParams` for rescue/endgame detection.
- Produces `StatefulStaticFrameDecisionParams` and nested `StaticFrameDecisionParams` for the pure static-frame pipeline.
- Maps mode-scoped `FIRE_COOLDOWN`, `M_GAP`, `COMBO_HANG_BASE`, `COMBO_HANG_MULT`, `SOFT_LOCK_RADIUS`, and `PREDICT_MULT`.
- Maps unscoped/general `COIN_BREAK_DELAY`, `TRACK_START_EXCLUDE`, and `TRACK_END_EXCLUDE` through existing resolver fallback behavior.
- Applies `M_GAP` to target selection, coin scoring, and fallback discard.
- Converts `COIN_BREAK_DELAY` seconds to breakthrough coin delay milliseconds and also carries seconds into command outcome planning.
- Maps ranked priorities for coin, combo, rollback elimination, normal elimination, and pair targets.
- Accepts explicit `active_coins` and passes them through to `StaticFrameDecisionParams`.
- Does not read INI files, own GUI state, mutate shared params, capture frames, or execute commands.

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

Last known full-suite results:

- `pytest`: 169 passed
- `ruff check`: all checks passed
- asset CLI: passed with the expected `space` note

Last targeted runtime strategy config check:

- `.venv\Scripts\python -m pytest tests\test_runtime_strategy_config.py tests\test_runtime_params.py`: 10 passed

## Next Recommended Step

The next clean step is to add a pure static-runtime orchestrator state.

Suggested scope:

- Given one already-captured raw frame, current runtime state, raw/shared params, level assets, and launcher templates, run the pure static frame pipeline end-to-end.
- Thread `RuntimeModeState`, `CommandOutcomeState`, and `CoinTrackerState` through a single immutable runtime state object.
- Detect/update active coins from the aligned static ROI before building `RuntimeStrategyConfig`.
- Update runtime mode state from the perceived `WorldState` and current mode params.
- Return the detailed decision result plus updated runtime state.
- Keep actual screen capture, window discovery, mouse execution, GUI controls, and UI-state clicks outside this slice.

## Design Rules To Preserve

- Preserve behavior first, then improve structure.
- Keep raw topology separate from derived geometry.
- Avoid reintroducing mutable global registries.
- Keep `space` special-case handling explicit.
- Add tests for each migrated behavior slice.
- Update `docs/migration_log.md` after each completed migration step.
