# AutoZuma Next

AutoZuma Next is the clean refactor target for the validated AutoZuma 2.0 prototype.

The initial migration goal is behavior preservation:

- Preserve validated visual recognition behavior.
- Preserve level topology assets and their semantics.
- Preserve the current greedy strategy as the baseline.
- Replace prototype coupling with explicit data models, replay tests, and clear runtime boundaries.

## Initial Repository Layout

```text
AutoZumaNext/
  assets/        # Migrated level assets and topology data.
  docs/          # Refactor notes and design records.
  src/autozuma/  # New implementation package.
  tests/         # Unit and replay regression tests.
```

See `docs/assets.md` for the migrated visual/topology asset inventory.
See `docs/session_handoff.md` for the current refactor status and next-step guidance.
See `docs/development_overview.md` for the current code-level runtime and capability baseline.
See `AGENTS.md` for repository test policy and targeted test commands.

## Launch

On Windows, double-click `launcher.bat` from the repository root to start the GUI.

Equivalent command:

```powershell
.\.venv\Scripts\python -m autozuma.gui.app
```

Default runtime controls:

- `F1`: Arm/Safe toggle.
- `F2`: save a debug snapshot.
- `F3`: force Safe.

The GUI also has matching buttons. F1/F2/F3 are polled as global Win32 hotkeys,
so they work while the game window has focus.

## Completed-level grade collection

When the existing UI automation detects the green `OK` button on a completed-level
`STATS` screen, AutoZuma now reads and archives the result before clicking the button.
The parser anchors every STATS field to the detected OK-button position, so dragging
the result panel does not change the field locations.

Gameplay can still use virtual/background mouse input, but menu and result-dialog
buttons use a focused physical click. This avoids the Zuma UI accepting the pressed
animation while rejecting a synthetic button release.

Results are created lazily under `grade/`:

- One append-only CSV per campaign level, for example `grade/1-1.csv`.
- One source screenshot per recorded row under `grade/screenshots/<level>/`.
- One GAME OVER CSV per failed campaign level under `grade/gameover/`, with
  matching screenshots under `grade/gameover/screenshots/<level>/`.
- Failed OCR evidence under `grade/failed/` after the configured retry limit.

CSV rows contain only values read from the result screen. The level is encoded by
the CSV filename, so timestamps, internal map IDs, screenshot paths, OCR diagnostics,
and runtime parameter snapshots are not written into the table. Campaign IDs are
accepted only for levels 1-1 through 3-5, 4-1 through 6-6, 7-1 through 12-7, and
13-1.

While the session is detecting rather than actively playing, AutoZuma also checks
for the Adventure stage menu. A screen is accepted only when both `ADVENTURE` and
`PLAY` are recognized; AutoZuma then clicks the stage doorway at the configured
640×480 client coordinate `(251, 335)`. Repeated clicks are throttled.

## Migration Rule

Do not bulk-copy prototype modules directly into this repository. Move behavior in small slices, with replay checks or review notes for each important migration.
