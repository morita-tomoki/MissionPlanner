# Architecture

The deep reference. `CLAUDE.md` holds the short version; this file explains the
"why" so future sessions don't re-litigate settled design.

## Goal & constraints

- Rewrite **only the command & control layer** of MissionPlanner (connect,
  telemetry, commands, params, mission monitoring) — not log analysis, not
  firmware flashing.
- **Multiplatform**, developed on macOS. Stack fixed by the human: **Python +
  Qt Quick (QML)**.
- **Solo engineer + Claude Code**: must be developable, testable, and maintainable
  by an agent with no cross-session memory.
- **Multi-vehicle simultaneous control** must be a first-class capability, not a
  retrofit.

## The shape

```
┌───────────────────────────────────────────────┐
│  QML (View)  — declarative, data-bound only     │  knows Qt
├───────────────────────────────────────────────┤
│  qt/ (ViewModel bridge)                         │  knows Qt (ONLY layer that does)
│    FleetModel(QAbstractListModel)               │
│    VehicleVM(QObject: Q_PROPERTY/Signal/Slot)   │
├═══════════════════════════════════════════════┤  ← import-linter boundary
│  core/  (pure Python, asyncio, NO Qt imports)   │
│    fleet.py      FleetManager                    │
│    vehicle.py    Vehicle  (1 actor per craft)    │
│    router.py     demux by (sysid, compid)        │
│    protocols/    param / mission / command / …   │
│    state/        frozen dataclasses + reducers   │
│    codec/        pymavlink parse/pack ONLY        │
│    link/         async byte streams (serial/udp/…│
└───────────────────────────────────────────────┘
```

## Layers

### `core.link` — transport
`Link` is an async byte-stream abstraction (`open/read/write/close` + a `state`
observable). It is **not** shaped like `SerialPort` (the legacy `ICommsSerial`
leaked serial concepts onto TCP/UDP/BLE). Serial-only options live inside
`SerialLink`. `TlogReplayLink` replays a recorded `.tlog` and is the backbone of
deterministic regression tests.

### `core.codec` — MAVLink codec
Wraps `pymavlink` as a **pure parser/serializer**: bytes in → messages out, message
in → bytes out. No sockets, no threads. Dialect definitions are the reusable asset
carried over from ArduPilot. See ADR-0004.

### `core.state` — vehicle state
Small `@dataclass(frozen=True, slots=True)` value objects (`Attitude`, `Position`,
`Battery`, `Gps`, `FlightMode`, …) composed into `VehicleState`, **always SI units**.
`reducers.py` holds one small pure function per message type
(`reduce(state, msg) -> state`) — replacing the legacy 2,280-line `switch`. Pure
functions are trivially snapshot-testable.

### `core.protocols` — C2 operations
One file per MAVLink micro-protocol (param, mission, command, ftp, log, fence,
rally). Each is `async`, cancellable, with explicit timeouts + retry policy. No
global "give me the port" mutex — each op subscribes to the message stream and
awaits its reply.

### `core.router` — demultiplex
Classifies incoming messages by `(sysid, compid)` and delivers to the right
`Vehicle` inbox. Replaces the legacy global `sysidcurrent`.

### `core.vehicle` — the actor (multi-vehicle key)
Each `Vehicle` owns a private `asyncio.Queue` inbox and runs its own task:
receive → reduce → publish new immutable state. Commands are async methods.
Because there is no shared mutable state, N vehicles = N independent actors with
no locking. This is what makes multi-vehicle safe and simple. See ADR-0003.

### `core.fleet` — FleetManager
Owns links and the `{(sysid,compid): Vehicle}` map, exposes an observable of
vehicle add/remove, and offers group commands (`asyncio.gather` over selected
vehicles).

### `qt/` — presentation bridge (the only Qt-aware code)
`FleetModel(QAbstractListModel)` exposes the fleet to QML; `VehicleVM(QObject)`
exposes one vehicle's state via `Q_PROPERTY` + `NOTIFY`, and commands via `@Slot`
(bridged to core coroutines with `qasync`). Unit conversion and display formatting
happen here. See ADR-0002 for the qasync single-event-loop decision.

## Concurrency model

`asyncio` throughout, unified with the Qt event loop via `qasync` in a **single
process, single thread**. No `threading`, no `Thread.Sleep` polling, no locks in
core. Backpressure comes from `asyncio.Queue` / stream `await`s.

## Testing strategy

- **Unit**: pure reducers and protocols with fake links/messages (stdlib only).
- **tlog replay**: feed a recorded flight through `TlogReplayLink`, assert the
  resulting state timeline (snapshot). Deterministic, no hardware.
- **SITL smoke** (`-m sitl`): spin ArduPilot SITL, connect over UDP, run a scripted
  scenario (connect → arm → set mode → …). End-to-end without real aircraft.
- The Qt layer stays thin enough that most logic is covered without a display.
