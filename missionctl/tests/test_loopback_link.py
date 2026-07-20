from missionctl.core.codec import MavlinkCodec
from missionctl.core.link.loopback import LoopbackLink


async def test_feed_then_read_decodes() -> None:
    link = LoopbackLink()
    await link.open()
    enc = MavlinkCodec(system_id=9)
    link.feed(
        enc.encode(
            enc.raw.MAVLink_heartbeat_message(
                type=2, autopilot=3, base_mode=0, custom_mode=0, system_status=0, mavlink_version=3
            )
        )
    )
    msgs = MavlinkCodec().decode(await link.read())
    assert msgs[0].get_type() == "HEARTBEAT"
    assert msgs[0].get_srcSystem() == 9


async def test_captures_writes() -> None:
    link = LoopbackLink()
    await link.open()
    await link.write(b"abc")
    await link.write(b"def")
    assert link.sent == [b"abc", b"def"]
