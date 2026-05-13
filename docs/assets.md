# Assets

This document records the migrated visual and topology assets from the AutoZuma 2.0 prototype.

## Directory Layout

```text
assets/
  levels/
    backgrounds/  # Static level background images used by visual matching.
    topology/     # Decoded track topology JSON files.
  templates/
    launcher/     # Frog/launcher visual templates.
    ui/           # UI button templates.
```

## Level Backgrounds

Location: `assets/levels/backgrounds`

Count: 21

Purpose:

- Static level recognition.
- ROI alignment.
- Background subtraction for ball detection.
- Background subtraction around known treasure points.

Migrated files:

- `BlackSwirley.jpg`
- `claw.jpg`
- `coaster.jpg`
- `Groovefest.jpg`
- `inversespiral.jpg`
- `longrange.jpg`
- `loopy.jpg`
- `overunder.jpg`
- `Riverbed.jpg`
- `serpents.jpg`
- `Snakepit.jpg`
- `spaceinvaders.jpg`
- `Spiral.jpg`
- `squaresville.jpg`
- `Targetglyph.jpg`
- `tiltspiral.jpg`
- `triangle.jpg`
- `tunnellevel.jpg`
- `turnaround.jpg`
- `underover.jpg`
- `warshak.jpg`

## Level Topology

Location: `assets/levels/topology`

Count: 22

Purpose:

- Launcher pivot coordinates.
- Sparse path control points.
- Multi-track metadata where present.
- Treasure-point coordinates.
- Source data for dense track generation and cumulative-distance indexing.

Migrated files:

- `blackswirley.json`
- `claw.json`
- `coaster.json`
- `Groovefest.json`
- `inversespiral.json`
- `longrange.json`
- `loopy.json`
- `overunder.json`
- `riverbed.json`
- `serpents.json`
- `snakepit.json`
- `space.json`
- `spaceinvaders.json`
- `spiral.json`
- `squaresville.json`
- `targetglyph.json`
- `tiltspiral.json`
- `triangle.json`
- `tunnellevel.json`
- `turnaround.json`
- `underover.json`
- `warshak.json`

Special case:

- `space.json` has no matching static background image. The original game assets do not provide a static background for this dynamic-background level. It must be handled by a dedicated level-detection and ROI strategy later.

## Launcher Template

Location: `assets/templates/launcher`

Files:

- `SMALLFROGonPAD.png`

Purpose:

- Rotated frog template cache.
- Launcher angle estimation.
- Current-ball and next-ball sample point inference.

## UI Templates

Location: `assets/templates/ui`

Files:

- `ui_ok.png`
- `ui_continue.png`

Purpose:

- End/continue/confirmation UI detection.
- Automated UI click targeting.

Known missing optional file:

- `ui_start_again.png` was referenced by the prototype settings but did not exist in the source asset directory. It should be added only if future UI automation needs it.

## Code Ownership

The migrated assets are loaded by `autozuma.assets.loader` and audited by `autozuma.assets.validator`.

Runtime-ready image and topology assets are combined by `autozuma.assets.registry.load_asset_registry`.
