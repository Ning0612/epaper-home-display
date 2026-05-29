from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

import yaml
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from app.services.weather import WeatherService
from app.state import state

if TYPE_CHECKING:
    from app.config import Settings

logger = logging.getLogger(__name__)

_SETTINGS_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>ePaper — Location</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <style>
    *{box-sizing:border-box;margin:0;padding:0}
    body{font-family:system-ui,sans-serif;background:#f3f4f6;padding:1rem;max-width:720px}
    h1{font-size:1.1rem;font-weight:600;margin-bottom:.75rem;color:#111}
    #map{height:400px;border-radius:8px;box-shadow:0 1px 4px rgba(0,0,0,.15)}
    .bar{display:flex;align-items:center;gap:.75rem;margin-top:.6rem;flex-wrap:wrap}
    .co{font-size:.85rem;color:#374151}.co b{color:#111}
    .hint{flex:1;font-size:.75rem;color:#6b7280}
    button{padding:.4rem 1.1rem;background:#2563eb;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:.85rem}
    button:hover{background:#1d4ed8}
    #msg{font-size:.8rem;margin-top:.4rem;min-height:1.1rem}
    .ok{color:#16a34a}.err{color:#dc2626}
  </style>
</head>
<body>
  <h1>Weather Location</h1>
  <div id="map"></div>
  <div class="bar">
    <span class="co">Lat <b id="vla">__LAT__</b></span>
    <span class="co">Lon <b id="vlo">__LON__</b></span>
    <span class="hint">Click map or drag marker to change</span>
    <button onclick="save()">Save</button>
  </div>
  <div id="msg"></div>
  <script>
    var la=__LAT__,lo=__LON__;
    var map=L.map('map').setView([la,lo],10);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'© OpenStreetMap'}).addTo(map);
    var mk=L.marker([la,lo],{draggable:true}).addTo(map);
    function upd(p){la=+p.lat.toFixed(5);lo=+p.lng.toFixed(5);document.getElementById('vla').textContent=la;document.getElementById('vlo').textContent=lo;}
    mk.on('dragend',function(e){upd(e.target.getLatLng());});
    map.on('click',function(e){mk.setLatLng(e.latlng);upd(e.latlng);});
    async function save(){
      var el=document.getElementById('msg');
      try{
        var r=await fetch('/settings/location',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({lat:la,lon:lo})});
        el.textContent=r.ok?'✓ Saved':'Error '+r.status;
        el.className=r.ok?'ok':'err';
      }catch(e){el.textContent='Error: '+e.message;el.className='err';}
    }
  </script>
</body>
</html>"""


class _LocationBody(BaseModel):
    lat: float
    lon: float


class _AIUsageBody(BaseModel):
    codex_5h_pct: float | None = None
    codex_5h_reset: str | None = None
    codex_weekly_pct: float | None = None
    codex_weekly_reset: str | None = None
    claude_5h_pct: float | None = None
    claude_5h_reset: str | None = None


def create_app(settings: "Settings", weather_service: WeatherService) -> FastAPI:
    app = FastAPI(title="ePaper Home Display", version="0.1.0")

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/state")
    async def get_state():
        return JSONResponse({
            "temperature": state.temperature,
            "humidity": state.humidity,
            "light_raw": state.light_raw,
            "light_is_bright": state.light_is_bright,
            "presence": state.presence,
            "presence_score": state.presence_score,
            "weather_current": state.weather_current,
            "weather_forecast": state.weather_forecast,
            "weather_fetched_at": state.weather_fetched_at.isoformat() if state.weather_fetched_at else None,
            "last_door_event": state.last_door_event,
            "last_face_event": state.last_face_event,
            "last_alert": state.last_alert,
            "security_status": state.security_status,
            "active_reminder": state.active_reminder,
            "display_busy": state.display_busy,
            "started_at": state.started_at.isoformat(),
            "codex_usage_5h": state.codex_usage_5h,
            "codex_usage_week": state.codex_usage_week,
            "codex_5h_reset": state.codex_5h_reset,
            "codex_weekly_reset": state.codex_weekly_reset,
            "claude_usage_5h": state.claude_usage_5h,
            "claude_usage_week": state.claude_usage_week,
            "claude_5h_reset": state.claude_5h_reset,
        })

    @app.get("/logs/env")
    async def get_env_logs(limit: int = 50):
        from app.storage.logs import get_env_logs
        return {"logs": await get_env_logs(limit)}

    @app.get("/logs/presence")
    async def get_presence_logs(limit: int = 50):
        from app.storage.logs import get_presence_logs
        return {"logs": await get_presence_logs(limit)}

    @app.get("/logs/events")
    async def get_events(limit: int = 50):
        from app.storage.logs import get_system_events
        return {"events": await get_system_events(limit)}

    @app.get("/settings", response_class=HTMLResponse)
    async def settings_page():
        lat = round(settings.weather.lat, 5)
        lon = round(settings.weather.lon, 5)
        html = (
            _SETTINGS_HTML
            .replace("__LAT__", str(lat))
            .replace("__LON__", str(lon))
        )
        return HTMLResponse(html)

    @app.post("/ai_usage")
    async def post_ai_usage(body: _AIUsageBody):
        from app.storage.logs import log_ai_usage
        from datetime import datetime as _dt
        if body.codex_5h_pct is not None:
            state.codex_usage_5h = max(0.0, min(1.0, body.codex_5h_pct / 100.0))
        if body.codex_5h_reset is not None:
            state.codex_5h_reset = body.codex_5h_reset
        if body.codex_weekly_pct is not None:
            state.codex_usage_week = max(0.0, min(1.0, body.codex_weekly_pct / 100.0))
        if body.codex_weekly_reset is not None:
            state.codex_weekly_reset = body.codex_weekly_reset
        if body.claude_5h_pct is not None:
            state.claude_usage_5h = max(0.0, min(1.0, body.claude_5h_pct / 100.0))
        if body.claude_5h_reset is not None:
            state.claude_5h_reset = body.claude_5h_reset
        await log_ai_usage(body.model_dump())
        return {"ok": True, "updated_at": _dt.now().isoformat()}

    @app.put("/settings/location")
    async def set_location(body: _LocationBody):
        if not (-90 <= body.lat <= 90):
            raise HTTPException(400, detail="lat must be -90..90")
        if not (-180 <= body.lon <= 180):
            raise HTTPException(400, detail="lon must be -180..180")

        weather_service.set_location(body.lat, body.lon)
        settings.weather.lat = round(body.lat, 5)
        settings.weather.lon = round(body.lon, 5)

        local_path = "config.local.yaml"
        try:
            local_raw: dict = {}
            if os.path.exists(local_path):
                with open(local_path, "r", encoding="utf-8") as f:
                    local_raw = yaml.safe_load(f) or {}
            weather_section = local_raw.setdefault("weather", {})
            weather_section["lat"] = round(body.lat, 5)
            weather_section["lon"] = round(body.lon, 5)
            with open(local_path, "w", encoding="utf-8") as f:
                yaml.dump(local_raw, f, default_flow_style=False)
        except Exception as exc:
            logger.error("Failed to write config.local.yaml: %s", exc)
            raise HTTPException(500, detail="Location updated in memory but failed to persist")

        return {"ok": True, "lat": round(body.lat, 5), "lon": round(body.lon, 5)}

    return app
