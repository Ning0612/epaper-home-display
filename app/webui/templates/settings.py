_SETTINGS_HTML = r"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>ePaper 設定</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,600;9..40,700&family=DM+Mono:wght@400;500&display=swap">
  <style>
    *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
    :root{
      --bg:#080d18;--surface:#0f172a;--surface2:#1a253d;--border:#1e3a5f;
      --primary:#38bdf8;--primary-h:#0ea5e9;
      --text:#e2e8f0;--muted:#64748b;
      --r:8px;--sh:0 2px 12px rgba(0,0,0,.4)
    }
    body{font-family:'DM Sans',system-ui,sans-serif;background:var(--bg);color:var(--text);display:flex;min-height:100vh}
    .sb{width:210px;background:var(--surface);border-right:1px solid var(--border);padding:1.25rem 0;position:sticky;top:0;height:100vh;overflow-y:auto;flex-shrink:0;display:flex;flex-direction:column}
    .sb-foot{margin-top:auto;padding:.75rem 1rem;border-top:1px solid var(--border)}
    .sb-foot a{display:flex;align-items:center;gap:.5rem;font-size:.83rem;color:var(--primary);text-decoration:none;padding:.4rem .5rem;border-radius:6px;transition:background .15s}
    .sb-foot a:hover{background:rgba(56,189,248,.08)}
    .sb-title{font-size:.7rem;font-weight:700;text-transform:uppercase;letter-spacing:.1em;color:var(--muted);padding:0 1rem .6rem}
    .nav{display:flex;align-items:center;gap:.5rem;padding:.5rem 1rem;cursor:pointer;font-size:.85rem;color:var(--muted);border-left:3px solid transparent;transition:all .15s;user-select:none}
    .nav:hover{background:var(--surface2);color:var(--text)}
    .nav.active{color:var(--primary);border-left-color:var(--primary);background:rgba(56,189,248,.08);font-weight:500}
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
      font-size:.85rem;color:var(--text);background:var(--bg);
      transition:border-color .15s,box-shadow .15s;outline:none
    }
    input:focus,select:focus{border-color:var(--primary);box-shadow:0 0 0 3px rgba(56,189,248,.15)}
    select option{background:var(--surface);color:var(--text)}
    :root{color-scheme:dark}
    .row2{display:flex;gap:.65rem}.row2 .f{flex:1;margin-bottom:0}
    .tog-row{display:flex;align-items:center;justify-content:space-between;padding:.5rem 0}
    .tog-lbl{font-size:.875rem;font-weight:500}
    .tog-desc{font-size:.73rem;color:var(--muted);margin-top:.1rem}
    .sw{position:relative;width:40px;height:22px;flex-shrink:0}
    .sw input{opacity:0;width:0;height:0}
    .sl{position:absolute;inset:0;background:var(--border);border-radius:22px;cursor:pointer;transition:.2s}
    .sl::before{content:'';position:absolute;width:16px;height:16px;left:3px;top:3px;background:#94a3b8;border-radius:50%;transition:.2s;box-shadow:0 1px 3px rgba(0,0,0,.4)}
    input:checked+.sl{background:var(--primary)}
    input:checked+.sl::before{transform:translateX(18px);background:#fff}
    #map{height:300px;border-radius:6px;border:1px solid var(--border);margin-top:.4rem}
    #map .leaflet-tile-pane{filter:invert(100%) hue-rotate(180deg) brightness(90%)}
    .coord{display:flex;gap:1rem;margin-top:.6rem;font-size:.83rem;color:var(--muted)}
    .coord b{color:var(--text)}
    .btn-row{display:flex;justify-content:flex-end;margin-top:1.1rem}
    button{padding:.45rem 1.2rem;border:none;border-radius:6px;font-size:.83rem;font-weight:500;cursor:pointer;transition:background .15s}
    .btn-p{background:var(--primary);color:#080d18}
    .btn-p:hover{background:var(--primary-h)}
    .info{display:grid;grid-template-columns:auto 1fr;gap:.4rem .9rem;font-size:.85rem}
    .ik{color:var(--muted);font-weight:500}.iv{font-family:'DM Mono',monospace;color:var(--text)}
    pre{background:var(--surface2);padding:.7rem;border-radius:6px;font-size:.75rem;overflow-x:auto;color:var(--muted);line-height:1.5;font-family:'DM Mono',monospace}
    hr{border:none;border-top:1px solid var(--border);margin:.9rem 0}
    #toast{position:fixed;bottom:1.5rem;right:1.5rem;padding:.65rem 1.1rem;border-radius:var(--r);font-size:.83rem;font-weight:500;box-shadow:0 4px 12px rgba(0,0,0,.4);opacity:0;transform:translateY(.4rem);transition:opacity .22s,transform .22s;pointer-events:none;z-index:9999}
    #toast.show{opacity:1;transform:none}
    #toast.ok{background:#0a2e1a;color:#34d399;border:1px solid rgba(52,211,153,.3)}
    #toast.err{background:#2e0a0a;color:#f87171;border:1px solid rgba(248,113,113,.3)}
    @media(max-width:600px){
      body{flex-direction:column}
      .sb{width:100%;height:auto;position:static;display:flex;flex-wrap:wrap;gap:.2rem;padding:.6rem;border-right:none;border-bottom:1px solid var(--border)}
      .sb-title{display:none}
      .nav{border-left:none;border-radius:6px;padding:.35rem .65rem}
      .nav.active{background:rgba(56,189,248,.15);color:var(--primary);border-left:none}
      .sb-foot{margin-top:0;padding:0;border-top:none}
      .sb-foot a{padding:.35rem .65rem;font-size:.83rem}
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
  <div class="sb-foot">
    <a href="/desk"><span class="ni">📖</span>書桌前分析</a>
  </div>
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
      <a href="/desk" style="display:inline-block;padding:.45rem 1.2rem;background:var(--primary);color:#080d18;border-radius:6px;font-size:.83rem;font-weight:600;text-decoration:none">開啟 Dashboard →</a>
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
