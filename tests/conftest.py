"""Fixtures communes : données isolées + pas de tick WebSocket bruyant."""

from __future__ import annotations

import asyncio

import pytest


@pytest.fixture
def client(monkeypatch, tmp_path):
    import app.main as main

    monkeypatch.setattr(main, "DATA_DIR", tmp_path)
    monkeypatch.setattr(main, "TILES_FILE", tmp_path / "tiles.json")
    monkeypatch.setattr(main, "METEO_UI_FILE", tmp_path / "meteo_ui.json")
    monkeypatch.setattr(main, "NAV_FILE", tmp_path / "app_nav.json")

    async def quiet_tick() -> None:
        await asyncio.Event().wait()

    monkeypatch.setattr(main, "tick_loop", quiet_tick)

    from fastapi.testclient import TestClient

    with TestClient(main.app) as c:
        yield c
