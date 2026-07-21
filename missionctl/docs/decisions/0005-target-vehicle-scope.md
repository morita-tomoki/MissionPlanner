# 5. Target vehicle scope: control Plane, display Rover, exclude Copter

## Status
Accepted — 2026-07-20

## Context
The product does not need to manage every ArduPilot vehicle type. The operator
requirement is:
- **Plane** — full command & control (arm, mode, mission, etc.).
- **Rover** — display only, presented as a surface vessel ("艦艇"). No commanding.
- **Copter** — out of scope entirely (neither display nor control).

## Decision
- The command layer (`core/protocols`) targets **ArduPlane**. Mode tables and
  command semantics are Plane's (`core/modes.py`, `PLANE_MODES`).
- Telemetry/state (`core/state`) stays vehicle-type-agnostic (SI units, raw
  `custom_mode`), so Rover can be displayed without special-casing the core.
- The presentation layer decides rendering: Plane as aircraft (controllable),
  Rover as a vessel (read-only). Copter frames may be ignored by the UI.
- Guard commands: the command protocol should refuse to command a vehicle whose
  HEARTBEAT type is not a Plane (deferred to when MAV_TYPE is tracked in state;
  noted in ROADMAP).

## Consequences
- We only need Plane mode name↔number mapping in core now (answers Q3).
- Rover support is "free" on the telemetry side; only display work is needed.
- Excluding Copter trims mode tables and UI affordances.

## Rejected alternatives
- Generic all-vehicle control: more mode tables and command edge cases than the
  requirement justifies.
