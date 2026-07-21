from missionctl.core.codec import MavlinkCodec, MavlinkMessage
from missionctl.core.state import VehicleState, reduce

C = MavlinkCodec(system_id=1, component_id=1)


def _statustext(
    text: str, *, severity: int = 4, msg_id: int = 0, chunk_seq: int = 0
) -> MavlinkMessage:
    return C.raw.MAVLink_statustext_message(
        severity=severity, text=text.encode(), id=msg_id, chunk_seq=chunk_seq
    )


def test_single_prearm_message_captured() -> None:
    s = reduce(VehicleState.initial(1, 1), _statustext("PreArm: Compass not healthy", severity=4))
    assert len(s.messages) == 1
    assert s.messages[0].severity == 4
    assert s.messages[0].text == "PreArm: Compass not healthy"
    assert s.last_message is not None and s.last_message.text.startswith("PreArm:")


def test_messages_accumulate_in_order() -> None:
    s = VehicleState.initial()
    s = reduce(s, _statustext("Arm: Throttle too high", severity=3))
    s = reduce(s, _statustext("EKF3 IMU0 is using GPS", severity=6))
    assert [m.text for m in s.messages] == ["Arm: Throttle too high", "EKF3 IMU0 is using GPS"]
    assert s.last_message is not None and s.last_message.text == "EKF3 IMU0 is using GPS"


def test_backlog_is_bounded() -> None:
    s = VehicleState.initial()
    for i in range(30):
        s = reduce(s, _statustext(f"msg {i}", severity=6))
    assert len(s.messages) == 20  # _MAX_MESSAGES
    assert s.messages[-1].text == "msg 29"
    assert s.messages[0].text == "msg 10"  # oldest dropped


def test_chunked_message_is_reassembled() -> None:
    # A >50-char message split across two chunks with the same non-zero id.
    first = "PreArm: ".ljust(50, ".")  # exactly 50 chars → not the final chunk
    assert len(first) == 50
    second = "tail of the message"
    s = VehicleState.initial()
    s = reduce(s, _statustext(first, severity=4, msg_id=42, chunk_seq=0))
    assert s.messages == ()  # not finalised until the short chunk arrives
    s = reduce(s, _statustext(second, severity=4, msg_id=42, chunk_seq=1))
    assert len(s.messages) == 1
    assert s.messages[0].text == first + second
    assert s.statustext_reassembly == (0, "")  # buffer cleared
