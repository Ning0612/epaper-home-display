from app.webui.templates.theme import (
    _CSRF_FETCH_SCRIPT,
    _FAVICON_DATA_URI,
    _THEME_CONTROL_SCRIPT,
    _THEME_CSS,
    _THEME_INIT_SCRIPT,
)


_WIFI_HTML = (
    r"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="description" content="ePaper Home Display WiFi 設定入口">
  <meta name="csrf-token" content="__CSRF__">
  <title>ePaper Home Display / WiFi 設定</title>
  <link rel="icon" type="image/svg+xml" href="__FAVICON__">
  <script>__THEME_INIT__</script>
  <style>
    __THEME_CSS__
    body{padding:0}
    .wifi-wrap{max-width:600px;margin:auto;padding:1.5rem 1rem 3.2rem}
    .wifi-card{padding:1.2rem}
    .wifi-title{margin:.45rem 0 0;padding-bottom:.7rem;border-bottom:1px solid var(--line);font-size:clamp(2rem,7vw,3rem);line-height:.95;font-weight:400;letter-spacing:-.05em}
    .wifi-sub{margin:.6rem 0 1.2rem;color:var(--muted);font-size:.88rem;line-height:1.5}
    .section-title{display:flex;align-items:center;justify-content:space-between;gap:.75rem;margin-bottom:.45rem;color:var(--muted);font:700 .72rem Consolas,monospace;letter-spacing:.03em}
    .field-with-action{display:flex;align-items:stretch;gap:.5rem}
    .field-with-action select{flex:1;min-width:0}
    .field-with-action button{flex:none;white-space:nowrap}
    .net-list{display:grid;gap:.4rem;margin:.7rem 0 1rem}
    .net-item{display:flex;align-items:center;gap:.7rem;padding:.55rem .7rem;border:1px solid var(--line);background:var(--inset);cursor:pointer;transition:background .15s,border-color .15s}
    .net-item:hover,.net-item.selected{background:var(--surface-2);border-color:var(--teal)}
    .net-ssid{flex:1;min-width:0;overflow-wrap:anywhere;font:700 .82rem Consolas,monospace}
    .net-sig,.net-lock{color:var(--muted);font:400 .7rem Consolas,monospace;white-space:nowrap}
    .net-empty{padding:.7rem 0;color:var(--muted);font:400 .8rem Consolas,monospace}
    .sig-bar{display:flex;align-items:flex-end;gap:1px;height:13px;flex:none}
    .sig-bar span{width:3px;background:var(--muted)}
    .sig-bar.s4 span{background:var(--teal)}.sig-bar.s3 span:nth-child(-n+3){background:var(--teal)}
    .sig-bar.s2 span:nth-child(-n+2){background:var(--amber)}.sig-bar.s1 span:nth-child(1){background:var(--coral)}
    .divider{border:0;border-top:1px solid var(--line);margin:1rem 0}
    .connect-btn{width:100%;margin-top:.2rem}
    .wifi-footer{margin-top:0}
    @media(max-width:480px){.field-with-action{flex-direction:column}.field-with-action button{width:100%}}
  </style>
</head>
<body data-page="wifi">
  <header class="topbar">
    <div class="topbar-in">
      <div class="brand"><span class="brand-mark">EH</span><span class="brand-copy">EPAPER HOME DISPLAY<span class="brand-sub">LOCAL DEVICE / NETWORK SETUP</span></span></div>
      <div class="theme-toggle" role="group" aria-label="配色主題切換">
        <button type="button" data-theme-choice="light" aria-pressed="false">LIGHT</button>
        <button type="button" data-theme-choice="dark" aria-pressed="false">DARK</button>
      </div>
    </div>
  </header>
  <main class="wifi-wrap">
    <div class="kicker">00 / network</div>
    <h1 class="wifi-title">WiFi 設定</h1>
    <p class="wifi-sub">掃描附近網路、選取 SSID，再輸入密碼建立連線設定。</p>
    <section class="card wifi-card">
      <div class="field">
        <div class="section-title"><span>附近的 WiFi 網路</span><span id="scan-status" aria-live="polite"></span></div>
        <div class="field-with-action">
          <select id="ssidSelect" aria-label="選擇附近的 WiFi 網路"><option value="">尚未掃描</option></select>
          <button type="button" class="ghost" id="refreshBtn">掃描</button>
        </div>
        <div id="netList" class="net-list" aria-live="polite"><div class="net-empty">按「掃描」載入附近網路。</div></div>
        <div id="scanMessage" class="message error" style="display:none" aria-live="polite"></div>
      </div>

      <hr class="divider">
      <div class="field"><label for="ssidInput">WiFi 名稱（SSID）</label><input type="text" id="ssidInput" placeholder="可手動輸入 SSID" autocomplete="off"></div>
      <div class="field"><label for="pwdInput">密碼（開放網路請留空）</label><input type="password" id="pwdInput" placeholder="WiFi 密碼" autocomplete="off"></div>
      <button type="button" class="connect-btn" id="connectBtn">連線</button>
      <div id="connectMessage" class="message" style="display:none" aria-live="polite"></div>
    </section>
  </main>
  <footer class="site-footer wifi-footer"><div class="footer-in"><div class="footer-repo"><span class="label">SOURCE</span><a href="https://github.com/Ning0612/epaper-home-display">Ning0612/epaper-home-display</a></div><div class="footer-meta">WiFi setup portal · local device</div></div></footer>
  <script>
  function sigClass(signal){return signal>=75?'s4':signal>=50?'s3':signal>=25?'s2':'s1';}
  function sigBars(signal){var h=['4px','7px','10px','13px'];return '<div class="sig-bar '+sigClass(signal)+'">'+h.map(function(x){return '<span style="height:'+x+'"></span>';}).join('')+'</div>';}
  function esc(value){return String(value).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
  function showScanMessage(message){var el=document.getElementById('scanMessage');el.textContent=message;el.style.display='block';}
  function hideScanMessage(){document.getElementById('scanMessage').style.display='none';}
  function showConnectMessage(type,message){var el=document.getElementById('connectMessage');el.className='message '+type;el.textContent=message;el.style.display='block';}
  function selectNetwork(ssid){
    document.getElementById('ssidSelect').value=ssid;
    document.getElementById('ssidInput').value=ssid;
    document.querySelectorAll('.net-item').forEach(function(item){item.classList.toggle('selected',item.dataset.ssid===ssid);});
    hideScanMessage();
    document.getElementById('pwdInput').focus();
  }
  function renderNetworks(networks){
    var select=document.getElementById('ssidSelect'),previous=select.value;
    select.innerHTML='<option value="">選擇附近網路…</option>';
    networks.forEach(function(network){
      var option=document.createElement('option');option.value=network.ssid;option.textContent=network.ssid+' · '+network.signal+'%';select.appendChild(option);
    });
    if(networks.some(function(network){return network.ssid===previous}))select.value=previous;
    var list=document.getElementById('netList');
    if(!networks.length){list.innerHTML='<div class="net-empty">附近未偵測到 WiFi，請手動輸入 SSID。</div>';return;}
    list.innerHTML=networks.map(function(network){var locked=network.security&&network.security!=='Open';return '<div class="net-item" data-ssid="'+esc(network.ssid)+'" tabindex="0" role="button" aria-label="選擇 '+esc(network.ssid)+'">'+sigBars(network.signal)+'<span class="net-ssid">'+esc(network.ssid)+'</span><span class="net-sig">'+network.signal+'%</span><span class="net-lock">'+(locked?'SECURE':'OPEN')+'</span></div>';}).join('');
  }
  async function loadNetworks(){
    var button=document.getElementById('refreshBtn'),status=document.getElementById('scan-status'),hasNetworks=document.querySelector('.net-item');
    button.disabled=true;button.textContent='掃描中…';status.textContent='';hideScanMessage();
    if(!hasNetworks)document.getElementById('netList').innerHTML='<div class="skeleton" style="height:2.4rem"></div><div class="skeleton" style="height:2.4rem"></div>';
    try{
      var response=await fetch('/api/wifi/scan');
      var data=await response.json();
      if(!response.ok)throw new Error(data.detail||'WiFi 掃描失敗');
      renderNetworks(data.networks||[]);status.textContent='已更新';
    }catch(error){
      showScanMessage('暫時無法連線：'+(error.message||'WiFi 掃描失敗'));
      status.textContent='保留上次結果';
      if(!hasNetworks)document.getElementById('netList').innerHTML='<div class="net-empty">目前無法取得網路清單，請稍後重試或手動輸入 SSID。</div>';
    }finally{button.disabled=false;button.textContent='掃描';}
  }
  async function doConnect(){
    var ssid=document.getElementById('ssidInput').value.trim(),password=document.getElementById('pwdInput').value,button=document.getElementById('connectBtn');
    if(!ssid){showConnectMessage('error','請輸入 WiFi 名稱（SSID）');return;}
    button.disabled=true;showConnectMessage('warn','正在建立連線設定…');
    try{
      var response=await fetch('/api/wifi/connect',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ssid:ssid,password:password})});
      var data=await response.json();
      if(!response.ok)throw new Error(data.detail||'連線失敗');
      showConnectMessage('','連線指令已送出。AP 熱點即將關閉，請等待 15–30 秒確認裝置重新上線。');
    }catch(error){
      var networkLost=!error.message||error.message==='Failed to fetch'||/NetworkError|Load failed/.test(error.message);
      if(networkLost)showConnectMessage('warn','頁面已失去連線，通常代表 AP 正在切換網路。請等待 15–30 秒後確認裝置狀態。');
      else{button.disabled=false;showConnectMessage('error','連線失敗：'+error.message);}
    }
  }
  document.getElementById('refreshBtn').addEventListener('click',loadNetworks);
  document.getElementById('ssidSelect').addEventListener('change',function(){if(this.value)selectNetwork(this.value);});
  document.getElementById('netList').addEventListener('click',function(event){var item=event.target.closest('.net-item');if(item)selectNetwork(item.dataset.ssid);});
  document.getElementById('netList').addEventListener('keydown',function(event){var item=event.target.closest('.net-item');if(item&&(event.key==='Enter'||event.key===' ')){event.preventDefault();selectNetwork(item.dataset.ssid);}});
  document.getElementById('connectBtn').addEventListener('click',doConnect);
  document.getElementById('pwdInput').addEventListener('keydown',function(event){if(event.key==='Enter')doConnect();});
  loadNetworks();
  </script>
  <script>__CSRF_FETCH__</script>
  <script>__THEME_CONTROL__</script>
</body>
</html>"""
    .replace("__FAVICON__", _FAVICON_DATA_URI)
    .replace("__THEME_INIT__", _THEME_INIT_SCRIPT)
    .replace("__THEME_CSS__", _THEME_CSS)
    .replace("__CSRF_FETCH__", _CSRF_FETCH_SCRIPT)
    .replace("__THEME_CONTROL__", _THEME_CONTROL_SCRIPT)
)


def _render_wifi(csrf_token: str) -> str:
    return _WIFI_HTML.replace("__CSRF__", csrf_token)
