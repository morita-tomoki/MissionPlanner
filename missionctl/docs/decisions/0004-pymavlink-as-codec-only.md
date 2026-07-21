# 4. pymavlink as a codec only (we own the async transport)

## Status
Accepted — 2026-07-20

## Context
We need MAVLink framing for the ArduPilot dialect. `pymavlink` is the canonical
ArduPilot library, but its `mavutil.mavlink_connection` owns the socket/serial
handle and uses blocking reads — exactly the pattern that made the legacy GCS
freeze and forced a thread-per-link model.

## Decision
Use `pymavlink` strictly as a **codec**: `MAVLink.parse_buffer(bytes) -> messages`
and `msg.pack(mav) -> bytes`. All I/O is owned by `missionctl.core.link` (async
transports). pymavlink never touches a socket in this project. The dialect XML
(common / ardupilotmega) is the reusable asset carried over from the ecosystem.

## Consequences
- Non-blocking, single-threaded async I/O with backpressure.
- We can feed the same codec from a live link or a `TlogReplayLink` for tests —
  identical parsing path in prod and in CI.
- We reimplement connection/retry logic ourselves (in `protocols/`), which we want
  anyway for cancellation + timeouts.

## Rejected alternatives
- `mavutil` for I/O: blocking, thread-bound, hard to cancel — the legacy trap.
- MAVSDK: incomplete ArduPilot support, extra server process (see ADR-0002).
