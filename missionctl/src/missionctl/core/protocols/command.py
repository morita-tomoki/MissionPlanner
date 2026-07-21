"""Command protocol for ArduPlane (ADR-0005): arm/disarm and set_mode.

Each operation builds a COMMAND_LONG, sends it, and awaits the matching
COMMAND_ACK, with an explicit timeout and bounded retries. Fully async and
cancellable; expected failures (timeout, rejection) come back as a ``Result``,
not an exception. No global port mutex, no blocking — the request primitive
registers the reply waiter *before* sending so an ACK can't be missed.
"""

from __future__ import annotations

from missionctl.core.codec import MavlinkMessage
from missionctl.core.modes import PLANE_MODES
from missionctl.core.protocols.channel import MakeFn, RequestFn
from missionctl.core.util.result import Result

# MAVLink standard constants (stable; kept here to avoid importing pymavlink
# outside the codec — see ADR-0004 and DISCOVERIES).
_CMD_COMPONENT_ARM_DISARM = 400
_CMD_DO_SET_MODE = 176
_MODE_FLAG_CUSTOM_MODE_ENABLED = 1
_RESULT_ACCEPTED = 0
_ARM_FORCE_MAGIC = 21196.0  # param2 to bypass prearm checks (only when forced)


class CommandProtocol:
    def __init__(
        self,
        *,
        make: MakeFn,
        request: RequestFn,
        target: tuple[int, int],
    ) -> None:
        self._make = make
        self._request = request
        self._target = target

    async def arm(
        self, *, force: bool = False, timeout: float = 3.0, retries: int = 3
    ) -> Result[int]:
        return await self._command_long(
            _CMD_COMPONENT_ARM_DISARM,
            (1.0, _ARM_FORCE_MAGIC if force else 0.0),
            timeout=timeout,
            retries=retries,
        )

    async def disarm(
        self, *, force: bool = False, timeout: float = 3.0, retries: int = 3
    ) -> Result[int]:
        return await self._command_long(
            _CMD_COMPONENT_ARM_DISARM,
            (0.0, _ARM_FORCE_MAGIC if force else 0.0),
            timeout=timeout,
            retries=retries,
        )

    async def set_mode(
        self, mode: int | str, *, timeout: float = 3.0, retries: int = 3
    ) -> Result[int]:
        if isinstance(mode, str):
            number = PLANE_MODES.get(mode.upper())
            if number is None:
                return Result(ok=False, error=f"unknown Plane mode: {mode!r}")
        else:
            number = mode
        return await self._command_long(
            _CMD_DO_SET_MODE,
            (float(_MODE_FLAG_CUSTOM_MODE_ENABLED), float(number)),
            timeout=timeout,
            retries=retries,
        )

    async def _command_long(
        self, command: int, params: tuple[float, ...], *, timeout: float, retries: int
    ) -> Result[int]:
        p = list(params) + [0.0] * (7 - len(params))

        def is_ack(m: MavlinkMessage) -> bool:
            return m.get_type() == "COMMAND_ACK" and int(m.to_dict()["command"]) == command

        last_error = "no attempt made"
        for attempt in range(retries):
            msg = self._make(
                "command_long",
                target_system=self._target[0],
                target_component=self._target[1],
                command=command,
                confirmation=attempt,
                param1=p[0],
                param2=p[1],
                param3=p[2],
                param4=p[3],
                param5=p[4],
                param6=p[5],
                param7=p[6],
            )
            try:
                ack = await self._request(msg, is_ack, timeout)
            except TimeoutError:
                last_error = f"timeout awaiting COMMAND_ACK for command {command}"
                continue
            result = int(ack.to_dict()["result"])
            if result == _RESULT_ACCEPTED:
                return Result(ok=True, value=result)
            return Result(ok=False, error=f"command {command} rejected: MAV_RESULT={result}")
        return Result(ok=False, error=last_error)
