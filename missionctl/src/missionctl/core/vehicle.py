"""A single vehicle, modeled as an asyncio actor (ADR-0003).

Each vehicle owns a private inbox and its own task: it consumes messages,
folds them into an immutable ``VehicleState`` via the pure reducers, and
publishes each new snapshot on an observable. No shared mutable state, no locks —
N vehicles are N independent actors, which is what makes multi-vehicle safe.
"""

from __future__ import annotations

import asyncio

from missionctl.core.codec import MavlinkMessage
from missionctl.core.state import VehicleState, reduce
from missionctl.core.util.observable import Observable


class Vehicle:
    def __init__(self, sysid: int, compid: int) -> None:
        self.sysid = sysid
        self.compid = compid
        self._inbox: asyncio.Queue[MavlinkMessage] = asyncio.Queue()
        self._state: Observable[VehicleState] = Observable(VehicleState.initial(sysid, compid))
        self._task: asyncio.Task[None] | None = None

    @property
    def address(self) -> tuple[int, int]:
        return (self.sysid, self.compid)

    @property
    def state(self) -> Observable[VehicleState]:
        return self._state

    def deliver(self, msg: MavlinkMessage) -> None:
        """Hand a message to this vehicle's inbox (called by the router)."""
        self._inbox.put_nowait(msg)

    def start(self) -> asyncio.Task[None]:
        if self._task is None:
            self._task = asyncio.create_task(
                self._run(), name=f"vehicle-{self.sysid}-{self.compid}"
            )
        return self._task

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
            self._task = None

    async def wait_idle(self) -> None:
        """Await until every delivered message has been processed (test helper)."""
        await self._inbox.join()

    async def _run(self) -> None:
        while True:
            msg = await self._inbox.get()
            try:
                self._state.set(reduce(self._state.value, msg))
            finally:
                self._inbox.task_done()
