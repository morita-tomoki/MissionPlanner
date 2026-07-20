# Discoveries

A living knowledge base of gotchas and hard-won facts, so no session re-learns
them. Add an entry the moment you burn time figuring something out. Searchable by
topic heading. (Decisions with trade-offs go in `decisions/` as ADRs instead.)

---

## ArduPilot SITL

- Start one vehicle: `sim_vehicle.py -v ArduCopter --console --map -I0`
- Second instance: `-I1` (its ports are offset by +10; default GCS UDP is
  `udp:127.0.0.1:14550`, instance 1 is `:14560`).
- SITL takes a few seconds to emit the first HEARTBEAT — wait for it before arming.
- (Confirm these on first real use and update if the local setup differs.)

## pymavlink (used as codec only)

- Use `pymavlink.dialects.v20.ardupilotmega` for the ArduPilot dialect.
- `mav.parse_buffer(bytes)` can return `None` (no complete message yet) — always
  guard with `or []`.
- Do **not** use `mavutil.mavlink_connection` for I/O — it blocks. We own the async
  transport; pymavlink only frames/deframes. (ADR-0004.)
- `MAVLink(None, srcSystem=…, srcComponent=…)` works for parse/pack (file only
  used when sending). Set `mav.robust_parsing = True` so garbage doesn't raise.
- With robust parsing, unparseable bytes come back as a `MAVLink_bad_data` message
  (`get_type() == "BAD_DATA"`), NOT an exception. `MavlinkCodec.decode` filters
  these out so callers see only real messages.
- pymavlink has no type stubs → confined to `core/codec` under a relaxed pyright
  execution environment; build dialect messages via `MavlinkCodec.raw` so the
  import stays in that one module.

## UDP transport

- Connect to SITL: `UdpLink(local_addr=("0.0.0.0", 14550))` (listen; learns the
  peer from the first datagram and can reply). A `remote_addr`-only link uses a
  *connected* socket, so `sendto(data)` takes no address (passing one raises).

## tlog format

- A `.tlog` is a sequence of records: 8-byte big-endian microsecond timestamp,
  followed by one raw MAVLink packet. Strip the 8 bytes before feeding the codec.

## Qt / qasync / macOS

- The core must never import PySide6 (import-linter enforces). Only `missionctl.qt`.
- On macOS the Qt event loop must run on the main thread; qasync installs the
  asyncio loop onto it. (Verify when M5 starts.)
- USB serial devices appear as `/dev/tty.usbmodem*`.
