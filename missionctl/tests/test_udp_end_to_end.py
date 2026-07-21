"""End-to-end over real UDP sockets using the in-repo FakePlane simulator.

This exercises the actual transport + codec + router + vehicle + command path —
not hand-written fakes wired straight into a Vehicle — so it catches wiring bugs
the unit tests can't. It is NOT a substitute for the external SITL smoke test
(FakePlane only models our assumptions about ArduPlane).
"""

import asyncio
import contextlib

from missionctl.core.fleet import FleetManager
from missionctl.core.link.udp import UdpLink
from tests.support.fakeplane import FakePlane
from tests.support.waiters import await_vehicle, wait_state


async def test_discover_arm_and_setmode_over_udp() -> None:
    gcs = UdpLink(local_addr=("127.0.0.1", 0))
    await gcs.open()
    fleet = FleetManager()
    runner = asyncio.create_task(fleet.run_link(gcs))
    plane = FakePlane(("127.0.0.1", gcs.local_port))
    await plane.start()
    try:
        # Discovered from a real heartbeat over the wire.
        vehicle = await await_vehicle(fleet, (1, 1), timeout=3.0)
        await wait_state(vehicle, lambda s: not s.armed, timeout=3.0)

        # Command round-trips over real UDP (COMMAND_LONG -> COMMAND_ACK).
        assert (await vehicle.commands.arm(timeout=3.0)).ok
        assert (await vehicle.commands.set_mode("GUIDED", timeout=3.0)).ok

        # FakePlane reflects the changes into its heartbeat; state catches up.
        await wait_state(vehicle, lambda s: s.armed and s.custom_mode == 15, timeout=3.0)
    finally:
        await plane.stop()
        runner.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await runner
        await fleet.stop()
        await gcs.close()
