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
    label{display:block;font-size:.78rem;font-weight:500;margin-bottom:.3rem;color:var(--muted)}
    input[type=text],input[type=password]{
      width:100%;padding:.45rem .75rem;border:1px solid var(--border);
      border-radius:6px;font-size:.875rem;color:var(--text);background:var(--bg);outline:none;
      margin-bottom:.75rem}
    input:focus{border-color:var(--primary)}
    input:disabled{opacity:.5;cursor:not-allowed}
    .section-title{font-size:.75rem;color:var(--muted);margin-bottom:.4rem;display:flex;align-items:center;justify-content:space-between}
    .refresh-link{font-size:.72rem;color:var(--primary);cursor:pointer;background:none;border:none;padding:0;text-decoration:underline}
    .refresh-link:disabled{opacity:.5;cursor:not-allowed}
    .net-list{margin-bottom:.75rem}
    .net-item{display:flex;align-items:center;gap:.75rem;padding:.5rem .75rem;
              border:1px solid var(--border);border-radius:7px;margin-bottom:.35rem;
              cursor:pointer;transition:background .15s}
    .net-item:hover{background:rgba(56,189,248,.07);border-color:var(--primary)}
    .net-item.selected{background:rgba(56,189,248,.12);border-color:var(--primary)}
    .net-ssid{font-weight:600;font-size:.88rem;flex:1;word-break:break-all}
    .net-sig{font-size:.73rem;color:var(--muted);white-space:nowrap}
    .net-lock{font-size:.82rem}
    .net-empty{font-size:.82rem;color:var(--muted);padding:.35rem 0}
    .divider{border:none;border-top:1px solid var(--border);margin:.75rem 0}
    .connect-btn{width:100%;padding:.55rem;border:none;border-radius:6px;font-size:.9rem;
                 font-weight:700;cursor:pointer;background:var(--primary);color:#060A14;
                 display:flex;align-items:center;justify-content:center;gap:.5rem;transition:filter .15s}
    .connect-btn:hover{filter:brightness(1.1)}
    .connect-btn:disabled{opacity:.5;cursor:not-allowed}
    .msg{padding:.55rem .85rem;border-radius:6px;font-size:.82rem;font-weight:500;margin-top:.75rem;line-height:1.5}
    .msg.ok{background:rgba(52,211,153,.1);border:1px solid rgba(52,211,153,.3);color:var(--green)}
    .msg.err{background:rgba(248,113,113,.1);border:1px solid rgba(248,113,113,.3);color:var(--red)}
    .msg.info{background:rgba(56,189,248,.1);border:1px solid rgba(56,189,248,.3);color:var(--primary)}
    .msg.warn{background:rgba(251,191,36,.1);border:1px solid rgba(251,191,36,.3);color:var(--amber)}
    .spin{display:inline-block;width:.9rem;height:.9rem;border:2px solid currentColor;
          border-top-color:transparent;border-radius:50%;animation:spin .7s linear infinite}
    @keyframes spin{to{transform:rotate(360deg)}}
    .sig-bar{display:flex;gap:1px;align-items:flex-end;height:13px;flex-shrink:0}
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
  <p class="sub">從清單點選，或直接輸入 WiFi 名稱（SSID），再輸入密碼連線。</p>

  <div class="section-title">
    <span>附近的 WiFi 網路</span>
    <button class="refresh-link" id="refreshBtn" onclick="loadNetworks()">重新整理</button>
  </div>
  <div id="netList" class="net-list">
    <div class="net-empty"><span class="spin"></span> 正在載入...</div>
  </div>

  <hr class="divider">

  <label for="ssidInput">WiFi 名稱（SSID）</label>
  <input type="text" id="ssidInput" placeholder="點選上方清單或在此手動輸入" autocomplete="off"
         onkeydown="if(event.key==='Enter')document.getElementById('pwdInput').focus()">

  <label for="pwdInput">密碼（開放網路請留空）</label>
  <input type="password" id="pwdInput" placeholder="WiFi 密碼" autocomplete="off"
         onkeydown="if(event.key==='Enter')doConnect()">

  <button class="connect-btn" id="connectBtn" onclick="doConnect()">連線</button>

  <div id="msg" style="display:none"></div>
</div>

<script>
function sigClass(s){return s>=75?'s4':s>=50?'s3':s>=25?'s2':'s1';}
function sigBars(s){
  var c=sigClass(s),h=['4px','7px','10px','13px'];
  return '<div class="sig-bar '+c+'">'+h.map(function(x){return'<span style="height:'+x+'"></span>';}).join('')+'</div>';
}
function esc(s){return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
function showMsg(t,m){var e=document.getElementById('msg');e.className='msg '+t;e.innerHTML=m;e.style.display='block';}
function hideMsg(){document.getElementById('msg').style.display='none';}
function setDisabled(v){
  ['ssidInput','pwdInput','connectBtn','refreshBtn'].forEach(function(id){
    document.getElementById(id).disabled=v;
  });
}

function loadNetworks(){
  var rb=document.getElementById('refreshBtn');
  rb.disabled=true;
  document.getElementById('netList').innerHTML='<div class="net-empty"><span class="spin"></span> 正在載入...</div>';
  fetch('/api/wifi/scan')
    .then(function(r){
      if(!r.ok)return r.json().then(function(d){throw new Error(d.detail||'載入失敗');});
      return r.json();
    })
    .then(function(data){
      rb.disabled=false;
      renderNets(data.networks||[]);
    })
    .catch(function(e){
      rb.disabled=false;
      document.getElementById('netList').innerHTML='<div class="net-empty">無法載入網路清單：'+esc(e.message)+'</div>';
    });
}

function renderNets(nets){
  var el=document.getElementById('netList');
  if(!nets.length){
    el.innerHTML='<div class="net-empty">附近未偵測到 WiFi 網路，請手動輸入 SSID。</div>';
    return;
  }
  el.innerHTML=nets.map(function(n){
    var lock=(n.security&&n.security!=='Open')?'🔒':'🔓';
    return '<div class="net-item" onclick="selectNet('+esc(JSON.stringify(n.ssid))+',this)">'+
      sigBars(n.signal)+
      '<span class="net-ssid">'+esc(n.ssid)+'</span>'+
      '<span class="net-sig">'+n.signal+'%</span>'+
      '<span class="net-lock">'+lock+'</span>'+
      '</div>';
  }).join('');
}

function selectNet(ssid,el){
  document.querySelectorAll('.net-item').forEach(function(x){x.classList.remove('selected');});
  el.classList.add('selected');
  document.getElementById('ssidInput').value=ssid;
  document.getElementById('pwdInput').focus();
  hideMsg();
}

function doConnect(){
  var ssid=document.getElementById('ssidInput').value.trim();
  if(!ssid){showMsg('err','請輸入 WiFi 名稱（SSID）');return;}
  var pwd=document.getElementById('pwdInput').value;
  setDisabled(true);
  showMsg('info','<span class="spin"></span> 正在建立連線設定...');

  fetch('/api/wifi/connect',{
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({ssid:ssid,password:pwd})
  })
  .then(function(r){
    if(!r.ok)return r.json().then(function(d){throw new Error(d.detail||'連線失敗');});
    return r.json();
  })
  .then(function(){
    showMsg('ok',
      '✓ 連線指令已送出！<br>'+
      'AP 熱點即將關閉，此頁面將失效。<br>'+
      '裝置連上網路後電子紙將自動切回正常顯示（約 15–30 秒）。');
  })
  .catch(function(e){
    var isNetErr=(!e.message||e.message==='Failed to fetch'||
                  e.message.indexOf('NetworkError')>=0||e.message.indexOf('Load failed')>=0);
    if(isNetErr){
      showMsg('warn',
        '⚠️ 頁面已失去連線。<br>'+
        '通常代表 AP 已成功關閉並正在切換網路。<br>'+
        '請等待 15–30 秒後確認裝置是否連上網路。');
    } else {
      setDisabled(false);
      showMsg('err','✗ 連線失敗：'+e.message);
    }
  });
}

// Auto-load network list on page open
loadNetworks();
</script>
</body>
</html>"""
