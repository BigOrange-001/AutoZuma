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
