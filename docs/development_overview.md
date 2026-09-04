# AutoZuma Development Overview

This document records the current implementation as a development baseline. It is
intended to describe the code that is actually on the active branch, rather than
older migration plans that may no longer match runtime behavior.

## Project Purpose

AutoZuma Next is a Windows visual-automation client for Zuma Deluxe. It uses
deterministic computer vision, decoded per-level topology, rule-based target scoring,
and explicit Win32 input adapters. It is not a machine-learning or reinforcement-
learning system.

The current implementation targets the original 640x480 game client. Static level
backgrounds and topology are first-class runtime assets.

## Main Runtime Path

The normal GUI path is:

1. `launcher.bat` starts `python -m autozuma.gui.app`.
2. The PySide6 GUI starts in Safe state.
3. Arm starts a synchronous 100 ms frame timer and enables command execution.
4. Each frame locates a visible Zuma Deluxe client window and captures its client rect.
5. UI, result-dialog, and Adventure-menu automation run before gameplay.
6. Detecting sessions identify a static level from its background image.
7. Playing sessions align the level ROI, perceive the world, update runtime state,
   select a command, and optionally execute it.
8. The GUI renders an in-memory diagnostic overlay. Periodic debug output writes an
   overlay PNG under `debug/`.

The CLI uses the same session/runtime pipeline, with a paced loop and fixed F1/F2/F3
Win32 hotkeys.

## Runtime Boundaries

The implementation is deliberately layered:

- `assets` loads and validates backgrounds, topology, and templates.
- `topology` turns sparse control points into dense Catmull-Rom tracks and cumulative
  distances.
- `vision` aligns the ROI and detects launcher state, balls, colors, clusters, and coins.
- `strategy` scores targets, checks reachability, chooses swaps and fallback discards,
  and maintains action memory.
- `decision` converts one perceived frame into an explicit command.
- `runtime` owns modes, session state, UI precedence, result capture, and live loops.
- `control` maps ROI coordinates to client coordinates and performs Win32 input.
- `gui` exposes live controls, parameters, preview, and a transient event log.

Pure data and decision functions are kept separate from capture, filesystem, sleeping,
and mouse side effects.

## Assets And Supported Levels

The repository contains 22 topology files and 21 static backgrounds. All 22 levels are
supported: `space` uses a dedicated dynamic-background path, while the other 21 levels,
including multi-track levels, use static background matching and subtraction.

All static backgrounds are 640x480. Topology provides:

- the frog pivot;
- one or more ordered tracks;
- treasure points;
- control-point flags used to distinguish visible track sections from tunnel/occluded
  sections.

Level IDs are canonicalized to lowercase when topology is loaded. The registry,
topology, dense geometry, recognition result, and runtime session therefore share the
same identifier even when an asset filename such as `Groovefest.json` contains capitals.

Dense tracks retain a visibility-region id for every sampled point. Region `-1` is an
occluded/unshootable segment; non-negative ids identify separate visible sequence
regions. This prevents hidden tunnel sections from being treated as ordinary visible
ball-chain geometry.

## Perception

### Level and ROI

Static level recognition uses grayscale `TM_CCOEFF_NORMED` matching against all static
backgrounds. After a level is selected, the same background is used to align a 640x480
ROI inside the captured client frame.

The dynamic `space` level is recognized without a background template. A sparse sample
of the playfield measures the stable black/purple nebula palette and requires separate
minimum ratios for purple, bright purple, and dark pixels. This distinguishes the live
scene from all 21 static backgrounds and rejects the observed dimmed pause layer and
pause-menu frame. Live capture already supplies the unscaled 640x480 client area, so the
space ROI uses that frame directly rather than running an alignment search.

### Launcher

The frog template is rotated in 5-degree steps. The lowest masked grayscale error gives
the launcher angle, after which fixed offsets sample the current and next ball colors.
The smaller next-ball sample additionally requires minimum brightness, enough valid
color pixels, and a dominant-color vote, so a briefly exposed dark background is not
accepted as a white ball. The reported launcher confidence is diagnostic; it is not
currently a decision gate.

Next-ball strategy is also temporally gated: the live runtime requires three consecutive
matching frame observations before swap scoring may use the color. Any conflicting or
unknown observation invalidates it immediately, and every emitted shot clears the
evidence because the launcher queue has advanced. With the 100 ms frame loop and the
normal 350 ms fire cooldown, this reuses frames that already occur during cooldown and
adds only constant-time state updates, not another vision pass.

### Balls and clusters

Ball perception is constrained to dense track geometry:

- grayscale background difference isolates moving foreground;
- morphology cleans the track-local mask;
- distance-transform peaks provide ball centers;
- centers are projected only onto visible track points;
- occluded topology regions are never emitted as shootable entities;
- spatially indistinguishable projections at a multi-track crossing are reduced to one
  assignment using local predecessor/successor support;
- entities carry their visible-region id into topological clusters.

For `space`, where frame subtraction is impossible, the same topology constrains a
high-value HSV mask to a narrow track band. Small star points are removed by morphology,
then distance-transform peaks provide ball centers and the normal color/projection/
cluster path resumes. This is one lightweight mask pass, not template matching for each
ball and not a reconstructed animated background.

Unknown-color entities and hidden-region boundaries are sequence barriers. Strategy is
not allowed to skip through them and invent a combo from observations whose colors are
not known. Likewise, a large missing topological gap prevents clusters on either side
from being treated as adjacent.

This is intentionally conservative. A single frame cannot recover the true color of a
fully hidden ball, so the runtime avoids optimistic combo scoring instead of fabricating
hidden state.

### Coins

Coins are detected only near topology treasure points. Lifetime tracking filters very
short foreground changes, tolerates short disappearances, and supports temporary locks
after coin commands.

## Strategy

The runtime has Normal, Rescue, and Endgame modes. Rescue is triggered by balls close to
the track end and takes priority. Endgame is entered after the spawn region has remained
empty for a timed interval.

Target types include:

- pair insertion;
- normal elimination;
- rollback elimination;
- multi-depth combo;
- direct coin;
- breakthrough coin with a delayed second shot;
- fallback discard.

Scores combine mode-specific priority ranks with distance, shot/track orthogonality,
local track straightness, and combo depth. Finite-width line-of-sight checks reject
blocked targets. The next ball is selected only when its best score clears the configured
swap ratio, its color has passed runtime confirmation, and the swap cooldown is ready.

`PAIR` is reserved for a genuinely observed single-ball cluster. A multi-ball
elimination near a deeper combo may still receive the lower pair-priority score, but it
remains semantically `ELIM`; this keeps both its cluster aim and post-shot lock behavior
consistent with a multi-ball elimination.

Every target whose primary target is a ball uses the shared forward-biased ball-aim
rule after reachability filtering. A single ball, or the middle ball of an odd-sized
reachable sequence, is aimed one ball radius (`16 px`) farther toward increasing track
distance. An even-sized reachable sequence uses its endpoint-side middle ball. This
same rule is used by normal scoring, combo/elimination targets, breakthrough-coin
blockers, and the last-resort cluster discard path.

Coin shots use the projectile as a `32 px`-wide collision strip. The scorer searches
from the coin-center ray outward in one-pixel increments and may choose an off-center
aim ray when it still intersects the coin and avoids blocking balls. The actual coin
coordinate is retained separately so action memory locks the coin rather than the
off-center aim point.

Action memory tracks deadzones, cluster locks, virtual in-flight balls, coin locks, fire
cooldown, and swap cooldown. Locks and combo-chain reasoning are restricted to the same
visible sequence region and do not cross tunnels.

The previous target-coordinate prediction module was removed. Current aim points come
from reachable observed entities and local track geometry.

## Input And Safety Semantics

The GUI starts Safe and does no live frame work until armed. On the current branch, Arm
also enables command execution; there is no separate dry-run checkbox. The default INI
uses virtual/background mouse messages for gameplay.

Menus and result buttons always use a focused physical click because the game can show a
synthetic pressed state while rejecting the corresponding release. Gameplay physical
clicks convert client coordinates to screen coordinates; virtual clicks keep client
coordinates.

GUI hotkeys are persisted in `config/gui_settings.json` and can differ from defaults.
CLI hotkeys remain F1 Arm/Safe, F2 debug snapshot, and F3 Safe.

## UI And Result Capture

OK and Continue templates preempt gameplay. Before an OK click is released, the runtime
tries to recognize and archive either a completed-level STATS screen or a GAME OVER
screen. Failed OCR is retried before a failure screenshot and error text are saved.

Successful results use one append-only CSV per campaign level plus source screenshots.
The grade is encoded by the filename. The current numeric parser validates syntax and
campaign identifiers but does not yet perform strong cross-field plausibility checks.

While detecting, Adventure-menu automation requires OCR evidence for both ADVENTURE and
PLAY before clicking the normalized doorway target.

## Current Diagnostics And Evidence

The GUI event log is in-memory only and retains its most recent lines. Persisted runtime
evidence currently consists of:

- overlay PNGs in `debug/`;
- per-level CSV files and screenshots in `grade/`;
- OCR failure PNG/TXT pairs in `grade/failed/`;
- optional GAME OVER archives in `grade/gameover/`.

`build_debug_summary()` can build structured diagnostic data, but the current file sink
writes only overlay PNGs.

## Current Limitations

- Dynamic `space` support assumes the normal unscaled 640x480 Zuma client capture;
  arbitrary resized/fullscreen rendering is rejected because topology coordinates would
  no longer align.
- Fully hidden ball colors cannot be reconstructed from a single frame; occluded regions
  therefore use conservative sequence barriers.
- There is no game-process launcher/restart supervisor or shared-memory orchestration.
- GUI frame capture, OCR, strategy, waits, and rendering are synchronous.
- GUI FPS is fixed by its 100 ms timer; the controller's `fps` field is not wired to it.
- `detailed_analysis`, `coin_hang_time`, and `gap_priority_th` are reserved values that do
  not currently affect decision behavior.
- Result OCR lacks semantic plausibility validation and transactional screenshot/CSV
  persistence.
- Some older migration documentation still describes removed prediction and dry-run
  behavior; this overview and the current code are authoritative for new work.

## Regression Policy

Perception, topology, strategy, execution, runtime, and GUI behavior are covered by the
Python tests under `tests/`. Changes to shared models, perception sequencing, or runtime
state must run the focused suites first and the full suite before handoff.

The current crossing/occlusion, unified aiming, launcher-stability, canonical-level ID,
and dynamic-space changes pass all 303 applicable regression tests and the full Ruff
check. The user-managed INI/default-value parity test is intentionally excluded from
project verification. The runtime changes add no extra capture; their additional work
consists of a small conflict-resolution pass over detected entities, visibility-region
checks, constant-size launcher evidence, coin-ray checks only while a promoted coin is
active, and the dedicated space mask described above.
