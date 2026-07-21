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
import logging
from dataclasses import replace

from missionctl.core.codec import MavlinkMessage
from missionctl.core.protocols import (
    CommandProtocol,
    MakeFn,
    MessageStream,
    MissionProtocol,
    ParamProtocol,
    Predicate,
    SendFn,
)
from missionctl.core.state import VehicleState, reduce
from missionctl.core.util.observable import Observable

log = logging.getLogger(__name__)

# MAV_DATA_STREAM_ALL — request every telemetry stream (see DISCOVERIES).
_DATA_STREAM_ALL = 0


class Vehicle:
    def __init__(
        self,
        sysid: int,
        compid: int,
        *,
        heartbeat_timeout: float = 3.0,
        monitor_interval: float = 1.0,
    ) -> None:
        self.sysid = sysid
        self.compid = compid
        self._inbox: asyncio.Queue[MavlinkMessage] = asyncio.Queue()
        self._state: Observable[VehicleState] = Observable(VehicleState.initial(sysid, compid))
        self._task: asyncio.Task[None] | None = None
        self._monitor_task: asyncio.Task[None] | None = None
        self._waiters: list[tuple[Predicate, asyncio.Future[MavlinkMessage]]] = []
        self._streams: list[tuple[Predicate, asyncio.Queue[MavlinkMessage]]] = []
        self._send: SendFn | None = None
        self._make: MakeFn | None = None
        self._commands: CommandProtocol | None = None
        self._params: ParamProtocol | None = None
        self._mission: MissionProtocol | None = None
        self._heartbeat_timeout = heartbeat_timeout
        self._monitor_interval = monitor_interval
        self._last_heartbeat: float | None = None

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

    @property
    def mission(self) -> MissionProtocol:
        if self._mission is None:
            raise RuntimeError("vehicle has no outbound link bound (call bind_output)")
        return self._mission

    def bind_output(self, *, send: SendFn, make: MakeFn) -> None:
        """Wire the outbound path (called by FleetManager with the link's writer)."""
        self._send = send
        self._make = make
        self._commands = CommandProtocol(
            make=make,
            request=self.request,
            open_stream=self.open_stream,
            target=self.address,
        )
        self._params = ParamProtocol(
            make=make,
            send=self._send_message,
            request=self.request,
            open_stream=self.open_stream,
            target=self.address,
        )
        self._mission = MissionProtocol(
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

    async def request_data_streams(self, rate_hz: int = 4) -> None:
        """Ask the vehicle to start sending telemetry. ArduPilot stays largely
        silent until a GCS requests streams (or sets message intervals), so this
        is sent once on connect. Fire-and-forget; failures are logged, not raised
        (e.g. a read-only replay link has nothing to send to)."""
        if self._make is None or self._send is None:
            return
        msg = self._make(
            "request_data_stream",
            target_system=self.sysid,
            target_component=self.compid,
            req_stream_id=_DATA_STREAM_ALL,
            req_message_rate=rate_hz,
            start_stop=1,
        )
        try:
            await self._send(msg)
        except Exception:
            log.debug("request_data_streams failed for %s", self.address, exc_info=True)

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
            self._monitor_task = asyncio.create_task(
                self._monitor(), name=f"vehicle-monitor-{self.sysid}-{self.compid}"
            )
        return self._task

    async def stop(self) -> None:
        tasks = [t for t in (self._task, self._monitor_task) if t is not None]
        for t in tasks:
            t.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._task = None
        self._monitor_task = None

    async def wait_idle(self) -> None:
        """Await until every delivered message has been processed (test helper)."""
        await self._inbox.join()

    async def _run(self) -> None:
        while True:
            msg = await self._inbox.get()
            try:
                self._process(msg)
            except Exception:
                # A single malformed message must never kill the actor — that
                # would silently freeze this vehicle's state. Log and carry on.
                log.exception("error processing message for %s", self.address)
            finally:
                self._inbox.task_done()

    def _process(self, msg: MavlinkMessage) -> None:
        new_state = reduce(self._state.value, msg)
        if msg.get_type() == "HEARTBEAT":
            self._last_heartbeat = asyncio.get_running_loop().time()
            if not new_state.link_alive:
                new_state = replace(new_state, link_alive=True)  # link came back
        self._state.set(new_state)
        self._resolve_waiters(msg)
        self._fan_out_to_streams(msg)

    async def _monitor(self) -> None:
        """Mark the link lost if no HEARTBEAT arrives within the timeout. Connection
        liveness is actor-managed metadata (the pure reducers never see time)."""
        loop = asyncio.get_running_loop()
        while True:
            await asyncio.sleep(self._monitor_interval)
            if self._last_heartbeat is None:
                continue
            alive = (loop.time() - self._last_heartbeat) <= self._heartbeat_timeout
            if alive != self._state.value.link_alive:
                self._state.set(replace(self._state.value, link_alive=alive))

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
