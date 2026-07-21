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

If no SITL is installed, build ArduPlane SITL from source — the full, verified
recipe (clone, the EmPy 3.3.4 `em.py` workaround, `waf` build, and the exact
launch line) is in `docs/DISCOVERIES.md` → "ArduPilot SITL". Summary:

1. Launch the built binary emitting MAVLink to our GCS on UDP 14550:
   ```bash
   build/sitl/bin/arduplane --model plane --speedup 10 \
     --home -35.363261,149.165230,584,353 --defaults <defaults.parm> \
     --serial0 udpclient:127.0.0.1:14550
   ```
   Put `ARMING_CHECK 0` in the defaults so the smoke test can arm.
2. Our GCS listens: `UdpLink(local_addr=("0.0.0.0", 14550))` (this is what
   `test_sitl_smoke.py` does). First HEARTBEAT is near-instant; GPS fix in ~2 s.
3. `make sitl` should then pass (connect → arm → GUIDED → disarm).

## After running
- If you learned something about the local SITL setup (flags, ports, timing),
  add it to `docs/DISCOVERIES.md` under "ArduPilot SITL" so the next session
  doesn't rediscover it.
- Gate any test that needs SITL behind the `sitl` pytest marker so the default
  headless `make check` stays hardware-free.
