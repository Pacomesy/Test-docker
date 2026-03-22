import asyncio
import json
import os
import sys
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo, available_timezones

import fastapi as fastapi_mod
import uvicorn as uvicorn_mod
from fastapi import FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.i18n_api import UnknownTimezoneError, api_msg
from app.version import __version__ as _package_version

DATA_DIR = Path(os.environ.get("DATA_DIR", "/data"))
TILES_FILE = DATA_DIR / "tiles.json"
METEO_UI_FILE = DATA_DIR / "meteo_ui.json"
NAV_FILE = DATA_DIR / "app_nav.json"
STATIC_DIR = Path(__file__).resolve().parent / "static"

APP_VERSION = os.environ.get("APP_VERSION", _package_version)


def about_payload() -> dict:
    return {
        "app": APP_VERSION,
        "frontend": APP_VERSION,
        "backend": {
            "python": sys.version.split()[0],
            "fastapi": fastapi_mod.__version__,
            "uvicorn": uvicorn_mod.__version__,
        },
        "docker": os.environ.get("DOCKER_IMAGE_VERSION"),
        "components": {
            "plotly": "2.35.2 (CDN plot.ly)",
            "open_meteo": "Géocodage + archive — open-meteo.com",
            "fonts": "Google Fonts — Outfit, JetBrains Mono",
        },
    }

DEFAULT_TILES = [
    {"id": str(uuid.uuid4()), "timezone": "Europe/Paris"},
    {"id": str(uuid.uuid4()), "timezone": "UTC"},
    {"id": str(uuid.uuid4()), "timezone": "America/New_York"},
]


def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_tiles() -> list[dict]:
    _ensure_data_dir()
    if not TILES_FILE.is_file():
        save_tiles(list(DEFAULT_TILES))
        return list(DEFAULT_TILES)
    try:
        raw = json.loads(TILES_FILE.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            return list(DEFAULT_TILES)
        out = []
        for item in raw:
            if isinstance(item, dict) and "timezone" in item:
                tid = item.get("id") or str(uuid.uuid4())
                out.append({"id": str(tid), "timezone": str(item["timezone"])})
        return out if out else list(DEFAULT_TILES)
    except (json.JSONDecodeError, OSError):
        return list(DEFAULT_TILES)


def save_tiles(tiles: list[dict]) -> None:
    _ensure_data_dir()
    TILES_FILE.write_text(
        json.dumps(tiles, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


DEFAULT_METEO_UI: dict = {
    "v": 1,
    "dateStart": "",
    "dateEnd": "",
    "resolution": "day",
    "geoQuery": "",
    "place": None,
}


def load_meteo_ui() -> dict:
    _ensure_data_dir()
    if not METEO_UI_FILE.is_file():
        return dict(DEFAULT_METEO_UI)
    try:
        raw = json.loads(METEO_UI_FILE.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return dict(DEFAULT_METEO_UI)
        out = dict(DEFAULT_METEO_UI)
        out.update(raw)
        if out.get("resolution") not in ("hour", "day"):
            out["resolution"] = "day"
        if out.get("v") != 1:
            out["v"] = 1
        return out
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULT_METEO_UI)


def save_meteo_ui(state: dict) -> None:
    _ensure_data_dir()
    METEO_UI_FILE.write_text(
        json.dumps(state, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


DEFAULT_NAV: dict = {"activeRoute": "/"}


def load_nav() -> dict:
    _ensure_data_dir()
    if not NAV_FILE.is_file():
        return dict(DEFAULT_NAV)
    try:
        raw = json.loads(NAV_FILE.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return dict(DEFAULT_NAV)
        r = raw.get("activeRoute")
        if r not in ("/", "/meteo"):
            return dict(DEFAULT_NAV)
        return {"activeRoute": r}
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULT_NAV)


def save_nav(state: dict) -> None:
    _ensure_data_dir()
    NAV_FILE.write_text(
        json.dumps(state, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def validate_tz(name: str) -> str:
    if name not in available_timezones():
        raise UnknownTimezoneError(name)
    return name


def format_time_for_zone(tz_name: str) -> dict:
    z = ZoneInfo(tz_name)
    now = datetime.now(z)
    return {
        "timezone": tz_name,
        "iso": now.isoformat(),
        "time": now.strftime("%H:%M:%S"),
        "date": now.strftime("%Y-%m-%d"),
        "offset": now.strftime("%z"),
    }


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._connections.add(ws)

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(ws)

    async def broadcast_json(self, payload: dict) -> None:
        async with self._lock:
            dead: list[WebSocket] = []
            text = json.dumps(payload, ensure_ascii=False)
            for ws in self._connections:
                try:
                    await ws.send_text(text)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self._connections.discard(ws)


class TileIn(BaseModel):
    timezone: str = Field(..., min_length=1, description="Identifiant IANA, ex. Europe/Paris")


class TileOrderIn(BaseModel):
    order: list[str] = Field(..., min_length=1, description="IDs des tuiles dans le nouvel ordre")


class MeteoPlaceIn(BaseModel):
    lat: float
    lon: float
    label: str = Field(..., min_length=1)


class MeteoUiIn(BaseModel):
    dateStart: str
    dateEnd: str
    resolution: Literal["hour", "day"]
    geoQuery: str = ""
    place: MeteoPlaceIn | None = None


class NavIn(BaseModel):
    activeRoute: Literal["/", "/meteo"]


manager = ConnectionManager()
_tiles_state: list[dict] = []
_meteo_ui_state: dict = dict(DEFAULT_METEO_UI)
_nav_state: dict = dict(DEFAULT_NAV)
_tick_task: asyncio.Task | None = None


async def tick_loop() -> None:
    while True:
        tiles = list(_tiles_state)
        times = [format_time_for_zone(t["timezone"]) for t in tiles]
        await manager.broadcast_json({"type": "tick", "tiles": tiles, "times": times})
        await asyncio.sleep(1)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _tiles_state, _meteo_ui_state, _nav_state, _tick_task
    _tiles_state = load_tiles()
    _meteo_ui_state = load_meteo_ui()
    _nav_state = load_nav()
    _tick_task = asyncio.create_task(tick_loop())
    yield
    if _tick_task:
        _tick_task.cancel()
        try:
            await _tick_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="Horloge multi-fuseaux",
    version=APP_VERSION,
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if STATIC_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR), name="assets")


def _static_html_response(
    filename: str, x_app_locale: str | None
) -> FileResponse:
    path = STATIC_DIR / filename
    if not path.is_file():
        raise HTTPException(
            status_code=404,
            detail=api_msg(x_app_locale, "page_missing"),
        )
    return FileResponse(path)


@app.get("/")
async def clock_page(x_app_locale: str | None = Header(None, alias="X-App-Locale")):
    return _static_html_response("clock.html", x_app_locale)


@app.get("/meteo")
async def meteo_page(x_app_locale: str | None = Header(None, alias="X-App-Locale")):
    return _static_html_response("meteo.html", x_app_locale)


@app.get("/api/version")
async def get_version():
    return {"version": APP_VERSION}


@app.get("/api/about")
async def get_about():
    return about_payload()


@app.get("/api/tiles")
async def get_tiles():
    return {"tiles": list(_tiles_state)}


@app.post("/api/tiles")
async def add_tile(
    body: TileIn,
    x_app_locale: str | None = Header(None, alias="X-App-Locale"),
):
    tz = body.timezone
    try:
        tz = validate_tz(tz.strip())
    except UnknownTimezoneError as e:
        raise HTTPException(
            status_code=400,
            detail=api_msg(x_app_locale, "unknown_tz", name=e.tz_name),
        ) from e
    if any(t["timezone"] == tz for t in _tiles_state):
        raise HTTPException(
            status_code=409,
            detail=api_msg(x_app_locale, "duplicate_tile"),
        )
    tile = {"id": str(uuid.uuid4()), "timezone": tz}
    _tiles_state.append(tile)
    save_tiles(_tiles_state)
    await manager.broadcast_json({"type": "tiles_updated", "tiles": list(_tiles_state)})
    return tile


@app.delete("/api/tiles/{tile_id}")
async def remove_tile(
    tile_id: str,
    x_app_locale: str | None = Header(None, alias="X-App-Locale"),
):
    global _tiles_state
    before = len(_tiles_state)
    _tiles_state = [t for t in _tiles_state if t["id"] != tile_id]
    if len(_tiles_state) == before:
        raise HTTPException(
            status_code=404,
            detail=api_msg(x_app_locale, "tile_not_found"),
        )
    save_tiles(_tiles_state)
    await manager.broadcast_json({"type": "tiles_updated", "tiles": list(_tiles_state)})
    return {"ok": True}


@app.put("/api/tiles/order")
async def reorder_tiles(
    body: TileOrderIn,
    x_app_locale: str | None = Header(None, alias="X-App-Locale"),
):
    global _tiles_state
    current_ids = [t["id"] for t in _tiles_state]
    if len(body.order) != len(current_ids) or set(body.order) != set(current_ids):
        raise HTTPException(
            status_code=400,
            detail=api_msg(x_app_locale, "order_invalid"),
        )
    by_id = {t["id"]: t for t in _tiles_state}
    _tiles_state = [by_id[i] for i in body.order]
    save_tiles(_tiles_state)
    await manager.broadcast_json({"type": "tiles_updated", "tiles": list(_tiles_state)})
    return {"tiles": list(_tiles_state)}


@app.get("/api/timezones")
async def list_timezones(q: str | None = None, limit: int = 200):
    zones = sorted(available_timezones())
    if q:
        q_lower = q.lower()
        zones = [z for z in zones if q_lower in z.lower()]
    return {"timezones": zones[: max(1, min(limit, 500))]}


@app.get("/api/meteo/ui")
async def get_meteo_ui():
    return dict(_meteo_ui_state)


@app.put("/api/meteo/ui")
async def put_meteo_ui(body: MeteoUiIn):
    global _meteo_ui_state
    place_dict: dict | None = None
    if body.place is not None:
        place_dict = {
            "lat": body.place.lat,
            "lon": body.place.lon,
            "label": body.place.label,
        }
    _meteo_ui_state = {
        "v": 1,
        "dateStart": body.dateStart,
        "dateEnd": body.dateEnd,
        "resolution": body.resolution,
        "geoQuery": body.geoQuery,
        "place": place_dict,
    }
    save_meteo_ui(_meteo_ui_state)
    await manager.broadcast_json(
        {"type": "meteo_updated", "meteo": dict(_meteo_ui_state)}
    )
    return dict(_meteo_ui_state)


@app.get("/api/nav")
async def get_nav():
    return dict(_nav_state)


@app.put("/api/nav")
async def put_nav(body: NavIn):
    global _nav_state
    _nav_state = {"activeRoute": body.activeRoute}
    save_nav(_nav_state)
    await manager.broadcast_json(
        {"type": "nav_updated", "activeRoute": body.activeRoute}
    )
    return dict(_nav_state)


@app.websocket("/ws")
async def websocket_clock(ws: WebSocket):
    await manager.connect(ws)
    try:
        times = [format_time_for_zone(t["timezone"]) for t in _tiles_state]
        await ws.send_json(
            {
                "type": "init",
                "tiles": list(_tiles_state),
                "times": times,
                "meteo": dict(_meteo_ui_state),
                "activeRoute": _nav_state["activeRoute"],
            }
        )
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(ws)
