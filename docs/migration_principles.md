# Migration Principles

## Preserve Behavior Before Improving It

The prototype has already validated the feasibility of the visual pipeline, topology model, and greedy decision logic. The refactor should first reproduce that behavior with cleaner boundaries before making strategy changes.

## Assets Are First-Class

Level backgrounds, launcher templates, UI templates, and decoded topology JSON files are core product assets. They should be versioned, validated, and migrated deliberately.

## Explicit Data Models

Replace implicit dictionaries and positional arrays with named models:

- `LevelAssets`
- `LevelTopology`
- `LevelGeometry`
- `Track`
- `BallEntity`
- `Cluster`
- `LauncherState`
- `WorldState`
- `TargetCandidate`
- `Command`

## Replay Before Runtime

Every migrated perception or strategy slice should be runnable against stored screenshots before it is wired into live mouse execution.

## Runtime Safety

No input command should be emitted unless the bot is armed, the game window is known, the map/ROI state is valid, and the command is explicit.
