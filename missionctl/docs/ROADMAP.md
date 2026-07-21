# Roadmap

Work is sliced into **vertical, independently-verifiable increments**. Each slice
should fit one Claude session, ship a test, and leave `main` green. Check a box
only when its slice is merged and green. Keep `STATUS.md` pointing at the next one.

## M0 — Operating scaffold (this milestone bootstraps the process)
- [x] Project skeleton, `pyproject.toml`, `Makefile`, `.importlinter`
- [x] `CLAUDE.md` + `docs/` ledger + `.claude/skills`
- [x] Minimal green core (`Observable`, `Link` protocol, state models/reducers stub)
- [x] Import-boundary test + CI workflow
- [ ] `make check` runs green in CI on a real runner (verify on first PR)

## M1 — Transport & codec  ✅
- [x] `Link` protocol finalized; `LoopbackLink` for tests
- [x] `MavlinkCodec` (pymavlink) — parse a byte buffer into messages
- [x] `UdpLink` — async UDP transport (for SITL @ udp:127.0.0.1:14550)
- [x] `TlogReplayLink` — replay a `.tlog`, strip µs timestamps, feed codec
- [x] Test: replay a fixture tlog, assert N HEARTBEATs parsed (+ codec/udp/loopback)

## M2 — State from telemetry  ✅
- [x] `Router` demux by (sysid, compid)
- [x] `Vehicle` actor: inbox → reduce → publish `Observable[VehicleState]`
- [x] `FleetManager`: auto-creates vehicles on first sighting, `run_link`
- [x] Reducers for HEARTBEAT, ATTITUDE, GLOBAL_POSITION_INT, SYS_STATUS, GPS_RAW_INT
- [x] Test: tlog replay → vehicle-state snapshot; multi-sysid routing

## M3 — Commands & protocols (async, cancellable, retrying)  — Plane (ADR-0005)  ✅
- [x] `CommandProtocol`: arm/disarm, set_mode (COMMAND_LONG + COMMAND_ACK,
      timeout + retries); Vehicle outbound `request` primitive; Plane mode table
- [x] `ParamProtocol`: get / set / download-all with progress (Vehicle
      `open_stream` primitive + `protocols/channel.py` I/O contracts)
- [x] `MissionProtocol`: download / upload (handshake state machine) / set-current
      — verified against real 4.6.3 (upload 3 → download 3 → set_current)
- [x] SITL smoke test scaffold: connect → arm → set GUIDED → disarm + mission
      roundtrip
      (`tests/test_sitl_smoke.py`, `sitl`-marked, skips if 14550 quiet). Also a
      real-UDP e2e via in-repo `FakePlane` runs in the default gate.

## Robustness (hardening pass)
- [x] Vehicle actor survives a malformed message (guarded reduce + logging)
- [x] Request telemetry streams on connect (REQUEST_DATA_STREAM ALL)
- [x] `UdpLink.open()` idempotent (double-open no longer rebinds the socket)
- [x] Vehicle lost detection: `link_alive` flips false after a heartbeat-timeout,
      true again when telemetry resumes (per-vehicle monitor task)
- [x] Link reconnection: `run_link(reconnect=True)` reopens on EOF/error with
      exponential backoff until cancelled
- [x] `set_mode(confirm=True)`: confirm the change via HEARTBEAT.custom_mode, not
      just COMMAND_ACK (verified on 4.6.3)
- [x] `set_safety(safe)`: toggle safety switch via MAV_CMD_DO_SET_SAFETY_SWITCH_STATE
      (verified accepted on 4.6.3)

## M4 — Multi-vehicle  ✅
- [x] `FleetManager`: multiple links; each vehicle bound to its discovery link's
      outbound (per-chunk active-outbound, race-free); `fleet` observable
- [x] Group command via `asyncio.gather` (arm all)
- [x] Ignore MAVLink sysid 0 (reserved) — no phantom (0,0) vehicle
- [x] Headless: two FakePlanes on two UDP links (independent state, group arm)
- [x] SITL: two real ArduPlane 4.6.3 instances (sysid 1/2, ports 14550/14560),
      independent state + group arm verified

## M5 prep (done ahead of the UI)
- [x] Capture STATUSTEXT into `VehicleState.messages` (bounded backlog) with
      MAVLink2 chunk reassembly — this is where PreArm:/Arm:/error lines live, for
      the HUD banner. `last_message` convenience + severity per line. Verified on
      4.6.3 (captured "Arm: Accels inconsistent", severity 2).

## M5 — Qt/QML presentation
- [ ] `qasync` app bootstrap (`missionctl.qt.app`)
- [ ] `FleetModel(QAbstractListModel)` + `VehicleVM`
- [ ] QML: fleet list, per-vehicle HUD (SkiaSharp-equivalent via QtQuick), map
- [ ] Unit conversion + banners in the ViewModel layer

## Backlog / later
- [ ] Packaging (.app via briefcase/pyinstaller)
- [ ] Optional headless daemon + IPC (ZeroMQ) for remote/multi-operator
- [ ] Signing/crypto (MAVLink2 signing) as a codec middleware
