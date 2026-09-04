# Topology

AutoZuma Next separates original topology data from derived geometry.

## LevelTopology

`LevelTopology` is the raw decoded map asset:

- Level id.
- Frog pivot.
- Sparse control points.
- Treasure points.
- Special detection flags such as the dynamic-background `space` level.

It does not contain dense tracks or cumulative distances.

## LevelGeometry

`LevelGeometry` is derived from `LevelTopology`:

- One `TrackGeometry` for each source track.
- Dense Catmull-Rom sampled points.
- Per-point cumulative distances along each track.
- Per-point visibility-region ids derived from source control-point flags.

Control-point flag `1` marks tunnel/occluded geometry. Dense segments touching an
occluded control point use visibility region `-1`; visible sections use monotonically
increasing non-negative region ids. Vision projects balls only onto visible regions, and
strategy does not calculate adjacency, rollback, combo chains, or tail locks across an
occluded boundary.

This keeps asset parsing independent from geometric algorithms and allows later vision code to use the same geometry without reinterpreting JSON.
