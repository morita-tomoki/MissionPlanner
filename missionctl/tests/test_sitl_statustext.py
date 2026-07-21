"""Capture a real PreArm/Arm STATUSTEXT from ArduPlane SITL.

Marked ``sitl``. Enables all arming checks and attempts to arm; if arming is
refused (the usual case) a PreArm/Arm STATUSTEXT must have been captured. If the
vehicle happens to be armable, the test skips rather than failing (non-flaky).
"""

import asyncio
import contextlib

import pytest

from missionctl.core.fleet import FleetManager
from missionctl.core.link.udp import UdpLink
from tests.support.waiters import await_vehicle, wait_state

pytestmark = pytest.mark.sitl


async def test_prearm_or_arm_statustext_is_captured() -> None:
    gcs = UdpLink(local_addr=("0.0.0.0", 14550))
    try:
        await gcs.open()
    except OSError as exc:
        pytest.skip(f"cannot bind 14550: {exc}")

    fleet = FleetManager()
    runner = asyncio.create_task(fleet.run_link(gcs))
    try:
        try:
            vehicle = await await_vehicle(fleet, timeout=5.0)
        except TimeoutError:
            pytest.skip("no SITL heartbeat on udp:0.0.0.0:14550")

        assert (await vehicle.params.set("ARMING_CHECK", 1, timeout=3.0)).ok
        arm = await vehicle.commands.arm(timeout=5.0)
        if arm.ok:
            await vehicle.commands.disarm(timeout=5.0)
            pytest.skip("vehicle was armable; no PreArm/Arm STATUSTEXT emitted")

        with contextlib.suppress(TimeoutError):
            await wait_state(
                vehicle,
                lambda s: any("Arm" in m.text for m in s.messages),
                timeout=5.0,
            )
        arm_msgs = [m for m in vehicle.state.value.messages if "Arm" in m.text]
        assert arm_msgs, "expected a PreArm/Arm STATUSTEXT after a refused arm"
    finally:
        runner.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await runner
        await fleet.stop()
        await gcs.close()
