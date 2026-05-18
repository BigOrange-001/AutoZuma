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

## Migration Rule

Do not bulk-copy prototype modules directly into this repository. Move behavior in small slices, with replay checks or review notes for each important migration.
