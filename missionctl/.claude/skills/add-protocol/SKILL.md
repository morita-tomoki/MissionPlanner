---
name: add-protocol
description: Add a new MAVLink micro-protocol (e.g. param, mission, fence, rally, log download) to the MissionCtl core in the standard shape. Use when implementing a new command/telemetry protocol under core/protocols.
---

# Add a MAVLink protocol

Every protocol follows the same shape so the codebase stays uniform and testable.
Do not fold protocols together — one file, one concern (avoid the legacy god-class).

## Steps

1. **One file per protocol** under `src/missionctl/core/protocols/<name>.py`.
   No Qt imports. Pure async.

2. **Async + cancellable + explicit timeout.** Every public operation:
   - is `async def`, takes `timeout: float` and honours `CancellationToken`/
     `asyncio.timeout`,
   - subscribes to the relevant incoming message(s), sends its request, awaits the
     matching reply, and unsubscribes in `finally`,
   - retries with an explicit policy (do not spin; no busy-wait).
   - **Never** exposes a synchronous wrapper. (See CLAUDE.md invariants.)

3. **Return `Result`-style outcomes** for expected failures (timeout, NACK) and
   raise typed exceptions only for genuine faults. No bare `except: pass`.

4. **Dependencies are injected**, not global: the protocol receives a `send`
   callable and a `subscribe`/message-stream handle from its `Vehicle`. This keeps
   it unit-testable with fakes.

5. **Tests (headless first):**
   - Unit test with a fake message stream (stdlib only) — happy path, timeout,
     NACK, cancellation.
   - If it commands a vehicle, add a `@pytest.mark.sitl` end-to-end test.

6. **Wire it into `Vehicle`** as an attribute (e.g. `self.mission = MissionProtocol(...)`).

7. **Update docs:** tick the ROADMAP box, note any protocol quirks in DISCOVERIES.

## Reference
`docs/ARCHITECTURE.md` → "core.protocols", and ADR-0004 (pymavlink is codec-only).
