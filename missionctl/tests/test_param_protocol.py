from missionctl.core.codec import MavlinkCodec, MavlinkMessage
from missionctl.core.vehicle import Vehicle

CODEC = MavlinkCodec()


def _param_value(name: str, value: float, index: int, count: int) -> MavlinkMessage:
    return CODEC.make(
        "param_value",
        param_id=name.encode(),
        param_value=value,
        param_type=9,
        param_count=count,
        param_index=index,
    )


async def test_get_returns_value() -> None:
    v = Vehicle(1, 1)

    async def responder(msg: MavlinkMessage) -> None:
        # reply to a PARAM_REQUEST_READ with the requested param's value
        if msg.get_type() == "PARAM_REQUEST_READ":
            v.deliver(_param_value("CRUISE_SPEED", 18.0, index=0, count=1))

    v.bind_output(send=responder, make=CODEC.make)
    v.start()
    res = await v.params.get("CRUISE_SPEED", timeout=1.0)
    assert res.ok
    assert res.value == 18.0
    await v.stop()


async def test_set_echoes_new_value() -> None:
    v = Vehicle(1, 1)
    sent: list[MavlinkMessage] = []

    async def responder(msg: MavlinkMessage) -> None:
        sent.append(msg)
        if msg.get_type() == "PARAM_SET":
            d = msg.to_dict()
            v.deliver(
                _param_value(
                    d["param_id"].decode() if isinstance(d["param_id"], bytes) else d["param_id"],
                    float(d["param_value"]),
                    index=0,
                    count=1,
                )
            )

    v.bind_output(send=responder, make=CODEC.make)
    v.start()
    res = await v.params.set("TRIM_ARSPD_CM", 2200.0, timeout=1.0)
    assert res.ok
    assert res.value == 2200.0
    assert sent[0].get_type() == "PARAM_SET"
    assert int(sent[0].to_dict()["param_type"]) == 9  # REAL32
    await v.stop()


async def test_get_timeout() -> None:
    v = Vehicle(1, 1)

    async def silent(msg: MavlinkMessage) -> None:
        pass

    v.bind_output(send=silent, make=CODEC.make)
    v.start()
    res = await v.params.get("NOPE", timeout=0.05, retries=2)
    assert not res.ok
    assert res.error is not None and "timeout" in res.error
    await v.stop()


async def test_download_all_collects_full_table_with_progress() -> None:
    v = Vehicle(1, 1)
    table = {"P1": 1.0, "P2": 2.0, "P3": 3.0}

    async def responder(msg: MavlinkMessage) -> None:
        if msg.get_type() == "PARAM_REQUEST_LIST":
            for i, (name, value) in enumerate(table.items()):
                v.deliver(_param_value(name, value, index=i, count=len(table)))

    v.bind_output(send=responder, make=CODEC.make)
    v.start()

    seen: list[float] = []
    res = await v.params.download_all(progress=seen.append, idle_timeout=1.0)
    assert res.ok
    assert res.value == table
    assert seen[-1] == 1.0  # progress reaches 100%
    await v.stop()


async def test_download_all_incomplete_reports_failure() -> None:
    v = Vehicle(1, 1)

    async def responder(msg: MavlinkMessage) -> None:
        if msg.get_type() == "PARAM_REQUEST_LIST":
            # advertise 3 but only send 1, then go silent
            v.deliver(_param_value("ONLY", 1.0, index=0, count=3))

    v.bind_output(send=responder, make=CODEC.make)
    v.start()
    res = await v.params.download_all(idle_timeout=0.1)
    assert not res.ok
    assert res.error is not None and "incomplete" in res.error
    await v.stop()
