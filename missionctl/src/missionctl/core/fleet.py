"""FleetManager — owns links, routes their traffic, and manages the set of
vehicles. Vehicles are created automatically the first time a new
``(sysid, compid)`` is seen, so multi-vehicle "just works", including the case of
several vehicles each on their own link.

Each vehicle is bound to the outbound of the link it was *discovered* on, so its
commands go back out the right link. Because a link's decoded chunk is routed
synchronously (no await between decode and routing), the per-chunk "active
outbound" is race-free even with multiple links pumping concurrently on the loop.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Awaitable, Callable, Iterable
from typing import NamedTuple

from missionctl.core.codec import MavlinkCodec, MavlinkMessage
from missionctl.core.link import Link
from missionctl.core.router import Address, Router
from missionctl.core.util.observable import Observable
from missionctl.core.vehicle import Vehicle

log = logging.getLogger(__name__)

_RECONNECT_BACKOFF_START = 1.0
_RECONNECT_BACKOFF_MAX = 16.0


class _Outbound(NamedTuple):
    send: Callable[[MavlinkMessage], Awaitable[None]]
    make: Callable[..., MavlinkMessage]


def _is_real_source(msg: MavlinkMessage) -> bool:
    """MAVLink system id 0 is the reserved "unknown/broadcast" id, never a real
    vehicle. Ignore such messages so they don't spawn a phantom (0,0) vehicle
    (observed from SITL during boot)."""
    return msg.get_srcSystem() != 0


class FleetManager:
    def __init__(self) -> None:
        self._router = Router()
        self._vehicles: dict[Address, Vehicle] = {}
        self._bg_tasks: set[asyncio.Task[None]] = set()
        # Set immediately before each synchronous routing block; a vehicle newly
        # discovered during that block binds to this link's outbound.
        self._active_outbound: _Outbound | None = None
        self._active_request_streams = False
        # Current fleet as an immutable tuple; the UI binds to this.
        self.fleet: Observable[tuple[Vehicle, ...]] = Observable(())
        self._router.on_unknown(self._on_unknown)

    @property
    def vehicles(self) -> tuple[Vehicle, ...]:
        return tuple(self._vehicles.values())

    def get(self, sysid: int, compid: int) -> Vehicle | None:
        return self._vehicles.get((sysid, compid))

    def ingest(self, messages: Iterable[MavlinkMessage]) -> None:
        """Route already-decoded messages with no link context (test/injection).
        Vehicles created this way are unbound (no outbound command path)."""
        self._active_outbound = None
        self._active_request_streams = False
        for msg in messages:
            if _is_real_source(msg):
                self._router.route(msg)

    async def run_link(
        self,
        link: Link,
        codec: MavlinkCodec | None = None,
        *,
        request_streams: bool = True,
        reconnect: bool = False,
    ) -> None:
        """Open a link and pump its bytes through the codec + router until EOF.

        One codec instance per link (it holds parser state). Vehicles discovered on
        this link bind to its outbound. Set ``request_streams=False`` for read-only
        sources like tlog replay. With ``reconnect=True``, on EOF or a transport
        error the link is closed and reopened with exponential backoff until the
        task is cancelled — vehicles then go link_alive=False via their own
        heartbeat timeout and recover when telemetry resumes.
        """
        codec = codec or MavlinkCodec()

        async def send(msg: MavlinkMessage) -> None:
            await link.write(codec.encode(msg))

        outbound = _Outbound(send=send, make=codec.make)
        backoff = _RECONNECT_BACKOFF_START
        while True:
            try:
                await link.open()
                backoff = _RECONNECT_BACKOFF_START  # reset after a clean open
                while chunk := await link.read():
                    messages = codec.decode(chunk)
                    # Set the active context right before the sync routing block.
                    self._active_outbound = outbound
                    self._active_request_streams = request_streams
                    for msg in messages:
                        if _is_real_source(msg):
                            self._router.route(msg)
            except (OSError, ConnectionError) as exc:
                if not reconnect:
                    raise
                log.warning("link error on %s: %s — reconnecting", type(link).__name__, exc)

            if not reconnect:
                return
            with contextlib.suppress(Exception):
                await link.close()
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, _RECONNECT_BACKOFF_MAX)

    async def stop(self) -> None:
        await asyncio.gather(*(v.stop() for v in self._vehicles.values()))

    def _on_unknown(self, address: Address, msg: MavlinkMessage) -> None:
        self._add(address).deliver(msg)

    def _add(self, address: Address) -> Vehicle:
        vehicle = Vehicle(address[0], address[1])
        outbound = self._active_outbound
        if outbound is not None:
            vehicle.bind_output(send=outbound.send, make=outbound.make)
        self._vehicles[address] = vehicle
        self._router.register(address, vehicle.deliver)
        vehicle.start()
        if outbound is not None and self._active_request_streams:
            # Fire-and-forget; request_data_streams handles its own errors.
            task = asyncio.create_task(
                vehicle.request_data_streams(), name=f"reqstream-{address[0]}-{address[1]}"
            )
            self._bg_tasks.add(task)
            task.add_done_callback(self._bg_tasks.discard)
        self.fleet.set(tuple(self._vehicles.values()))
        return vehicle
