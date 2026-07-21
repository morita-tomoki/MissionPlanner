# 6. Target firmware: ArduPlane 4.6.3 (pinned)

## Status
Accepted — 2026-07-20

## Context
The operator specified a single firmware version for the target aircraft and will
use only that version going forward. Pinning avoids drift in mode numbers, message
definitions, parameter names, and command semantics across firmware releases.

## Decision
The target firmware is **ArduPlane 4.6.3** (git tag `Plane-4.6.3`). All SITL
verification builds from that tag. If the operator moves to a new version later,
supersede this ADR (and re-verify the mode table / dialect assumptions).

## Consequences
- SITL build recipe (DISCOVERIES) pins `-b Plane-4.6.3`.
- `core/modes.py` (Plane mode numbers) and the MAVLink command assumptions are
  validated against 4.6.3 specifically (verified: connect, telemetry, set_mode,
  arm/disarm, full 1445-param download).
- The pymavlink dialect we vendor should stay compatible with 4.6.x; revisit if a
  message/enum mismatch ever appears.

## Rejected alternatives
- Tracking latest/stable automatically: reintroduces the drift this pin avoids.
