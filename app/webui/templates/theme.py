"""Shared visual and browser helpers for the ePaper WebUI templates."""

_THEME_INIT_SCRIPT = r"""(function(){
  var key='iot-ui-theme',stored=null;
  try{stored=localStorage.getItem(key)}catch(e){}
  var theme=(stored==='light'||stored==='dark')?stored:
    (window.matchMedia&&window.matchMedia('(prefers-color-scheme:dark)').matches?'dark':'light');
  document.documentElement.dataset.theme=theme;
})();"""

_THEME_CSS = r""":root{
  color-scheme:light;
  --paper:#f1ede2;--surface:#fbf8ef;--surface-2:#e7e3d6;
  --ink:#17231f;--ink-soft:#263a34;--line:#b9b8aa;--muted:#68736c;
  --teal:#0b716a;--teal-dark:#07534f;--coral:#cf5a47;--coral-dark:#a94436;
  --amber:#bd812d;--amber-dark:#98641d;--shadow:rgba(23,35,31,.15);
  --inset:#fffdf7;--input-border:#7e9188;--chart-grid:#d4d2c5;
  --unknown:#a9ada3;--placeholder:#9aa39b;--grid-dot:rgba(23,35,31,.045);
  --danger-surface:#fff6ed;
  --crop-overlay:rgba(23,35,31,.55);
  --mint:#a8d2c4;--on-dark:#fbf8ef;--on-light:#17231f;
  --dark-block-muted:#aab8ae;--nav-border:#71847a;
  --on-ring:rgba(168,210,196,.18);--off-ring:rgba(207,90,71,.18);
  /* Compatibility aliases for existing page-specific controls. */
  --bg:var(--paper);--surface2:var(--surface-2);--border:var(--line);
  --primary:var(--teal);--green:var(--teal);--red:var(--coral);--text:var(--ink);
}
:root[data-theme="dark"]{
  color-scheme:dark;
  --paper:#141b18;--surface:#1c2622;--surface-2:#24312c;
  --ink:#eef1ea;--ink-soft:#0a100d;--line:#3a4a43;--muted:#93a69c;
  --teal:#1fae9c;--teal-dark:#167d70;--coral:#e2705a;--coral-dark:#b8543f;
  --amber:#d99a3f;--amber-dark:#a97a2f;--shadow:rgba(0,0,0,.4);
  --inset:#101512;--input-border:#48584f;--chart-grid:#3a473f;
  --unknown:#6b756e;--placeholder:#66756c;--grid-dot:rgba(255,255,255,.035);
  --danger-surface:#241a16;
  --crop-overlay:rgba(0,0,0,.55);
}

*,*::before,*::after{box-sizing:border-box}
html,body{min-height:100%}
body{
  margin:0;background-color:var(--paper);
  background-image:linear-gradient(var(--grid-dot) 1px,transparent 1px),linear-gradient(90deg,var(--grid-dot) 1px,transparent 1px);
  background-size:20px 20px;color:var(--ink);font-family:Georgia,'Noto Serif TC',serif;
}
button,input,select,textarea{font-family:Consolas,monospace}
a{color:var(--teal)}
button:focus-visible,a:focus-visible,input:focus-visible,select:focus-visible,textarea:focus-visible{
  outline:2px solid var(--mint);outline-offset:2px;
}

.topbar{background:var(--ink-soft);border-bottom:5px solid var(--coral);color:var(--on-dark);padding:1rem}
.topbar-in{max-width:1040px;margin:auto;display:flex;align-items:center;justify-content:space-between;gap:1rem}
.brand{display:flex;align-items:center;gap:.7rem;color:inherit;text-decoration:none}
.brand-mark{display:grid;place-items:center;width:2.25rem;height:2.25rem;border:2px solid var(--mint);color:var(--mint);font:700 1rem Consolas,monospace}
.brand-copy{font:700 .82rem Consolas,monospace;letter-spacing:.08em}
.brand-sub{display:block;margin-top:.22rem;color:var(--dark-block-muted);font:400 .68rem Consolas,monospace;letter-spacing:.02em}
.topbar-actions{display:flex;align-items:center;justify-content:flex-end;gap:.6rem;flex-wrap:wrap}
.nav{display:flex;gap:.4rem;flex-wrap:wrap;justify-content:flex-end}
.nav-link{border:1px solid var(--nav-border);border-radius:0;color:var(--on-dark);padding:.46rem .6rem;text-decoration:none;background:transparent;font:700 .72rem Consolas,monospace;cursor:pointer;transition:background .15s,color .15s}
.nav-link:hover,.nav-link.active{background:var(--mint);border-color:var(--mint);color:var(--on-light)}
.nav-link.danger{background:transparent;border-color:var(--nav-border);color:var(--on-dark)}
.nav-link.danger:hover{background:var(--coral);border-color:var(--coral);color:var(--on-dark)}

.theme-toggle{display:flex;border:1px solid var(--nav-border);overflow:hidden}
.theme-toggle button{border:0;border-radius:0;padding:.46rem .6rem;background:transparent;color:var(--on-dark);font:700 .68rem Consolas,monospace;letter-spacing:.04em;cursor:pointer}
.theme-toggle button+button{border-left:1px solid var(--nav-border)}
.theme-toggle button.active{background:var(--mint);color:var(--on-light)}
.theme-toggle button:hover:not(.active){background:var(--on-ring)}

.main-content{min-height:calc(100vh - 96px)}
.page-wrap{max-width:1040px;margin:auto;padding:1.45rem 1rem 3.2rem;counter-reset:card}
.page-wrap.narrow{max-width:720px}
.page-title{margin:0 0 1.35rem;padding-bottom:1rem;border-bottom:1px solid var(--line);font-size:clamp(2rem,6vw,4rem);line-height:.92;letter-spacing:-.06em;font-weight:400}
.page-title::before{display:block;margin-bottom:.45rem;color:var(--teal);font:700 .72rem/1 Consolas,monospace;letter-spacing:.14em;text-transform:uppercase}
body[data-page="desk"] .page-title::before{content:'01 / desk'}
body[data-page="environment"] .page-title::before{content:'02 / environment'}
body[data-page="images"] .page-title::before{content:'03 / images'}
body[data-page="settings"] .page-title::before{content:'04 / configuration'}
.kicker{color:var(--teal);font:700 .72rem Consolas,monospace;letter-spacing:.14em;text-transform:uppercase}

.card{position:relative;background:var(--surface);border:1px solid var(--ink);border-radius:0;padding:1.05rem;margin-bottom:1rem;box-shadow:5px 5px 0 var(--line)}
.card::before{content:'';position:absolute;top:0;left:0;width:42px;height:4px;background:var(--teal)}
.card-title{display:flex;align-items:baseline;gap:.55rem;margin:0 0 1rem;padding-bottom:.65rem;border-bottom:1px solid var(--line);color:var(--ink);font:700 1.05rem Georgia,'Noto Serif TC',serif;letter-spacing:0;text-transform:none}
.card-title::before{counter-increment:card;content:counter(card,decimal-leading-zero);color:var(--coral);font:700 .7rem Consolas,monospace}
.danger-card{border-color:var(--coral);background:var(--danger-surface)}
.danger-card::before{background:var(--coral)}
.danger-card .card-title{color:var(--coral)}

.metric-grid,.stats-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.6rem;margin-bottom:1.2rem}
.metric,.stat{background:var(--inset);border:1px solid var(--line);border-radius:0;padding:.8rem .9rem;box-shadow:none;text-align:center;min-height:78px}
.stat-label,.stat-sub{font:700 .68rem Consolas,monospace;color:var(--muted)}
.stat-value{font:700 1.05rem/1.2 Consolas,monospace;color:var(--teal)}
.stat-unit{font:400 .78rem Consolas,monospace;color:var(--muted)}
.badge,.pill{display:inline-block;border-radius:0;padding:.18rem .4rem;min-width:3.2rem;text-align:center;color:var(--on-dark);font:700 .68rem Consolas,monospace}
.badge-green,.badge-occ,.pill.on{background:var(--teal)}
.badge-gray,.badge-unocc,.pill.off{background:var(--coral)}
.temp-val{color:var(--teal)}.hum-val{color:var(--teal)}.hi-val{color:var(--amber)}.lo-val{color:var(--coral)}

form{margin:0}
input,select,textarea{width:100%;padding:.64rem .68rem;border:1px solid var(--input-border);border-radius:0;background:var(--inset);color:var(--ink);font:700 .88rem Consolas,monospace}
input:focus,select:focus,textarea:focus{outline:2px solid var(--mint);outline-offset:1px;border-color:var(--teal)}
input::placeholder,textarea::placeholder{color:var(--placeholder);font-weight:400}
select option{background:var(--inset);color:var(--ink)}
label{display:block;margin-bottom:.3rem;color:var(--muted);font:700 .72rem Consolas,monospace;letter-spacing:.03em}
.f{margin-bottom:1rem}.f:last-child{margin-bottom:0}
.hint{font:400 .76rem Consolas,monospace;color:var(--muted);margin-left:.3rem}.hint strong,.hint b{color:var(--teal)}
.row2{display:flex;gap:.65rem}.row2 .f{flex:1;margin-bottom:0}
.sw{position:relative;width:2.7rem;height:1.35rem;flex-shrink:0}.sw input{position:absolute;opacity:0;width:1px;height:1px}.sl{position:absolute;inset:0;background:var(--line);border:1px solid var(--ink);border-radius:0;cursor:pointer;transition:background .2s}.sl::before{content:'';position:absolute;width:.85rem;height:.85rem;left:3px;top:3px;background:var(--surface);border-radius:50%;transition:transform .2s}.sw input:checked+.sl{background:var(--teal)}.sw input:checked+.sl::before{transform:translateX(1.25rem)}
.btn-row,.actions{display:flex;justify-content:flex-end;align-items:center;gap:.6rem;margin-top:1.1rem;flex-wrap:wrap}
button{border:1px solid var(--teal-dark);border-radius:0;padding:.7rem .85rem;cursor:pointer;background:var(--teal);color:var(--on-dark);font:700 .8rem Consolas,monospace}
button:hover,.btn-p:hover{background:var(--teal-dark)}
.btn-p{background:var(--teal);color:var(--on-dark);border-color:var(--teal-dark)}
.btn-s{background:var(--surface-2);border-color:var(--ink);color:var(--ink)}
.btn-s:hover,.btn-tf:hover{background:var(--line);color:var(--ink)}
.btn-d,.danger{background:var(--coral);border-color:var(--coral);color:var(--on-dark)}
.btn-d:hover,.danger:hover{background:var(--coral-dark)}
.btn-tf{background:transparent;border-color:var(--teal);color:var(--teal);padding:.32rem .65rem;white-space:nowrap}
.ghost{background:transparent;border-color:var(--teal);color:var(--teal)}
.ghost:hover{background:var(--teal);border-color:var(--teal);color:var(--on-dark)}
.btn-row button{min-width:145px}.actions button{flex:1;min-width:170px}
button:disabled{opacity:.55;cursor:wait}

.message{margin-bottom:1rem;padding:.8rem 1rem;border:1px solid var(--teal);border-left:5px solid var(--teal);background:var(--surface);font:700 .8rem/1.5 Consolas,monospace}
.message.error{border-color:var(--coral);color:var(--coral)}
.message.warn{border-color:var(--amber);color:var(--ink)}
.info{color:var(--muted);font-size:.82rem;line-height:1.5;margin:.85rem 0 0;padding:.65rem .75rem;background:var(--surface-2);border-left:3px solid var(--teal)}
.skeleton{background:var(--surface-2);border:1px solid var(--line);min-height:2.4rem}
.table-wrap,.stat-table-wrap{overflow-x:auto;border:1px solid var(--line)}
table{width:100%;border-collapse:collapse;background:var(--inset);font:400 .78rem Consolas,monospace}
th,td{padding:.62rem .65rem;border-bottom:1px solid var(--line);text-align:left;white-space:nowrap}
th{background:var(--surface-2);color:var(--teal-dark);font-size:.68rem;letter-spacing:.04em}
tbody tr:last-child td{border-bottom:0}

.status-banner{display:flex;align-items:center;justify-content:space-between;gap:1rem;padding:1rem 1.1rem;margin-bottom:1rem;background:var(--ink-soft);color:var(--on-dark);box-shadow:5px 5px 0 var(--line)}
.status-label{font:700 .7rem Consolas,monospace;letter-spacing:.12em;color:var(--mint)}
.status-value{margin-top:.25rem;font-size:1.5rem}.status-value::before{content:'';display:inline-block;width:.7rem;height:.7rem;margin:0 .45rem .08rem 0;background:var(--mint);border-radius:50%;box-shadow:0 0 0 4px var(--on-ring)}
.status-banner.state-off .status-value::before{background:var(--coral);box-shadow:0 0 0 4px var(--off-ring)}
.updated{color:var(--dark-block-muted);font:400 .7rem Consolas,monospace;text-align:right}
.legend-row{display:flex;gap:1rem;flex-wrap:wrap;color:var(--muted);font:400 .75rem Consolas,monospace;margin:.4rem 0}
.key{display:inline-block;width:.72rem;height:.72rem;margin-right:.3rem;vertical-align:-1px}.key.on{background:var(--teal)}.key.off{background:var(--coral)}.key.unknown{background:var(--unknown)}

canvas{display:block;width:100%;background:var(--inset);border:1px solid var(--line)}
svg text{font-family:Consolas,monospace}
#toast{position:fixed;right:1rem;bottom:1rem;z-index:10001;max-width:min(420px,calc(100vw - 2rem));padding:.8rem 1rem;border:1px solid var(--teal);border-left:5px solid var(--teal);background:var(--surface);color:var(--ink);font:700 .8rem Consolas,monospace;box-shadow:5px 5px 0 var(--line);opacity:0;transform:translateY(.4rem);transition:opacity .22s,transform .22s;pointer-events:none}
#toast.show{opacity:1;transform:none}#toast.err{border-color:var(--coral);border-left-color:var(--coral);color:var(--coral)}#toast.info{border-color:var(--amber);border-left-color:var(--amber)}

.site-footer{background:var(--ink-soft);color:var(--dark-block-muted);margin-top:2rem;padding:1.2rem 1rem}
.footer-in{max-width:1040px;margin:auto;display:flex;align-items:center;justify-content:space-between;gap:1rem;flex-wrap:wrap}
.footer-repo{display:flex;align-items:baseline;gap:.5rem;font:700 .74rem Consolas,monospace}.footer-repo .label{color:var(--mint);text-transform:uppercase;letter-spacing:.12em}
.footer-repo a{color:var(--on-dark);text-decoration:none;border-bottom:1px solid var(--nav-border)}.footer-repo a:hover{color:var(--mint);border-color:var(--mint)}
.footer-meta{color:var(--dark-block-muted);font:400 .7rem Consolas,monospace}

.login-wrap{max-width:22rem;margin:4rem auto;padding:0 1rem}.login-tools{position:fixed;top:1rem;right:1rem}

@media(min-width:760px){.metric-grid,.stats-grid{grid-template-columns:repeat(6,minmax(0,1fr))}}
@media(max-width:720px){
  .topbar-in{align-items:flex-start;flex-direction:column}.topbar-actions{justify-content:flex-start}.nav{justify-content:flex-start}
  .status-banner{align-items:flex-start;flex-direction:column}.updated{text-align:left}.row2{flex-direction:column;gap:0}.page-wrap{padding-top:1rem}
}
@media(max-width:480px){.metric-grid,.stats-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.footer-in{flex-direction:column;align-items:flex-start}.login-tools{top:.6rem;right:.6rem}}
"""

_CSRF_FETCH_SCRIPT = r"""(function(){
  function cookieValue(name){
    var prefix=name+'=';
    return document.cookie.split(';').map(function(part){return part.trim()}).filter(function(part){return part.indexOf(prefix)===0})[0]?.slice(prefix.length)||'';
  }
  var nativeFetch=window.fetch.bind(window);
  window.fetch=function(input,init){
    var options=init?Object.assign({},init):{};
    var method=(options.method||(input&&input.method)||'GET').toUpperCase();
    var url;
    try{url=new URL(typeof input==='string'?input:input.url,window.location.href)}catch(e){return nativeFetch(input,options)}
    if(url.origin===window.location.origin&&!/^(GET|HEAD|OPTIONS|TRACE)$/.test(method)){
      var token=cookieValue('csrf');
      if(token){
        var headers=new Headers(options.headers||(typeof Request!=='undefined'&&input instanceof Request?input.headers:undefined));
        headers.set('X-CSRF-Token',token);options.headers=headers;
      }
    }
    return nativeFetch(input,options);
  };
  function showLogoutError(message){
    var toast=document.getElementById('toast');
    if(toast){toast.textContent=message;toast.className='show err';}
    else{window.alert(message);}
  }
  window.postLogout=async function(){
    var response;
    try{response=await window.fetch('/logout',{method:'POST'});}
    catch(e){showLogoutError('登出失敗，請確認網路後再試');return;}
    if(!response.ok){showLogoutError('登出失敗，請重新整理後再試');return;}
    window.location.href='/login';
  };
  document.querySelectorAll('[data-action="logout"]').forEach(function(button){
    button.addEventListener('click',function(){window.postLogout()});
  });
})();"""

_THEME_CONTROL_SCRIPT = r"""(function(){
  function sync(){
    var current=document.documentElement.dataset.theme;
    document.querySelectorAll('[data-theme-choice]').forEach(function(button){
      var active=button.dataset.themeChoice===current;
      button.classList.toggle('active',active);button.setAttribute('aria-pressed',active?'true':'false');
    });
  }
  function setTheme(theme){
    if(theme!=='light'&&theme!=='dark')return;
    document.documentElement.dataset.theme=theme;
    try{localStorage.setItem('iot-ui-theme',theme)}catch(e){}
    sync();
    document.dispatchEvent(new CustomEvent('iot-theme-change'));
  }
  document.querySelectorAll('[data-theme-choice]').forEach(function(button){
    button.addEventListener('click',function(){setTheme(button.dataset.themeChoice)});
  });
  sync();
})();"""

_FAVICON_DATA_URI = (
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E"
    "%3Crect width='32' height='32' fill='%230a100d'/%3E"
    "%3Crect x='2' y='2' width='28' height='28' fill='none' stroke='%23a8d2c4' stroke-width='2'/%3E"
    "%3Ctext x='16' y='21' font-family='Consolas,monospace' font-size='12' font-weight='700' "
    "fill='%23a8d2c4' text-anchor='middle'%3EEH%3C/text%3E%3C/svg%3E"
)
