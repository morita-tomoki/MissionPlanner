---
name: run-sitl
description: Run MissionCtl against ArduPilot SITL for end-to-end verification without real hardware. Use when a slice touches live telemetry, commands, params, or missions and needs to be proven against a simulated vehicle.
---

# Run against SITL

SITL (Software-In-The-Loop) is how we verify C2 behaviour end-to-end with no
aircraft. Prefer the automated smoke test; drop to manual only when debugging.

## Automated (preferred)
```bash
make sitl        # runs pytest -m sitl
```
These tests start/connect to SITL, run a scripted scenario, and assert on state.
Keep them fast and deterministic. If SITL is not installed, the marked tests skip
(they must never fail the normal `make check`).

## Manual (debugging)
1. Start one vehicle (needs ArduPilot's `sim_vehicle.py` on PATH):
   ```bash
   sim_vehicle.py -v ArduCopter --console --map -I0
   ```
   For a second vehicle in the same run, add another with `-I1` (ports +10).
2. Connect MissionCtl to `udp:127.0.0.1:14550` (instance 1: `:14560`).
3. Wait for the first HEARTBEAT before commanding (SITL needs a few seconds).

## After running
- If you learned something about the local SITL setup (flags, ports, timing),
  add it to `docs/DISCOVERIES.md` under "ArduPilot SITL" so the next session
  doesn't rediscover it.
- Gate any test that needs SITL behind the `sitl` pytest marker so the default
  headless `make check` stays hardware-free.
