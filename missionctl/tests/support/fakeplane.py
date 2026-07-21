"""A minimal ArduPlane simulator over real UDP, for end-to-end tests.

It is deliberately tiny — just enough to exercise the actual transport +
codec + command paths without external SITL:

- emits HEARTBEAT (MAV_TYPE_FIXED_WING) at a fixed rate to the GCS,
- ACKs any COMMAND_LONG with MAV_RESULT_ACCEPTED, and reflects arm
  (MAV_CMD_COMPONENT_ARM_DISARM) and mode (MAV_CMD_DO_SET_MODE) into the
  heartbeat it sends next.

It dogfoods our own ``UdpLink`` (connected mode) as its transport. This is NOT a
substitute for the real SITL smoke test — it validates our side of the wire, not
ArduPlane's actual behaviour.
"""

from __future__ import annotations

import asyncio
import contextlib

from missionctl.core.codec import MavlinkCodec, MavlinkMessage
from missionctl.core.link.udp import UdpLink

_MAV_TYPE_FIXED_WING = 1
_MAV_AUTOPILOT_ARDUPILOTMEGA = 3
_ARMED_FLAG = 0b1000_0000
_CMD_ARM_DISARM = 400
_CMD_DO_SET_MODE = 176


class FakePlane:
    def __init__(
        self, gcs_addr: tuple[str, int], *, sysid: int = 1, compid: int = 1, hz: float = 20.0
    ) -> None:
        self._link = UdpLink(remote_addr=gcs_addr)
        self._tx = MavlinkCodec(system_id=sysid, component_id=compid)
        self._rx = MavlinkCodec()
        self._hz = hz
        self._armed = False
        self._custom_mode = 0
        self._tasks: list[asyncio.Task[None]] = []

    async def start(self) -> None:
        await self._link.open()
        self._tasks = [
            asyncio.create_task(self._beat_loop(), name="fakeplane-beat"),
            asyncio.create_task(self._rx_loop(), name="fakeplane-rx"),
        ]

    async def stop(self) -> None:
        for task in self._tasks:
            task.cancel()
        for task in self._tasks:
            with contextlib.suppress(asyncio.CancelledError):
                await task
        await self._link.close()

    def _heartbeat(self) -> MavlinkMessage:
        return self._tx.make(
            "heartbeat",
            type=_MAV_TYPE_FIXED_WING,
            autopilot=_MAV_AUTOPILOT_ARDUPILOTMEGA,
            base_mode=_ARMED_FLAG if self._armed else 0,
            custom_mode=self._custom_mode,
            system_status=4,
            mavlink_version=3,
        )

    async def _beat_loop(self) -> None:
        while True:
            await self._link.write(self._tx.encode(self._heartbeat()))
            await asyncio.sleep(1.0 / self._hz)

    async def _rx_loop(self) -> None:
        while True:
            data = await self._link.read()
            for msg in self._rx.decode(data):
                await self._handle(msg)

    async def _handle(self, msg: MavlinkMessage) -> None:
        if msg.get_type() != "COMMAND_LONG":
            return
        d = msg.to_dict()
        command = int(d["command"])
        if command == _CMD_ARM_DISARM:
            self._armed = int(d["param1"]) == 1
        elif command == _CMD_DO_SET_MODE:
            self._custom_mode = int(d["param2"])
        ack = self._tx.make(
            "command_ack",
            command=command,
            result=0,  # MAV_RESULT_ACCEPTED
            progress=0,
            result_param2=0,
            target_system=255,
            target_component=0,
        )
        await self._link.write(self._tx.encode(ack))
