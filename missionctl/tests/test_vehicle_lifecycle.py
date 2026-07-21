from missionctl.core.codec import MavlinkCodec, MavlinkMessage
from missionctl.core.vehicle import Vehicle
from tests.support.waiters import wait_state

CODEC = MavlinkCodec(system_id=1, component_id=1)


def _heartbeat() -> MavlinkMessage:
    return CODEC.make(
        "heartbeat",
        type=1,
        autopilot=3,
        base_mode=0,
        custom_mode=0,
        system_status=4,
        mavlink_version=3,
    )


async def test_link_lost_after_timeout_and_recovers() -> None:
    v = Vehicle(1, 1, heartbeat_timeout=0.15, monitor_interval=0.03)
    v.start()
    try:
        v.deliver(_heartbeat())
        await wait_state(v, lambda s: s.link_alive, timeout=1.0)

        # No further heartbeats → monitor marks the link lost.
        await wait_state(v, lambda s: not s.link_alive, timeout=1.0)

        # Heartbeats resume → link marked alive again.
        v.deliver(_heartbeat())
        await wait_state(v, lambda s: s.link_alive, timeout=1.0)
    finally:
        await v.stop()
