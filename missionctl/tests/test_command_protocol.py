import pytest

from missionctl.core.codec import MavlinkCodec, MavlinkMessage
from missionctl.core.vehicle import SendFn, Vehicle

CODEC = MavlinkCodec()


def _ack(command: int, result: int) -> MavlinkMessage:
    return CODEC.make(
        "command_ack",
        command=command,
        result=result,
        progress=0,
        result_param2=0,
        target_system=255,
        target_component=0,
    )


def _autoresponder(vehicle: Vehicle, result: int) -> SendFn:
    """A send sink that immediately ACKs whatever command it's given."""

    async def send(msg: MavlinkMessage) -> None:
        command = int(msg.to_dict()["command"])
        vehicle.deliver(_ack(command, result))

    return send


async def test_arm_accepted() -> None:
    v = Vehicle(1, 1)
    v.bind_output(send=_autoresponder(v, result=0), make=CODEC.make)
    v.start()
    res = await v.commands.arm(timeout=1.0)
    assert res.ok
    assert res.value == 0
    await v.stop()


async def test_command_rejected_returns_failure() -> None:
    v = Vehicle(1, 1)
    v.bind_output(send=_autoresponder(v, result=4), make=CODEC.make)  # MAV_RESULT_FAILED
    v.start()
    res = await v.commands.disarm(timeout=1.0)
    assert not res.ok
    assert res.error is not None and "MAV_RESULT=4" in res.error
    await v.stop()


async def test_timeout_after_retries() -> None:
    v = Vehicle(1, 1)
    sent: list[MavlinkMessage] = []

    async def silent(msg: MavlinkMessage) -> None:
        sent.append(msg)  # never ACKs

    v.bind_output(send=silent, make=CODEC.make)
    v.start()
    res = await v.commands.arm(timeout=0.05, retries=3)
    assert not res.ok
    assert res.error is not None and "timeout" in res.error
    assert len(sent) == 3  # one send per retry
    await v.stop()


async def test_set_mode_builds_correct_command() -> None:
    v = Vehicle(2, 1)
    sent: list[MavlinkMessage] = []

    async def capture_then_ack(msg: MavlinkMessage) -> None:
        sent.append(msg)
        v.deliver(_ack(int(msg.to_dict()["command"]), result=0))

    v.bind_output(send=capture_then_ack, make=CODEC.make)
    v.start()
    res = await v.commands.set_mode("GUIDED", timeout=1.0)
    assert res.ok

    d = sent[0].to_dict()
    assert int(d["command"]) == 176  # MAV_CMD_DO_SET_MODE
    assert int(d["param1"]) == 1  # MAV_MODE_FLAG_CUSTOM_MODE_ENABLED
    assert int(d["param2"]) == 15  # GUIDED
    assert d["target_system"] == 2
    assert d["target_component"] == 1
    await v.stop()


async def test_set_mode_unknown_name_does_not_send() -> None:
    v = Vehicle(1, 1)
    sent: list[MavlinkMessage] = []

    async def send(msg: MavlinkMessage) -> None:
        sent.append(msg)

    v.bind_output(send=send, make=CODEC.make)
    v.start()
    res = await v.commands.set_mode("NOTAMODE")
    assert not res.ok
    assert res.error is not None and "unknown" in res.error.lower()
    assert sent == []
    await v.stop()


def test_commands_unavailable_without_binding() -> None:
    v = Vehicle(1, 1)
    with pytest.raises(RuntimeError):
        _ = v.commands
