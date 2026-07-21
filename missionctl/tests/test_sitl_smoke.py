"""SITL smoke test against an external ArduPlane SITL (developed in a separate
repo, reached at udp:0.0.0.0:14550).

Marked ``sitl`` so it is excluded from the default headless ``make check`` and run
only via ``make sitl``. It skips cleanly if 14550 can't be bound or no heartbeat
arrives, so ``make sitl`` is safe to run even when no SITL is up.
"""

import asyncio
import contextlib

import pytest

from missionctl.core.fleet import FleetManager
from missionctl.core.link.udp import UdpLink
from tests.support.waiters import await_vehicle

pytestmark = pytest.mark.sitl

SITL_ADDR = ("0.0.0.0", 14550)


async def test_connect_arm_setmode_disarm() -> None:
    gcs = UdpLink(local_addr=SITL_ADDR)
    try:
        await gcs.open()
    except OSError as exc:  # port busy / not permitted
        pytest.skip(f"cannot bind {SITL_ADDR}: {exc}")

    fleet = FleetManager()
    runner = asyncio.create_task(fleet.run_link(gcs))
    try:
        try:
            vehicle = await await_vehicle(fleet, timeout=5.0)
        except TimeoutError:
            pytest.skip("no SITL heartbeat on udp:0.0.0.0:14550")

        arm = await vehicle.commands.arm(timeout=5.0)
        assert arm.ok, f"arm failed: {arm.error}"

        mode = await vehicle.commands.set_mode("GUIDED", timeout=5.0)
        assert mode.ok, f"set_mode failed: {mode.error}"

        disarm = await vehicle.commands.disarm(timeout=5.0)
        assert disarm.ok, f"disarm failed: {disarm.error}"
    finally:
        runner.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await runner
        await fleet.stop()
        await gcs.close()
