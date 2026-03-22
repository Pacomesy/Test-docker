"""Tests HTTP : routes REST."""

from __future__ import annotations

import pytest


def test_get_version(client) -> None:
    r = client.get("/api/version")
    assert r.status_code == 200
    data = r.json()
    assert "version" in data
    assert data["version"]


def test_get_about(client) -> None:
    r = client.get("/api/about")
    assert r.status_code == 200
    body = r.json()
    assert "backend" in body
    assert "components" in body


def test_get_tiles_after_startup(client) -> None:
    r = client.get("/api/tiles")
    assert r.status_code == 200
    tiles = r.json()["tiles"]
    assert isinstance(tiles, list)
    assert len(tiles) >= 1


def test_post_tile_valid(client) -> None:
    r0 = client.get("/api/tiles")
    existing = {t["timezone"] for t in r0.json()["tiles"]}
    candidate = "Europe/Berlin"
    if candidate in existing:
        pytest.skip("Europe/Berlin déjà présent dans les tuiles par défaut")

    r = client.post("/api/tiles", json={"timezone": candidate})
    assert r.status_code == 200
    assert r.json()["timezone"] == candidate
    assert "id" in r.json()


def test_post_tile_unknown_timezone(client) -> None:
    r = client.post("/api/tiles", json={"timezone": "Nowhere/Land"})
    assert r.status_code == 400
    assert "detail" in r.json()


def test_post_tile_unknown_timezone_localized_header(client) -> None:
    r = client.post(
        "/api/tiles",
        json={"timezone": "Bad/Zone"},
        headers={"X-App-Locale": "en"},
    )
    assert r.status_code == 400
    assert "Unknown" in r.json()["detail"]


def test_post_tile_duplicate(client) -> None:
    r0 = client.get("/api/tiles")
    tz = r0.json()["tiles"][0]["timezone"]
    r = client.post("/api/tiles", json={"timezone": tz})
    assert r.status_code == 409


def test_delete_tile_not_found(client) -> None:
    r = client.delete("/api/tiles/nonexistent-id-000")
    assert r.status_code == 404


def test_delete_tile_ok(client) -> None:
    r0 = client.get("/api/tiles")
    tiles = r0.json()["tiles"]
    if len(tiles) < 2:
        pytest.skip("besoin d’au moins 2 tuiles")
    tid = tiles[-1]["id"]
    r = client.delete(f"/api/tiles/{tid}")
    assert r.status_code == 200
    assert r.json() == {"ok": True}
    ids = {t["id"] for t in client.get("/api/tiles").json()["tiles"]}
    assert tid not in ids


def test_put_order_invalid(client) -> None:
    r = client.put("/api/tiles/order", json={"order": ["only-one"]})
    assert r.status_code == 400


def test_put_order_ok(client) -> None:
    r0 = client.get("/api/tiles")
    tiles = r0.json()["tiles"]
    if len(tiles) < 2:
        pytest.skip("besoin d’au moins 2 tuiles pour réordonner")
    ids = [t["id"] for t in tiles]
    rev = list(reversed(ids))
    r = client.put("/api/tiles/order", json={"order": rev})
    assert r.status_code == 200
    assert [t["id"] for t in r.json()["tiles"]] == rev


def test_list_timezones_default_limit(client) -> None:
    r = client.get("/api/timezones")
    assert r.status_code == 200
    zones = r.json()["timezones"]
    assert len(zones) >= 10
    assert len(zones) <= 200


def test_list_timezones_query_and_limit(client) -> None:
    r = client.get("/api/timezones", params={"q": "paris", "limit": 5})
    assert r.status_code == 200
    zones = r.json()["timezones"]
    assert len(zones) <= 5
    assert all("paris" in z.lower() for z in zones)


def test_list_timezones_limit_capped(client) -> None:
    r = client.get("/api/timezones", params={"limit": 9999})
    assert r.status_code == 200
    assert len(r.json()["timezones"]) <= 500


def test_clock_page(client) -> None:
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")
    assert b"clock-page.js" in r.content


def test_meteo_page(client) -> None:
    r = client.get("/meteo")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")
    assert b"meteo-page.js" in r.content


def test_get_nav_default(client) -> None:
    r = client.get("/api/nav")
    assert r.status_code == 200
    assert r.json()["activeRoute"] == "/"


def test_put_nav_roundtrip(client) -> None:
    r = client.put("/api/nav", json={"activeRoute": "/meteo"})
    assert r.status_code == 200
    assert r.json()["activeRoute"] == "/meteo"
    assert client.get("/api/nav").json()["activeRoute"] == "/meteo"


def test_put_nav_invalid_route(client) -> None:
    r = client.put("/api/nav", json={"activeRoute": "/nowhere"})
    assert r.status_code == 422


def test_get_meteo_ui_default(client) -> None:
    r = client.get("/api/meteo/ui")
    assert r.status_code == 200
    d = r.json()
    assert d["v"] == 1
    assert d["resolution"] in ("hour", "day")


def test_put_meteo_ui_roundtrip(client) -> None:
    body = {
        "dateStart": "2025-01-01",
        "dateEnd": "2025-01-15",
        "resolution": "hour",
        "geoQuery": "Paris",
        "place": {"lat": 48.85, "lon": 2.35, "label": "Paris, FR"},
    }
    r = client.put("/api/meteo/ui", json=body)
    assert r.status_code == 200
    assert r.json()["place"]["label"] == "Paris, FR"
    r2 = client.get("/api/meteo/ui")
    assert r2.json()["geoQuery"] == "Paris"
