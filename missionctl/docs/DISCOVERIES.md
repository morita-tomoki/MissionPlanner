# Discoveries

A living knowledge base of gotchas and hard-won facts, so no session re-learns
them. Add an entry the moment you burn time figuring something out. Searchable by
topic heading. (Decisions with trade-offs go in `decisions/` as ADRs instead.)

---

## ArduPilot SITL

TARGET FIRMWARE IS PINNED: **ArduPlane 4.6.3** (tag `Plane-4.6.3`) — ADR-0006.
Build and verify only against this version.

VERIFIED 2026-07-20 against 4.6.3: full stack over real UDP 14550 — connect,
real telemetry (mode=MANUAL, gps_fix=6, 10 sats, 584 m, 12.6 V), set_mode GUIDED,
arm, disarm, AND a full parameter download (`download_all` → 1445 params) all
succeeded. Assumptions held (ArduPlane DOES ACK DO_SET_MODE/ARM_DISARM; Plane mode
numbers correct; SI reducers sane).

### Build from source (no apt/sudo needed)
1. Clone shallow at the pinned tag:
   `git clone --depth 1 --recurse-submodules --shallow-submodules -b Plane-4.6.3 \
    https://github.com/ArduPilot/ardupilot.git`  (~380 MB)
   IMPORTANT: the recursive clone here can leave some submodules (e.g. `modules/waf`,
   `modules/mavlink`) empty, and `./waf` then just self-heals and asks to re-run
   without building. Run `git submodule update --init --recursive --depth 1` before
   building, and confirm `git submodule status --recursive | grep '^-'` is empty.
2. Build deps: `pexpect future pymavlink` via pip, plus **EmPy 3.3.4** — its wheel
   FAILS to build under modern pip. Workaround: EmPy is a single file; extract it:
   `pip download --no-deps --no-binary :all: empy==3.3.4 -d /tmp/e && tar xf … &&
    cp empy-3.3.4/em.py <user-site-packages>/`.
3. `cd ardupilot && python3 ./waf configure --board sitl && python3 ./waf plane`
   (~3.5 min; binary at `build/sitl/bin/arduplane`).

### Run it emitting MAVLink to our GCS on UDP 14550
```
build/sitl/bin/arduplane --model plane --speedup 10 \
  --home -35.363261,149.165230,584,353 \
  --defaults <defaults.parm> \
  --serial0 udpclient:127.0.0.1:14550
```
- Device string for UDP out is `udpclient:127.0.0.1:14550`. SITL is the udp client;
  our `UdpLink(local_addr=("0.0.0.0", 14550))` listens and learns the peer.
- Put `ARMING_CHECK 0` in the defaults file so the smoke test can arm. Base plane
  params: `Tools/autotest/models/plane.parm`.
- GPS reaches a 3D/RTK fix within a couple of seconds; first HEARTBEAT is near-
  instant. Then `make sitl` passes against it.
- (sim_vehicle.py + MAVProxy is the "normal" path but needs MAVProxy; running the
  binary directly with `--serial0 udpclient:` avoids that dependency.)

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

## Commands (Plane)

- Arm/disarm: `COMMAND_LONG` command=400 (MAV_CMD_COMPONENT_ARM_DISARM),
  param1=1/0, param2=21196 to force. Set mode: command=176 (MAV_CMD_DO_SET_MODE),
  param1=1 (MAV_MODE_FLAG_CUSTOM_MODE_ENABLED), param2=custom_mode number.
  Both answered by `COMMAND_ACK` with `result` (0 = MAV_RESULT_ACCEPTED).
- These IDs are the stable MAVLink standard; hardcoded in `protocols/command.py`
  to avoid importing pymavlink outside the codec (ADR-0004).
- Register the ACK waiter BEFORE sending the command (Vehicle.request does this),
  or a fast ACK can arrive before the waiter exists and be missed.

## Python tooling gotchas

- pyright strict won't bind a generic through a `@classmethod`/`@staticmethod`
  factory that uses the class TypeVar (`Result.success` → `Result[Unknown]`).
  Construct the dataclass directly and let the function's `-> Result[int]` return
  annotation infer the element type.
- ruff `ASYNC109` flags any async function with a `timeout` parameter. Our protocol
  API intentionally exposes per-op timeouts, so it's ignored in pyproject; the
  timeout is enforced internally with `asyncio.timeout(...)`.

## UDP transport

- Connect to SITL: `UdpLink(local_addr=("0.0.0.0", 14550))` (listen; learns the
  peer from the first datagram and can reply). A `remote_addr`-only link uses a
  *connected* socket, so `sendto(data)` takes no address (passing one raises).
- A **connected** UDP socket only accepts datagrams whose source matches its
  connected peer. So if you open a listen socket twice you rebind to a new source
  port, and a peer connected to the *first* port silently drops your writes.
  `UdpLink.open()` is therefore idempotent — a second open() is a no-op.
- Telemetry: ArduPilot stays nearly silent until the GCS sends REQUEST_DATA_STREAM
  (stream id 0 = ALL) or SET_MESSAGE_INTERVAL. We send REQUEST_DATA_STREAM on
  connect. If a real vehicle looks "connected but no telemetry", check this first.

## Testing

- `tests/support/fakeplane.py` is a minimal ArduPlane sim over real UDP (heartbeat
  + COMMAND_ACK). Use it for real-transport e2e without external SITL. It encodes
  OUR assumptions, so it is not a substitute for the `sitl`-marked smoke test.
- `sitl`-marked tests are excluded from `make check` (addopts `-m 'not sitl'`) and
  run via `make sitl` (which skips if 14550 is quiet).

## tlog format

- A `.tlog` is a sequence of records: 8-byte big-endian microsecond timestamp,
  followed by one raw MAVLink packet. Strip the 8 bytes before feeding the codec.

## Qt / qasync / macOS

- The core must never import PySide6 (import-linter enforces). Only `missionctl.qt`.
- On macOS the Qt event loop must run on the main thread; qasync installs the
  asyncio loop onto it. (Verify when M5 starts.)
- USB serial devices appear as `/dev/tty.usbmodem*`.
