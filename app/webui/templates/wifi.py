_WIFI_HTML = r"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>WiFi 設定 — ePaper</title>
  <style>
    *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
    :root{
      --bg:#060A14;--surface:#0C1225;--border:#1B2842;
      --primary:#38BDF8;--green:#34D399;--red:#F87171;--amber:#FBBF24;
      --text:#DDE6F0;--muted:#4E647A;--r:10px;
    }
    body{background:var(--bg);color:var(--text);font-family:system-ui,sans-serif;
         min-height:100vh;display:flex;align-items:flex-start;justify-content:center;
         padding:1.5rem 1rem}
    .card{background:var(--surface);border:1px solid var(--border);border-radius:var(--r);
          padding:1.5rem;width:100%;max-width:480px;box-shadow:0 4px 24px rgba(0,0,0,.5)}
    h1{font-size:1.15rem;font-weight:700;margin-bottom:.25rem}
    .sub{font-size:.78rem;color:var(--muted);margin-bottom:1.25rem}
    .btn{padding:.5rem 1.1rem;border:none;border-radius:6px;font-size:.83rem;font-weight:600;
         cursor:pointer;transition:filter .15s;display:inline-flex;align-items:center;gap:.4rem}
    .btn-p{background:var(--primary);color:#060A14}.btn-p:hover{filter:brightness(1.1)}
    .btn-p:disabled{opacity:.5;cursor:not-allowed}
    .btn-s{background:var(--surface);border:1px solid var(--border);color:var(--text);cursor:pointer}
    .net-list{margin-top:1rem}
    .net-item{display:flex;align-items:center;gap:.75rem;padding:.6rem .75rem;
              border:1px solid var(--border);border-radius:7px;margin-bottom:.4rem;
              cursor:pointer;transition:background .15s}
    .net-item:hover{background:rgba(56,189,248,.07);border-color:var(--primary)}
    .net-item.selected{background:rgba(56,189,248,.12);border-color:var(--primary)}
    .net-ssid{font-weight:600;font-size:.9rem;flex:1;word-break:break-all}
    .net-sig{font-size:.75rem;color:var(--muted);white-space:nowrap}
    .net-lock{font-size:.85rem}
    .connect-box{margin-top:1rem;padding:1rem;background:rgba(56,189,248,.05);
                 border:1px solid var(--border);border-radius:8px}
    .connect-ssid{font-size:.85rem;font-weight:600;margin-bottom:.6rem}
    .connect-ssid span{color:var(--primary)}
    .connect-box label{display:block;font-size:.78rem;font-weight:500;margin-bottom:.3rem;color:var(--muted)}
    .connect-box input{width:100%;padding:.45rem .75rem;border:1px solid var(--border);
                       border-radius:6px;font-size:.875rem;color:var(--text);background:var(--bg);outline:none}
    .connect-box input:focus{border-color:var(--primary)}
    .btn-row{display:flex;gap:.6rem;margin-top:.75rem;justify-content:flex-end}
    .msg{padding:.55rem .85rem;border-radius:6px;font-size:.82rem;font-weight:500;margin-top:.75rem}
    .msg.ok{background:rgba(52,211,153,.1);border:1px solid rgba(52,211,153,.3);color:var(--green)}
    .msg.err{background:rgba(248,113,113,.1);border:1px solid rgba(248,113,113,.3);color:var(--red)}
    .msg.info{background:rgba(56,189,248,.1);border:1px solid rgba(56,189,248,.3);color:var(--primary)}
    .spin{display:inline-block;width:1rem;height:1rem;border:2px solid currentColor;
          border-top-color:transparent;border-radius:50%;animation:spin .7s linear infinite}
    @keyframes spin{to{transform:rotate(360deg)}}
    .sig-bar{display:flex;gap:1px;align-items:flex-end;height:14px;flex-shrink:0}
    .sig-bar span{width:3px;background:var(--muted);border-radius:1px}
    .sig-bar.s4 span{background:var(--green)}
    .sig-bar.s3 span:nth-child(-n+3){background:var(--green)}
    .sig-bar.s2 span:nth-child(-n+2){background:var(--amber)}
    .sig-bar.s1 span:nth-child(1){background:var(--red)}
  </style>
</head>
<body>
<div class="card">
  <h1>📡 WiFi 設定</h1>
  <p class="sub">選擇附近的 WiFi 網路並輸入密碼，連線後裝置將自動回到正常模式。</p>
  <button class="btn btn-p" id="scanBtn" onclick="scan()">🔍 掃描 WiFi 網路</button>
  <div id="netList" class="net-list"></div>
  <div id="connectBox" class="connect-box" style="display:none">
    <div class="connect-ssid">連線到：<span id="selSsid"></span></div>
    <label>WiFi 密碼</label>
    <input type="password" id="pwdInput" placeholder="輸入 WiFi 密碼" autocomplete="off"
           onkeydown="if(event.key==='Enter')doConnect()">
    <div class="btn-row">
      <button class="btn btn-s" onclick="cancelConnect()">取消</button>
      <button class="btn btn-p" id="connectBtn" onclick="doConnect()">連線</button>
    </div>
  </div>
  <div id="msg" style="display:none"></div>
</div>

<script>
var selectedSsid = null;

function sigClass(s) {
  if (s >= 75) return 's4';
  if (s >= 50) return 's3';
  if (s >= 25) return 's2';
  return 's1';
}

function sigBars(s) {
  var c = sigClass(s);
  var heights = ['4px', '7px', '10px', '13px'];
  return '<div class="sig-bar ' + c + '">' +
    heights.map(function(h) { return '<span style="height:' + h + '"></span>'; }).join('') +
    '</div>';
}

function escHtml(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function scan() {
  var btn = document.getElementById('scanBtn');
  btn.disabled = true;
  btn.innerHTML = '<span class="spin"></span> 掃描中...';
  showMsg('info', '正在掃描附近的 WiFi 網路...');
  fetch('/api/wifi/scan')
    .then(function(r) {
      if (!r.ok) return r.json().then(function(d) { throw new Error(d.detail || '掃描失敗'); });
      return r.json();
    })
    .then(function(data) {
      btn.disabled = false;
      btn.innerHTML = '🔍 重新掃描';
      hideMsg();
      renderNets(data.networks || []);
    })
    .catch(function(e) {
      btn.disabled = false;
      btn.innerHTML = '🔍 重新掃描';
      showMsg('err', '掃描失敗：' + e.message);
    });
}

function renderNets(nets) {
  var el = document.getElementById('netList');
  if (!nets.length) {
    el.innerHTML = '<p style="color:var(--muted);font-size:.83rem;margin-top:.5rem">未找到任何網路</p>';
    return;
  }
  el.innerHTML = nets.map(function(n) {
    var lock = (n.security && n.security !== 'Open') ? '🔒' : '🔓';
    var id = 'net-' + encodeURIComponent(n.ssid);
    return '<div class="net-item" onclick="selectNet(' + JSON.stringify(n.ssid) + ')" id="' + id + '">' +
      sigBars(n.signal) +
      '<span class="net-ssid">' + escHtml(n.ssid) + '</span>' +
      '<span class="net-sig">' + n.signal + '%</span>' +
      '<span class="net-lock">' + lock + '</span>' +
      '</div>';
  }).join('');
}

function selectNet(ssid) {
  selectedSsid = ssid;
  document.querySelectorAll('.net-item').forEach(function(el) { el.classList.remove('selected'); });
  var el = document.getElementById('net-' + encodeURIComponent(ssid));
  if (el) el.classList.add('selected');
  document.getElementById('selSsid').textContent = ssid;
  document.getElementById('connectBox').style.display = 'block';
  document.getElementById('pwdInput').value = '';
  document.getElementById('pwdInput').focus();
  hideMsg();
}

function cancelConnect() {
  selectedSsid = null;
  document.getElementById('connectBox').style.display = 'none';
  document.querySelectorAll('.net-item').forEach(function(el) { el.classList.remove('selected'); });
}

function doConnect() {
  if (!selectedSsid) return;
  var pwd = document.getElementById('pwdInput').value;
  var btn = document.getElementById('connectBtn');
  btn.disabled = true;
  btn.innerHTML = '<span class="spin"></span> 連線中...';
  showMsg('info', '正在連線到「' + escHtml(selectedSsid) + '」...');

  fetch('/api/wifi/connect', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ssid: selectedSsid, password: pwd })
  })
  .then(function(r) {
    if (!r.ok) return r.json().then(function(d) { throw new Error(d.detail || '連線失敗'); });
    return r.json();
  })
  .then(function() {
    btn.disabled = false;
    btn.innerHTML = '連線';
    showMsg('ok', '✓ 連線成功！裝置正在切換網路，此頁面約 15 秒後無法存取（正常現象）。');
  })
  .catch(function(e) {
    btn.disabled = false;
    btn.innerHTML = '連線';
    showMsg('err', '✗ 連線失敗：' + e.message);
  });
}

function showMsg(type, text) {
  var el = document.getElementById('msg');
  el.className = 'msg ' + type;
  el.textContent = text;
  el.style.display = 'block';
}

function hideMsg() {
  document.getElementById('msg').style.display = 'none';
}
</script>
</body>
</html>"""
