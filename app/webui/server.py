from __future__ import annotations

import asyncio
import dataclasses
import logging
import os
import re
import subprocess
import threading
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

_LOCAL_CFG = "config.local.yaml"
_config_lock = threading.Lock()

# ── HTML ──────────────────────────────────────────────────────────────────────

_SETTINGS_HTML = r"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>ePaper 設定</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <style>
    *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
    :root{
      --bg:#f1f5f9;--surface:#fff;--border:#e2e8f0;
      --primary:#3b82f6;--primary-h:#2563eb;
      --text:#0f172a;--muted:#64748b;
      --r:8px;--sh:0 1px 3px rgba(0,0,0,.08),0 1px 2px rgba(0,0,0,.06)
    }
    body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:var(--bg);color:var(--text);display:flex;min-height:100vh}
    .sb{width:210px;background:var(--surface);border-right:1px solid var(--border);padding:1.25rem 0;position:sticky;top:0;height:100vh;overflow-y:auto;flex-shrink:0}
    .sb-title{font-size:.7rem;font-weight:700;text-transform:uppercase;letter-spacing:.1em;color:var(--muted);padding:0 1rem .6rem}
    .nav{display:flex;align-items:center;gap:.5rem;padding:.5rem 1rem;cursor:pointer;font-size:.85rem;color:var(--muted);border-left:3px solid transparent;transition:all .15s;user-select:none}
    .nav:hover{background:var(--bg);color:var(--text)}
    .nav.active{color:var(--primary);border-left-color:var(--primary);background:#eff6ff;font-weight:500}
    .ni{width:1.2rem;text-align:center;font-size:.95rem}
    .main{flex:1;padding:2rem;max-width:680px;overflow-y:auto}
    .sec{display:none}.sec.active{display:block}
    .sec-head{margin-bottom:1.4rem}
    .sec-title{font-size:1.2rem;font-weight:600;display:flex;align-items:center;gap:.4rem}
    .sec-desc{font-size:.78rem;color:var(--muted);margin-top:.2rem}
    .card{background:var(--surface);border:1px solid var(--border);border-radius:var(--r);padding:1.4rem;box-shadow:var(--sh);margin-bottom:1.1rem}
    .c-sub{font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);margin-bottom:.9rem}
    .f{margin-bottom:1rem}.f:last-of-type{margin-bottom:0}
    label{display:block;font-size:.78rem;font-weight:500;margin-bottom:.3rem}
    .hint{font-weight:400;color:var(--muted);font-size:.72rem;margin-left:.3rem}
    input[type=text],input[type=number],input[type=password],select{
      width:100%;padding:.45rem .7rem;border:1px solid var(--border);border-radius:6px;
      font-size:.85rem;color:var(--text);background:var(--surface);
      transition:border-color .15s,box-shadow .15s;outline:none
    }
    input:focus,select:focus{border-color:var(--primary);box-shadow:0 0 0 3px rgba(59,130,246,.15)}
    .row2{display:flex;gap:.65rem}.row2 .f{flex:1;margin-bottom:0}
    .tog-row{display:flex;align-items:center;justify-content:space-between;padding:.5rem 0}
    .tog-lbl{font-size:.875rem;font-weight:500}
    .tog-desc{font-size:.73rem;color:var(--muted);margin-top:.1rem}
    .sw{position:relative;width:40px;height:22px;flex-shrink:0}
    .sw input{opacity:0;width:0;height:0}
    .sl{position:absolute;inset:0;background:#cbd5e1;border-radius:22px;cursor:pointer;transition:.2s}
    .sl::before{content:'';position:absolute;width:16px;height:16px;left:3px;top:3px;background:#fff;border-radius:50%;transition:.2s;box-shadow:0 1px 3px rgba(0,0,0,.2)}
    input:checked+.sl{background:var(--primary)}
    input:checked+.sl::before{transform:translateX(18px)}
    #map{height:300px;border-radius:6px;border:1px solid var(--border);margin-top:.4rem}
    .coord{display:flex;gap:1rem;margin-top:.6rem;font-size:.83rem;color:var(--muted)}
    .coord b{color:var(--text)}
    .btn-row{display:flex;justify-content:flex-end;margin-top:1.1rem}
    button{padding:.45rem 1.2rem;border:none;border-radius:6px;font-size:.83rem;font-weight:500;cursor:pointer;transition:background .15s}
    .btn-p{background:var(--primary);color:#fff}
    .btn-p:hover{background:var(--primary-h)}
    .info{display:grid;grid-template-columns:auto 1fr;gap:.4rem .9rem;font-size:.85rem}
    .ik{color:var(--muted);font-weight:500}.iv{font-family:monospace;color:var(--text)}
    pre{background:#f1f5f9;padding:.7rem;border-radius:6px;font-size:.75rem;overflow-x:auto;color:#334155;line-height:1.5}
    hr{border:none;border-top:1px solid var(--border);margin:.9rem 0}
    #toast{position:fixed;bottom:1.5rem;right:1.5rem;padding:.65rem 1.1rem;border-radius:var(--r);font-size:.83rem;font-weight:500;box-shadow:0 4px 12px rgba(0,0,0,.18);opacity:0;transform:translateY(.4rem);transition:opacity .22s,transform .22s;pointer-events:none;z-index:9999}
    #toast.show{opacity:1;transform:none}
    #toast.ok{background:#166534;color:#fff}
    #toast.err{background:#991b1b;color:#fff}
    @media(max-width:600px){
      body{flex-direction:column}
      .sb{width:100%;height:auto;position:static;display:flex;flex-wrap:wrap;gap:.2rem;padding:.6rem;border-right:none;border-bottom:1px solid var(--border)}
      .sb-title{display:none}
      .nav{border-left:none;border-radius:6px;padding:.35rem .65rem}
      .nav.active{background:var(--primary);color:#fff;border-left:none}
      .main{padding:1rem}
    }
  </style>
</head>
<body>

<nav class="sb">
  <div class="sb-title">設定</div>
  <div class="nav active" onclick="go('weather',this)"><span class="ni">☁️</span>天氣</div>
  <div class="nav" onclick="go('mqtt',this)"><span class="ni">🔗</span>MQTT</div>
  <div class="nav" onclick="go('display',this)"><span class="ni">🖥️</span>顯示器</div>
  <div class="nav" onclick="go('presence',this)"><span class="ni">👁️</span>在場偵測</div>
  <div class="nav" onclick="go('voice',this)"><span class="ni">🔊</span>語音</div>
  <div class="nav" onclick="go('notif',this)"><span class="ni">💬</span>通知</div>
  <div class="nav" onclick="go('general',this)"><span class="ni">⚙️</span>一般</div>
  <div class="nav" onclick="go('wifi',this)"><span class="ni">📶</span>WiFi</div>
</nav>

<main class="main">

  <!-- Weather -->
  <div id="sec-weather" class="sec active">
    <div class="sec-head">
      <div class="sec-title">☁️ 天氣設定</div>
      <div class="sec-desc">OpenWeatherMap API 金鑰、單位與更新頻率</div>
    </div>
    <div class="card">
      <div class="c-sub">API 設定</div>
      <div class="f">
        <label>OpenWeatherMap API Key</label>
        <input type="password" id="w-key" placeholder="輸入 API Key">
      </div>
      <div class="row2">
        <div class="f">
          <label>溫度單位</label>
          <select id="w-units">
            <option value="metric">°C（metric）</option>
            <option value="imperial">°F（imperial）</option>
            <option value="standard">K（standard）</option>
          </select>
        </div>
        <div class="f">
          <label>更新間隔 <span class="hint">（秒，60–3600）</span></label>
          <input type="number" id="w-interval" min="60" max="3600" step="60">
        </div>
      </div>
      <div class="btn-row"><button class="btn-p" onclick="saveWeather()">儲存</button></div>
    </div>
    <div class="card">
      <div class="c-sub">地點</div>
      <p style="font-size:.78rem;color:var(--muted);margin-bottom:.3rem">點擊地圖或拖曳標記來選取位置</p>
      <div id="map"></div>
      <div class="coord">
        <span>緯度 <b id="v-lat">__LAT__</b></span>
        <span>經度 <b id="v-lon">__LON__</b></span>
      </div>
      <div class="btn-row"><button class="btn-p" onclick="saveLocation()">儲存位置</button></div>
    </div>
  </div>

  <!-- MQTT -->
  <div id="sec-mqtt" class="sec">
    <div class="sec-head">
      <div class="sec-title">🔗 MQTT 設定</div>
      <div class="sec-desc">Broker 連線資訊</div>
    </div>
    <div class="card">
      <div class="f">
        <label>Broker Host</label>
        <input type="text" id="m-host" placeholder="192.168.1.100">
      </div>
      <div class="row2">
        <div class="f">
          <label>Port <span class="hint">（1–65535）</span></label>
          <input type="number" id="m-port" min="1" max="65535">
        </div>
        <div class="f">
          <label>Client ID</label>
          <input type="text" id="m-client" placeholder="epaper-home-display">
        </div>
      </div>
      <div class="btn-row"><button class="btn-p" onclick="saveMQTT()">儲存</button></div>
    </div>
  </div>

  <!-- Display -->
  <div id="sec-display" class="sec">
    <div class="sec-head">
      <div class="sec-title">🖥️ 顯示器設定</div>
      <div class="sec-desc">e-Paper 更新時機與顯示行為</div>
    </div>
    <div class="card">
      <div class="f">
        <label>e-Paper 型號</label>
        <select id="d-model">
          <option value="epd7in5_V2">Waveshare 7.5" V2</option>
          <option value="epd7in5">Waveshare 7.5" V1</option>
          <option value="epd5in83_V2">Waveshare 5.83" V2</option>
          <option value="mock">Mock（測試用）</option>
        </select>
      </div>
      <hr>
      <div class="row2">
        <div class="f">
          <label>Dashboard 觸發秒 <span class="hint">（0–59）</span></label>
          <input type="number" id="d-trigger" min="0" max="59">
        </div>
        <div class="f">
          <label>延遲補償 <span class="hint">（秒，≥ 0）</span></label>
          <input type="number" id="d-lag" min="0" max="30">
        </div>
      </div>
      <div class="f" style="margin-top:.9rem">
        <label>天氣顯示更新間隔 <span class="hint">（秒）</span></label>
        <input type="number" id="d-wi" min="60" max="3600" step="60">
      </div>
      <div class="btn-row"><button class="btn-p" onclick="saveDisplay()">儲存</button></div>
    </div>
  </div>

  <!-- Presence -->
  <div id="sec-presence" class="sec">
    <div class="sec-head">
      <div class="sec-title">👁️ 在場偵測</div>
      <div class="sec-desc">調整各感測器評分權重與判斷閾值</div>
    </div>
    <div class="card">
      <div class="c-sub">評分權重</div>
      <div class="row2">
        <div class="f">
          <label>光線</label>
          <input type="number" id="p-light" min="0" max="10" step="0.5">
        </div>
        <div class="f">
          <label>門感測</label>
          <input type="number" id="p-door" min="0" max="10" step="0.5">
        </div>
        <div class="f">
          <label>人臉辨識</label>
          <input type="number" id="p-face" min="0" max="10" step="0.5">
        </div>
      </div>
      <hr>
      <div class="c-sub">判斷閾值</div>
      <div class="f">
        <label>在場閾值 <span class="hint">（≥ 此值視為在家，≥ 0）</span></label>
        <input type="number" id="p-thr" min="0" max="20" step="0.5">
      </div>
      <hr>
      <div class="c-sub">時間窗口</div>
      <div class="row2">
        <div class="f">
          <label>門感測窗口 <span class="hint">（秒）</span></label>
          <input type="number" id="p-dwin" min="30" max="3600" step="30">
        </div>
        <div class="f">
          <label>人臉辨識窗口 <span class="hint">（秒）</span></label>
          <input type="number" id="p-fwin" min="30" max="3600" step="30">
        </div>
      </div>
      <div class="btn-row"><button class="btn-p" onclick="savePresence()">儲存</button></div>
    </div>
  </div>

  <!-- Voice -->
  <div id="sec-voice" class="sec">
    <div class="sec-head">
      <div class="sec-title">🔊 語音設定</div>
      <div class="sec-desc">提示音與播放器</div>
    </div>
    <div class="card">
      <div class="tog-row">
        <div>
          <div class="tog-lbl">啟用提示音</div>
          <div class="tog-desc">事件發生時播放音效</div>
        </div>
        <label class="sw"><input type="checkbox" id="v-en"><span class="sl"></span></label>
      </div>
      <hr>
      <div class="f">
        <label>播放器指令</label>
        <input type="text" id="v-player" placeholder="aplay">
      </div>
      <div class="btn-row"><button class="btn-p" onclick="saveVoice()">儲存</button></div>
    </div>
  </div>

  <!-- Notifications -->
  <div id="sec-notif" class="sec">
    <div class="sec-head">
      <div class="sec-title">💬 通知設定</div>
      <div class="sec-desc">Discord Webhook 告警</div>
    </div>
    <div class="card">
      <div class="f">
        <label>Discord Webhook URL</label>
        <input type="password" id="n-discord" placeholder="https://discord.com/api/webhooks/...">
      </div>
      <div class="btn-row"><button class="btn-p" onclick="saveNotif()">儲存</button></div>
    </div>
  </div>

  <!-- General -->
  <div id="sec-general" class="sec">
    <div class="sec-head">
      <div class="sec-title">⚙️ 一般設定</div>
      <div class="sec-desc">系統時區</div>
    </div>
    <div class="card">
      <div class="f">
        <label>時區 <span class="hint">（例：Asia/Taipei）</span></label>
        <input type="text" id="g-tz" placeholder="Asia/Taipei">
      </div>
      <div class="btn-row"><button class="btn-p" onclick="saveGeneral()">儲存</button></div>
    </div>
  </div>

  <!-- WiFi -->
  <div id="sec-wifi" class="sec">
    <div class="sec-head">
      <div class="sec-title">📶 WiFi 狀態</div>
      <div class="sec-desc">目前網路連線資訊</div>
    </div>
    <div class="card" id="wifi-card">
      <div style="font-size:.85rem;color:var(--muted)">載入中…</div>
    </div>
    <div class="card">
      <div class="c-sub">更換 WiFi</div>
      <p style="font-size:.78rem;color:var(--muted);margin-bottom:.8rem">由於安全限制，更換 WiFi 需透過 SSH 執行：</p>
      <pre>sudo nmcli dev wifi connect "SSID名稱" password "密碼"</pre>
      <p style="font-size:.72rem;color:var(--muted);margin-top:.5rem">或編輯 /etc/wpa_supplicant/wpa_supplicant.conf 後重啟網路</p>
    </div>
  </div>

</main>

<div id="toast"></div>

<script>
var mapLat=__LAT__, mapLon=__LON__;
var lmap=null, lmk=null;

function go(name,el){
  document.querySelectorAll('.sec').forEach(function(s){s.classList.remove('active')});
  document.querySelectorAll('.nav').forEach(function(n){n.classList.remove('active')});
  document.getElementById('sec-'+name).classList.add('active');
  el.classList.add('active');
  if(name==='weather' && !lmap) initMap();
  if(name==='wifi') loadWifi();
}

function toast(msg,ok){
  var t=document.getElementById('toast');
  t.textContent=msg; t.className='show '+(ok?'ok':'err');
  clearTimeout(t._t); t._t=setTimeout(function(){t.className=''},3000);
}

function initMap(){
  lmap=L.map('map').setView([mapLat,mapLon],10);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'© OpenStreetMap'}).addTo(lmap);
  lmk=L.marker([mapLat,mapLon],{draggable:true}).addTo(lmap);
  function upd(ll){
    mapLat=+ll.lat.toFixed(5); mapLon=+ll.lng.toFixed(5);
    document.getElementById('v-lat').textContent=mapLat;
    document.getElementById('v-lon').textContent=mapLon;
  }
  lmk.on('dragend',function(e){upd(e.target.getLatLng())});
  lmap.on('click',function(e){lmk.setLatLng(e.latlng);upd(e.latlng)});
}

async function loadCfg(){
  try{
    var r=await fetch('/settings/config');
    var c=await r.json();
    var w=c.weather||{};
    // api_key is masked server-side; update placeholder to reflect whether it is set
    document.getElementById('w-key').placeholder=w.api_key_set?'（已設定，重新輸入以更新）':'輸入 API Key';
    document.getElementById('w-units').value=w.units||'metric';
    document.getElementById('w-interval').value=w.fetch_interval_seconds??600;
    // lat/lon: use explicit null check so value 0 is valid
    if(w.lat!=null && w.lon!=null){
      mapLat=w.lat; mapLon=w.lon;
      document.getElementById('v-lat').textContent=mapLat;
      document.getElementById('v-lon').textContent=mapLon;
      if(lmap){lmap.setView([mapLat,mapLon]);lmk.setLatLng([mapLat,mapLon]);}
    }
    var m=c.mqtt||{};
    document.getElementById('m-host').value=m.broker_host||'';
    document.getElementById('m-port').value=m.broker_port??1883;
    document.getElementById('m-client').value=m.client_id||'';
    var d=c.display||{};
    document.getElementById('d-model').value=d.model||'epd7in5_V2';
    document.getElementById('d-trigger').value=d.dashboard_trigger_second??57;
    document.getElementById('d-lag').value=d.display_lag_seconds??3;
    document.getElementById('d-wi').value=d.weather_update_interval??600;
    var p=c.presence||{};
    document.getElementById('p-light').value=p.light_weight??1.0;
    document.getElementById('p-door').value=p.door_weight??1.0;
    document.getElementById('p-face').value=p.face_weight??2.0;
    document.getElementById('p-thr').value=p.threshold??2.0;
    document.getElementById('p-dwin').value=p.door_window_seconds??300;
    document.getElementById('p-fwin').value=p.face_window_seconds??600;
    var v=c.voice||{};
    document.getElementById('v-en').checked=v.enabled!==false;
    document.getElementById('v-player').value=v.player||'aplay';
    var dc=c.discord||{};
    document.getElementById('n-discord').placeholder=dc.webhook_set?'（已設定，重新輸入以更新）':'https://discord.com/api/webhooks/...';
    document.getElementById('g-tz').value=c.timezone||'Asia/Taipei';
  }catch(e){console.error('loadCfg',e)}
}

async function loadWifi(){
  var card=document.getElementById('wifi-card');
  try{
    var r=await fetch('/settings/wifi');
    var d=await r.json();
    var rows=Object.entries(d).map(function(kv){
      return '<div class="ik">'+kv[0]+'</div><div class="iv">'+(kv[1]||'—')+'</div>';
    }).join('');
    card.innerHTML='<div class="info">'+rows+'</div>';
  }catch(e){
    card.innerHTML='<div style="color:var(--muted);font-size:.85rem">無法取得 WiFi 資訊</div>';
  }
}

async function put(path,data){
  var r=await fetch(path,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  if(!r.ok) throw new Error('HTTP '+r.status);
  return r.json();
}

async function saveLocation(){
  try{await put('/settings/location',{lat:mapLat,lon:mapLon});toast('✓ 位置已儲存',true);}
  catch(e){toast('儲存失敗：'+e.message,false);}
}
async function saveWeather(){
  try{
    var body={
      units:document.getElementById('w-units').value,
      fetch_interval_seconds:+document.getElementById('w-interval').value
    };
    // only include api_key if user typed something new
    var key=document.getElementById('w-key').value.trim();
    if(key) body.api_key=key;
    await put('/settings/weather',body);
    document.getElementById('w-key').value='';
    document.getElementById('w-key').placeholder='（已設定，重新輸入以更新）';
    toast('✓ 天氣設定已儲存',true);
  }catch(e){toast('儲存失敗：'+e.message,false);}
}
async function saveMQTT(){
  try{
    await put('/settings/mqtt',{
      broker_host:document.getElementById('m-host').value.trim(),
      broker_port:+document.getElementById('m-port').value,
      client_id:document.getElementById('m-client').value.trim()
    });
    toast('✓ MQTT 已儲存',true);
  }catch(e){toast('儲存失敗：'+e.message,false);}
}
async function saveDisplay(){
  try{
    await put('/settings/display',{
      model:document.getElementById('d-model').value,
      dashboard_trigger_second:+document.getElementById('d-trigger').value,
      display_lag_seconds:+document.getElementById('d-lag').value,
      weather_update_interval:+document.getElementById('d-wi').value
    });
    toast('✓ 顯示器設定已儲存',true);
  }catch(e){toast('儲存失敗：'+e.message,false);}
}
async function savePresence(){
  try{
    await put('/settings/presence',{
      light_weight:+document.getElementById('p-light').value,
      door_weight:+document.getElementById('p-door').value,
      face_weight:+document.getElementById('p-face').value,
      threshold:+document.getElementById('p-thr').value,
      door_window_seconds:+document.getElementById('p-dwin').value,
      face_window_seconds:+document.getElementById('p-fwin').value
    });
    toast('✓ 在場偵測已儲存',true);
  }catch(e){toast('儲存失敗：'+e.message,false);}
}
async function saveVoice(){
  try{
    await put('/settings/voice',{
      enabled:document.getElementById('v-en').checked,
      player:document.getElementById('v-player').value.trim()
    });
    toast('✓ 語音設定已儲存',true);
  }catch(e){toast('儲存失敗：'+e.message,false);}
}
async function saveNotif(){
  try{
    var url=document.getElementById('n-discord').value.trim();
    // only update if user typed something new
    if(!url){toast('請輸入 Webhook URL，或留空以清除',false);return;}
    await put('/settings/notifications',{discord_webhook_url:url==='clear'?'':url});
    document.getElementById('n-discord').value='';
    document.getElementById('n-discord').placeholder='（已設定，重新輸入以更新）';
    toast('✓ 通知設定已儲存',true);
  }catch(e){toast('儲存失敗：'+e.message,false);}
}
async function saveGeneral(){
  try{
    await put('/settings/general',{timezone:document.getElementById('g-tz').value.trim()});
    toast('✓ 一般設定已儲存',true);
  }catch(e){toast('儲存失敗：'+e.message,false);}
}

loadCfg();
initMap();
</script>
</body>
</html>"""


# ── Config persistence ────────────────────────────────────────────────────────

def _save_to_config(updates: dict) -> None:
    """Atomically deep-merge *updates* into config.local.yaml (thread-safe)."""
    with _config_lock:
        local_raw: dict = {}
        if os.path.exists(_LOCAL_CFG):
            with open(_LOCAL_CFG, "r", encoding="utf-8") as f:
                local_raw = yaml.safe_load(f) or {}
            if not isinstance(local_raw, dict):
                local_raw = {}

        def _merge(base: dict, patch: dict) -> None:
            for k, v in patch.items():
                if isinstance(v, dict) and isinstance(base.get(k), dict):
                    _merge(base[k], v)
                else:
                    base[k] = v

        _merge(local_raw, updates)
        tmp = _LOCAL_CFG + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            yaml.dump(local_raw, f, default_flow_style=False, sort_keys=False)
        os.replace(tmp, _LOCAL_CFG)


# ── Request bodies ────────────────────────────────────────────────────────────

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


class _WeatherBody(BaseModel):
    api_key: str | None = None
    units: str | None = None
    fetch_interval_seconds: int | None = None


class _MQTTBody(BaseModel):
    broker_host: str | None = None
    broker_port: int | None = None
    client_id: str | None = None


class _DisplayBody(BaseModel):
    model: str | None = None
    dashboard_trigger_second: int | None = None
    display_lag_seconds: int | None = None
    weather_update_interval: int | None = None


class _PresenceBody(BaseModel):
    light_weight: float | None = None
    door_weight: float | None = None
    face_weight: float | None = None
    threshold: float | None = None
    door_window_seconds: int | None = None
    face_window_seconds: int | None = None


class _VoiceBody(BaseModel):
    enabled: bool | None = None
    player: str | None = None


class _NotificationsBody(BaseModel):
    discord_webhook_url: str | None = None


class _GeneralBody(BaseModel):
    timezone: str | None = None


# ── App factory ───────────────────────────────────────────────────────────────

def create_app(settings: "Settings", weather_service: WeatherService) -> FastAPI:
    app = FastAPI(title="ePaper Home Display", version="0.1.0")

    # ── Read-only ──────────────────────────────────────────────────────────────

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

    # ── Settings pages & config ────────────────────────────────────────────────

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

    @app.get("/settings/config")
    async def get_config():
        d = dataclasses.asdict(settings)
        # Mask secrets: replace value with a boolean indicator
        w = d.get("weather", {})
        api_key = w.pop("api_key", "")
        w["api_key_set"] = bool(api_key)
        dc = d.get("discord", {})
        webhook = dc.pop("webhook_url", "")
        dc["webhook_set"] = bool(webhook)
        return JSONResponse(d)

    @app.get("/settings/wifi")
    async def get_wifi():
        info: dict[str, str] = {}

        async def _run(cmd: list[str]) -> str:
            return await asyncio.to_thread(
                lambda: subprocess.check_output(
                    cmd, text=True, stderr=subprocess.DEVNULL, timeout=3
                )
            )

        try:
            ssid = (await _run(["iwgetid", "wlan0", "-r"])).strip()
            info["SSID"] = ssid or "—"
        except Exception:
            info["SSID"] = "無法取得"
        try:
            out = await _run(["ip", "-4", "addr", "show", "wlan0"])
            for line in out.splitlines():
                if "inet " in line:
                    info["IP 位址"] = line.strip().split()[1]
                    break
            else:
                info["IP 位址"] = "無法取得"
        except Exception:
            info["IP 位址"] = "無法取得"
        try:
            out = await _run(["iwconfig", "wlan0"])
            m = re.search(r"Signal level=(-?\d+)\s*dBm", out)
            info["訊號強度"] = f"{m.group(1)} dBm" if m else "無法取得"
        except Exception:
            info["訊號強度"] = "無法取得"
        return info

    # ── Settings mutations ─────────────────────────────────────────────────────
    # Pattern: validate → persist → update memory (memory unchanged on persist failure)

    @app.put("/settings/location")
    async def set_location(body: _LocationBody):
        if not (-90 <= body.lat <= 90):
            raise HTTPException(400, detail="lat must be -90..90")
        if not (-180 <= body.lon <= 180):
            raise HTTPException(400, detail="lon must be -180..180")

        lat = round(body.lat, 5)
        lon = round(body.lon, 5)
        try:
            _save_to_config({"weather": {"lat": lat, "lon": lon}})
        except Exception as exc:
            logger.error("Failed to persist location: %s", exc)
            raise HTTPException(500, detail="Failed to persist location")

        settings.weather.lat = lat
        settings.weather.lon = lon
        weather_service.set_location(lat, lon)
        return {"ok": True, "lat": lat, "lon": lon}

    @app.put("/settings/weather")
    async def set_weather(body: _WeatherBody):
        patch = body.model_dump(exclude_none=True)
        if "fetch_interval_seconds" in patch and not (60 <= patch["fetch_interval_seconds"] <= 3600):
            raise HTTPException(400, detail="fetch_interval_seconds must be 60–3600")
        if "units" in patch and patch["units"] not in ("metric", "imperial", "standard"):
            raise HTTPException(400, detail="units must be metric/imperial/standard")
        if not patch:
            return {"ok": True}

        try:
            _save_to_config({"weather": patch})
        except Exception as exc:
            logger.error("Failed to persist weather settings: %s", exc)
            raise HTTPException(500, detail="Failed to persist settings")

        for k, v in patch.items():
            setattr(settings.weather, k, v)
        return {"ok": True}

    @app.put("/settings/mqtt")
    async def set_mqtt(body: _MQTTBody):
        patch = body.model_dump(exclude_none=True)
        if "broker_host" in patch and not patch["broker_host"].strip():
            raise HTTPException(400, detail="broker_host must not be empty")
        if "broker_port" in patch and not (1 <= patch["broker_port"] <= 65535):
            raise HTTPException(400, detail="broker_port must be 1–65535")
        if not patch:
            return {"ok": True}

        try:
            _save_to_config({"mqtt": patch})
        except Exception as exc:
            logger.error("Failed to persist MQTT settings: %s", exc)
            raise HTTPException(500, detail="Failed to persist settings")

        for k, v in patch.items():
            setattr(settings.mqtt, k, v)
        return {"ok": True}

    @app.put("/settings/display")
    async def set_display(body: _DisplayBody):
        patch = body.model_dump(exclude_none=True)
        if "dashboard_trigger_second" in patch and not (0 <= patch["dashboard_trigger_second"] <= 59):
            raise HTTPException(400, detail="dashboard_trigger_second must be 0–59")
        if "display_lag_seconds" in patch and patch["display_lag_seconds"] < 0:
            raise HTTPException(400, detail="display_lag_seconds must be >= 0")
        if "weather_update_interval" in patch and not (60 <= patch["weather_update_interval"] <= 3600):
            raise HTTPException(400, detail="weather_update_interval must be 60–3600")
        if not patch:
            return {"ok": True}

        try:
            _save_to_config({"display": patch})
        except Exception as exc:
            logger.error("Failed to persist display settings: %s", exc)
            raise HTTPException(500, detail="Failed to persist settings")

        for k, v in patch.items():
            setattr(settings.display, k, v)
        return {"ok": True}

    @app.put("/settings/presence")
    async def set_presence(body: _PresenceBody):
        patch = body.model_dump(exclude_none=True)
        for weight_key in ("light_weight", "door_weight", "face_weight", "threshold"):
            if weight_key in patch and patch[weight_key] < 0:
                raise HTTPException(400, detail=f"{weight_key} must be >= 0")
        for window_key in ("door_window_seconds", "face_window_seconds"):
            if window_key in patch and not (30 <= patch[window_key] <= 3600):
                raise HTTPException(400, detail=f"{window_key} must be 30–3600")
        if not patch:
            return {"ok": True}

        try:
            _save_to_config({"presence": patch})
        except Exception as exc:
            logger.error("Failed to persist presence settings: %s", exc)
            raise HTTPException(500, detail="Failed to persist settings")

        for k, v in patch.items():
            setattr(settings.presence, k, v)
        return {"ok": True}

    @app.put("/settings/voice")
    async def set_voice(body: _VoiceBody):
        patch = body.model_dump(exclude_none=True)
        if "player" in patch and not patch["player"].strip():
            raise HTTPException(400, detail="player must not be empty")
        if not patch:
            return {"ok": True}

        try:
            _save_to_config({"voice": patch})
        except Exception as exc:
            logger.error("Failed to persist voice settings: %s", exc)
            raise HTTPException(500, detail="Failed to persist settings")

        for k, v in patch.items():
            setattr(settings.voice, k, v)
        return {"ok": True}

    @app.put("/settings/notifications")
    async def set_notifications(body: _NotificationsBody):
        patch = body.model_dump(exclude_none=True)
        url = patch.get("discord_webhook_url", "")
        if url and not url.startswith("https://"):
            raise HTTPException(400, detail="discord_webhook_url must start with https://")

        try:
            _save_to_config({"discord": {"webhook_url": url}})
        except Exception as exc:
            logger.error("Failed to persist notification settings: %s", exc)
            raise HTTPException(500, detail="Failed to persist settings")

        settings.discord.webhook_url = url
        return {"ok": True}

    @app.put("/settings/general")
    async def set_general(body: _GeneralBody):
        if body.timezone is None:
            return {"ok": True}
        tz = body.timezone.strip()
        if not tz:
            raise HTTPException(400, detail="timezone must not be empty")

        try:
            _save_to_config({"timezone": tz})
        except Exception as exc:
            logger.error("Failed to persist general settings: %s", exc)
            raise HTTPException(500, detail="Failed to persist settings")

        settings.timezone = tz
        return {"ok": True}

    # ── AI usage (internal) ────────────────────────────────────────────────────

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

    return app
