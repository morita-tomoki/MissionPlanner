# STATUS — you are here

> Keep this file tiny and current. It is the first thing a new session reads.
> Update it at the end of every session (`/end-session`).

## Baseline
- Branch: `claude/hud-structure-rendering-ja83ju` (M0 PR merged per user).
- `make check`: green locally — 20 tests, ruff, pyright strict, 2 import contracts.

## Done
- M0 operating scaffold: config, `CLAUDE.md`, `docs/` ledger, `.claude/skills`, CI.
- **M1 transport & codec**: `MavlinkCodec` (pymavlink codec-only, drops BAD_DATA,
  reassembles split frames), `LoopbackLink` (test double), `UdpLink` (async UDP,
  listen/connect modes — the SITL transport), `TlogReplayLink` (strips µs
  timestamps, frames v1/v2). 20 tests green.

## Now
- Nothing in progress.

## Next single action
- **M2**: add `Router` (`core/router.py`) that demuxes decoded messages by
  `(sysid, compid)`, then `Vehicle` (`core/vehicle.py`) as an asyncio actor:
  inbox → reduce → publish `Observable[VehicleState]`. Start with a HEARTBEAT
  reducer (armed flag + mode) and a tlog-replay snapshot test. See ROADMAP M2,
  ADR-0003 (actor-per-vehicle), and `/add-protocol` conventions.

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
