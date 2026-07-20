# STATUS — you are here

> Keep this file tiny and current. It is the first thing a new session reads.
> Update it at the end of every session (`/end-session`).

## Baseline
- Branch: `claude/hud-structure-rendering-ja83ju` (M0 PR merged; M1–M3 on top).
- `make check`: green locally — 39 tests, ruff, pyright strict, 2 import contracts.

## Scope (ADR-0005)
- Control target = **Plane**. Rover = display-only (vessel). Copter = excluded.

## Done
- M0 operating scaffold; M1 transport & codec (`UdpLink` = SITL transport).
- **M2 state from telemetry**: Router, Vehicle actor, FleetManager, 5 reducers.
- **M3 commands (CommandProtocol)**: arm/disarm + set_mode for Plane via
  `COMMAND_LONG`→`COMMAND_ACK`, explicit timeout + bounded retries, `Result`
  outcomes. Vehicle gained an outbound path (`bind_output`) and a `request`
  primitive (registers the reply waiter *before* sending, so ACKs aren't missed).
  `core/modes.py` Plane mode table. 39 tests (arm/nack/timeout/set_mode/bad-mode).

## Now
- Nothing in progress.

## Next single action
- **M3 cont. — `ParamProtocol`** in `core/protocols/param.py`: get one
  (PARAM_REQUEST_READ→PARAM_VALUE), set (PARAM_SET→confirming PARAM_VALUE), and
  download-all (PARAM_REQUEST_LIST→N×PARAM_VALUE with progress via `IProgress`-style
  callback). Reuse the Vehicle `request` primitive; for download-all add a
  streaming variant that collects until the expected count. Follow `/add-protocol`.
  Unit-test with a fake responder; SITL later.

## Later (waiting on external)
- **SITL** in a separate repo; connect via `UdpLink(local_addr=("0.0.0.0", 14550))`.
  SITL-marked tests stay skipped until then. First SITL use: arm→set GUIDED→disarm.

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
