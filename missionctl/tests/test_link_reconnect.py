import asyncio
import contextlib

import pytest

import missionctl.core.fleet as fleet_module
from missionctl.core.codec import MavlinkCodec
from missionctl.core.fleet import FleetManager
from missionctl.core.link.base import Link, LinkState
from missionctl.core.util.observable import Observable


class FlakyLink(Link):
    """Returns one chunk per open, then raises to force a reconnect."""

    def __init__(self, chunk: bytes) -> None:
        self._state: Observable[LinkState] = Observable(LinkState.DISCONNECTED)
        self._chunk = chunk
        self._reads_since_open = 0
        self.open_count = 0

    @property
    def state(self) -> Observable[LinkState]:
        return self._state

    async def open(self) -> None:
        self.open_count += 1
        self._reads_since_open = 0
        self._state.set(LinkState.CONNECTED)

    async def read(self) -> bytes:
        self._reads_since_open += 1
        if self._reads_since_open == 1:
            return self._chunk
        raise ConnectionResetError("simulated link drop")

    async def write(self, data: bytes) -> None:
        pass

    async def close(self) -> None:
        self._state.set(LinkState.DISCONNECTED)


async def test_run_link_reconnects_on_transport_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(fleet_module, "_RECONNECT_BACKOFF_START", 0.01)
    monkeypatch.setattr(fleet_module, "_RECONNECT_BACKOFF_MAX", 0.02)

    enc = MavlinkCodec(system_id=1, component_id=1)
    chunk = enc.encode(
        enc.make(
            "heartbeat",
            type=1,
            autopilot=3,
            base_mode=0,
            custom_mode=0,
            system_status=4,
            mavlink_version=3,
        )
    )
    link = FlakyLink(chunk)
    fleet = FleetManager()
    runner = asyncio.create_task(fleet.run_link(link, reconnect=True, request_streams=False))
    try:
        async with asyncio.timeout(3.0):
            while link.open_count < 2 or not fleet.vehicles:  # noqa: ASYNC110
                await asyncio.sleep(0.01)
        assert link.open_count >= 2  # a reconnect happened
        assert fleet.get(1, 1) is not None
    finally:
        runner.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await runner
        await fleet.stop()
