"""FleetManager — owns links, routes their traffic, and manages the set of
vehicles. Vehicles are created automatically the first time a new
``(sysid, compid)`` is seen, so multi-vehicle "just works" for any link carrying
more than one craft.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterable

from missionctl.core.codec import MavlinkCodec, MavlinkMessage
from missionctl.core.link import Link
from missionctl.core.router import Address, Router
from missionctl.core.util.observable import Observable
from missionctl.core.vehicle import Vehicle


class FleetManager:
    def __init__(self) -> None:
        self._router = Router()
        self._vehicles: dict[Address, Vehicle] = {}
        # Current fleet as an immutable tuple; the UI binds to this.
        self.fleet: Observable[tuple[Vehicle, ...]] = Observable(())
        self._router.on_unknown(self._on_unknown)

    @property
    def vehicles(self) -> tuple[Vehicle, ...]:
        return tuple(self._vehicles.values())

    def get(self, sysid: int, compid: int) -> Vehicle | None:
        return self._vehicles.get((sysid, compid))

    def ingest(self, messages: Iterable[MavlinkMessage]) -> None:
        """Route already-decoded messages to their vehicles."""
        for msg in messages:
            self._router.route(msg)

    async def run_link(self, link: Link, codec: MavlinkCodec | None = None) -> None:
        """Open a link and pump its bytes through the codec + router until EOF.

        One codec instance per link (it holds parser state). Runs until the link
        returns b"" (e.g. a tlog reaching its end); a live link runs until closed.
        """
        codec = codec or MavlinkCodec()
        await link.open()
        while chunk := await link.read():
            self.ingest(codec.decode(chunk))

    async def stop(self) -> None:
        await asyncio.gather(*(v.stop() for v in self._vehicles.values()))

    def _on_unknown(self, address: Address, msg: MavlinkMessage) -> None:
        self._add(address).deliver(msg)

    def _add(self, address: Address) -> Vehicle:
        vehicle = Vehicle(address[0], address[1])
        self._vehicles[address] = vehicle
        self._router.register(address, vehicle.deliver)
        vehicle.start()
        self.fleet.set(tuple(self._vehicles.values()))
        return vehicle
