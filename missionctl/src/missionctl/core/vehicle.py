"""A single vehicle, modeled as an asyncio actor (ADR-0003).

Each vehicle owns a private inbox and its own task: it consumes messages,
folds them into an immutable ``VehicleState`` via the pure reducers, and
publishes each new snapshot on an observable. No shared mutable state, no locks —
N vehicles are N independent actors, which is what makes multi-vehicle safe.

Once bound to a link (``bind_output``) a vehicle also exposes an outbound path.
Two primitives serve the protocols:
- ``request``: send + await a single reply (waiter registered before send, so a
  fast ACK is never missed).
- ``open_stream``: receive every message matching a predicate until closed —
  used for streamed responses such as a full parameter download.
"""

from __future__ import annotations

import asyncio

from missionctl.core.codec import MavlinkMessage
from missionctl.core.protocols import (
    CommandProtocol,
    MakeFn,
    MessageStream,
    ParamProtocol,
    Predicate,
    SendFn,
)
from missionctl.core.state import VehicleState, reduce
from missionctl.core.util.observable import Observable


class Vehicle:
    def __init__(self, sysid: int, compid: int) -> None:
        self.sysid = sysid
        self.compid = compid
        self._inbox: asyncio.Queue[MavlinkMessage] = asyncio.Queue()
        self._state: Observable[VehicleState] = Observable(VehicleState.initial(sysid, compid))
        self._task: asyncio.Task[None] | None = None
        self._waiters: list[tuple[Predicate, asyncio.Future[MavlinkMessage]]] = []
        self._streams: list[tuple[Predicate, asyncio.Queue[MavlinkMessage]]] = []
        self._send: SendFn | None = None
        self._commands: CommandProtocol | None = None
        self._params: ParamProtocol | None = None

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

    @property
    def params(self) -> ParamProtocol:
        if self._params is None:
            raise RuntimeError("vehicle has no outbound link bound (call bind_output)")
        return self._params

    def bind_output(self, *, send: SendFn, make: MakeFn) -> None:
        """Wire the outbound path (called by FleetManager with the link's writer)."""
        self._send = send
        self._commands = CommandProtocol(make=make, request=self.request, target=self.address)
        self._params = ParamProtocol(
            make=make,
            send=self._send_message,
            request=self.request,
            open_stream=self.open_stream,
            target=self.address,
        )

    def deliver(self, msg: MavlinkMessage) -> None:
        """Hand a message to this vehicle's inbox (called by the router)."""
        self._inbox.put_nowait(msg)

    async def _send_message(self, message: MavlinkMessage) -> None:
        if self._send is None:
            raise RuntimeError("vehicle has no outbound link bound")
        await self._send(message)

    async def request(
        self, message: MavlinkMessage, predicate: Predicate, timeout: float
    ) -> MavlinkMessage:
        """Register a reply waiter, send ``message``, and await the first incoming
        message matching ``predicate``. Raises ``TimeoutError`` on timeout."""
        loop = asyncio.get_running_loop()
        future: asyncio.Future[MavlinkMessage] = loop.create_future()
        entry = (predicate, future)
        self._waiters.append(entry)
        try:
            await self._send_message(message)
            async with asyncio.timeout(timeout):
                return await future
        finally:
            if entry in self._waiters:
                self._waiters.remove(entry)

    def open_stream(self, predicate: Predicate) -> MessageStream:
        """Open a live feed of incoming messages matching ``predicate``."""
        queue: asyncio.Queue[MavlinkMessage] = asyncio.Queue()
        entry = (predicate, queue)
        self._streams.append(entry)

        def close() -> None:
            if entry in self._streams:
                self._streams.remove(entry)

        return MessageStream(queue, close)

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
                self._fan_out_to_streams(msg)
            finally:
                self._inbox.task_done()

    def _resolve_waiters(self, msg: MavlinkMessage) -> None:
        for entry in list(self._waiters):
            predicate, future = entry
            if not future.done() and predicate(msg):
                future.set_result(msg)
                self._waiters.remove(entry)

    def _fan_out_to_streams(self, msg: MavlinkMessage) -> None:
        for predicate, queue in self._streams:
            if predicate(msg):
                queue.put_nowait(msg)
