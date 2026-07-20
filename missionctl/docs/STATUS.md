# STATUS — you are here

> Keep this file tiny and current. It is the first thing a new session reads.
> Update it at the end of every session (`/end-session`).

## Baseline
- Branch: `claude/hud-structure-rendering-ja83ju` (M0 PR merged; M1+M2 on top).
- `make check`: green locally — 30 tests, ruff, pyright strict, 2 import contracts.

## Done
- M0 operating scaffold: config, `CLAUDE.md`, `docs/` ledger, `.claude/skills`, CI.
- **M1 transport & codec**: `MavlinkCodec` (codec-only), `LoopbackLink`, `UdpLink`
  (SITL transport), `TlogReplayLink`.
- **M2 state from telemetry**: `Router` (demux by sysid/compid, callback-based),
  `Vehicle` (asyncio actor: inbox→reduce→publish `Observable[VehicleState]`),
  `FleetManager` (auto-creates vehicles, `fleet` observable, `run_link`). Reducers
  for HEARTBEAT/ATTITUDE/GLOBAL_POSITION_INT/SYS_STATUS/GPS_RAW_INT (SI units).
  Tests: tlog-replay snapshot + two-vehicle independent routing.

## Now
- Nothing in progress.

## Next single action
- **M3 (commands)**: implement `CommandProtocol` in
  `core/protocols/command.py` — arm/disarm + set_mode via `COMMAND_LONG`, awaiting
  `COMMAND_ACK`, with timeout + retry (async, cancellable, no blocking). Wire a
  `send`/subscribe path from `Vehicle` (Vehicle currently only receives; add an
  outbound sink + a way for protocols to await specific reply messages). Follow
  the `/add-protocol` skill. Unit-test with a fake message stream; SITL test later.

## Later (waiting on external)
- **SITL** in a separate repo; connect via `UdpLink(local_addr=("0.0.0.0", 14550))`.
  SITL-marked tests stay skipped until then.

## Later (waiting on external)
- **SITL** is developed in a separate repo; connect via `UdpLink(local_addr=
  ("0.0.0.0", 14550))` when ready. SITL-marked tests stay skipped until then.

## Notes for the next session
- The core deliberately keeps tests stdlib-only, so `pytest` stays green even
  before pymavlink/PySide6 are exercised. When you add codec tests, gate
  hardware/SITL ones behind the `sitl` marker.
- **CI location:** GitHub Actions only reads workflows from the *repo root*
  `.github/workflows/`, so the CI file lives at
  `.github/workflows/missionctl-ci.yml` (repo root), path-filtered to
  `missionctl/**` and running with `working-directory: missionctl`. If this
  project is ever extracted to its own repo, move it to that repo's root.
