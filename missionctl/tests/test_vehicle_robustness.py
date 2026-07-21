import asyncio

from missionctl.core.codec import MavlinkCodec, MavlinkMessage
from missionctl.core.vehicle import Vehicle


class _BrokenHeartbeat:
    """A message that claims to be a HEARTBEAT but whose dict is missing the
    fields the reducer needs — reduce_heartbeat will raise KeyError on it."""

    def get_type(self) -> str:
        return "HEARTBEAT"

    def get_srcSystem(self) -> int:
        return 1

    def get_srcComponent(self) -> int:
        return 1

    def to_dict(self) -> dict[str, object]:
        return {}  # no base_mode / custom_mode


async def test_bad_message_does_not_kill_the_actor() -> None:
    v = Vehicle(1, 1)
    v.start()

    v.deliver(_BrokenHeartbeat())  # would raise inside the reducer
    good = MavlinkCodec(system_id=1, component_id=1).raw.MAVLink_heartbeat_message(
        type=1, autopilot=3, base_mode=128, custom_mode=15, system_status=4, mavlink_version=3
    )
    v.deliver(good)

    # If the actor died on the bad message, the good one never processes and
    # this join hangs — so bound it.
    await asyncio.wait_for(v.wait_idle(), timeout=1.0)
    assert v.state.value.armed is True
    assert v.state.value.custom_mode == 15
    await v.stop()


async def test_request_data_streams_sends_expected_message() -> None:
    v = Vehicle(1, 1)
    codec = MavlinkCodec()
    sent: list[MavlinkMessage] = []

    async def send(msg: MavlinkMessage) -> None:
        sent.append(msg)

    v.bind_output(send=send, make=codec.make)
    await v.request_data_streams(rate_hz=5)

    assert sent[0].get_type() == "REQUEST_DATA_STREAM"
    d = sent[0].to_dict()
    assert d["req_stream_id"] == 0  # MAV_DATA_STREAM_ALL
    assert d["req_message_rate"] == 5
    assert d["start_stop"] == 1
