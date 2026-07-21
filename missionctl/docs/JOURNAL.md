# Journal

Append-only. One dated entry per session. Newest at the top. Keep entries short:
what changed, why, and what's next. This is the narrative memory of the project.

---

## 2026-07-20 — M3 params (ParamProtocol) + streaming primitive

- `ParamProtocol` (`core/protocols/param.py`): `get` (PARAM_REQUEST_READ→
  PARAM_VALUE), `set` (PARAM_SET as REAL32→confirming PARAM_VALUE), and
  `download_all` (PARAM_REQUEST_LIST→N×PARAM_VALUE), with a progress callback;
  completes at the advertised param_count, fails on idle. Per-index re-request of
  dropped params is left as a future refinement (noted in code).
- Added a second Vehicle primitive, `open_stream(predicate) -> MessageStream`, for
  streamed responses (download vs. one-shot `request`). Extracted the protocol↔
  vehicle I/O contracts into `core/protocols/channel.py` (Predicate/MakeFn/SendFn/
  RequestFn/OpenStreamFn + MessageStream) so vehicle depends downward on protocols
  and there's no import cycle. `command.py` now imports its aliases from there.
- Opened PR #2 (M1–M3) into master; our `check` CI job is green (the failing
  `Build OSX` job is the legacy C# build, unrelated to missionctl/).
- 44 tests green (param get/set/timeout, download_all full + incomplete). Next:
  MissionProtocol.

---

## 2026-07-20 — M3 commands (Plane) + scope decision

- Scope confirmed by operator and recorded as ADR-0005: **control target = Plane**,
  Rover = display-only (vessel), Copter = excluded. Answered QUESTIONS Q3.
- `CommandProtocol` (`core/protocols/command.py`): arm/disarm + set_mode via
  `COMMAND_LONG` → `COMMAND_ACK`, explicit timeout + bounded retries, returns
  `Result[int]`. Plane mode table in `core/modes.py` (name→number for set_mode,
  reverse for display).
- Gave `Vehicle` an outbound path: `bind_output(send, make)` and a `request`
  primitive that registers the reply waiter **before** sending (so a fast ACK is
  never missed — a race I hit while designing the test). Incoming messages now
  both reduce state and resolve pending waiters. `FleetManager.run_link` wires the
  link's writer + `codec.make` into each discovered vehicle.
- `codec.make(msg_type, **fields)` added so command construction stays confined to
  the codec (ADR-0004); protocols never import pymavlink.
- Tooling notes: `Result` helper classmethods didn't bind the generic under pyright
  strict → construct `Result(...)` directly and let the `-> Result[int]` return
  type infer T. Disabled ruff ASYNC109 (our protocol API intentionally takes
  `timeout` params; applied internally via `asyncio.timeout`).
- 39 tests green (arm accepted, rejection→failure, timeout after N retries,
  set_mode builds correct COMMAND_LONG, unknown mode doesn't send, unbound vehicle
  refuses commands). Next: `ParamProtocol`.

---

## 2026-07-20 — M2 state from telemetry

- Added `Router` (demux by `(sysid, compid)`, callback-based so it needs no
  dependency on the vehicle/fleet layers — replaces the legacy global
  `sysidcurrent`), `Vehicle` (asyncio actor per craft: private inbox →
  `reduce()` → publish `Observable[VehicleState]`; ADR-0003), and `FleetManager`
  (auto-creates a vehicle on first sighting of a new address, exposes a `fleet`
  observable, `run_link` pumps bytes→codec→router).
- Message reducers: HEARTBEAT (armed flag + custom_mode), ATTITUDE,
  GLOBAL_POSITION_INT, SYS_STATUS, GPS_RAW_INT — one small pure fn each, all
  normalising to SI units. Extended `VehicleState` with `Gps` + `custom_mode`.
- Routing keys off the *decoded* message's src ids (set at pack time), not the
  raw constructed message — noted for future tests.
- Human-readable mode names are vehicle-type specific; parked as QUESTIONS Q3,
  state keeps the raw `custom_mode` for now.
- 30 tests green (5 reducer unit tests, two-vehicle routing, fleet observable,
  full tlog-replay snapshot). Next: M3 commands (arm/set_mode via COMMAND_LONG).

---

## 2026-07-20 — M1 transport & codec

- Implemented `MavlinkCodec` (ADR-0004: pymavlink as codec only, no I/O). Stateful
  parser reassembles frames split across reads; drops `MAVLink_bad_data`; public
  surface typed via `MavlinkMessage` protocol so strict core is unaffected.
- Added three `Link` implementations: `LoopbackLink` (in-memory test double),
  `UdpLink` (async UDP, listen + connect modes — this is how we'll reach SITL at
  udp:127.0.0.1:14550), `TlogReplayLink` (strips 8-byte µs timestamps, frames
  MAVLink v1/v2 including signed).
- Isolated pymavlink's untyped-ness to a single relaxed pyright execution
  environment on `core/codec`; rest of core stays strict. import-linter layers
  updated to include `codec`.
- 20 tests green (codec roundtrip/split/garbage, loopback, udp roundtrip + peer
  learning, tlog replay count). User confirmed M0 PR merged; SITL lives in a
  separate repo and will be connected at 14550 later.
- Next: M2 — Router demux + Vehicle actor + first HEARTBEAT reducer.

---

## 2026-07-20 — M0 operating scaffold

- Bootstrapped the repository as a Python + Qt Quick (QML) rewrite of the C2 layer.
- Established the operating system for long-horizon solo/Claude development:
  `CLAUDE.md` contract, `docs/` ledger (this journal, STATUS, ROADMAP, ARCHITECTURE,
  DISCOVERIES, QUESTIONS, ADRs), and `.claude/skills` (start/end-session, run-sitl,
  add-protocol, record-decision).
- Decided the core architecture: pure-Python asyncio core that never imports Qt,
  one actor per vehicle, immutable SI-unit state, pymavlink as codec only. Recorded
  as ADR-0002/0003/0004.
- Wired the trust substrate: `make check` (ruff + pyright strict + import-linter +
  pytest) and a CI workflow; import-linter forbids `core` → Qt.
- Implemented a minimal green core so the baseline is real from day one.
- Next: M1 — MavlinkCodec over pymavlink + first parse test.
