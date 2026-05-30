_DESK_HTML = r"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>書桌前分析</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,600;9..40,700&family=DM+Mono:wght@400;500&display=swap">
  <style>
    *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
    :root{
      --bg:#080d18;--surface:#0f172a;--surface2:#1a253d;--border:#1e3a5f;
      --primary:#38bdf8;--primary-h:#0ea5e9;--green:#34d399;--amber:#fbbf24;--red:#f87171;
      --muted:#64748b;--text:#e2e8f0;
      --r:10px;--sh:0 2px 12px rgba(0,0,0,.4)
    }
    body{font-family:'DM Sans',system-ui,sans-serif;background:var(--bg);color:var(--text);min-height:100vh}
    .topbar{display:flex;align-items:center;justify-content:space-between;padding:.9rem 1.5rem;background:rgba(15,23,42,.85);backdrop-filter:blur(8px);border-bottom:1px solid var(--border);position:sticky;top:0;z-index:10}
    .topbar-title{font-size:1.1rem;font-weight:600}
    .topbar-link{font-size:.8rem;color:var(--primary);text-decoration:none;padding:.3rem .7rem;border:1px solid var(--primary);border-radius:6px}
    .container{max-width:900px;margin:0 auto;padding:1.5rem}
    .card{background:var(--surface);border:1px solid var(--border);border-radius:var(--r);padding:1.3rem;box-shadow:var(--sh);margin-bottom:1.2rem}
    .card-title{font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.07em;color:var(--muted);margin-bottom:1rem}
    .stats-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:.8rem;margin-bottom:1.2rem}
    .stat{background:var(--surface);border:1px solid var(--border);border-radius:var(--r);padding:1rem 1.2rem;box-shadow:var(--sh)}
    .stat-label{font-size:.72rem;color:var(--muted);margin-bottom:.3rem}
    .stat-value{font-size:1.5rem;font-weight:700;line-height:1.2;font-family:'DM Mono',monospace}
    .stat-sub{font-size:.72rem;color:var(--muted);margin-top:.2rem}
    .badge{display:inline-block;padding:.2rem .65rem;border-radius:99px;font-size:.78rem;font-weight:600}
    .badge-green{background:rgba(52,211,153,.15);color:#34d399}
    .badge-gray{background:rgba(100,116,139,.15);color:#94a3b8}
    .sensor-row{display:flex;align-items:center;gap:1rem;font-size:.85rem;flex-wrap:wrap}
    .sensor-bar-wrap{flex:1;min-width:180px}
    .sensor-bar{height:8px;background:var(--surface2);border-radius:4px;position:relative;overflow:visible}
    .sensor-fill{height:100%;border-radius:4px;background:var(--primary);transition:width .4s}
    .sensor-threshold-line{position:absolute;top:-3px;bottom:-3px;width:2px;background:var(--amber);border-radius:1px}
    .chart-wrap{overflow-x:auto}
    table{width:100%;border-collapse:collapse;font-size:.82rem}
    th{text-align:left;padding:.5rem .7rem;font-size:.72rem;color:var(--muted);font-weight:600;border-bottom:1px solid var(--border)}
    td{padding:.5rem .7rem;border-bottom:1px solid rgba(30,58,95,.5)}
    tr:last-child td{border-bottom:none}
    .badge-occ{background:rgba(56,189,248,.15);color:#7dd3fc}
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
    bars+='<rect x="'+x1+'" y="6" width="'+w+'" height="36" rx="3" fill="#38bdf8" opacity="'+opacity+'"/>';
  });
  var labels='';
  for(var h=0;h<=24;h+=6){
    var x=h/24*W;
    var t=new Date(start24+h*3600000);
    var lbl=String(t.getHours()).padStart(2,'0')+':00';
    var anchor=h===0?'start':h===24?'end':'middle';
    labels+='<text x="'+x+'" y="'+H+'" text-anchor="'+anchor+'" font-size="10" fill="#64748b">'+lbl+'</text>';
    labels+='<line x1="'+x+'" y1="44" x2="'+x+'" y2="47" stroke="#475569" stroke-width="1"/>';
  }
  return '<svg viewBox="0 0 '+W+' '+(H+2)+'" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;min-width:320px">'
    +'<rect width="'+W+'" height="48" rx="4" fill="#0f172a"/>'
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
    bars+='<rect x="'+(x+1)+'" y="'+y+'" width="'+bW+'" height="'+h+'" rx="2" fill="#38bdf8" opacity="'+opacity+'"/>';
    if(i%7===0||i===29){
      var lbl=d.date.slice(5);
      labels+='<text x="'+(x+bW/2)+'" y="'+(svgH-2)+'" text-anchor="middle" font-size="9" fill="#64748b">'+lbl+'</text>';
    }
  });
  return '<svg viewBox="0 0 '+W+' '+svgH+'" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;min-width:320px">'
    +'<rect width="'+W+'" height="'+svgH+'" rx="4" fill="#0f172a"/>'
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
