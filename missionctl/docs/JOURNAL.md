# Journal

Append-only. One dated entry per session. Newest at the top. Keep entries short:
what changed, why, and what's next. This is the narrative memory of the project.

---

## 2026-07-20 — STATUSTEXT capture (M5/HUD prep) ✅

- Added STATUSTEXT reduction: `reduce_statustext` folds lines into
  `VehicleState.messages` (bounded to 20, oldest first) with a `StatusText`
  (severity, text). This is where PreArm:/Arm:/sensor-error messages arrive —
  answering the operator's question (they were NOT captured before). `last_message`
  convenience for a HUD banner.
- MAVLink2 chunk reassembly: chunks with the same non-zero id are joined; a chunk
  shorter than the 50-byte field is the last. Buffer lives in state
  (`statustext_reassembly`) so the reducer stays pure.
- Verified on real 4.6.3: enabled ARMING_CHECK=1 and attempted arm → rejected
  (MAV_RESULT=4) and we captured "Arm: Accels inconsistent" (severity 2). Added a
  sitl regression test that skips gracefully when the vehicle happens to be armable.
- 62 headless tests + 4 sitl.

## 2026-07-20 — Robustness pass (lost/reconnect/mode-confirm/safety) ✅

Four operator-requested hardening items:
- Vehicle lost detection: a per-vehicle monitor task marks `VehicleState.link_alive`
  false when no HEARTBEAT arrives within `heartbeat_timeout` (default 3 s), and true
  again when telemetry resumes. Liveness is actor-managed metadata; reducers stay
  pure (they never read time — the actor stamps last-heartbeat via the loop clock).
- Link reconnection: `run_link(reconnect=True)` reopens the link on EOF or
  OSError/ConnectionError with exponential backoff (1→16 s) until cancelled;
  vehicles go link_alive=false via their own timeout and recover on resume.
- `set_mode(confirm=True)` (default): after the ACK, wait for a HEARTBEAT reporting
  the new custom_mode before declaring success (ACK ≠ applied). Opens the HEARTBEAT
  feed BEFORE sending so the confirming heartbeat isn't missed (same
  register-before-send race the unit test caught; 1 Hz SITL heartbeats had masked it).
- `set_safety(safe)`: MAV_CMD_DO_SET_SAFETY_SWITCH_STATE (5300), SAFE=0/DANGEROUS=1.
- Verified on real 4.6.3: link_alive true on connect; set_mode FBWA/GUIDED confirmed
  (state reflects the change); set_safety(True/False) both ACCEPTED. Lost detection
  and reconnection covered by headless tests (FlakyLink + short-timeout monitor).
- 58 headless tests + 3 sitl.

## 2026-07-20 — M4 multi-vehicle (verified on 2× real SITL) ✅

- Fixed the FleetManager outbound binding for multi-link: each vehicle now binds
  to the outbound of the link it was discovered on. Implemented as a per-chunk
  "active outbound" set immediately before the synchronous routing block — since a
  decoded chunk is routed with no intervening await, it's race-free even with
  several links pumping concurrently on the one event loop. (Previously a single
  global _outbound meant a vehicle could command out the wrong link.)
- Ignore MAVLink sysid 0 (reserved broadcast/unknown) so a phantom (0,0) vehicle
  isn't created — observed coming from SITL during boot. Filter + test added.
- Verified: headless (two FakePlanes, sysid 1&2, on two UDP links → independent
  state, group arm via gather, disarm-one-leaves-other-armed) AND two real
  ArduPlane 4.6.3 SITL instances (sysid 1 on 14550, sysid 2 on 14560): same
  assertions pass; fleet is exactly {(1,1),(2,1)} with the sysid-0 filter.
- 53 headless tests + 3 sitl tests. The C2 core is feature-complete through M4.
  Next: M5 Qt/QML UI (Mac work; not exercisable headlessly here).

## 2026-07-20 — M3 MissionProtocol (verified on 4.6.3) ✅ — M3 complete

- `MissionProtocol` (`core/protocols/mission.py`) + `MissionItem` dataclass
  (int lat/lon, matching MISSION_ITEM_INT): download (REQUEST_LIST→COUNT→
  N×REQUEST_INT/ITEM_INT→ACK), upload (COUNT→answer the vehicle's item requests→
  ACK — a handshake state machine using `open_stream`), and set_current.
- Verified against real ArduPlane 4.6.3: upload 3 items → ACCEPTED, download → 3,
  set_current(1) → ok. Added a `sitl`-marked mission roundtrip test; both sitl
  tests pass on 4.6.3.
- Real-firmware behavior observed and handled: ArduPilot stores seq0 as home
  (frame 0, AMSL ~584 m) and normalizes our frame=6 (GLOBAL_RELATIVE_ALT_INT)
  waypoints to frame=3 (GLOBAL_RELATIVE_ALT) on download; z values preserved.
- 51 headless tests + 2 sitl. M3 (Command/Param/Mission) is complete and
  SITL-verified. Next: M4 multi-vehicle (or M5 Qt/QML UI).

## 2026-07-20 — Pinned target firmware to ArduPlane 4.6.3 ✅

- Operator specified ArduPlane 4.6.3 as the only target version. Rebuilt SITL from
  tag `Plane-4.6.3` and re-verified over real UDP 14550: connect, telemetry,
  set_mode GUIDED, arm/disarm, and a FULL parameter download (`download_all` →
  **1445 params**) all succeeded. `make sitl` passes against 4.6.3.
- Recorded as ADR-0006 (pin) and updated the DISCOVERIES build recipe to the tag.
- Gotcha: ArduPilot's `--recurse-submodules` shallow clone left `modules/waf` and
  `modules/mavlink` empty; `./waf` self-heals to "try again" and exits 0 without
  building. Fix: `git submodule update --init --recursive --depth 1` first.

## 2026-07-20 — Verified against REAL ArduPlane SITL (initial, on 4.5)

- Built genuine ArduPlane SITL from source in this container (Plane-4.5, waf,
  ~3.5 min) and ran the full missionctl stack against it over UDP 14550.
- Results: connected (sysid 1/compid 1); real telemetry reduced correctly
  (mode=MANUAL, gps_fix=6, 10 sats, alt 584.1 m, batt 12.6 V); `set_mode GUIDED`
  → ACCEPTED; `arm` → ACCEPTED (state reflected armed=True, mode=GUIDED);
  `disarm` → ACCEPTED; `params.get("WP_LOITER_RAD")` → 80.0. `make sitl` passes.
- This closes the top review risk for the command/param/telemetry paths: our
  assumptions held against real firmware (ArduPlane DOES COMMAND_ACK DO_SET_MODE
  and ARM_DISARM; Plane mode numbers correct; SI reducers sane).
- Full reproducible build+run recipe recorded in DISCOVERIES (incl. the EmPy 3.3.4
  em.py extraction workaround and the `--serial0 udpclient:127.0.0.1:14550` launch).
- Note: the SITL install lives outside the repo and is ephemeral (reclaimed with
  the container); the recipe is the durable artifact.

---

## 2026-07-20 — Hardening + simple SITL

- Actor robustness: `Vehicle._run` now guards `reduce`/dispatch with try/except +
  logging, so one malformed message can't silently kill a vehicle's task (it
  previously would, freezing that vehicle's state).
- Telemetry on connect: `Vehicle.request_data_streams` (REQUEST_DATA_STREAM ALL);
  `FleetManager` fires it for newly discovered vehicles on live links
  (`run_link(request_streams=…)`, default True; replay passes False).
- Simple SITL: added in-repo `FakePlane` (tests/support) that emits heartbeats and
  ACKs commands over real UDP, plus `test_udp_end_to_end.py` (runs in the default
  gate — first coverage of the *real* transport+command path, not fakes) and
  `test_sitl_smoke.py` (`sitl`-marked, targets external 14550, skips if quiet).
  Excluded `sitl` from the default pytest run.
- BUG FOUND & FIXED via the e2e: `UdpLink.open()` was not idempotent. The test
  opened the link to read its port, then `run_link` opened it again, binding a
  second socket; heartbeats to the first socket still arrived (so discovery
  "worked") but writes went out the second socket, whose source port the peer's
  connected socket rejected — commands silently never arrived. `open()` is now
  idempotent. Recorded in DISCOVERIES.
- 47 tests + 1 sitl (skipped). Next: MissionProtocol.

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
