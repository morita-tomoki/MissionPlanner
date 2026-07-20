# Journal

Append-only. One dated entry per session. Newest at the top. Keep entries short:
what changed, why, and what's next. This is the narrative memory of the project.

---

## 2026-07-20 — M1 transport & codec

- Implemented `MavlinkCodec` (ADR-0004: pymavlink as codec only, no I/O). Stateful
  parser reassembles frames split across reads; drops `MAVLink_bad_data`; public
  surface typed via `MavlinkMessage` protocol so strict core is unaffected.
- Added three `Link` implementations: `LoopbackLink` (in-memory test double),
  `UdpLink` (async UDP, listen + connect modes — this is how we'll reach SITL at
  udp:127.0.0.1:14550), `TlogReplayLink` (strips 8-byte µs timestamps, frames
  MAVLink v1/v2 including signed).
- Isolated pymavlink's untyped-ness to a single relaxed pyright execution
  environment on `core/codec`; rest of core stays strict. import-linter layers
  updated to include `codec`.
- 20 tests green (codec roundtrip/split/garbage, loopback, udp roundtrip + peer
  learning, tlog replay count). User confirmed M0 PR merged; SITL lives in a
  separate repo and will be connected at 14550 later.
- Next: M2 — Router demux + Vehicle actor + first HEARTBEAT reducer.

---

## 2026-07-20 — M0 operating scaffold

- Bootstrapped the repository as a Python + Qt Quick (QML) rewrite of the C2 layer.
- Established the operating system for long-horizon solo/Claude development:
  `CLAUDE.md` contract, `docs/` ledger (this journal, STATUS, ROADMAP, ARCHITECTURE,
  DISCOVERIES, QUESTIONS, ADRs), and `.claude/skills` (start/end-session, run-sitl,
  add-protocol, record-decision).
- Decided the core architecture: pure-Python asyncio core that never imports Qt,
  one actor per vehicle, immutable SI-unit state, pymavlink as codec only. Recorded
  as ADR-0002/0003/0004.
- Wired the trust substrate: `make check` (ruff + pyright strict + import-linter +
  pytest) and a CI workflow; import-linter forbids `core` → Qt.
- Implemented a minimal green core so the baseline is real from day one.
- Next: M1 — MavlinkCodec over pymavlink + first parse test.
