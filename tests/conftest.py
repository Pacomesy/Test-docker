"""Fixtures communes : données isolées + pas de tick WebSocket bruyant."""

from __future__ import annotations

import asyncio

import pytest

# Doit rester aligné avec X-Client-Id utilisé dans les tests qui mutent l’état.
CID_A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"


@pytest.fixture
def client(monkeypatch, tmp_path):
    import app.main as main

    monkeypatch.setattr(main, "DATA_DIR", tmp_path)
    monkeypatch.setattr(main, "TILES_FILE", tmp_path / "tiles.json")
    monkeypatch.setattr(main, "METEO_UI_FILE", tmp_path / "meteo_ui.json")
    monkeypatch.setattr(main, "NAV_FILE", tmp_path / "app_nav.json")
    monkeypatch.setattr(main, "CONTROL_FILE", tmp_path / "control.json")

    async def quiet_tick() -> None:
        await asyncio.Event().wait()

    monkeypatch.setattr(main, "tick_loop", quiet_tick)

    from fastapi.testclient import TestClient

    with TestClient(main.app) as c:
        ra = c.post("/api/control/request", headers={"X-Client-Id": CID_A})
        assert ra.status_code == 200
        yield c


@pytest.fixture
def client_fresh(monkeypatch, tmp_path):
    """Même isolation sans prise de contrôle automatique."""
    import app.main as main

    monkeypatch.setattr(main, "DATA_DIR", tmp_path)
    monkeypatch.setattr(main, "TILES_FILE", tmp_path / "tiles.json")
    monkeypatch.setattr(main, "METEO_UI_FILE", tmp_path / "meteo_ui.json")
    monkeypatch.setattr(main, "NAV_FILE", tmp_path / "app_nav.json")
    monkeypatch.setattr(main, "CONTROL_FILE", tmp_path / "control.json")

    async def quiet_tick() -> None:
        await asyncio.Event().wait()

    monkeypatch.setattr(main, "tick_loop", quiet_tick)

    from fastapi.testclient import TestClient

    with TestClient(main.app) as c:
        yield c
