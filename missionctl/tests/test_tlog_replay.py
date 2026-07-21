from pathlib import Path

from missionctl.core.codec import MavlinkCodec
from missionctl.core.link.tlog_replay import TlogReplayLink


def _write_tlog(path: Path, heartbeats: int) -> None:
    enc = MavlinkCodec(system_id=1)
    buf = bytearray()
    for i in range(heartbeats):
        hb = enc.raw.MAVLink_heartbeat_message(
            type=2, autopilot=3, base_mode=0, custom_mode=0, system_status=0, mavlink_version=3
        )
        packet: bytes = enc.encode(hb)
        buf += (1_000_000 * i).to_bytes(8, "big")  # 8-byte µs timestamp
        buf += packet
    path.write_bytes(bytes(buf))


async def test_replay_strips_timestamps_and_yields_frames(tmp_path: Path) -> None:
    tlog = tmp_path / "flight.tlog"
    _write_tlog(tlog, heartbeats=5)

    link = TlogReplayLink(tlog)
    await link.open()
    dec = MavlinkCodec()

    count = 0
    while chunk := await link.read():
        for msg in dec.decode(chunk):
            if msg.get_type() == "HEARTBEAT":
                count += 1

    assert count == 5


async def test_empty_tlog_reads_eof(tmp_path: Path) -> None:
    tlog = tmp_path / "empty.tlog"
    tlog.write_bytes(b"")
    link = TlogReplayLink(tlog)
    await link.open()
    assert await link.read() == b""
