from missionctl.core.codec import MavlinkCodec


def _heartbeat_bytes(codec: MavlinkCodec) -> bytes:
    hb = codec.raw.MAVLink_heartbeat_message(
        type=2, autopilot=3, base_mode=81, custom_mode=0, system_status=4, mavlink_version=3
    )
    return codec.encode(hb)


def test_encode_then_decode_roundtrip() -> None:
    enc = MavlinkCodec(system_id=1, component_id=1)
    dec = MavlinkCodec()
    msgs = dec.decode(_heartbeat_bytes(enc))
    assert len(msgs) == 1
    assert msgs[0].get_type() == "HEARTBEAT"
    assert msgs[0].get_srcSystem() == 1


def test_decode_reassembles_split_frames() -> None:
    # A frame split across two decode() calls must be reassembled by the stateful
    # parser — the exact case the legacy byte-by-byte loop handled with a goto.
    enc = MavlinkCodec(system_id=7)
    dec = MavlinkCodec()
    data = _heartbeat_bytes(enc)
    assert dec.decode(data[:3]) == []
    tail = dec.decode(data[3:])
    assert len(tail) == 1
    assert tail[0].get_srcSystem() == 7


def test_decode_handles_garbage_without_raising() -> None:
    dec = MavlinkCodec()
    assert dec.decode(b"\x00\x01\x02not a frame") == []
