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

## M3 + M4 complete ✅
- **M3**: Command/Param/Mission protocols — verified on real ArduPlane 4.6.3.
- **M4 multi-vehicle**: FleetManager binds each vehicle to its discovery link's
  outbound (per-chunk active-outbound, race-free across concurrent links);
  ignores reserved sysid 0. Verified with two FakePlanes (headless) AND **two
  real SITL instances** (sysid 1/2 on 14550/14560): independent state + group arm
  via `asyncio.gather`. 53 headless tests + 3 sitl tests.

## Robustness pass (done 2026-07-20)
- Vehicle lost detection (`link_alive` via per-vehicle heartbeat-timeout monitor);
  link reconnection (`run_link(reconnect=True)`, exp backoff); `set_mode(confirm=
  True)` confirms via HEARTBEAT; `set_safety(safe)` (MAV_CMD_DO_SET_SAFETY_SWITCH_
  STATE 5300). Mode-confirm + safety verified on real 4.6.3; lost/reconnect via
  headless tests. 58 headless tests + 3 sitl.

## Now
- Nothing in progress. The whole C2 core (connect → telemetry → commands →
  params → mission → multi-vehicle) is implemented, SITL-verified on 4.6.3, and
  hardened (lost detection, reconnection, mode-confirm, safety switch).

## Next single action
- **M5 — Qt/QML UI** (the largest remaining chunk). Start `missionctl.qt`:
  `qasync` app bootstrap (`missionctl.qt.app`), a `FleetModel(QAbstractListModel)`
  over `FleetManager.fleet`, and a `VehicleVM(QObject)` exposing one vehicle's
  `VehicleState` via `Q_PROPERTY`/`NOTIFY` + `@Slot` commands. First slice: a
  minimal QML window listing the fleet and showing one vehicle's mode/armed/gps.
  NOTE: Qt needs the `gui` extra and a display — this milestone is real work on
  the Mac; it cannot be exercised headlessly in the cloud container. Keep all
  logic in ViewModels so it stays unit-testable without a display. in `core/protocols/mission.py`: download
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
