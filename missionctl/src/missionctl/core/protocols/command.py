"""Command protocol for ArduPlane (ADR-0005): arm/disarm, set_mode, safety switch.

Each operation builds a COMMAND_LONG, sends it, and awaits the matching
COMMAND_ACK, with an explicit timeout and bounded retries. Fully async and
cancellable; expected failures (timeout, rejection) come back as a ``Result``,
not an exception. No global port mutex, no blocking — the request primitive
registers the reply waiter *before* sending so an ACK can't be missed.

set_mode can additionally *confirm* the change by watching HEARTBEAT.custom_mode
(a COMMAND_ACK only means "accepted", not "applied").
"""

from __future__ import annotations

import asyncio

from missionctl.core.codec import MavlinkMessage
from missionctl.core.modes import PLANE_MODES
from missionctl.core.protocols.channel import MakeFn, OpenStreamFn, RequestFn
from missionctl.core.util.result import Result

# MAVLink standard constants (stable; kept here to avoid importing pymavlink
# outside the codec — see ADR-0004 and DISCOVERIES).
_CMD_COMPONENT_ARM_DISARM = 400
_CMD_DO_SET_MODE = 176
_CMD_DO_SET_SAFETY_SWITCH_STATE = 5300
_MODE_FLAG_CUSTOM_MODE_ENABLED = 1
_RESULT_ACCEPTED = 0
_ARM_FORCE_MAGIC = 21196.0  # param2 to bypass prearm checks (only when forced)
_SAFETY_SAFE = 0  # SAFETY_SWITCH_STATE_SAFE — motors inhibited
_SAFETY_DANGEROUS = 1  # SAFETY_SWITCH_STATE_DANGEROUS — safety off, armable


class CommandProtocol:
    def __init__(
        self,
        *,
        make: MakeFn,
        request: RequestFn,
        open_stream: OpenStreamFn,
        target: tuple[int, int],
    ) -> None:
        self._make = make
        self._request = request
        self._open_stream = open_stream
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

    async def set_safety(
        self, safe: bool, *, timeout: float = 3.0, retries: int = 3
    ) -> Result[int]:
        """Toggle the safety switch. ``safe=True`` engages safety (motors
        inhibited); ``safe=False`` disengages it (armable)."""
        state = _SAFETY_SAFE if safe else _SAFETY_DANGEROUS
        return await self._command_long(
            _CMD_DO_SET_SAFETY_SWITCH_STATE, (float(state),), timeout=timeout, retries=retries
        )

    async def set_mode(
        self,
        mode: int | str,
        *,
        timeout: float = 3.0,
        retries: int = 3,
        confirm: bool = True,
        confirm_timeout: float = 3.0,
    ) -> Result[int]:
        """Set the flight mode. With ``confirm=True`` (default), wait for a
        HEARTBEAT reporting the new custom_mode before returning success — an ACK
        alone only means the command was accepted, not that the mode changed."""
        if isinstance(mode, str):
            number = PLANE_MODES.get(mode.upper())
            if number is None:
                return Result(ok=False, error=f"unknown Plane mode: {mode!r}")
        else:
            number = mode

        set_mode_params = (float(_MODE_FLAG_CUSTOM_MODE_ENABLED), float(number))
        if not confirm:
            return await self._command_long(
                _CMD_DO_SET_MODE, set_mode_params, timeout=timeout, retries=retries
            )

        # Open the HEARTBEAT feed BEFORE sending, so the heartbeat that reports the
        # new mode (which can arrive right after the ACK) is never missed.
        stream = self._open_stream(lambda m: m.get_type() == "HEARTBEAT")
        try:
            acked = await self._command_long(
                _CMD_DO_SET_MODE, set_mode_params, timeout=timeout, retries=retries
            )
            if not acked.ok:
                return acked
            try:
                async with asyncio.timeout(confirm_timeout):
                    while True:
                        hb = await stream.next(confirm_timeout)
                        if int(hb.to_dict()["custom_mode"]) == number:
                            return Result(ok=True, value=number)
            except TimeoutError:
                return Result(
                    ok=False, error=f"mode {number} accepted but not observed in HEARTBEAT"
                )
        finally:
            stream.close()

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
