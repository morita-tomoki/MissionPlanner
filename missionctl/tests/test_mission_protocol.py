from missionctl.core.codec import MavlinkCodec, MavlinkMessage
from missionctl.core.protocols import MissionItem
from missionctl.core.vehicle import Vehicle

CODEC = MavlinkCodec()


def _wp(seq: int, lat_e7: int, lon_e7: int, alt: float) -> MissionItem:
    return MissionItem(seq=seq, command=16, x=lat_e7, y=lon_e7, z=alt)


async def test_download_reads_all_items() -> None:
    """Fake vehicle: answer REQUEST_LIST with COUNT, each REQUEST_INT with an ITEM."""
    v = Vehicle(1, 1)
    stored = [_wp(0, -353632610, 1491652300, 100.0), _wp(1, -353600000, 1491600000, 120.0)]

    async def responder(msg: MavlinkMessage) -> None:
        t = msg.get_type()
        if t == "MISSION_REQUEST_LIST":
            v.deliver(
                CODEC.make(
                    "mission_count",
                    target_system=255,
                    target_component=0,
                    count=len(stored),
                    mission_type=0,
                )
            )
        elif t == "MISSION_REQUEST_INT":
            seq = int(msg.to_dict()["seq"])
            it = stored[seq]
            v.deliver(
                CODEC.make(
                    "mission_item_int",
                    target_system=255,
                    target_component=0,
                    seq=it.seq,
                    frame=it.frame,
                    command=it.command,
                    current=it.current,
                    autocontinue=it.autocontinue,
                    param1=it.param1,
                    param2=it.param2,
                    param3=it.param3,
                    param4=it.param4,
                    x=it.x,
                    y=it.y,
                    z=it.z,
                    mission_type=0,
                )
            )

    v.bind_output(send=responder, make=CODEC.make)
    v.start()
    res = await v.mission.download(timeout=1.0, item_timeout=1.0)
    assert res.ok
    assert res.value is not None
    assert [i.seq for i in res.value] == [0, 1]
    assert res.value[0].command == 16
    assert res.value[1].z == 120.0
    await v.stop()


async def test_upload_drives_the_handshake() -> None:
    """Fake vehicle: on COUNT, request each item, then ACK accepted."""
    v = Vehicle(1, 1)
    received: list[int] = []

    async def responder(msg: MavlinkMessage) -> None:
        t = msg.get_type()
        if t == "MISSION_COUNT":
            count = int(msg.to_dict()["count"])
            for seq in range(count):
                v.deliver(
                    CODEC.make(
                        "mission_request_int",
                        target_system=255,
                        target_component=0,
                        seq=seq,
                        mission_type=0,
                    )
                )
        elif t == "MISSION_ITEM_INT":
            received.append(int(msg.to_dict()["seq"]))
            # once we've been sent the last item, ACK
            if len(received) == 3:
                v.deliver(
                    CODEC.make(
                        "mission_ack",
                        target_system=255,
                        target_component=0,
                        type=0,
                        mission_type=0,
                    )
                )

    v.bind_output(send=responder, make=CODEC.make)
    v.start()
    items = [_wp(i, -353632610 + i, 1491652300, 50.0 + i) for i in range(3)]
    res = await v.mission.upload(items, timeout=2.0)
    assert res.ok
    assert res.value == 3
    assert received == [0, 1, 2]
    await v.stop()


async def test_upload_rejected() -> None:
    v = Vehicle(1, 1)

    async def responder(msg: MavlinkMessage) -> None:
        if msg.get_type() == "MISSION_COUNT":
            v.deliver(
                CODEC.make(
                    "mission_ack",
                    target_system=255,
                    target_component=0,
                    type=13,  # MAV_MISSION_ERROR
                    mission_type=0,
                )
            )

    v.bind_output(send=responder, make=CODEC.make)
    v.start()
    res = await v.mission.upload([_wp(0, 0, 0, 10.0)], timeout=1.0)
    assert not res.ok
    assert res.error is not None and "13" in res.error
    await v.stop()


async def test_set_current() -> None:
    v = Vehicle(1, 1)

    async def responder(msg: MavlinkMessage) -> None:
        if msg.get_type() == "MISSION_SET_CURRENT":
            seq = int(msg.to_dict()["seq"])
            v.deliver(
                CODEC.make("mission_current", seq=seq, total=5, mission_state=0, mission_mode=0)
            )

    v.bind_output(send=responder, make=CODEC.make)
    v.start()
    res = await v.mission.set_current(3, timeout=1.0)
    assert res.ok
    assert res.value == 3
    await v.stop()
