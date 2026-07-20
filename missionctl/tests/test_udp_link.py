import asyncio

import pytest

from missionctl.core.link.udp import UdpLink


async def test_one_way_datagram_roundtrip() -> None:
    listener = UdpLink(local_addr=("127.0.0.1", 0))
    await listener.open()
    sender = UdpLink(remote_addr=("127.0.0.1", listener.local_port))
    await sender.open()
    try:
        await sender.write(b"ping")
        data = await asyncio.wait_for(listener.read(), 1.0)
        assert data == b"ping"
    finally:
        await sender.close()
        await listener.close()


async def test_listener_learns_peer_and_can_reply() -> None:
    listener = UdpLink(local_addr=("127.0.0.1", 0))
    await listener.open()
    sender = UdpLink(local_addr=("127.0.0.1", 0), remote_addr=("127.0.0.1", listener.local_port))
    await sender.open()
    try:
        await sender.write(b"hello")
        assert await asyncio.wait_for(listener.read(), 1.0) == b"hello"
        # listener now knows the peer and can reply
        await listener.write(b"world")
        assert await asyncio.wait_for(sender.read(), 1.0) == b"world"
    finally:
        await sender.close()
        await listener.close()


def test_requires_an_address() -> None:
    with pytest.raises(ValueError):
        UdpLink()
