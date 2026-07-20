"""A single vehicle, modeled as an asyncio actor (ADR-0003).

Each vehicle owns a private inbox and its own task: it consumes messages,
folds them into an immutable ``VehicleState`` via the pure reducers, and
publishes each new snapshot on an observable. No shared mutable state, no locks —
N vehicles are N independent actors, which is what makes multi-vehicle safe.

A vehicle also exposes an outbound path once bound to a link (``bind_output``):
protocols send a message and await a specific reply via ``request`` (the reply
waiter is registered *before* the send, so a fast ACK cannot be missed).
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from missionctl.core.codec import MavlinkMessage
from missionctl.core.protocols import CommandProtocol, MakeFn
from missionctl.core.state import VehicleState, reduce
from missionctl.core.util.observable import Observable

Predicate = Callable[[MavlinkMessage], bool]
SendFn = Callable[[MavlinkMessage], Awaitable[None]]


class Vehicle:
    def __init__(self, sysid: int, compid: int) -> None:
        self.sysid = sysid
        self.compid = compid
        self._inbox: asyncio.Queue[MavlinkMessage] = asyncio.Queue()
        self._state: Observable[VehicleState] = Observable(VehicleState.initial(sysid, compid))
        self._task: asyncio.Task[None] | None = None
        self._waiters: list[tuple[Predicate, asyncio.Future[MavlinkMessage]]] = []
        self._send: SendFn | None = None
        self._commands: CommandProtocol | None = None

    @property
    def address(self) -> tuple[int, int]:
        return (self.sysid, self.compid)

    @property
    def state(self) -> Observable[VehicleState]:
        return self._state

    @property
    def commands(self) -> CommandProtocol:
        if self._commands is None:
            raise RuntimeError("vehicle has no outbound link bound (call bind_output)")
        return self._commands

    def bind_output(self, *, send: SendFn, make: MakeFn) -> None:
        """Wire the outbound path (called by FleetManager with the link's writer)."""
        self._send = send
        self._commands = CommandProtocol(make=make, request=self.request, target=self.address)

    def deliver(self, msg: MavlinkMessage) -> None:
        """Hand a message to this vehicle's inbox (called by the router)."""
        self._inbox.put_nowait(msg)

    async def request(
        self, message: MavlinkMessage, predicate: Predicate, timeout: float
    ) -> MavlinkMessage:
        """Register a reply waiter, send ``message``, and await the first incoming
        message matching ``predicate``. Raises ``TimeoutError`` on timeout."""
        if self._send is None:
            raise RuntimeError("vehicle has no outbound link bound")
        loop = asyncio.get_running_loop()
        future: asyncio.Future[MavlinkMessage] = loop.create_future()
        entry = (predicate, future)
        self._waiters.append(entry)
        try:
            await self._send(message)
            async with asyncio.timeout(timeout):
                return await future
        finally:
            if entry in self._waiters:
                self._waiters.remove(entry)

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
                self._resolve_waiters(msg)
            finally:
                self._inbox.task_done()

    def _resolve_waiters(self, msg: MavlinkMessage) -> None:
        for entry in list(self._waiters):
            predicate, future = entry
            if not future.done() and predicate(msg):
                future.set_result(msg)
                self._waiters.remove(entry)
