_SHELL = r"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>__TITLE__ — ePaper</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  __EXTRA_HEAD__
  <style>
    *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
    :root{
      --bg:#060A14;--surface:#0C1225;--surface2:#111C32;--border:#1B2842;
      --primary:#38BDF8;--pdim:rgba(56,189,248,.1);
      --green:#34D399;--amber:#FBBF24;--red:#F87171;
      --text:#DDE6F0;--muted:#4E647A;
      --r:10px;--sh:0 2px 16px rgba(0,0,0,.5);
      --sb-w:240px;--sb-icon:64px;
      color-scheme:dark;
    }
    html,body{height:100%}
    body{font-family:'Outfit',system-ui,sans-serif;background:var(--bg);color:var(--text)}
    .app{display:flex;min-height:100vh}
    /* Sidebar */
    .sidebar{
      width:var(--sb-w);background:var(--surface);border-right:1px solid var(--border);
      display:flex;flex-direction:column;position:fixed;left:0;top:0;bottom:0;z-index:100;
      transition:transform .25s cubic-bezier(.4,0,.2,1);
    }
    .sb-head{
      padding:1.1rem 1rem .9rem;display:flex;align-items:center;gap:.7rem;
      border-bottom:1px solid var(--border);flex-shrink:0;
    }
    .sb-logo{font-size:1.3rem;flex-shrink:0;line-height:1;min-width:1.5rem;text-align:center}
    .sb-brand{overflow:hidden;min-width:0}
    .sb-name{font-size:.875rem;font-weight:700;letter-spacing:.01em;white-space:nowrap}
    .sb-sub{font-size:.65rem;color:var(--muted);font-family:'JetBrains Mono',monospace;white-space:nowrap}
    .sb-nav{flex:1;padding:.5rem 0;overflow-y:auto}
    .sb-section{padding:.7rem 1rem .25rem;font-size:.6rem;font-weight:700;text-transform:uppercase;letter-spacing:.1em;color:var(--muted)}
    .nav-a{
      display:flex;align-items:center;gap:.75rem;padding:.55rem 1rem;
      color:var(--muted);text-decoration:none;border-left:2px solid transparent;
      transition:color .15s,background .15s,border-color .15s;font-size:.875rem;font-weight:500;
    }
    .nav-a:hover{color:var(--text);background:rgba(255,255,255,.04)}
    .nav-a.active{color:var(--primary);border-left-color:var(--primary);background:var(--pdim)}
    .nav-a.danger:hover{color:var(--red);background:rgba(248,113,113,.08)}
    .nav-ic{font-size:1.05rem;width:1.4rem;text-align:center;flex-shrink:0;line-height:1}
    .nav-lbl{font-size:.875rem}
    .sb-foot{padding:.5rem 0;border-top:1px solid var(--border);flex-shrink:0}
    /* Page area */
    .page-area{flex:1;display:flex;flex-direction:column;margin-left:var(--sb-w);min-height:100vh;transition:margin-left .25s cubic-bezier(.4,0,.2,1)}
    .main-content{flex:1}
    /* Mobile topbar */
    .mobile-bar{display:none;align-items:center;gap:.75rem;padding:.6rem 1rem;background:var(--surface);border-bottom:1px solid var(--border);position:sticky;top:0;z-index:50;flex-shrink:0}
    .menu-btn{width:2.1rem;height:2.1rem;border-radius:7px;background:transparent;border:1px solid var(--border);color:var(--text);font-size:.95rem;cursor:pointer;display:flex;align-items:center;justify-content:center;flex-shrink:0;padding:0;line-height:1;transition:background .15s}
    .menu-btn:hover{background:var(--surface2)}
    .mobile-page-title{font-size:.9rem;font-weight:600}
    /* Overlay */
    .overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.65);z-index:99;backdrop-filter:blur(2px)}
    /* Tablet 768-1023px: icon-only */
    @media(min-width:768px) and (max-width:1023px){
      .page-area{margin-left:var(--sb-icon)}
      .sidebar{width:var(--sb-icon)}
      .sb-brand,.sb-section,.nav-lbl{display:none}
      .sb-head{justify-content:center;padding:1.1rem .5rem .9rem}
      .nav-a{justify-content:center;padding:.65rem;position:relative}
      .nav-a[title]:hover::after{
        content:attr(title);position:absolute;left:calc(100% + .35rem);top:50%;transform:translateY(-50%);
        background:var(--surface2);color:var(--text);padding:.3rem .65rem;border-radius:6px;
        font-size:.78rem;white-space:nowrap;z-index:300;border:1px solid var(--border);
        box-shadow:0 4px 14px rgba(0,0,0,.5);pointer-events:none;
      }
    }
    /* Mobile <768px: slide drawer */
    @media(max-width:767px){
      .sidebar{transform:translateX(-100%);overflow:hidden}
      .sidebar.open{transform:translateX(0)}
      .page-area{margin-left:0}
      .mobile-bar{display:flex}
      .overlay.show{display:block}
    }
    /* Shared utilities */
    .page-wrap{max-width:960px;margin:0 auto;padding:1.75rem 1.5rem}
    .page-wrap.narrow{max-width:720px}
    .page-title{font-size:1.15rem;font-weight:700;margin-bottom:1.5rem;display:flex;align-items:center;gap:.5rem}
    .card{background:var(--surface);border:1px solid var(--border);border-radius:var(--r);padding:1.3rem;box-shadow:var(--sh);margin-bottom:1.2rem}
    .card-title{font-size:.68rem;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);margin-bottom:1rem}
    input[type=text],input[type=number],input[type=password],select{width:100%;padding:.45rem .75rem;border:1px solid var(--border);border-radius:6px;font-size:.875rem;color:var(--text);background:var(--bg);transition:border-color .15s,box-shadow .15s;outline:none;font-family:inherit}
    input:focus,select:focus{border-color:var(--primary);box-shadow:0 0 0 3px rgba(56,189,248,.15)}
    select option{background:var(--surface);color:var(--text)}
    button{font-family:inherit;cursor:pointer}
    .btn-p{padding:.45rem 1.2rem;border:none;border-radius:6px;font-size:.83rem;font-weight:600;background:var(--primary);color:#060A14;transition:filter .15s}
    .btn-p:hover{filter:brightness(1.1)}
    .btn-s{padding:.45rem 1.2rem;border:1px solid var(--border);border-radius:6px;font-size:.83rem;font-weight:500;background:var(--surface2);color:var(--text);transition:background .15s}
    .btn-s:hover{background:#1C2940}
    .btn-d{padding:.45rem 1.2rem;border:1px solid rgba(248,113,113,.3);border-radius:6px;font-size:.83rem;font-weight:500;background:rgba(248,113,113,.1);color:var(--red);transition:background .15s}
    .btn-d:hover{background:rgba(248,113,113,.2)}
    .f{margin-bottom:1rem}.f:last-of-type{margin-bottom:0}
    label{display:block;font-size:.78rem;font-weight:500;margin-bottom:.3rem}
    .hint{font-weight:400;color:var(--muted);font-size:.72rem;margin-left:.3rem}
    .row2{display:flex;gap:.65rem}.row2 .f{flex:1;margin-bottom:0}
    .btn-row{display:flex;justify-content:flex-end;gap:.6rem;margin-top:1.1rem}
    .tog-row{display:flex;align-items:center;justify-content:space-between;padding:.5rem 0}
    .tog-lbl{font-size:.875rem;font-weight:500}
    .tog-desc{font-size:.73rem;color:var(--muted);margin-top:.1rem}
    .sw{position:relative;width:40px;height:22px;flex-shrink:0}
    .sw input{opacity:0;width:0;height:0}
    .sl{position:absolute;inset:0;background:var(--border);border-radius:22px;cursor:pointer;transition:.2s}
    .sl::before{content:'';position:absolute;width:16px;height:16px;left:3px;top:3px;background:#94a3b8;border-radius:50%;transition:.2s;box-shadow:0 1px 3px rgba(0,0,0,.4)}
    input:checked+.sl{background:var(--primary)}
    input:checked+.sl::before{transform:translateX(18px);background:#fff}
    #toast{position:fixed;bottom:1.5rem;right:1.5rem;padding:.65rem 1.1rem;border-radius:var(--r);font-size:.83rem;font-weight:500;box-shadow:0 4px 12px rgba(0,0,0,.4);opacity:0;transform:translateY(.4rem);transition:opacity .22s,transform .22s;pointer-events:none;z-index:10001}
    #toast.show{opacity:1;transform:none}
    #toast.ok{background:#0a2e1a;color:#34d399;border:1px solid rgba(52,211,153,.3)}
    #toast.err{background:#2e0a0a;color:#f87171;border:1px solid rgba(248,113,113,.3)}
    #toast.info{background:#0a1e2e;color:#7dd3fc;border:1px solid rgba(56,189,248,.3)}
    @media(max-width:600px){.page-wrap{padding:1rem}}
  </style>
</head>
<body>
<div class="app">
  <aside class="sidebar" id="sidebar">
    <div class="sb-head">
      <span class="sb-logo">⚡</span>
      <div class="sb-brand">
        <div class="sb-name">ePaper Display</div>
        <div class="sb-sub">Home System</div>
      </div>
    </div>
    <nav class="sb-nav">
      <div class="sb-section">監控</div>
      <a href="/desk" class="nav-a__DESK_A__" title="書桌前分析">
        <span class="nav-ic">📊</span>
        <span class="nav-lbl">書桌前分析</span>
      </a>
      <div class="sb-section">管理</div>
      <a href="/images" class="nav-a__IMAGES_A__" title="圖片輪播">
        <span class="nav-ic">🖼️</span>
        <span class="nav-lbl">圖片輪播</span>
      </a>
      <a href="/settings" class="nav-a__SETTINGS_A__" title="系統設定">
        <span class="nav-ic">⚙️</span>
        <span class="nav-lbl">系統設定</span>
      </a>
    </nav>
    <div class="sb-foot">
      <a href="/logout" class="nav-a danger" title="登出">
        <span class="nav-ic">🚪</span>
        <span class="nav-lbl">登出</span>
      </a>
    </div>
  </aside>

  <div class="overlay" id="overlay" onclick="closeSidebar()"></div>

  <div class="page-area">
    <div id="toast"></div>
    <header class="mobile-bar">
      <button class="menu-btn" id="menu-btn" onclick="toggleSidebar()">☰</button>
      <span class="mobile-page-title">__TITLE__</span>
    </header>
    <div class="main-content">
      __CONTENT__
    </div>
  </div>
</div>

<script>
function toggleSidebar(){
  var sb=document.getElementById('sidebar');
  var ov=document.getElementById('overlay');
  var btn=document.getElementById('menu-btn');
  var open=sb.classList.toggle('open');
  ov.classList.toggle('show',open);
  if(btn) btn.textContent=open?'×':'☰';
}
function closeSidebar(){
  var sb=document.getElementById('sidebar');
  var ov=document.getElementById('overlay');
  var btn=document.getElementById('menu-btn');
  sb.classList.remove('open');
  ov.classList.remove('show');
  if(btn) btn.textContent='☰';
}
</script>
</body>
</html>"""


def _make_shell(page_id: str, title: str, content: str, extra_head: str = "") -> str:
    desk_a     = " active" if page_id == "desk"     else ""
    images_a   = " active" if page_id == "images"   else ""
    settings_a = " active" if page_id == "settings" else ""
    return (
        _SHELL
        .replace("__TITLE__", title)
        .replace("__EXTRA_HEAD__", extra_head)
        .replace("__CONTENT__", content)
        .replace("__DESK_A__", desk_a)
        .replace("__IMAGES_A__", images_a)
        .replace("__SETTINGS_A__", settings_a)
    )
