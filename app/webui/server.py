from __future__ import annotations

import asyncio
import dataclasses
import html as _html
import logging
import os
import re
import secrets
import subprocess
import threading
from typing import TYPE_CHECKING

import yaml
from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from passlib.context import CryptContext
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.services.weather import WeatherService
from app.state import state

if TYPE_CHECKING:
    from app.config import Settings

logger = logging.getLogger(__name__)

_LOCAL_CFG = "config.local.yaml"
_config_lock = threading.Lock()
_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


class _AuthMiddleware(BaseHTTPMiddleware):
    _PUBLIC = frozenset({"/health", "/login", "/logout", "/ai_usage"})

    async def dispatch(self, request: Request, call_next):
        if request.url.path not in self._PUBLIC:
            if not request.session.get("authenticated"):
                if "text/html" in request.headers.get("accept", ""):
                    return RedirectResponse(
                        url=f"/login?next={request.url.path}", status_code=302
                    )
                return JSONResponse({"detail": "Unauthorized"}, status_code=401)
        return await call_next(request)

# ── HTML ──────────────────────────────────────────────────────────────────────

_DESK_HTML = r"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>書桌前分析</title>
  <style>
    *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
    :root{
      --bg:#0f172a;--surface:#1e293b;--surface2:#283548;--border:#334155;
      --primary:#3b82f6;--green:#22c55e;--muted:#64748b;--text:#e2e8f0;
      --r:10px;--sh:0 2px 8px rgba(0,0,0,.3)
    }
    body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:var(--bg);color:var(--text);min-height:100vh}
    .topbar{display:flex;align-items:center;justify-content:space-between;padding:.9rem 1.5rem;background:var(--surface);border-bottom:1px solid var(--border);position:sticky;top:0;z-index:10}
    .topbar-title{font-size:1.1rem;font-weight:600}
    .topbar-link{font-size:.8rem;color:var(--primary);text-decoration:none;padding:.3rem .7rem;border:1px solid var(--primary);border-radius:6px}
    .container{max-width:900px;margin:0 auto;padding:1.5rem}
    .card{background:var(--surface);border:1px solid var(--border);border-radius:var(--r);padding:1.3rem;box-shadow:var(--sh);margin-bottom:1.2rem}
    .card-title{font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.07em;color:var(--muted);margin-bottom:1rem}
    .stats-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:.8rem;margin-bottom:1.2rem}
    .stat{background:var(--surface);border:1px solid var(--border);border-radius:var(--r);padding:1rem 1.2rem;box-shadow:var(--sh)}
    .stat-label{font-size:.72rem;color:var(--muted);margin-bottom:.3rem}
    .stat-value{font-size:1.5rem;font-weight:700;line-height:1.2}
    .stat-sub{font-size:.72rem;color:var(--muted);margin-top:.2rem}
    .badge{display:inline-block;padding:.2rem .65rem;border-radius:99px;font-size:.78rem;font-weight:600}
    .badge-green{background:rgba(34,197,94,.15);color:#4ade80}
    .badge-gray{background:rgba(100,116,139,.15);color:#94a3b8}
    .sensor-row{display:flex;align-items:center;gap:1rem;font-size:.85rem;flex-wrap:wrap}
    .sensor-bar-wrap{flex:1;min-width:180px}
    .sensor-bar{height:8px;background:var(--surface2);border-radius:4px;position:relative;overflow:visible}
    .sensor-fill{height:100%;border-radius:4px;background:var(--primary);transition:width .4s}
    .sensor-threshold-line{position:absolute;top:-3px;bottom:-3px;width:2px;background:#f59e0b;border-radius:1px}
    .chart-wrap{overflow-x:auto}
    table{width:100%;border-collapse:collapse;font-size:.82rem}
    th{text-align:left;padding:.5rem .7rem;font-size:.72rem;color:var(--muted);font-weight:600;border-bottom:1px solid var(--border)}
    td{padding:.5rem .7rem;border-bottom:1px solid rgba(51,65,85,.5)}
    tr:last-child td{border-bottom:none}
    .badge-occ{background:rgba(59,130,246,.15);color:#93c5fd}
    .badge-unocc{background:rgba(100,116,139,.15);color:#94a3b8}
    .refresh-ts{font-size:.72rem;color:var(--muted);text-align:right;margin-top:.3rem}
    @media(max-width:600px){.container{padding:1rem}.topbar{padding:.7rem 1rem}}
  </style>
</head>
<body>

<div class="topbar">
  <div class="topbar-title">📖 書桌前分析</div>
  <a href="/settings" class="topbar-link">⚙️ 設定</a>
</div>

<div class="container">

  <!-- Status Stats -->
  <div class="stats-grid" id="stats-grid">
    <div class="stat"><div class="stat-label">目前狀態</div><div class="stat-value" id="s-presence">—</div></div>
    <div class="stat"><div class="stat-label">今日累計</div><div class="stat-value" id="s-today">—</div></div>
    <div class="stat"><div class="stat-label">本次時段</div><div class="stat-value" id="s-segment">—</div><div class="stat-sub" id="s-since"></div></div>
    <div class="stat"><div class="stat-label">今日次數</div><div class="stat-value" id="s-count">—</div></div>
  </div>

  <!-- Sensor -->
  <div class="card">
    <div class="card-title">光線感測器</div>
    <div class="sensor-row">
      <span>目前值：<b id="s-light">—</b></span>
      <span>閾值：<b id="s-thresh">—</b></span>
      <div class="sensor-bar-wrap">
        <div class="sensor-bar">
          <div class="sensor-fill" id="s-fill" style="width:0%"></div>
          <div class="sensor-threshold-line" id="s-tline" style="left:0%"></div>
        </div>
      </div>
    </div>
    <div class="refresh-ts" id="last-refresh"></div>
  </div>

  <!-- 24h Timeline -->
  <div class="card">
    <div class="card-title">近 24 小時狀態軸</div>
    <div class="chart-wrap" id="timeline-wrap">
      <div style="color:var(--muted);font-size:.85rem">載入中…</div>
    </div>
  </div>

  <!-- 30-day Chart -->
  <div class="card">
    <div class="card-title">近 30 天書桌前時間</div>
    <div class="chart-wrap" id="barchart-wrap">
      <div style="color:var(--muted);font-size:.85rem">載入中…</div>
    </div>
    <div style="display:flex;gap:2rem;margin-top:.9rem;font-size:.82rem;flex-wrap:wrap">
      <span>30 天平均：<b id="avg30">—</b></span>
      <span>最高一天：<b id="max30">—</b></span>
    </div>
  </div>

  <!-- Daily Stats Table -->
  <div class="card">
    <div class="card-title">每日統計（最近 30 天）</div>
    <div style="overflow-x:auto">
      <table id="daily-table">
        <thead><tr><th>日期</th><th>書桌前時間</th><th>書桌前比例</th></tr></thead>
        <tbody id="daily-tbody"><tr><td colspan="3" style="color:var(--muted)">載入中…</td></tr></tbody>
      </table>
    </div>
  </div>

  <!-- Recent Sessions -->
  <div class="card">
    <div class="card-title">最近時段紀錄</div>
    <div style="overflow-x:auto">
      <table id="sessions-table">
        <thead><tr><th>開始</th><th>結束</th><th>持續時間</th></tr></thead>
        <tbody id="sessions-tbody"><tr><td colspan="3" style="color:var(--muted)">載入中…</td></tr></tbody>
      </table>
    </div>
  </div>

</div>

<script>
function fmtDuration(sec){
  if(!sec||sec<=0) return '0m';
  var h=Math.floor(sec/3600), m=Math.floor((sec%3600)/60);
  if(h===0) return m+'m';
  if(m===0) return h+'h';
  return h+'h '+m+'m';
}

function fmtTime(iso){
  if(!iso) return '進行中';
  var d=new Date(iso);
  return d.toLocaleTimeString('zh-TW',{hour:'2-digit',minute:'2-digit',hour12:false});
}

function fmtDate(iso){
  if(!iso) return '';
  return iso.slice(0,10);
}

function renderTimeline(sessions){
  var now=Date.now();
  var start24=now-86400000;
  var W=800, H=48;
  var bars='';
  sessions.forEach(function(s){
    var x1=Math.max(0,(new Date(s.start_ts).getTime()-start24)/86400000*W);
    var endMs=s.end_ts?new Date(s.end_ts).getTime():now;
    var x2=Math.min(W,(endMs-start24)/86400000*W);
    var w=Math.max(2,x2-x1);
    var opacity=s.end_ts?'0.75':'0.95';
    bars+='<rect x="'+x1+'" y="6" width="'+w+'" height="36" rx="3" fill="#3b82f6" opacity="'+opacity+'"/>';
  });
  var labels='';
  for(var h=0;h<=24;h+=6){
    var x=h/24*W;
    var t=new Date(start24+h*3600000);
    var lbl=String(t.getHours()).padStart(2,'0')+':00';
    labels+='<text x="'+x+'" y="'+H+'" text-anchor="middle" font-size="10" fill="#64748b">'+lbl+'</text>';
    labels+='<line x1="'+x+'" y1="44" x2="'+x+'" y2="47" stroke="#475569" stroke-width="1"/>';
  }
  return '<svg viewBox="0 0 '+W+' '+(H+2)+'" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;min-width:320px">'
    +'<rect width="'+W+'" height="48" rx="4" fill="#1e293b"/>'
    +bars+labels+'</svg>';
}

function renderBarChart(daily30d){
  var W=800, bH=140, svgH=170;
  var maxSec=Math.max.apply(null,daily30d.map(function(d){return d.total_seconds;}));
  if(maxSec===0) maxSec=3600;
  var bW=W/30-2;
  var bars='',labels='';
  daily30d.forEach(function(d,i){
    var x=i*(W/30);
    var h=Math.max(2,d.total_seconds/maxSec*bH);
    var y=bH-h;
    var opacity=d.total_seconds>0?'0.75':'0.2';
    bars+='<rect x="'+(x+1)+'" y="'+y+'" width="'+bW+'" height="'+h+'" rx="2" fill="#3b82f6" opacity="'+opacity+'"/>';
    if(i%7===0||i===29){
      var lbl=d.date.slice(5);
      labels+='<text x="'+(x+bW/2)+'" y="'+(svgH-2)+'" text-anchor="middle" font-size="9" fill="#64748b">'+lbl+'</text>';
    }
  });
  return '<svg viewBox="0 0 '+W+' '+svgH+'" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;min-width:320px">'
    +'<rect width="'+W+'" height="'+svgH+'" rx="4" fill="#1e293b"/>'
    +bars+labels+'</svg>';
}

async function loadStats(){
  try{
    var r=await fetch('/api/desk/stats');
    var d=await r.json();
    var occ=d.presence==='OCCUPIED';
    document.getElementById('s-presence').innerHTML=
      '<span class="badge '+(occ?'badge-green':'badge-gray')+'">'+(occ?'在桌前':'不在')+'</span>';
    document.getElementById('s-today').textContent=fmtDuration(d.today_total_seconds);
    document.getElementById('s-segment').textContent=fmtDuration(d.current_segment_seconds);
    document.getElementById('s-since').textContent=d.last_change_ts?('自 '+fmtTime(d.last_change_ts)):'';
    document.getElementById('s-count').textContent=d.today_session_count+'次';
    document.getElementById('s-light').textContent=d.light_raw??'—';
    document.getElementById('s-thresh').textContent=d.threshold??'—';
    var raw=d.light_raw??0, thresh=d.threshold??500;
    var fillPct=Math.min(100,raw/1023*100).toFixed(1);
    var threshPct=Math.min(100,thresh/1023*100).toFixed(1);
    document.getElementById('s-fill').style.width=fillPct+'%';
    document.getElementById('s-tline').style.left=threshPct+'%';
    document.getElementById('last-refresh').textContent='最後更新：'+new Date().toLocaleTimeString('zh-TW',{hour12:false});
  }catch(e){console.error('stats',e);}
}

async function loadHistory(){
  try{
    var r=await fetch('/api/desk/history');
    var d=await r.json();
    document.getElementById('timeline-wrap').innerHTML=renderTimeline(d.timeline_24h||[]);

    document.getElementById('barchart-wrap').innerHTML=renderBarChart(d.daily_30d||[]);

    var totals=(d.daily_30d||[]).map(function(x){return x.total_seconds;});
    var nonZero=totals.filter(function(x){return x>0;});
    var avg=nonZero.length?Math.round(nonZero.reduce(function(a,b){return a+b;},0)/nonZero.length):0;
    var max=nonZero.length?Math.max.apply(null,nonZero):0;
    document.getElementById('avg30').textContent=fmtDuration(avg);
    document.getElementById('max30').textContent=fmtDuration(max);

    var tbody=document.getElementById('daily-tbody');
    var rows=(d.daily_30d||[]).slice().reverse().map(function(x){
      var pct=Math.round(x.total_seconds/864);
      return '<tr><td>'+x.date+'</td><td>'+fmtDuration(x.total_seconds)+'</td><td>'+pct+'%</td></tr>';
    }).join('');
    tbody.innerHTML=rows||'<tr><td colspan="3" style="color:var(--muted)">無資料</td></tr>';
  }catch(e){console.error('history',e);}
}

async function loadSessions(){
  try{
    var r=await fetch('/api/desk/sessions?limit=20');
    var d=await r.json();
    var tbody=document.getElementById('sessions-tbody');
    var rows=(d.sessions||[]).map(function(s){
      var badge=s.end_ts?'':'<span class="badge badge-green" style="font-size:.65rem">進行中</span>';
      return '<tr><td>'+fmtTime(s.start_ts)+'<br><span style="font-size:.72rem;color:var(--muted)">'+fmtDate(s.start_ts)+'</span></td>'
        +'<td>'+(s.end_ts?fmtTime(s.end_ts):badge)+'</td>'
        +'<td>'+(s.duration_seconds!=null?fmtDuration(s.duration_seconds):'—')+'</td></tr>';
    }).join('');
    tbody.innerHTML=rows||'<tr><td colspan="3" style="color:var(--muted)">無紀錄</td></tr>';
  }catch(e){console.error('sessions',e);}
}

loadStats(); loadHistory(); loadSessions();
setInterval(loadStats, 30000);
setInterval(function(){loadHistory();loadSessions();}, 300000);
</script>
</body>
</html>"""


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
  <div class="nav" onclick="go('presence',this)"><span class="ni">💡</span>在場偵測</div>
  <div class="nav" onclick="go('voice',this)"><span class="ni">🔊</span>語音</div>
  <div class="nav" onclick="go('notif',this)"><span class="ni">💬</span>通知</div>
  <div class="nav" onclick="go('general',this)"><span class="ni">⚙️</span>一般</div>
  <div class="nav" onclick="go('wifi',this)"><span class="ni">📶</span>WiFi</div>
  <div class="nav" onclick="go('auth',this)"><span class="ni">🔒</span>安全</div>
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
      <div class="f">
        <label>刷新觸發秒 <span class="hint">（0–59，用來補償電子紙刷新延遲）</span></label>
        <input type="number" id="d-trigger" min="0" max="59">
      </div>
      <div class="f" style="margin-top:.9rem">
        <label>全刷新間隔 <span class="hint">（次數，1–100；每 N 次做一次全刷新清除鬼影）</span></label>
        <input type="number" id="d-fre" min="1" max="100">
      </div>
      <div class="btn-row"><button class="btn-p" onclick="saveDisplay()">儲存</button></div>
    </div>
  </div>

  <!-- Presence -->
  <div id="sec-presence" class="sec">
    <div class="sec-head">
      <div class="sec-title">💡 在場偵測</div>
      <div class="sec-desc">燈亮即判定為在場；人不在時暫停顯示更新</div>
    </div>
    <div class="card">
      <div class="f">
        <label>光線閾值 <span class="hint">（0–1023，ADC 原始值，高於此值判定為在場）</span></label>
        <input type="number" id="p-bright" min="0" max="1023">
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
      <div class="sec-desc">Discord Webhook 推播設定</div>
    </div>
    <div class="card">
      <div class="f">
        <label>Discord Webhook URL</label>
        <input type="password" id="n-discord" placeholder="https://discord.com/api/webhooks/...">
      </div>
      <hr>
      <div class="tog-row">
        <div><div class="tog-lbl">裝置上線通知</div><div class="tog-desc">服務啟動時通知 WebUI 連結</div></div>
        <label class="sw"><input type="checkbox" id="n-online"><span class="sl"></span></label>
      </div>
      <div class="tog-row">
        <div><div class="tog-lbl">時段結束通知</div><div class="tog-desc">離開書桌時推送該時段摘要</div></div>
        <label class="sw"><input type="checkbox" id="n-session"><span class="sl"></span></label>
      </div>
      <div class="f" style="margin-top:.5rem">
        <label>最短通知時段 <span class="hint">（分鐘，1–60）</span></label>
        <input type="number" id="n-min" min="1" max="60">
      </div>
      <hr>
      <div class="tog-row">
        <div><div class="tog-lbl">每日摘要通知</div><div class="tog-desc">每天固定時間推送昨日統計</div></div>
        <label class="sw"><input type="checkbox" id="n-daily"><span class="sl"></span></label>
      </div>
      <div class="f">
        <label>每日摘要時間 <span class="hint">（HH:MM）</span></label>
        <input type="text" id="n-time" placeholder="23:00" style="max-width:120px">
      </div>
      <div class="btn-row"><button class="btn-p" onclick="saveNotif()">儲存</button></div>
    </div>
    <div class="card">
      <div class="c-sub">書桌前分析</div>
      <p style="font-size:.85rem;color:var(--muted);margin-bottom:.6rem">查看即時狀態、今日統計與歷史紀錄</p>
      <a href="/desk" style="display:inline-block;padding:.45rem 1.2rem;background:var(--primary);color:#fff;border-radius:6px;font-size:.83rem;font-weight:500;text-decoration:none">開啟 Dashboard →</a>
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

  <!-- Auth -->
  <div id="sec-auth" class="sec">
    <div class="sec-head">
      <div class="sec-title">🔒 帳號安全</div>
      <div class="sec-desc">更改 WebUI 登入密碼</div>
    </div>
    <div class="card">
      <div class="c-sub">更改密碼</div>
      <div class="f">
        <label>目前密碼</label>
        <input type="password" id="a-cur" placeholder="輸入目前密碼">
      </div>
      <div class="f">
        <label>新密碼 <span class="hint">（至少 4 個字元）</span></label>
        <input type="password" id="a-new" placeholder="輸入新密碼">
      </div>
      <div class="f">
        <label>確認新密碼</label>
        <input type="password" id="a-conf" placeholder="再次輸入新密碼">
      </div>
      <div class="btn-row"><button class="btn-p" onclick="saveAuth()">更改密碼</button></div>
    </div>
    <div class="card">
      <div class="c-sub">會話管理</div>
      <p style="font-size:.82rem;color:var(--muted);margin-bottom:.8rem">Cookie 有效期 7 天，登出後需重新輸入密碼。</p>
      <a href="/logout" style="display:inline-block;padding:.45rem 1.2rem;background:#dc2626;color:#fff;border-radius:6px;font-size:.83rem;font-weight:500;text-decoration:none">登出</a>
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
    document.getElementById('d-fre').value=d.full_refresh_every??10;
    var sl=(c.sensors||{}).light||{};
    document.getElementById('p-bright').value=sl.bright_threshold??500;
    var v=c.voice||{};
    document.getElementById('v-en').checked=v.enabled!==false;
    document.getElementById('v-player').value=v.player||'aplay';
    var dc=c.discord||{};
    document.getElementById('n-discord').placeholder=dc.webhook_set?'（已設定，重新輸入以更新）':'https://discord.com/api/webhooks/...';
    document.getElementById('n-online').checked=dc.notify_device_online!==false;
    document.getElementById('n-session').checked=dc.notify_session_end!==false;
    document.getElementById('n-min').value=dc.session_end_min_minutes??5;
    document.getElementById('n-daily').checked=dc.notify_daily_summary!==false;
    document.getElementById('n-time').value=dc.daily_summary_time||'23:00';
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
      full_refresh_every:+document.getElementById('d-fre').value
    });
    toast('✓ 顯示器設定已儲存',true);
  }catch(e){toast('儲存失敗：'+e.message,false);}
}
async function savePresence(){
  try{
    await put('/settings/presence',{bright_threshold:+document.getElementById('p-bright').value});
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
    var body={
      notify_device_online:document.getElementById('n-online').checked,
      notify_session_end:document.getElementById('n-session').checked,
      session_end_min_minutes:+document.getElementById('n-min').value,
      notify_daily_summary:document.getElementById('n-daily').checked,
      daily_summary_time:document.getElementById('n-time').value.trim()
    };
    var url=document.getElementById('n-discord').value.trim();
    if(url) body.discord_webhook_url=(url==='clear'?'':url);
    await put('/settings/notifications',body);
    if(url){
      document.getElementById('n-discord').value='';
      document.getElementById('n-discord').placeholder='（已設定，重新輸入以更新）';
    }
    toast('✓ 通知設定已儲存',true);
  }catch(e){toast('儲存失敗：'+e.message,false);}
}
async function saveGeneral(){
  try{
    await put('/settings/general',{timezone:document.getElementById('g-tz').value.trim()});
    toast('✓ 一般設定已儲存',true);
  }catch(e){toast('儲存失敗：'+e.message,false);}
}
async function saveAuth(){
  var cur=document.getElementById('a-cur').value;
  var nw=document.getElementById('a-new').value;
  var conf=document.getElementById('a-conf').value;
  if(!cur||!nw||!conf){toast('請填寫所有欄位',false);return;}
  if(nw!==conf){toast('新密碼與確認密碼不一致',false);return;}
  if(nw.length<8){toast('密碼長度至少 8 個字元',false);return;}
  try{
    await put('/settings/auth',{current_password:cur,new_password:nw});
    document.getElementById('a-cur').value='';
    document.getElementById('a-new').value='';
    document.getElementById('a-conf').value='';
    toast('✓ 密碼已更新',true);
  }catch(e){toast('更改失敗：'+e.message,false);}
}

loadCfg();
initMap();
</script>
</body>
</html>"""


_LOGIN_HTML = r"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>登入 — ePaper Home Display</title>
  <style>
    *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
    :root{
      --bg:#0f172a;--surface:#1e293b;--border:#334155;
      --primary:#3b82f6;--primary-h:#2563eb;--text:#e2e8f0;--muted:#64748b;
      --err-bg:rgba(153,27,27,.15);--err-border:#991b1b;--r:10px
    }
    body{background:var(--bg);color:var(--text);min-height:100vh;display:flex;align-items:center;justify-content:center;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}
    .card{background:var(--surface);border:1px solid var(--border);border-radius:var(--r);padding:2rem;width:100%;max-width:360px;box-shadow:0 4px 24px rgba(0,0,0,.4)}
    .logo{text-align:center;font-size:2rem;margin-bottom:.4rem}
    .title{text-align:center;font-size:1.05rem;font-weight:600;margin-bottom:.25rem}
    .sub{text-align:center;font-size:.78rem;color:var(--muted);margin-bottom:1.5rem}
    .err{background:var(--err-bg);border:1px solid var(--err-border);color:#fca5a5;border-radius:6px;padding:.55rem .9rem;font-size:.82rem;margin-bottom:1rem}
    label{display:block;font-size:.78rem;font-weight:500;margin-bottom:.3rem}
    input[type=password]{width:100%;padding:.55rem .75rem;border:1px solid var(--border);border-radius:6px;font-size:.9rem;color:var(--text);background:#0f172a;outline:none;transition:border-color .15s,box-shadow .15s}
    input[type=password]:focus{border-color:var(--primary);box-shadow:0 0 0 3px rgba(59,130,246,.15)}
    .f{margin-bottom:.9rem}
    button{width:100%;padding:.6rem;background:var(--primary);color:#fff;border:none;border-radius:6px;font-size:.9rem;font-weight:500;cursor:pointer;margin-top:.5rem;transition:background .15s}
    button:hover{background:var(--primary-h)}
  </style>
</head>
<body>
<div class="card">
  <div class="logo">🖥️</div>
  <div class="title">ePaper Home Display</div>
  <div class="sub">__SUBTITLE__</div>
  __ERROR_HTML__
  <form method="post" action="/login">
    <input type="hidden" name="next" value="__NEXT__">
    <div class="f">
      <label>密碼</label>
      <input type="password" name="password" required autofocus placeholder="輸入密碼">
    </div>
    __CONFIRM_FIELD__
    <button type="submit">__BUTTON__</button>
  </form>
</div>
</body>
</html>"""


def _render_login(next_url: str = "/settings", error: str = "", is_setup: bool = False) -> str:
    raw_next = next_url if next_url.startswith("/") and not next_url.startswith("//") else "/settings"
    safe_next = _html.escape(raw_next, quote=True)
    subtitle = "首次設定 — 請設定登入密碼" if is_setup else "請輸入密碼以登入"
    button = "設定密碼" if is_setup else "登入"
    error_html = f'<div class="err">{_html.escape(error)}</div>' if error else ""
    confirm_field = (
        '<div class="f"><label>確認密碼</label>'
        '<input type="password" name="password_confirm" required placeholder="再次輸入密碼"></div>'
        if is_setup else ""
    )
    return (
        _LOGIN_HTML
        .replace("__SUBTITLE__", subtitle)
        .replace("__BUTTON__", button)
        .replace("__ERROR_HTML__", error_html)
        .replace("__CONFIRM_FIELD__", confirm_field)
        .replace("__NEXT__", safe_next)
    )


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
    full_refresh_every: int | None = None


class _PresenceBody(BaseModel):
    bright_threshold: int | None = None


class _VoiceBody(BaseModel):
    enabled: bool | None = None
    player: str | None = None


class _NotificationsBody(BaseModel):
    discord_webhook_url: str | None = None
    notify_device_online: bool | None = None
    notify_session_end: bool | None = None
    session_end_min_minutes: int | None = None
    notify_daily_summary: bool | None = None
    daily_summary_time: str | None = None


class _GeneralBody(BaseModel):
    timezone: str | None = None


class _AuthBody(BaseModel):
    current_password: str
    new_password: str


# ── App factory ───────────────────────────────────────────────────────────────

def create_app(settings: "Settings", weather_service: WeatherService) -> FastAPI:
    if not settings.webui.session_secret:
        settings.webui.session_secret = secrets.token_hex(32)
        _save_to_config({"webui": {"session_secret": settings.webui.session_secret}})

    app = FastAPI(title="ePaper Home Display", version="0.1.0")
    # SessionMiddleware must be outermost so session is populated before _AuthMiddleware runs
    app.add_middleware(_AuthMiddleware)
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.webui.session_secret,
        max_age=86400 * 7,
        https_only=False,
    )

    # ── Auth ───────────────────────────────────────────────────────────────────

    @app.get("/login", response_class=HTMLResponse)
    async def login_page(next: str = "/settings"):
        is_setup = not bool(settings.webui.password_hash)
        return HTMLResponse(_render_login(next_url=next, is_setup=is_setup))

    @app.post("/login", response_class=HTMLResponse)
    async def login_post(
        request: Request,
        password: str = Form(...),
        password_confirm: str = Form(""),
        next: str = Form("/settings"),
    ):
        is_setup = not bool(settings.webui.password_hash)
        safe_next = next if next.startswith("/") and not next.startswith("//") else "/settings"

        if is_setup:
            if len(password) < 8:
                return HTMLResponse(
                    _render_login(safe_next, "密碼長度至少 8 個字元", is_setup=True), status_code=400
                )
            if password != password_confirm:
                return HTMLResponse(
                    _render_login(safe_next, "兩次密碼不一致", is_setup=True), status_code=400
                )
            new_hash = _pwd_ctx.hash(password)
            # Double-check under lock: another request may have set the password concurrently
            if settings.webui.password_hash:
                is_setup = False
            else:
                _save_to_config({"webui": {"password_hash": new_hash}})
                settings.webui.password_hash = new_hash
                request.session["authenticated"] = True
                return RedirectResponse(url=safe_next, status_code=302)

        if not _pwd_ctx.verify(password, settings.webui.password_hash):
            return HTMLResponse(
                _render_login(safe_next, "密碼錯誤", is_setup=False), status_code=401
            )
        request.session["authenticated"] = True
        return RedirectResponse(url=safe_next, status_code=302)

    @app.get("/logout")
    async def logout(request: Request):
        request.session.clear()
        return RedirectResponse(url="/login", status_code=302)

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
        if "full_refresh_every" in patch and not (1 <= patch["full_refresh_every"] <= 100):
            raise HTTPException(400, detail="full_refresh_every must be 1–100")
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
        if "bright_threshold" in patch and not (0 <= patch["bright_threshold"] <= 1023):
            raise HTTPException(400, detail="bright_threshold must be 0–1023")
        if not patch:
            return {"ok": True}

        try:
            _save_to_config({"sensors": {"light": patch}})
        except Exception as exc:
            logger.error("Failed to persist presence settings: %s", exc)
            raise HTTPException(500, detail="Failed to persist settings")

        for k, v in patch.items():
            setattr(settings.sensors.light, k, v)
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
        if "session_end_min_minutes" in patch and not (1 <= patch["session_end_min_minutes"] <= 60):
            raise HTTPException(400, detail="session_end_min_minutes must be 1–60")
        if "daily_summary_time" in patch:
            t = patch["daily_summary_time"]
            m = re.match(r"^(\d{2}):(\d{2})$", t)
            if not m or not (0 <= int(m.group(1)) <= 23) or not (0 <= int(m.group(2)) <= 59):
                raise HTTPException(400, detail="daily_summary_time must be HH:MM (00:00–23:59)")

        discord_patch: dict = {}
        if "discord_webhook_url" in patch:
            discord_patch["webhook_url"] = patch["discord_webhook_url"]
        for key in (
            "notify_device_online", "notify_session_end", "session_end_min_minutes",
            "notify_daily_summary", "daily_summary_time",
        ):
            if key in patch:
                discord_patch[key] = patch[key]

        if not discord_patch:
            return {"ok": True}

        try:
            _save_to_config({"discord": discord_patch})
        except Exception as exc:
            logger.error("Failed to persist notification settings: %s", exc)
            raise HTTPException(500, detail="Failed to persist settings")

        if "webhook_url" in discord_patch:
            settings.discord.webhook_url = discord_patch["webhook_url"]
        for key in (
            "notify_device_online", "notify_session_end", "session_end_min_minutes",
            "notify_daily_summary", "daily_summary_time",
        ):
            if key in discord_patch:
                setattr(settings.discord, key, discord_patch[key])
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

    @app.put("/settings/auth")
    async def set_auth(body: _AuthBody):
        if not settings.webui.password_hash:
            raise HTTPException(400, detail="No password configured. Use the login page for first-time setup.")
        if not _pwd_ctx.verify(body.current_password, settings.webui.password_hash):
            raise HTTPException(403, detail="目前密碼錯誤")
        if len(body.new_password) < 8:
            raise HTTPException(400, detail="密碼長度至少 8 個字元")
        new_hash = _pwd_ctx.hash(body.new_password)
        _save_to_config({"webui": {"password_hash": new_hash}})
        settings.webui.password_hash = new_hash
        return {"ok": True}

    # ── Desk analytics ────────────────────────────────────────────────────────

    @app.get("/desk", response_class=HTMLResponse)
    async def desk_page():
        return HTMLResponse(_DESK_HTML)

    @app.get("/api/desk/stats")
    async def desk_stats():
        from datetime import datetime
        from app.storage.logs import get_sessions_for_date
        now = datetime.now()
        today_sessions = await get_sessions_for_date(now.date())

        today_completed_sec = sum(
            s["duration_seconds"] for s in today_sessions
            if s["duration_seconds"] is not None
        )
        ongoing_sec = 0
        if state.desk_session_start is not None and state.desk_session_start.date() == now.date():
            ongoing_sec = int((now - state.desk_session_start).total_seconds())

        today_count = len([s for s in today_sessions if s["duration_seconds"] is not None])
        if state.desk_session_start is not None and state.desk_session_start.date() == now.date():
            today_count += 1

        current_segment_sec = 0
        last_change_ts = None
        if state.presence == "OCCUPIED" and state.desk_session_start:
            current_segment_sec = int((now - state.desk_session_start).total_seconds())
            last_change_ts = state.desk_session_start.isoformat()
        elif state.presence == "UNOCCUPIED":
            completed = [s for s in today_sessions if s["end_ts"] is not None]
            if completed:
                last_end = max(s["end_ts"] for s in completed)
                try:
                    from datetime import datetime as _dt
                    last_end_dt = _dt.fromisoformat(last_end)
                    current_segment_sec = int((now - last_end_dt).total_seconds())
                    last_change_ts = last_end
                except ValueError:
                    pass

        return {
            "presence": state.presence,
            "light_raw": state.light_raw,
            "threshold": settings.sensors.light.bright_threshold,
            "today_total_seconds": today_completed_sec + ongoing_sec,
            "today_session_count": today_count,
            "current_segment_seconds": current_segment_sec,
            "session_start_ts": state.desk_session_start.isoformat() if state.desk_session_start else None,
            "last_change_ts": last_change_ts,
        }

    @app.get("/api/desk/history")
    async def desk_history():
        from datetime import datetime, timedelta
        from collections import defaultdict
        from app.storage.logs import get_sessions_last_n_days

        now = datetime.now()
        all_sessions = await get_sessions_last_n_days(30)

        # 24h timeline: include sessions that OVERLAP the last 24 hours
        # (started before cutoff but ended/ongoing within the window)
        cutoff_24h = (now - timedelta(hours=24)).isoformat()
        timeline_24h = [
            s for s in all_sessions
            if (s["end_ts"] is None and s["start_ts"] is not None)
            or (s["end_ts"] is not None and s["end_ts"] >= cutoff_24h)
            or s["start_ts"] >= cutoff_24h
        ]
        # Add current ongoing session if not already included
        if state.desk_session_start is not None and state.desk_session_id is not None:
            existing_ids = {s["id"] for s in timeline_24h}
            if state.desk_session_id not in existing_ids:
                timeline_24h.append({
                    "id": state.desk_session_id,
                    "start_ts": state.desk_session_start.isoformat(),
                    "end_ts": None,
                    "duration_seconds": None,
                })

        # 30-day totals (completed sessions only, plus today's ongoing for consistency)
        daily_totals: dict = defaultdict(int)
        for s in all_sessions:
            if s["duration_seconds"] is not None:
                date_key = s["start_ts"][:10]
                daily_totals[date_key] += s["duration_seconds"]

        # Add today's ongoing session so chart matches /api/desk/stats today total
        if state.desk_session_start is not None and state.desk_session_start.date() == now.date():
            ongoing_sec = int((now - state.desk_session_start).total_seconds())
            daily_totals[now.date().isoformat()] += ongoing_sec

        today = now.date()
        daily_30d = []
        for i in range(29, -1, -1):
            d = today - timedelta(days=i)
            date_str = d.isoformat()
            daily_30d.append({"date": date_str, "total_seconds": daily_totals.get(date_str, 0)})

        return {"timeline_24h": timeline_24h, "daily_30d": daily_30d}

    @app.get("/api/desk/sessions")
    async def desk_sessions(limit: int = 20):
        from app.storage.logs import get_recent_sessions
        return {"sessions": await get_recent_sessions(limit)}

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
