"""Two vehicles, each on its own real UDP link, into one FleetManager.

Validates the actor model + per-link outbound binding: two FakePlanes with
distinct sysids appear as two independent vehicles, and a command sent to one
must be answered by that vehicle's own link (not leak to the other). Runs in the
default gate (no external SITL).
"""

import asyncio
import contextlib

from missionctl.core.fleet import FleetManager
from missionctl.core.link.udp import UdpLink
from tests.support.fakeplane import FakePlane
from tests.support.waiters import await_vehicle, wait_state


async def test_two_vehicles_on_two_links() -> None:
    gcs1 = UdpLink(local_addr=("127.0.0.1", 0))
    gcs2 = UdpLink(local_addr=("127.0.0.1", 0))
    await gcs1.open()
    await gcs2.open()

    fleet = FleetManager()
    runners = [
        asyncio.create_task(fleet.run_link(gcs1)),
        asyncio.create_task(fleet.run_link(gcs2)),
    ]
    plane1 = FakePlane(("127.0.0.1", gcs1.local_port), sysid=1)
    plane2 = FakePlane(("127.0.0.1", gcs2.local_port), sysid=2)
    await plane1.start()
    await plane2.start()
    try:
        v1 = await await_vehicle(fleet, (1, 1), timeout=3.0)
        v2 = await await_vehicle(fleet, (2, 1), timeout=3.0)
        assert {v.address for v in fleet.vehicles} == {(1, 1), (2, 1)}

        # Group arm via asyncio.gather — each command must round-trip on its own link.
        results = await asyncio.gather(v1.commands.arm(timeout=3.0), v2.commands.arm(timeout=3.0))
        assert all(r.ok for r in results)

        await wait_state(v1, lambda s: s.armed, timeout=3.0)
        await wait_state(v2, lambda s: s.armed, timeout=3.0)

        # Independent state: disarm only vehicle 1.
        assert (await v1.commands.disarm(timeout=3.0)).ok
        await wait_state(v1, lambda s: not s.armed, timeout=3.0)
        assert v1.state.value.armed is False
        assert v2.state.value.armed is True  # vehicle 2 untouched
    finally:
        await plane1.stop()
        await plane2.stop()
        for r in runners:
            r.cancel()
        for r in runners:
            with contextlib.suppress(asyncio.CancelledError):
                await r
        await fleet.stop()
        await gcs1.close()
        await gcs2.close()
