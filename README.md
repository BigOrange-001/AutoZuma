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

## Migration Rule

Do not bulk-copy prototype modules directly into this repository. Move behavior in small slices, with replay checks or review notes for each important migration.
