# STATUS — you are here

> Keep this file tiny and current. It is the first thing a new session reads.
> Update it at the end of every session (`/end-session`).

## Baseline
- Branch: `claude/hud-structure-rendering-ja83ju` — open PR #2 into master.
- `make check`: green locally — 47 tests + 1 sitl (deselected), ruff, pyright
  strict, 2 import contracts. `make sitl` skips cleanly when no SITL is up.

## Scope (ADR-0005)
- Control target = **Plane**. Rover = display-only (vessel). Copter = excluded.

## Target firmware: ArduPlane 4.6.3 (pinned, ADR-0006)
- Verified 2026-07-20 against **4.6.3** over real UDP 14550: connect, telemetry,
  set_mode GUIDED, arm, disarm, and full `download_all` (1445 params) — all OK.
  Build+run recipe in DISCOVERIES → "ArduPilot SITL" (pins tag Plane-4.6.3; note
  the mandatory `git submodule update --init --recursive` step). SITL is ephemeral.

## Done
- M0 operating scaffold; M1 transport & codec (`UdpLink` = SITL transport).
- **M2 state from telemetry**: Router, Vehicle actor, FleetManager, 5 reducers.
- **M3 commands (CommandProtocol)**: arm/disarm + set_mode for Plane via
  `COMMAND_LONG`→`COMMAND_ACK`, timeout + retries, `Result` outcomes. Vehicle
  `request` primitive. `core/modes.py` Plane mode table.
- **M3 params (ParamProtocol)**: get (PARAM_REQUEST_READ→PARAM_VALUE), set
  (PARAM_SET→PARAM_VALUE), download_all (PARAM_REQUEST_LIST→N×PARAM_VALUE, with a
  progress callback; completes at param_count, fails on idle). Added Vehicle
  `open_stream` primitive and `protocols/channel.py` (shared I/O contracts +
  `MessageStream`). 44 tests.

## Hardening (done this session)
- Vehicle actor no longer dies on a malformed message (guarded reduce + logging).
- Telemetry requested on connect (REQUEST_DATA_STREAM ALL @4Hz) for live links.
- `UdpLink.open()` is idempotent (fixed a double-open socket-rebind bug found via
  the FakePlane e2e — see JOURNAL/DISCOVERIES).
- Added in-repo `FakePlane` (tests/support) + real-UDP e2e test, and a
  `sitl`-marked smoke test for the external SITL at 14550.

## M3 complete ✅
- Command, Param, and Mission protocols all implemented and **verified against
  real ArduPlane 4.6.3** (arm/mode/disarm, param get/set + 1445-param download,
  mission upload/download/set_current). Two `sitl`-marked tests pass on 4.6.3.

## Now
- Nothing in progress.

## Next single action
- **M4 — multi-vehicle**: run two SITL instances (I0 on 14550, I1 on 14560),
  connect one `UdpLink` per instance to the same `FleetManager`, assert two
  independent vehicles with independent state, and add a group command
  (`arm all`) via `asyncio.gather`. The actor model already supports this; this
  milestone proves it end-to-end. (Alternatively jump to **M5 Qt/QML UI** — the
  biggest remaining chunk — if the UI is higher priority than fleet scale.)
- Superseded next action was MissionProtocol (now done). in `core/protocols/mission.py`: download
  (MISSION_REQUEST_LIST → MISSION_COUNT → N× MISSION_REQUEST_INT/MISSION_ITEM_INT),
  upload (MISSION_COUNT → serve MISSION_REQUEST_INT → MISSION_ACK), and
  set-current (MISSION_SET_CURRENT). Uses both `request` and `open_stream`; the
  upload direction is a state machine (we answer the vehicle's item requests).
  Follow `/add-protocol`. Unit-test with a fake vehicle responder; SITL later.
  NOTE: mission items use frame/command enums — keep pymavlink confined to codec.

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
