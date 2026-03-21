"""Tests unitaires : fonctions pures de app.main (sans lancer l’app HTTP)."""

from __future__ import annotations

import json
from datetime import datetime

import pytest

from app.i18n_api import UnknownTimezoneError


def test_validate_tz_accepts_utc() -> None:
    from app.main import validate_tz

    assert validate_tz("UTC") == "UTC"


def test_validate_tz_rejects_invalid() -> None:
    from app.main import validate_tz

    with pytest.raises(UnknownTimezoneError) as exc:
        validate_tz("Not/AValidZone")
    assert exc.value.tz_name == "Not/AValidZone"


def test_format_time_for_zone_structure() -> None:
    from app.main import format_time_for_zone

    d = format_time_for_zone("UTC")
    assert d["timezone"] == "UTC"
    assert "T" in d["iso"]
    assert len(d["time"].split(":")) == 3
    assert len(d["date"].split("-")) == 3
    datetime.fromisoformat(d["iso"])


def test_about_payload_keys() -> None:
    from app.main import about_payload

    p = about_payload()
    assert p["app"]
    assert p["frontend"] == p["app"]
    assert "python" in p["backend"]
    assert "fastapi" in p["backend"]
    assert "uvicorn" in p["backend"]
    assert "components" in p
    assert "plotly" in p["components"]


def test_load_tiles_creates_default_when_missing(monkeypatch, tmp_path) -> None:
    import app.main as main

    monkeypatch.setattr(main, "DATA_DIR", tmp_path)
    monkeypatch.setattr(main, "TILES_FILE", tmp_path / "tiles.json")

    tiles = main.load_tiles()
    assert len(tiles) >= 1
    assert all("id" in t and "timezone" in t for t in tiles)
    assert main.TILES_FILE.is_file()


def test_load_tiles_repairs_malformed_json(monkeypatch, tmp_path) -> None:
    import app.main as main

    monkeypatch.setattr(main, "DATA_DIR", tmp_path)
    monkeypatch.setattr(main, "TILES_FILE", tmp_path / "tiles.json")
    main.TILES_FILE.write_text("not json", encoding="utf-8")

    tiles = main.load_tiles()
    assert isinstance(tiles, list)
    assert len(tiles) >= 1


def test_load_tiles_list_of_objects(monkeypatch, tmp_path) -> None:
    import app.main as main

    monkeypatch.setattr(main, "DATA_DIR", tmp_path)
    monkeypatch.setattr(main, "TILES_FILE", tmp_path / "tiles.json")
    main.TILES_FILE.write_text(
        json.dumps([{"id": "a1", "timezone": "UTC"}], ensure_ascii=False),
        encoding="utf-8",
    )

    tiles = main.load_tiles()
    assert len(tiles) == 1
    assert tiles[0]["timezone"] == "UTC"
    assert tiles[0]["id"] == "a1"


def test_save_tiles_roundtrip(monkeypatch, tmp_path) -> None:
    import app.main as main

    monkeypatch.setattr(main, "DATA_DIR", tmp_path)
    monkeypatch.setattr(main, "TILES_FILE", tmp_path / "tiles.json")

    data = [{"id": "x", "timezone": "Europe/Zurich"}]
    main.save_tiles(data)
    loaded = json.loads(main.TILES_FILE.read_text(encoding="utf-8"))
    assert loaded == data
