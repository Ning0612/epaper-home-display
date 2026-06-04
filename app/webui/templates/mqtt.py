from app.webui.templates.base import _make_shell

_MQTT_CONTENT = r"""
<style>
  .conn-card{display:flex;align-items:center;gap:1.2rem;padding:1rem 1.4rem;background:var(--surface);border:1px solid var(--border);border-radius:var(--r);margin-bottom:1.2rem;box-shadow:var(--sh)}
  .conn-dot{width:14px;height:14px;border-radius:50%;flex-shrink:0;transition:background .3s}
  .conn-dot.on{background:#34D399;box-shadow:0 0 8px rgba(52,211,153,.6)}
  .conn-dot.off{background:#F87171;box-shadow:0 0 8px rgba(248,113,113,.4)}
  .conn-info{flex:1}
  .conn-status{font-size:1rem;font-weight:700}
  .conn-broker{font-size:.75rem;color:var(--muted);font-family:'JetBrains Mono',monospace;margin-top:.15rem}
  .conn-ts{font-size:.72rem;color:var(--muted);white-space:nowrap}
  .topic-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:.8rem;margin-bottom:1.2rem}
  .topic-card{background:var(--surface);border:1px solid var(--border);border-radius:var(--r);padding:1rem 1.2rem;box-shadow:var(--sh)}
  .topic-head{display:flex;align-items:center;gap:.6rem;margin-bottom:.6rem}
  .topic-icon{font-size:1.1rem;line-height:1;flex-shrink:0}
  .topic-name{font-size:.72rem;font-family:'JetBrains Mono',monospace;color:var(--primary);word-break:break-all}
  .topic-rx-time{font-size:.7rem;color:var(--muted);margin-bottom:.5rem}
  .topic-rx-time.fresh{color:#34D399}
  .topic-rx-time.never{color:var(--muted);font-style:italic}
  .payload-box{background:#060A14;border:1px solid var(--border);border-radius:6px;padding:.65rem .8rem;font-family:'JetBrains Mono',monospace;font-size:.7rem;color:#94c6e8;max-height:160px;overflow-y:auto;white-space:pre-wrap;word-break:break-all;line-height:1.5}
  .log-tabs{display:flex;gap:.5rem;margin-bottom:.7rem}
  .log-tab{padding:.3rem .85rem;border:1px solid var(--border);border-radius:6px;font-size:.78rem;font-weight:600;background:var(--surface2);color:var(--muted);cursor:pointer;transition:all .15s}
  .log-tab.active{background:var(--primary);color:#060A14;border-color:var(--primary)}
  .log-panel{display:none}.log-panel.active{display:block}
  .log-wrap{overflow-x:auto}
  table{width:100%;border-collapse:collapse;font-size:.78rem}
  th{text-align:left;padding:.45rem .7rem;font-size:.68rem;color:var(--muted);font-weight:600;border-bottom:1px solid var(--border);white-space:nowrap}
  td{padding:.45rem .7rem;border-bottom:1px solid rgba(27,40,66,.5);vertical-align:top}
  tr:last-child td{border-bottom:none}
  .td-ts{font-family:'JetBrains Mono',monospace;white-space:nowrap;color:var(--muted);font-size:.7rem}
  .td-topic{font-family:'JetBrains Mono',monospace;color:var(--primary);white-space:nowrap;font-size:.72rem}
  .td-payload{font-family:'JetBrains Mono',monospace;color:#94c6e8;font-size:.7rem;max-width:400px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  .badge-conn{display:inline-block;padding:.15rem .55rem;border-radius:99px;font-size:.72rem;font-weight:600}
  .badge-conn.on{background:rgba(52,211,153,.15);color:#34d399}
  .badge-conn.off{background:rgba(248,113,113,.15);color:#f87171}
  .refresh-ts{font-size:.68rem;color:var(--muted);text-align:right;margin-top:.4rem}
  .empty-log{color:var(--muted);font-size:.82rem;padding:.6rem 0;text-align:center}
  .cam-card{background:var(--surface);border:1px solid var(--border);border-radius:var(--r);padding:1rem 1.2rem;box-shadow:var(--sh);margin-bottom:1.2rem}
  .cam-head{display:flex;align-items:center;gap:.6rem;margin-bottom:.75rem}
  .cam-title{font-size:.72rem;font-family:'JetBrains Mono',monospace;color:var(--primary)}
  .cam-badge{font-size:.68rem;padding:.1rem .5rem;border-radius:99px;font-weight:600;margin-left:auto}
  .cam-badge.live{background:rgba(52,211,153,.15);color:#34d399}
  .cam-badge.offline{background:rgba(100,116,139,.12);color:var(--muted)}
  .cam-frame{position:relative;width:100%;max-width:480px;background:#060A14;border-radius:6px;overflow:hidden;aspect-ratio:4/3}
  .cam-frame img{width:100%;height:100%;object-fit:contain;display:block}
  .cam-no-signal{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;color:var(--muted);font-size:.82rem;gap:.4rem}
  .cam-ts{font-size:.68rem;color:var(--muted);margin-top:.5rem;font-family:'JetBrains Mono',monospace}
</style>

<div class="page-wrap">
  <div class="page-title">📡 MQTT 監控</div>

  <!-- Connection status -->
  <div class="conn-card">
    <div class="conn-dot off" id="conn-dot"></div>
    <div class="conn-info">
      <div class="conn-status" id="conn-status">連線中…</div>
      <div class="conn-broker" id="conn-broker">broker: —</div>
    </div>
    <div class="conn-ts" id="conn-ts"></div>
  </div>

  <!-- Subscribed topic cards -->
  <div class="card-title" style="margin-bottom:.6rem;font-size:.68rem;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:var(--muted)">訂閱 Topics</div>
  <div class="topic-grid" id="topic-grid">
    <div class="topic-card" id="card-door">
      <div class="topic-head"><span class="topic-icon">🚪</span><span class="topic-name">home/security/door</span></div>
      <div class="topic-rx-time never" id="time-door">從未接收</div>
      <div class="payload-box" id="payload-door">—</div>
    </div>
    <div class="topic-card" id="card-face">
      <div class="topic-head"><span class="topic-icon">👤</span><span class="topic-name">home/security/face</span></div>
      <div class="topic-rx-time never" id="time-face">從未接收</div>
      <div class="payload-box" id="payload-face">—</div>
    </div>
    <div class="topic-card" id="card-alert">
      <div class="topic-head"><span class="topic-icon">🚨</span><span class="topic-name">home/security/alert</span></div>
      <div class="topic-rx-time never" id="time-alert">從未接收</div>
      <div class="payload-box" id="payload-alert">—</div>
    </div>
    <div class="topic-card" id="card-status">
      <div class="topic-head"><span class="topic-icon">📶</span><span class="topic-name">home/security/status</span></div>
      <div class="topic-rx-time never" id="time-status">從未接收</div>
      <div class="payload-box" id="payload-status">—</div>
    </div>
  </div>

  <!-- Camera feed -->
  <div class="card-title" style="margin-bottom:.6rem;font-size:.68rem;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:var(--muted)">相機畫面</div>
  <div class="cam-card">
    <div class="cam-head">
      <span class="topic-icon">📷</span>
      <span class="cam-title">home/security/camera</span>
      <span class="cam-badge offline" id="cam-badge">無訊號</span>
    </div>
    <div class="cam-frame" id="cam-frame">
      <div class="cam-no-signal" id="cam-no-signal">
        <span style="font-size:2rem;opacity:.3">📷</span>
        <span>尚未收到影像</span>
      </div>
      <img id="cam-img" alt="camera" style="display:none" />
    </div>
    <div class="cam-ts" id="cam-ts"></div>
  </div>

  <!-- Message logs -->
  <div class="card">
    <div class="log-tabs">
      <button class="log-tab active" onclick="showTab('rx')">收到的訊息 <span id="rx-count" style="opacity:.7"></span></button>
      <button class="log-tab" onclick="showTab('tx')">送出的訊息 <span id="tx-count" style="opacity:.7"></span></button>
    </div>

    <div id="panel-rx" class="log-panel active">
      <div class="log-wrap">
        <table>
          <thead><tr><th>時間</th><th>Topic</th><th>Agent</th><th>內容</th></tr></thead>
          <tbody id="rx-tbody"><tr><td colspan="4" class="empty-log">尚無接收紀錄</td></tr></tbody>
        </table>
      </div>
    </div>

    <div id="panel-tx" class="log-panel">
      <div class="log-wrap">
        <table>
          <thead><tr><th>時間</th><th>Topic</th><th>內容</th></tr></thead>
          <tbody id="tx-tbody"><tr><td colspan="3" class="empty-log">尚無發送紀錄</td></tr></tbody>
        </table>
      </div>
    </div>

    <div class="refresh-ts" id="refresh-ts"></div>
  </div>
</div>

<script>
var TOPIC_MAP = {
  'home/security/door':   {id:'door',   icon:'🚪'},
  'home/security/face':   {id:'face',   icon:'👤'},
  'home/security/alert':  {id:'alert',  icon:'🚨'},
  'home/security/status': {id:'status', icon:'📶'},
};

function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function relTime(isoStr) {
  if (!isoStr) return '從未接收';
  var diff = Math.floor((Date.now() - new Date(isoStr).getTime()) / 1000);
  if (diff < 5)   return '剛剛';
  if (diff < 60)  return diff + ' 秒前';
  if (diff < 3600) return Math.floor(diff / 60) + ' 分鐘前';
  if (diff < 86400) return Math.floor(diff / 3600) + ' 小時前';
  return Math.floor(diff / 86400) + ' 天前';
}

function fmtTime(isoStr) {
  if (!isoStr) return '—';
  var d = new Date(isoStr);
  return d.toLocaleTimeString('zh-TW', {hour:'2-digit', minute:'2-digit', second:'2-digit', hour12:false});
}

function payloadStr(p) {
  try { return JSON.stringify(p, null, 2); }
  catch(e) { return String(p); }
}

function payloadOneLine(p) {
  try { return JSON.stringify(p); }
  catch(e) { return String(p); }
}

function showTab(which) {
  ['rx','tx'].forEach(function(t) {
    document.getElementById('panel-'+t).classList.toggle('active', t===which);
    document.querySelectorAll('.log-tab').forEach(function(b,i){
      b.classList.toggle('active', (i===0&&which==='rx')||(i===1&&which==='tx'));
    });
  });
}

function buildRxRows(log) {
  if (!log || !log.length) return '<tr><td colspan="4" class="empty-log">尚無接收紀錄</td></tr>';
  return log.map(function(e) {
    var agent = escHtml((e.payload && e.payload.agent) ? e.payload.agent : '—');
    var raw = payloadOneLine(e.payload);
    var truncated = raw.length > 80 ? raw.slice(0, 80) + '…' : raw;
    var preview = escHtml(truncated);
    var full = escHtml(raw);
    return '<tr>'
      + '<td class="td-ts">'+fmtTime(e.received_at)+'</td>'
      + '<td class="td-topic">'+escHtml(e.topic)+'</td>'
      + '<td style="font-size:.7rem;color:var(--muted)">'+agent+'</td>'
      + '<td class="td-payload" title="'+full+'">'+preview+'</td>'
      + '</tr>';
  }).join('');
}

function buildTxRows(log) {
  if (!log || !log.length) return '<tr><td colspan="3" class="empty-log">尚無發送紀錄</td></tr>';
  return log.map(function(e) {
    var raw = payloadOneLine(e.payload);
    var truncated = raw.length > 100 ? raw.slice(0, 100) + '…' : raw;
    var preview = escHtml(truncated);
    var full = escHtml(raw);
    return '<tr>'
      + '<td class="td-ts">'+fmtTime(e.sent_at)+'</td>'
      + '<td class="td-topic">'+escHtml(e.topic)+'</td>'
      + '<td class="td-payload" title="'+full+'">'+preview+'</td>'
      + '</tr>';
  }).join('');
}

var _cameraAvailable = false;
var _cameraFrameAt = null;

function updateCameraFeed(cameraAvailable, cameraFrameAt) {
  var badge = document.getElementById('cam-badge');
  var img = document.getElementById('cam-img');
  var noSig = document.getElementById('cam-no-signal');

  _cameraAvailable = cameraAvailable;
  _cameraFrameAt = cameraFrameAt;

  if (cameraAvailable) {
    badge.className = 'cam-badge live';
    badge.textContent = 'LIVE';
    noSig.style.display = 'none';
    img.style.display = 'block';
  } else {
    badge.className = 'cam-badge offline';
    badge.textContent = '無訊號';
    img.style.display = 'none';
    noSig.style.display = 'flex';
    document.getElementById('cam-ts').textContent =
      cameraFrameAt ? '最後影格：' + fmtTime(cameraFrameAt) + '  (' + relTime(cameraFrameAt) + ')' : '';
  }
}

// Camera image refresh independent of status poll — updates as fast as WebUI allows.
setInterval(function() {
  if (document.hidden || !_cameraAvailable) return;
  var img = document.getElementById('cam-img');
  img.src = '/api/mqtt/camera/latest?t=' + Date.now();
  if (_cameraFrameAt) {
    document.getElementById('cam-ts').textContent =
      '最後影格：' + fmtTime(_cameraFrameAt) + '  (' + relTime(_cameraFrameAt) + ')';
  }
}, 333);

async function loadStatus() {
  try {
    var r = await fetch('/api/mqtt/status');
    var d = await r.json();

    // Connection
    var dot = document.getElementById('conn-dot');
    var connEl = document.getElementById('conn-status');
    if (d.connected) {
      dot.className = 'conn-dot on';
      connEl.innerHTML = '<span class="badge-conn on">已連線</span>';
    } else {
      dot.className = 'conn-dot off';
      connEl.innerHTML = '<span class="badge-conn off">未連線</span>';
    }
    document.getElementById('conn-broker').textContent = 'broker: ' + d.broker_host + ':' + d.broker_port;
    document.getElementById('conn-ts').textContent = new Date().toLocaleTimeString('zh-TW',{hour12:false});

    // Topic cards
    Object.keys(TOPIC_MAP).forEach(function(topic) {
      var m = TOPIC_MAP[topic];
      var rx = d.last_rx[topic];
      var timeEl = document.getElementById('time-'+m.id);
      var payloadEl = document.getElementById('payload-'+m.id);
      if (rx) {
        var rel = relTime(rx.received_at);
        timeEl.textContent = rel + '  (' + fmtTime(rx.received_at) + ')';
        var diffSec = (Date.now() - new Date(rx.received_at).getTime()) / 1000;
        timeEl.className = 'topic-rx-time' + (diffSec < 30 ? ' fresh' : '');
        payloadEl.textContent = payloadStr(rx.payload);
      } else {
        timeEl.textContent = '從未接收';
        timeEl.className = 'topic-rx-time never';
        payloadEl.textContent = '—';
      }
    });

    // Logs
    document.getElementById('rx-tbody').innerHTML = buildRxRows(d.rx_log);
    document.getElementById('tx-tbody').innerHTML = buildTxRows(d.tx_log);
    document.getElementById('rx-count').textContent = d.rx_log && d.rx_log.length ? '('+d.rx_log.length+')' : '';
    document.getElementById('tx-count').textContent = d.tx_log && d.tx_log.length ? '('+d.tx_log.length+')' : '';
    document.getElementById('refresh-ts').textContent = '最後更新：' + new Date().toLocaleTimeString('zh-TW',{hour12:false});

    // Camera feed — update with data from status response
    updateCameraFeed(d.camera_available, d.camera_frame_at);
  } catch(e) {
    console.error('mqtt status', e);
  }
}

loadStatus();
setInterval(loadStatus, 5000);
</script>
"""

_MQTT_HTML = _make_shell("mqtt", "MQTT 監控", _MQTT_CONTENT)
