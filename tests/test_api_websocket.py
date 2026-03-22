"""Tests WebSocket : message initial."""

from __future__ import annotations

H_A = {"X-Client-Id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"}


def test_websocket_init_payload(client) -> None:
    with client.websocket_connect("/ws") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "init"
        assert "tiles" in msg
        assert "times" in msg
        assert isinstance(msg["tiles"], list)
        assert isinstance(msg["times"], list)
        assert len(msg["times"]) == len(msg["tiles"])
        assert "meteo" in msg
        assert msg["meteo"]["v"] == 1
        assert "activeRoute" in msg
        assert msg["activeRoute"] in ("/", "/meteo")
        assert "control" in msg
        assert "controllerClientId" in msg["control"]


def test_websocket_nav_updated_on_put_nav(client) -> None:
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        r = client.put("/api/nav", json={"activeRoute": "/meteo"}, headers=H_A)
        assert r.status_code == 200
        msg = ws.receive_json()
        assert msg["type"] == "nav_updated"
        assert msg["activeRoute"] == "/meteo"


def test_websocket_meteo_updated_on_put_meteo_ui(client) -> None:
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        r = client.put(
            "/api/meteo/ui",
            json={
                "dateStart": "2025-02-01",
                "dateEnd": "2025-02-02",
                "resolution": "day",
                "geoQuery": "",
                "place": None,
            },
            headers=H_A,
        )
        assert r.status_code == 200
        msg = ws.receive_json()
        assert msg["type"] == "meteo_updated"
        assert msg["meteo"]["dateStart"] == "2025-02-01"
