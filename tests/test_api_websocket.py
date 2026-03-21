"""Tests WebSocket : message initial."""

from __future__ import annotations


def test_websocket_init_payload(client) -> None:
    with client.websocket_connect("/ws") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "init"
        assert "tiles" in msg
        assert "times" in msg
        assert isinstance(msg["tiles"], list)
        assert isinstance(msg["times"], list)
        assert len(msg["times"]) == len(msg["tiles"])
