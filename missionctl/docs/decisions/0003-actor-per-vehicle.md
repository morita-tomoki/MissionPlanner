# 3. One actor (asyncio task) per vehicle

## Status
Accepted — 2026-07-20

## Context
Multi-vehicle simultaneous control is a first-class requirement. The legacy code
kept a single global "current vehicle" (`sysidcurrent`) and one huge shared mutable
`CurrentState` updated under `lock(this)` — impossible to extend to N vehicles
safely, and a deadlock/contention hazard.

## Decision
Model each vehicle as an independent **actor**: a `Vehicle` with a private
`asyncio.Queue` inbox and its own task loop (`receive → reduce → publish`). The
`Router` demultiplexes incoming messages by `(sysid, compid)` into the right inbox.
`FleetManager` holds the set of vehicles and offers group commands via
`asyncio.gather`. No shared mutable state between vehicles; no locks.

## Consequences
- N vehicles = N isolated actors. Adding vehicles needs no locking or redesign.
- State per vehicle is an immutable snapshot published on an observable — the UI
  binds one ViewModel per vehicle with no cross-talk.
- Slight overhead: one task + inbox per vehicle, and fleet-level monitoring must
  aggregate across actors. Acceptable and explicit.

## Rejected alternatives
- Single event loop with a global switch over all vehicles: repeats the legacy
  2,280-line `switch` and the shared-state hazard.
