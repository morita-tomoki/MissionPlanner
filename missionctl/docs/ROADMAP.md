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

## M2 — State from telemetry
- [ ] `Router` demux by (sysid, compid)
- [ ] `Vehicle` actor: inbox → reduce → publish `Observable[VehicleState]`
- [ ] Reducers for HEARTBEAT, ATTITUDE, GLOBAL_POSITION_INT, SYS_STATUS, GPS_RAW_INT
- [ ] Test: tlog replay → snapshot of the state timeline

## M3 — Commands & protocols (async, cancellable, retrying)
- [ ] `CommandProtocol`: arm/disarm, set_mode (COMMAND_LONG + ACK handling)
- [ ] `ParamProtocol`: get / set / download-all with progress
- [ ] `MissionProtocol`: download / upload / set-current
- [ ] SITL smoke test: connect → arm → set GUIDED → disarm

## M4 — Multi-vehicle
- [ ] `FleetManager`: multiple links, vehicle add/remove observable
- [ ] Group command via `asyncio.gather`
- [ ] Test: two SITL instances (I0 / I1), independent state, group arm

## M5 — Qt/QML presentation
- [ ] `qasync` app bootstrap (`missionctl.qt.app`)
- [ ] `FleetModel(QAbstractListModel)` + `VehicleVM`
- [ ] QML: fleet list, per-vehicle HUD (SkiaSharp-equivalent via QtQuick), map
- [ ] Unit conversion + banners in the ViewModel layer

## Backlog / later
- [ ] Packaging (.app via briefcase/pyinstaller)
- [ ] Optional headless daemon + IPC (ZeroMQ) for remote/multi-operator
- [ ] Signing/crypto (MAVLink2 signing) as a codec middleware
