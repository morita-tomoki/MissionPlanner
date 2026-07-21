"""Two real ArduPlane SITL instances (sysid 1 on 14550, sysid 2 on 14560) into
one FleetManager. Marked ``sitl``; skips if the instances aren't up.

Launch (from the built binary — see DISCOVERIES), each in its own dir with a
distinct SYSID_THISMAV:
    arduplane -I0 --serial0 udpclient:127.0.0.1:14550  (SYSID_THISMAV 1)
    arduplane -I1 --serial0 udpclient:127.0.0.1:14560  (SYSID_THISMAV 2)
"""

import asyncio
import contextlib

import pytest

from missionctl.core.fleet import FleetManager
from missionctl.core.link.udp import UdpLink
from tests.support.waiters import await_vehicle, wait_state

pytestmark = pytest.mark.sitl


async def test_two_sitl_independent_and_group_arm() -> None:
    links: list[UdpLink] = []
    try:
        for port in (14550, 14560):
            link = UdpLink(local_addr=("0.0.0.0", port))
            try:
                await link.open()
            except OSError as exc:
                pytest.skip(f"cannot bind {port}: {exc}")
            links.append(link)

        fleet = FleetManager()
        runners = [asyncio.create_task(fleet.run_link(link)) for link in links]
        try:
            try:
                v1 = await await_vehicle(fleet, (1, 1), timeout=8.0)
                v2 = await await_vehicle(fleet, (2, 1), timeout=8.0)
            except TimeoutError:
                pytest.skip("two SITL instances (sysid 1 & 2) not detected on 14550/14560")

            # Group arm via gather — each command round-trips on its own link.
            results = await asyncio.gather(
                v1.commands.arm(timeout=6.0), v2.commands.arm(timeout=6.0)
            )
            assert all(r.ok for r in results), results

            await wait_state(v1, lambda s: s.armed, timeout=6.0)
            await wait_state(v2, lambda s: s.armed, timeout=6.0)

            # Independent: disarm only v1.
            assert (await v1.commands.disarm(timeout=6.0)).ok
            await wait_state(v1, lambda s: not s.armed, timeout=6.0)
            assert v1.state.value.armed is False
            assert v2.state.value.armed is True
        finally:
            for r in runners:
                r.cancel()
            for r in runners:
                with contextlib.suppress(asyncio.CancelledError):
                    await r
            await fleet.stop()
    finally:
        for link in links:
            await link.close()
