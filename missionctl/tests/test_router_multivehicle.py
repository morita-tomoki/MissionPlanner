from missionctl.core.codec import MavlinkCodec, MavlinkMessage
from missionctl.core.fleet import FleetManager


def _heartbeat(system_id: int, *, armed: bool, mode: int) -> list[MavlinkMessage]:
    # Encode with the given system id, then decode so the message carries the
    # correct src ids on the wire (routing keys off get_srcSystem/Component).
    enc = MavlinkCodec(system_id=system_id, component_id=1)
    hb = enc.raw.MAVLink_heartbeat_message(
        type=2,
        autopilot=3,
        base_mode=128 if armed else 0,
        custom_mode=mode,
        system_status=4,
        mavlink_version=3,
    )
    return MavlinkCodec().decode(enc.encode(hb))


async def test_two_vehicles_get_independent_state() -> None:
    fleet = FleetManager()
    fleet.ingest(_heartbeat(1, armed=True, mode=3) + _heartbeat(2, armed=False, mode=9))

    assert {v.address for v in fleet.vehicles} == {(1, 1), (2, 1)}
    v1 = fleet.get(1, 1)
    v2 = fleet.get(2, 1)
    assert v1 is not None and v2 is not None

    await v1.wait_idle()
    await v2.wait_idle()

    assert v1.state.value.armed is True
    assert v1.state.value.custom_mode == 3
    assert v2.state.value.armed is False
    assert v2.state.value.custom_mode == 9

    await fleet.stop()


async def test_fleet_observable_tracks_new_vehicles() -> None:
    fleet = FleetManager()
    seen: list[int] = []
    fleet.fleet.subscribe(lambda vs: seen.append(len(vs)))  # emits 0 immediately

    fleet.ingest(_heartbeat(1, armed=False, mode=0))
    fleet.ingest(_heartbeat(2, armed=False, mode=0))

    assert seen == [0, 1, 2]
    await fleet.stop()
