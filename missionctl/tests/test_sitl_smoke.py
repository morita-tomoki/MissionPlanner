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
from missionctl.core.protocols import MissionItem
from tests.support.waiters import await_vehicle

pytestmark = pytest.mark.sitl

SITL_ADDR = ("0.0.0.0", 14550)
HOME_LAT_E7, HOME_LON_E7 = -353632610, 1491652300


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


async def test_mission_upload_download_roundtrip() -> None:
    gcs = UdpLink(local_addr=SITL_ADDR)
    try:
        await gcs.open()
    except OSError as exc:
        pytest.skip(f"cannot bind {SITL_ADDR}: {exc}")

    fleet = FleetManager()
    runner = asyncio.create_task(fleet.run_link(gcs))
    try:
        try:
            vehicle = await await_vehicle(fleet, timeout=5.0)
        except TimeoutError:
            pytest.skip("no SITL heartbeat on udp:0.0.0.0:14550")

        items = [
            MissionItem(seq=0, command=16, x=HOME_LAT_E7, y=HOME_LON_E7, z=0.0, frame=0),
            MissionItem(seq=1, command=16, x=HOME_LAT_E7 + 1000, y=HOME_LON_E7 + 1000, z=100.0),
            MissionItem(seq=2, command=16, x=HOME_LAT_E7 + 2000, y=HOME_LON_E7, z=120.0),
        ]
        up = await vehicle.mission.upload(items, timeout=5.0)
        assert up.ok, f"upload failed: {up.error}"

        dn = await vehicle.mission.download(timeout=5.0, item_timeout=3.0)
        assert dn.ok, f"download failed: {dn.error}"
        assert dn.value is not None and len(dn.value) == 3

        sc = await vehicle.mission.set_current(1, timeout=3.0)
        assert sc.ok, f"set_current failed: {sc.error}"
    finally:
        runner.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await runner
        await fleet.stop()
        await gcs.close()
