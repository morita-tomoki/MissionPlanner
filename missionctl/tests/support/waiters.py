"""Small async polling helpers shared by integration tests."""

from __future__ import annotations

import asyncio
from collections.abc import Callable

from missionctl.core.fleet import FleetManager
from missionctl.core.state import VehicleState
from missionctl.core.vehicle import Vehicle


async def await_vehicle(
    fleet: FleetManager, address: tuple[int, int] | None = None, *, timeout: float
) -> Vehicle:
    """Wait until a vehicle (a specific address, or any) has been discovered."""
    async with asyncio.timeout(timeout):
        while True:
            if address is None:
                if fleet.vehicles:
                    return fleet.vehicles[0]
            else:
                vehicle = fleet.get(*address)
                if vehicle is not None:
                    return vehicle
            await asyncio.sleep(0.02)


async def wait_state(
    vehicle: Vehicle, predicate: Callable[[VehicleState], bool], *, timeout: float
) -> None:
    """Wait until the vehicle's published state satisfies ``predicate``."""
    async with asyncio.timeout(timeout):
        while not predicate(vehicle.state.value):
            await asyncio.sleep(0.02)
