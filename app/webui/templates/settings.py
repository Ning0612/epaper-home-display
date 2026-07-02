from app.webui.templates.base import _make_shell

_SETTINGS_EXTRA_HEAD = r"""<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>"""

_SETTINGS_CONTENT = r"""
<style>
  .acc{max-width:700px;margin:0 auto;padding:1.5rem 1rem}
  .acc-item{border:1px solid var(--border);border-radius:8px;margin-bottom:.5rem;overflow:hidden}
  .acc-head{
    display:flex;align-items:center;gap:.55rem;padding:.72rem 1rem;
    cursor:pointer;user-select:none;background:var(--surface);
    font-size:.9rem;font-weight:500;color:var(--text);transition:background .15s;
  }
  .acc-head:hover{background:var(--surface2)}
  .acc-ic{width:1.3rem;text-align:center;font-size:1rem}
  .acc-chev{margin-left:auto;font-size:.7rem;color:var(--muted);transition:transform .2s;line-height:1}
  .acc-item.open>.acc-head>.acc-chev{transform:rotate(180deg)}
  .acc-body{display:none;padding:.75rem 1rem 1rem;border-top:1px solid var(--border)}
  .acc-item.open>.acc-body{display:block}
  .c-sub{font-size:.68rem;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);margin-bottom:.9rem}
  #map{height:300px;border-radius:6px;border:1px solid var(--border);margin-top:.4rem}
  #map .leaflet-tile-pane{filter:invert(100%) hue-rotate(180deg) brightness(90%)}
  .coord{display:flex;gap:1rem;margin-top:.6rem;font-size:.83rem;color:var(--muted)}
  .coord b{color:var(--text)}
  .info{display:grid;grid-template-columns:auto 1fr;gap:.4rem .9rem;font-size:.85rem}
  .ik{color:var(--muted);font-weight:500}
  .iv{font-family:'JetBrains Mono',monospace;color:var(--text)}
  pre{background:var(--surface2);padding:.7rem;border-radius:6px;font-size:.75rem;overflow-x:auto;color:var(--muted);line-height:1.5;font-family:'JetBrains Mono',monospace}
  hr{border:none;border-top:1px solid var(--border);margin:.9rem 0}
  @media(max-width:600px){.acc{padding:1rem .5rem}}
</style>

<div class="acc">

  <div class="acc-item open" id="acc-weather">
    <div class="acc-head" onclick="toggle('weather')">
      <span class="acc-ic">☁️</span>天氣設定
      <span class="acc-chev">▾</span>
    </div>
    <div class="acc-body">
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
  </div>

  <div class="acc-item" id="acc-display">
    <div class="acc-head" onclick="toggle('display')">
      <span class="acc-ic">🖥️</span>顯示器設定
      <span class="acc-chev">▾</span>
    </div>
    <div class="acc-body">
      <div class="card">
        <div class="f">
          <label>e-Paper 型號</label>
          <select id="d-model" onchange="applyModelPreset(this.value)">
            <option value="epd7in3e">Waveshare 7.3" 7-color (epd7in3e)</option>
            <option value="epd7in5_V2">Waveshare 7.5" B&W (epd7in5_V2)</option>
            <option value="mock">Mock（測試用）</option>
          </select>
        </div>
        <hr>
        <div class="f">
          <label>刷新間隔 <span class="hint">（分鐘，須為 60 的因數）</span></label>
          <select id="d-interval">
            <option value="1">1 分鐘</option>
            <option value="2">2 分鐘</option>
            <option value="3">3 分鐘</option>
            <option value="4">4 分鐘</option>
            <option value="5">5 分鐘</option>
            <option value="6">6 分鐘</option>
            <option value="10">10 分鐘</option>
            <option value="12">12 分鐘</option>
            <option value="15">15 分鐘</option>
            <option value="20">20 分鐘</option>
            <option value="30">30 分鐘</option>
            <option value="60">60 分鐘</option>
          </select>
        </div>
        <div id="d-fre-row" class="f" style="margin-top:.9rem">
          <label>全刷新間隔 <span class="hint">（次數，1–100；每 N 次做一次全刷新清除鬼影）</span></label>
          <input type="number" id="d-fre" min="1" max="100">
        </div>
        <div class="btn-row"><button class="btn-p" onclick="saveDisplay()">儲存</button></div>
      </div>
    </div>
  </div>

  <div class="acc-item" id="acc-presence">
    <div class="acc-head" onclick="toggle('presence')">
      <span class="acc-ic">💡</span>在場偵測
      <span class="acc-chev">▾</span>
    </div>
    <div class="acc-body">
      <div class="card">
        <div class="c-sub" style="display:flex;align-items:center;justify-content:space-between">
          即時光線讀值
          <span id="lp-dot" style="width:8px;height:8px;border-radius:50%;background:var(--muted);display:inline-block;transition:background .3s"></span>
        </div>
        <div style="display:flex;align-items:baseline;gap:.5rem;margin-bottom:.7rem">
          <span id="lp-val" style="font-size:2rem;font-weight:700;font-family:'JetBrains Mono',monospace;color:var(--text);min-width:3.5ch">—</span>
          <span style="font-size:.78rem;color:var(--muted)">/1023</span>
          <span style="font-size:.78rem;color:var(--muted)">≈ <span id="lp-lux">—</span> lux</span>
          <span style="margin-left:auto">
            <span id="lp-badge" style="font-size:.78rem;font-weight:600;padding:.18rem .65rem;border-radius:999px;background:var(--surface2);color:var(--muted)">—</span>
          </span>
        </div>
        <div style="position:relative;height:10px;background:var(--surface2);border-radius:5px;margin-bottom:.35rem">
          <div id="lp-bar" style="height:100%;border-radius:5px;width:0%;transition:width .4s,background .3s;max-width:100%"></div>
          <div id="lp-thresh-line" style="position:absolute;top:-5px;bottom:-5px;width:2px;background:#f59e0b;border-radius:2px;left:49%;transform:translateX(-50%)">
            <span style="position:absolute;top:-17px;left:50%;transform:translateX(-50%);font-size:.6rem;white-space:nowrap;color:#f59e0b;font-weight:700">閾值</span>
          </div>
        </div>
        <div style="font-size:.7rem;color:var(--muted);display:flex;justify-content:space-between;margin-bottom:.2rem">
          <span>0 暗</span><span>1023 亮</span>
        </div>
      </div>
      <div class="card">
        <div class="f">
          <label>光線閾值 <span class="hint">（0–1023，ADC 原始值，低於此值判定為在場）</span></label>
          <input type="number" id="p-bright" min="0" max="1023" oninput="updThresh(this.value)">
        </div>
        <div class="btn-row"><button class="btn-p" onclick="savePresence()">儲存</button></div>
      </div>
    </div>
  </div>

  <div class="acc-item" id="acc-voice">
    <div class="acc-head" onclick="toggle('voice')">
      <span class="acc-ic">🔊</span>語音設定
      <span class="acc-chev">▾</span>
    </div>
    <div class="acc-body">
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
        <hr>
        <div class="c-sub">音量</div>
        <div class="f">
          <label>播放音量 <span class="hint">（0–100，目前：<b id="v-vol-val">80</b>）</span></label>
          <input type="range" id="v-vol" min="0" max="100" step="5"
                 oninput="document.getElementById('v-vol-val').textContent=this.value"
                 style="width:100%;accent-color:var(--primary)">
        </div>
        <div class="f">
          <label>ALSA Mixer 控制項 <span class="hint">（如 PCM / Master；留空則跳過音量設定）</span></label>
          <input type="text" id="v-alsa" placeholder="PCM" style="max-width:160px">
        </div>
        <div class="btn-row" style="margin-top:.6rem;margin-bottom:0;justify-content:flex-start;align-items:center;gap:.75rem">
          <button class="btn-s" id="v-test-btn" onclick="testVoice()">▶ 測試語音</button>
          <span id="v-test-status" style="font-size:.8rem;color:var(--muted)"></span>
        </div>
        <hr>
        <div class="c-sub">開門天氣提醒（TTS）</div>
        <div class="row2">
          <div class="f">
            <label>TTS 引擎</label>
            <select id="v-tts-engine" onchange="onTtsEngineChange(this.value)">
              <option value="espeak-ng">eSpeak NG</option>
              <option value="none">停用 TTS</option>
            </select>
          </div>
          <div class="f" id="v-tts-lang-row">
            <label>語音語言 <span class="hint">（espeak-ng voice，如 zh / zh-TW）</span></label>
            <input type="text" id="v-tts-lang" placeholder="zh" style="max-width:140px">
          </div>
        </div>
        <div class="f" id="v-tts-speed-row">
          <label>語速 <span class="hint">（50–500 words/min，預設 130）</span></label>
          <input type="number" id="v-tts-speed" min="50" max="500" step="10" style="max-width:140px">
        </div>
        <div class="btn-row"><button class="btn-p" onclick="saveVoice()">儲存</button></div>
      </div>
    </div>
  </div>

  <div class="acc-item" id="acc-notif">
    <div class="acc-head" onclick="toggle('notif')">
      <span class="acc-ic">💬</span>通知設定
      <span class="acc-chev">▾</span>
    </div>
    <div class="acc-body">
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
    </div>
  </div>

  <div class="acc-item" id="acc-mqtt">
    <div class="acc-head" onclick="toggle('mqtt')">
      <span class="acc-ic">📡</span>HydraCup MQTT 設定
      <span class="acc-chev">▾</span>
    </div>
    <div class="acc-body">
      <div class="card" id="mqtt-status-card">
        <div class="info">
          <div class="ik">Broker 連線</div><div class="iv" id="mq-st-broker">—</div>
          <div class="ik">HydraCup 裝置</div><div class="iv" id="mq-st-device">—</div>
          <div class="ik">最後更新</div><div class="iv" id="mq-st-updated">—</div>
        </div>
      </div>
      <div class="card">
        <div class="row2">
          <div class="f">
            <label>Broker Host</label>
            <input type="text" id="mq-host" placeholder="localhost">
          </div>
          <div class="f">
            <label>Broker Port</label>
            <input type="number" id="mq-port" min="1" max="65535">
          </div>
        </div>
        <div class="f">
          <label>Client ID</label>
          <input type="text" id="mq-cid" placeholder="epaper-home-display">
        </div>
        <div class="row2">
          <div class="f">
            <label>Username</label>
            <input type="text" id="mq-user" placeholder="">
          </div>
          <div class="f">
            <label>Password</label>
            <input type="password" id="mq-pass" placeholder="重新輸入以更新">
          </div>
        </div>
        <div class="f">
          <label>心跳逾時秒數 <span class="hint">距離上次收到 HydraCup 資料超過此秒數視為過期</span></label>
          <input type="number" id="mq-heartbeat" min="10" max="3600">
        </div>
        <div class="btn-row"><button class="btn-p" onclick="saveMqtt()">儲存</button></div>
      </div>
    </div>
  </div>

  <div class="acc-item" id="acc-printer">
    <div class="acc-head" onclick="toggle('printer')">
      <span class="acc-ic">🖨️</span>Bambu 印表機設定
      <span class="acc-chev">⌄</span>
    </div>
    <div class="acc-body">
      <div class="card" id="printer-status-card">
        <div class="info">
          <div class="ik">連線狀態</div><div class="iv" id="pr-st-broker">--</div>
          <div class="ik">列印狀態</div><div class="iv" id="pr-st-state">--</div>
          <div class="ik">最後更新</div><div class="iv" id="pr-st-updated">--</div>
        </div>
      </div>
      <div class="card">
        <div class="row2">
          <div class="f">
            <label>Host</label>
            <input type="text" id="pr-host" placeholder="留空停用">
          </div>
          <div class="f">
            <label>Port</label>
            <input type="number" id="pr-port" min="1" max="65535">
          </div>
        </div>
        <div class="f">
          <label>Serial</label>
          <input type="text" id="pr-serial" placeholder="印表機序號">
        </div>
        <div class="f">
          <label>Access Code</label>
          <input type="password" id="pr-code" placeholder="重新輸入以更新">
        </div>
        <div class="btn-row"><button class="btn-p" onclick="savePrinter()">儲存</button></div>
      </div>
    </div>
  </div>

  <div class="acc-item" id="acc-general">
    <div class="acc-head" onclick="toggle('general')">
      <span class="acc-ic">⚙️</span>一般設定
      <span class="acc-chev">▾</span>
    </div>
    <div class="acc-body">
      <div class="card">
        <div class="f">
          <label>時區 <span class="hint">（例：Asia/Taipei）</span></label>
          <input type="text" id="g-tz" placeholder="Asia/Taipei">
        </div>
        <div class="btn-row"><button class="btn-p" onclick="saveGeneral()">儲存</button></div>
      </div>
    </div>
  </div>

  <div class="acc-item" id="acc-wifi">
    <div class="acc-head" onclick="toggle('wifi')">
      <span class="acc-ic">📶</span>WiFi 狀態
      <span class="acc-chev">▾</span>
    </div>
    <div class="acc-body">
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
  </div>

  <div class="acc-item" id="acc-auth">
    <div class="acc-head" onclick="toggle('auth')">
      <span class="acc-ic">🔒</span>帳號安全
      <span class="acc-chev">▾</span>
    </div>
    <div class="acc-body">
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
  </div>

</div>

<script>
var mapLat=__LAT__, mapLon=__LON__;
var lmap=null, lmk=null;
var _presTimer=null;

var MODEL_PRESETS={
  'epd7in3e':   {interval:5, showFre:false},
  'epd7in5_V2': {interval:5, showFre:true},
  'mock':       {interval:5, showFre:true}
};
// Called only when user actively changes the model — resets to preset defaults.
function applyModelPreset(model){
  var p=MODEL_PRESETS[model];
  if(!p) return;
  document.getElementById('d-interval').value=String(p.interval);
  _applyModelVisibility(p);
}
// Called on page load — only updates visibility, preserves existing config values.
function _applyModelVisibility(p){
  document.getElementById('d-fre-row').style.display=p&&p.showFre?'':'none';
}

function toggle(name){
  var item=document.getElementById('acc-'+name);
  var wasOpen=item.classList.contains('open');
  document.querySelectorAll('.acc-item').forEach(function(i){i.classList.remove('open')});
  stopLightPoll();
  if(!wasOpen){
    item.classList.add('open');
    if(name==='weather'){
      if(!lmap) initMap();
      else setTimeout(function(){lmap.invalidateSize();},50);
    }
    if(name==='wifi') loadWifi();
    if(name==='mqtt') loadMqttStatus();
    if(name==='printer') loadPrinterStatus();
    if(name==='presence') startLightPoll();
  }
}

function updThresh(v){
  var pct=(Math.min(Math.max(+v||0,0),1023)/1023*100).toFixed(2);
  document.getElementById('lp-thresh-line').style.left=pct+'%';
}

function startLightPoll(){
  stopLightPoll();
  _fetchLight();
  _presTimer=setInterval(_fetchLight,2000);
}

function stopLightPoll(){
  if(_presTimer){clearInterval(_presTimer);_presTimer=null;}
}

async function _fetchLight(){
  try{
    var r=await fetch('/state');
    if(!r.ok){if(r.status===401)stopLightPoll();return;}
    var d=await r.json();
    var raw=d.light_raw;
    var dot=document.getElementById('lp-dot');
    var badge=document.getElementById('lp-badge');
    var _nodata='font-size:.78rem;font-weight:600;padding:.18rem .65rem;border-radius:999px;background:var(--surface2);color:var(--muted)';
    if(raw==null){
      document.getElementById('lp-val').textContent='—';
      document.getElementById('lp-lux').textContent='—';
      document.getElementById('lp-bar').style.width='0%';
      document.getElementById('lp-bar').style.background='var(--muted)';
      dot.style.background='var(--muted)';
      badge.textContent='無資料';badge.style.cssText=_nodata;
      return;
    }
    var dispRaw=Math.min(Math.max(raw,0),1023);
    var inp=document.getElementById('p-bright');
    var thresh=inp.value!==''?+inp.value:500;
    var bright=typeof d.light_is_bright==='boolean'?d.light_is_bright:dispRaw>=thresh;
    document.getElementById('lp-val').textContent=raw;
    document.getElementById('lp-lux').textContent=(dispRaw*0.098).toFixed(1);
    document.getElementById('lp-bar').style.width=(dispRaw/1023*100).toFixed(2)+'%';
    document.getElementById('lp-bar').style.background=bright?'var(--muted)':'var(--primary)';
    document.getElementById('lp-thresh-line').style.left=(thresh/1023*100).toFixed(2)+'%';
    if(!bright){
      dot.style.background='#22c55e';
      badge.textContent='亮燈（在場）';
      badge.style.cssText='font-size:.78rem;font-weight:600;padding:.18rem .65rem;border-radius:999px;background:rgba(34,197,94,.15);color:#16a34a';
    }else{
      dot.style.background='var(--muted)';
      badge.textContent='暗燈（離場）';
      badge.style.cssText=_nodata;
    }
  }catch(e){console.error('light poll',e);}
}

function toast(msg,ok){
  var t=document.getElementById('toast');
  t.textContent=msg; t.className='show '+(ok?'ok':'err');
  clearTimeout(t._t); t._t=setTimeout(function(){t.className=''},3000);
}

function initMap(){
  if(typeof L==='undefined'){
    var el=document.getElementById('map');
    if(el) el.innerHTML='<p style="padding:1rem;color:var(--muted);font-size:.85rem">⚠️ 地圖無法載入（需要網路連線）</p>';
    return;
  }
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
    document.getElementById('w-key').placeholder=w.api_key_set?'（已設定，重新輸入以更新）':'輸入 API Key';
    document.getElementById('w-units').value=w.units||'metric';
    document.getElementById('w-interval').value=w.fetch_interval_seconds??600;
    if(w.lat!=null && w.lon!=null){
      mapLat=w.lat; mapLon=w.lon;
      document.getElementById('v-lat').textContent=mapLat;
      document.getElementById('v-lon').textContent=mapLon;
      if(lmap && lmk){lmap.setView([mapLat,mapLon]);lmk.setLatLng([mapLat,mapLon]);}
    }
    var d=c.display||{};
    document.getElementById('d-model').value=d.model||'epd7in3e';
    document.getElementById('d-interval').value=String(d.dashboard_interval_minutes??5);
    document.getElementById('d-fre').value=d.full_refresh_every??10;
    _applyModelVisibility(MODEL_PRESETS[d.model||'epd7in3e']);
    var sl=(c.sensors||{}).light||{};
    document.getElementById('p-bright').value=sl.bright_threshold??500;
    var v=c.voice||{};
    document.getElementById('v-en').checked=v.enabled!==false;
    document.getElementById('v-player').value=v.player||'aplay';
    var vol=v.volume!=null?v.volume:80;
    document.getElementById('v-vol').value=vol;
    document.getElementById('v-vol-val').textContent=vol;
    document.getElementById('v-alsa').value=v.alsa_mixer_control!=null?v.alsa_mixer_control:'PCM';
    var eng=v.tts_engine||'espeak-ng';
    document.getElementById('v-tts-engine').value=eng;
    document.getElementById('v-tts-lang').value=v.tts_language||'zh';
    document.getElementById('v-tts-speed').value=v.tts_speed??130;
    onTtsEngineChange(eng);
    var dc=c.discord||{};
    document.getElementById('n-discord').placeholder=dc.webhook_set?'（已設定，重新輸入以更新）':'https://discord.com/api/webhooks/...';
    document.getElementById('n-online').checked=dc.notify_device_online!==false;
    document.getElementById('n-session').checked=dc.notify_session_end!==false;
    document.getElementById('n-min').value=dc.session_end_min_minutes??5;
    document.getElementById('n-daily').checked=dc.notify_daily_summary!==false;
    document.getElementById('n-time').value=dc.daily_summary_time||'23:00';
    var mq=c.mqtt||{};
    document.getElementById('mq-host').value=mq.broker_host||'localhost';
    document.getElementById('mq-port').value=mq.broker_port??1883;
    document.getElementById('mq-cid').value=mq.client_id||'epaper-home-display';
    document.getElementById('mq-user').value=mq.username||'';
    document.getElementById('mq-pass').placeholder=mq.password_set?'已設定，重新輸入以更新':'重新輸入以更新';
    document.getElementById('mq-heartbeat').value=mq.heartbeat_timeout_sec??180;
    var pr=c.printer||{};
    document.getElementById('pr-host').value=pr.host||'';
    document.getElementById('pr-port').value=pr.port??8883;
    document.getElementById('pr-serial').value=pr.serial||'';
    document.getElementById('pr-code').placeholder=pr.access_code_set?'已設定，重新輸入以更新':'重新輸入以更新';
    document.getElementById('g-tz').value=c.timezone||'Asia/Taipei';
  }catch(e){console.error('loadCfg',e)}
}

function escHtml(s){
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

async function loadWifi(){
  var card=document.getElementById('wifi-card');
  try{
    var r=await fetch('/settings/wifi');
    var d=await r.json();
    var rows=Object.entries(d).map(function(kv){
      return '<div class="ik">'+escHtml(kv[0])+'</div><div class="iv">'+(kv[1]?escHtml(kv[1]):'—')+'</div>';
    }).join('');
    card.innerHTML='<div class="info">'+rows+'</div>';
  }catch(e){
    card.innerHTML='<div style="color:var(--muted);font-size:.85rem">無法取得 WiFi 資訊</div>';
  }
}

async function loadMqttStatus(){
  try{
    var r=await fetch('/state');
    if(!r.ok) throw new Error('HTTP '+r.status);
    var d=await r.json();
    document.getElementById('mq-st-broker').textContent=d.hydra_broker_connected?'已連線':'未連線';
    document.getElementById('mq-st-device').textContent=d.hydra_device_online?'上線':'離線';
    document.getElementById('mq-st-updated').textContent=d.hydra_updated_at||'—';
  }catch(e){
    document.getElementById('mq-st-broker').textContent='無法取得';
    document.getElementById('mq-st-device').textContent='無法取得';
    document.getElementById('mq-st-updated').textContent='無法取得';
  }
}

async function loadPrinterStatus(){
  try{
    var r=await fetch('/state');
    if(!r.ok) throw new Error('HTTP '+r.status);
    var d=await r.json();
    document.getElementById('pr-st-broker').textContent=d.printer_broker_connected?'已連線':'未連線';
    document.getElementById('pr-st-state').textContent=d.printer_gcode_state||'--';
    document.getElementById('pr-st-updated').textContent=d.printer_updated_at||'--';
  }catch(e){
    document.getElementById('pr-st-broker').textContent='讀取失敗';
    document.getElementById('pr-st-state').textContent='讀取失敗';
    document.getElementById('pr-st-updated').textContent='讀取失敗';
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
    var key=document.getElementById('w-key').value.trim();
    if(key) body.api_key=key;
    await put('/settings/weather',body);
    document.getElementById('w-key').value='';
    document.getElementById('w-key').placeholder='（已設定，重新輸入以更新）';
    toast('✓ 天氣設定已儲存',true);
  }catch(e){toast('儲存失敗：'+e.message,false);}
}
async function saveDisplay(){
  try{
    await put('/settings/display',{
      model:document.getElementById('d-model').value,
      dashboard_interval_minutes:+document.getElementById('d-interval').value,
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
function onTtsEngineChange(val){
  var hide=val==='none';
  document.getElementById('v-tts-lang-row').style.display=hide?'none':'';
  document.getElementById('v-tts-speed-row').style.display=hide?'none':'';
}
async function testVoice(){
  var btn=document.getElementById('v-test-btn');
  var status=document.getElementById('v-test-status');
  btn.disabled=true;
  status.textContent='播放中...';
  try{
    var eng=document.getElementById('v-tts-engine').value;
    var body={
      volume:+document.getElementById('v-vol').value,
      alsa_mixer_control:document.getElementById('v-alsa').value.trim(),
      tts_engine:eng
    };
    if(eng!=='none'){
      body.tts_language=document.getElementById('v-tts-lang').value.trim();
      body.tts_speed=+document.getElementById('v-tts-speed').value;
    }
    var r=await fetch('/settings/voice/test',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    if(!r.ok) throw new Error('HTTP '+r.status);
    status.textContent='已送出測試';
    setTimeout(function(){status.textContent='';},4000);
  }catch(e){
    status.textContent='失敗：'+e.message;
  }finally{
    btn.disabled=false;
  }
}
async function saveVoice(){
  try{
    var eng=document.getElementById('v-tts-engine').value;
    var body={
      enabled:document.getElementById('v-en').checked,
      player:document.getElementById('v-player').value.trim(),
      volume:+document.getElementById('v-vol').value,
      alsa_mixer_control:document.getElementById('v-alsa').value.trim(),
      tts_engine:eng
    };
    if(eng!=='none'){
      body.tts_language=document.getElementById('v-tts-lang').value.trim();
      body.tts_speed=+document.getElementById('v-tts-speed').value;
    }
    await put('/settings/voice',body);
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
async function saveMqtt(){
  try{
    var body={
      broker_host:document.getElementById('mq-host').value.trim(),
      broker_port:+document.getElementById('mq-port').value,
      client_id:document.getElementById('mq-cid').value.trim(),
      username:document.getElementById('mq-user').value,
      heartbeat_timeout_sec:+document.getElementById('mq-heartbeat').value
    };
    var pass=document.getElementById('mq-pass').value;
    if(pass!=='') body.password=pass;
    await put('/settings/mqtt',body);
    document.getElementById('mq-pass').value='';
    document.getElementById('mq-pass').placeholder='已設定，重新輸入以更新';
    await loadMqttStatus();
    toast('HydraCup MQTT 設定已儲存',true);
  }catch(e){toast('儲存失敗：'+e.message,false);}
}
async function savePrinter(){
  try{
    var body={
      host:document.getElementById('pr-host').value.trim(),
      port:+document.getElementById('pr-port').value,
      serial:document.getElementById('pr-serial').value.trim()
    };
    var code=document.getElementById('pr-code').value;
    if(code!=='') body.access_code=code;
    await put('/settings/printer',body);
    document.getElementById('pr-code').value='';
    document.getElementById('pr-code').placeholder='已設定，重新輸入以更新';
    await loadPrinterStatus();
    toast('Bambu 印表機設定已儲存',true);
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
loadMqttStatus();
loadPrinterStatus();
initMap();
</script>
"""

_SETTINGS_HTML = _make_shell("settings", "系統設定", _SETTINGS_CONTENT, _SETTINGS_EXTRA_HEAD)
