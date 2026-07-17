from app.webui.templates.base import _make_shell


_DESK_CONTENT = r"""
<style>
  :root{--heat-0:#e7e3d6;--heat-1:#c9e1d7;--heat-2:#8fc4b4;--heat-3:#4b9b8e;--heat-4:#0b716a}
  :root[data-theme="dark"]{--heat-0:#24312c;--heat-1:#1e4f47;--heat-2:#1d7568;--heat-3:#1fae9c;--heat-4:#8ad7c5}
  .desk-heading{display:flex;align-items:flex-end;justify-content:space-between;gap:1.5rem;margin:.4rem 0 1.25rem}
  .desk-heading .page-title{flex:0 0 auto;margin:.45rem 0 0;padding:0;border:0;font-weight:700}
  .desk-heading .page-desc{flex:0 1 30rem;max-width:30rem;margin:0;line-height:1.55}
  .desk-error{display:block}
  .desk-error.is-hidden{display:none}
  .desk-summary-grid{margin-bottom:0}
  .desk-summary-grid .metric{min-height:78px}
  .metric label{display:block;color:var(--muted);font:700 .68rem Consolas,monospace;letter-spacing:.03em}
  .metric span{display:block;margin-top:.35rem;color:var(--teal);font:700 1.05rem Consolas,monospace;overflow-wrap:anywhere}
  .metric.state-off span{color:var(--coral)}
  .metric.state-off .pill{color:var(--on-dark)}
  .metric .pill{display:inline-block;color:var(--on-dark);font-size:.68rem}
  .pill.on{background:var(--teal)}
  .pill.off{background:var(--coral)}
  .pill.unknown{background:var(--unknown)}
  .desk-info{margin:.85rem 0 0}
  .sensor-meter{position:relative;height:1.15rem;margin:1.1rem 0 .4rem;background:var(--surface-2);border:1px solid var(--line)}
  .sensor-fill{height:100%;width:0;background:var(--teal);transition:width .2s ease}
  .threshold-mark{position:absolute;top:-.45rem;bottom:-.45rem;width:2px;background:var(--amber);transform:translateX(-1px)}
  .sensor-scale{display:flex;justify-content:space-between;color:var(--muted);font:400 .68rem Consolas,monospace}
  .sensor-readings{display:flex;justify-content:space-between;gap:1rem;margin-top:.8rem;font:700 .78rem Consolas,monospace}
  .sensor-readings strong{color:var(--teal)}
  .desk-canvas{display:block;width:100%;background:var(--inset);border:1px solid var(--line)}
  #timeline{height:80px}
  #daily-chart{height:280px}
  .heatmap-controls{flex-wrap:wrap;margin-top:-.25rem;margin-bottom:.7rem}
  .heatmap-period{min-width:8rem;text-align:center;white-space:nowrap}
  .heatmap-wrap{overflow-x:auto;border:1px solid var(--line);background:var(--inset);padding:.65rem .55rem .5rem}
  .heatmap-canvas{min-width:760px;height:154px;margin:0;border:0;background:transparent}
  .heatmap-legend{display:flex;align-items:center;gap:.35rem;margin:.65rem 0 0;color:var(--muted);font:400 .68rem Consolas,monospace}
  .heatmap-legend .key{margin-right:0}
  .heatmap-legend .key.heat-0{background:var(--heat-0)}
  .heatmap-legend .key.heat-1{background:var(--heat-1)}
  .heatmap-legend .key.heat-2{background:var(--heat-2)}
  .heatmap-legend .key.heat-3{background:var(--heat-3)}
  .heatmap-legend .key.heat-4{background:var(--heat-4)}
  .table-wrap{overflow-x:auto;border:1px solid var(--line)}
  .desk-table{width:100%;border-collapse:collapse;background:var(--inset);font:400 .78rem Consolas,monospace}
  .desk-table th,.desk-table td{padding:.62rem .65rem;border-bottom:1px solid var(--line);text-align:left;white-space:nowrap}
  .desk-table th{background:var(--surface-2);color:var(--teal-dark);font-size:.68rem;letter-spacing:.04em}
  .desk-table tbody tr:last-child td{border-bottom:0}
  .data-date{color:var(--muted);font-size:.72rem}
  .desk-table .empty-row td{text-align:center;color:var(--muted);padding:1rem}
  .desk-tip{position:fixed;pointer-events:none;display:none;z-index:10002;max-width:240px;padding:.45rem .65rem;background:var(--ink-soft);color:var(--on-dark);font:700 .72rem/1.45 Consolas,monospace;border:1px solid var(--mint);box-shadow:5px 5px 0 var(--line)}
  @media(max-width:720px){.desk-heading{display:block}.desk-heading .page-desc{margin-top:.65rem}}
  @media(max-width:480px){.sensor-readings{align-items:flex-start;flex-direction:column;gap:.25rem}.metric-grid .metric:last-child{grid-column:auto}}
</style>

<div class="page-wrap">
  <div class="desk-heading">
    <h1 class="page-title">書桌前分析</h1>
    <p class="page-desc">以光感測器記錄桌前狀態。資料每 30 秒更新一次，分析最近 24 小時、30 天與 1 年變化。</p>
  </div>

  <div class="message error desk-error is-hidden" id="desk-error" aria-live="polite"></div>
  <div class="loading-state" id="desk-loading" aria-live="polite" hidden>載入中…</div>

  <div class="status-banner" id="status-banner" aria-live="polite">
    <div>
      <div class="status-label">LIVE SENSOR STATUS</div>
      <div class="status-value" id="banner-presence">讀取中…</div>
    </div>
    <div class="updated">最後切換<br><strong id="last-change">—</strong></div>
  </div>

  <section class="card">
    <div class="card-title">總覽</div>
    <div class="metric-grid">
      <div class="metric" id="state-box"><label>目前狀態</label><span id="s-presence" class="pill">—</span></div>
      <div class="metric"><label>今日累計</label><span id="s-today">—</span></div>
      <div class="metric"><label>目前時段</label><span id="s-segment">—</span></div>
      <div class="metric"><label>今日切換次數</label><span id="s-count">—</span></div>
      <div class="metric"><label>光線數值</label><span id="s-light">—</span></div>
      <div class="metric"><label>光線閾值</label><span id="s-thresh">—</span></div>
    </div>
    <p class="info desk-info">當光線數值低於目前設定檔的光線閾值時，會記錄為在桌前；其他時間則記錄為離開。</p>
  </section>

  <section class="card">
    <div class="card-title">光線感測器</div>
    <div class="sensor-meter" role="progressbar" aria-label="目前光線數值" aria-valuemin="0" aria-valuemax="1023" aria-valuenow="0">
      <div class="sensor-fill" id="sensor-fill"></div>
      <span class="threshold-mark" id="threshold-marker" aria-hidden="true"></span>
    </div>
    <div class="sensor-scale"><span>0</span><span>1023</span></div>
    <div class="sensor-readings"><span>目前數值 <strong id="sensor-value">—</strong></span><span>閾值 <strong id="threshold-value">—</strong></span></div>
  </section>

  <section class="card">
    <div class="card-title">近 24 小時狀態軸</div>
    <div class="legend-row" aria-label="狀態顏色圖例">
      <span><i class="key on"></i>在桌前</span><span><i class="key off"></i>離開</span><span><i class="key unknown"></i>資料不足</span>
    </div>
    <canvas id="timeline" class="desk-canvas" width="900" height="80" aria-label="近 24 小時在桌前與離開的狀態軸"></canvas>
  </section>

  <section class="card">
    <div class="card-title">近 30 天書桌前時間</div>
    <div class="summary-grid">
      <div class="metric"><label>平均</label><span id="avg30">—</span></div>
      <div class="metric"><label>最高一天</label><span id="max30">—</span></div>
      <div class="metric"><label>有記錄天數</label><span id="days-count30">—</span></div>
    </div>
    <canvas id="daily-chart" class="desk-canvas" width="900" height="280" aria-label="近 30 天每日書桌前時間圖表"></canvas>
  </section>

  <section class="card">
    <div class="card-title">年度書桌前熱力圖</div>
    <div class="pagination heatmap-controls" role="group" aria-label="熱力圖年份切換">
      <button type="button" class="ghost" id="heatmap-prev" aria-label="較早年份">&#8249;</button>
      <span class="heatmap-period" id="heatmap-period" aria-live="polite">最近 365 天</span>
      <button type="button" class="ghost" id="heatmap-next" aria-label="較新年份">&#8250;</button>
    </div>
    <div class="heatmap-wrap">
      <canvas id="heatmap-canvas" class="heatmap-canvas" width="900" height="154" tabindex="0" aria-label="最近 365 天每日書桌前時間熱力圖"></canvas>
      <div class="heatmap-legend" aria-hidden="true">
        <span>少</span><i class="key heat-0"></i><i class="key heat-1"></i><i class="key heat-2"></i><i class="key heat-3"></i><i class="key heat-4"></i><span>多</span>
      </div>
    </div>
    <p class="info desk-info">每個色塊代表一天；顏色越深，當天在桌前的時間越長。灰色代表尚無資料。</p>
  </section>

  <section class="card">
    <div class="card-title">每日統計</div>
    <div class="table-wrap">
      <table class="desk-table" id="daily-table">
        <thead><tr><th>日期</th><th>書桌前</th><th>比例</th><th>切換次數</th></tr></thead>
        <tbody id="daily-tbody" aria-live="polite"><tr class="empty-row"><td colspan="4">載入中…</td></tr></tbody>
      </table>
    </div>
    <div class="pagination" aria-label="每日統計分頁">
      <button type="button" class="ghost" id="daily-prev">&#8249; 上一頁</button>
      <span class="pagination-info" id="daily-page-info" aria-live="polite">第 1 / 1 頁</span>
      <button type="button" class="ghost" id="daily-next">下一頁 &#8250;</button>
    </div>
  </section>

  <section class="card">
    <div class="card-title">最近時段紀錄</div>
    <div class="table-wrap">
      <table class="desk-table" id="sessions-table">
        <thead><tr><th>開始</th><th>結束</th><th>持續時間</th></tr></thead>
        <tbody id="sessions-tbody" aria-live="polite"><tr class="empty-row"><td colspan="3">載入中…</td></tr></tbody>
      </table>
    </div>
    <div class="pagination" aria-label="最近時段紀錄分頁">
      <button type="button" class="ghost" id="sessions-prev">&#8249; 上一頁</button>
      <span class="pagination-info" id="sessions-page-info" aria-live="polite">第 1 / 1 頁</span>
      <button type="button" class="ghost" id="sessions-next">下一頁 &#8250;</button>
    </div>
  </section>
</div>
<div class="desk-tip" id="desk-tip" role="tooltip"></div>

<script>
var PAGE_SIZE=10;
var deskData={status:null,timeline:[],daily30:[],dailyHistory:[],sessions:[]};
var dailyPage=1,sessionsPage=1,loading=false;
var dailyBars=[],heatmapCells=[],heatmapYear=null,heatmapYears=[],heatmapCache={},heatmapRequestSeq=0;
var heatmapResizeTimer;

function pad(value){return String(value).padStart(2,'0');}
function fmtDuration(seconds){
  seconds=Math.max(0,Number(seconds)||0);
  var hours=Math.floor(seconds/3600),minutes=Math.floor(seconds%3600/60);
  return hours+'h '+minutes+'m';
}
function dateKeyFromDate(date){return date.getFullYear()+pad(date.getMonth()+1)+pad(date.getDate());}
function dateFromKey(key){return new Date(Number(key.slice(0,4)),Number(key.slice(4,6))-1,Number(key.slice(6,8)),12);}
function dateKeyFromIso(value){
  var match=String(value||'').match(/^(\d{4})-(\d{2})-(\d{2})/);
  return match?match[1]+match[2]+match[3]:'';
}
function dateText(value){
  var key=/^\d{8}$/.test(String(value||''))?String(value):dateKeyFromIso(value);
  return /^\d{8}$/.test(key)?key.slice(0,4)+'-'+key.slice(4,6)+'-'+key.slice(6,8):'—';
}
function displayTimeZone(){return deskData.status&&deskData.status.timezone||undefined;}
function timeText(value){
  if(!value)return '—';
  var date=new Date(value);
  if(Number.isNaN(date.getTime()))return '—';
  var options={hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false},zone=displayTimeZone();
  if(zone)options.timeZone=zone;
  return date.toLocaleTimeString('zh-TW',options);
}
function dateTimeText(value){
  if(!value)return '進行中';
  var date=new Date(value);
  if(Number.isNaN(date.getTime()))return '—';
  var options={year:'numeric',month:'2-digit',day:'2-digit'},zone=displayTimeZone();
  if(zone)options.timeZone=zone;
  var parts=date.toLocaleDateString('en-US',options).split('/');
  return parts[2]+'-'+parts[0]+'-'+parts[1]+' '+timeText(value);
}
function chartColor(name){return getComputedStyle(document.documentElement).getPropertyValue(name).trim();}
function pct(seconds){return Math.round(Math.max(0,Math.min(86400,Number(seconds)||0))*100/86400)+'%';}
function esc(value){return String(value==null?'':value).replace(/[&<>"']/g,function(char){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char];});}

function fitCanvas(canvas){
  var rect=canvas.getBoundingClientRect();
  var cssW=rect.width||canvas.clientWidth||900;
  var cssH=rect.height||canvas.clientHeight||parseFloat(getComputedStyle(canvas).height)||Number(canvas.getAttribute('height'))||150;
  var dpr=window.devicePixelRatio||1;
  canvas.width=Math.max(1,Math.round(cssW*dpr));
  canvas.height=Math.max(1,Math.round(cssH*dpr));
  var context=canvas.getContext('2d');
  context.setTransform(dpr,0,0,dpr,0,0);
  return {g:context,w:cssW,h:cssH};
}

function updateSensor(status){
  var raw=Number(status&&status.light_raw),threshold=Number(status&&status.threshold),max=1023;
  var validRaw=Number.isFinite(raw)&&raw>=0,validThreshold=Number.isFinite(threshold)&&threshold>=0;
  var fill=validRaw?Math.max(0,Math.min(100,raw*100/max)):0;
  var mark=validThreshold?Math.max(0,Math.min(100,threshold*100/max)):0;
  var meter=document.querySelector('.sensor-meter');
  document.getElementById('sensor-fill').style.width=fill+'%';
  document.getElementById('threshold-marker').style.left=mark+'%';
  document.getElementById('sensor-value').textContent=validRaw?raw:'—';
  document.getElementById('threshold-value').textContent=validThreshold?threshold:'—';
  meter.setAttribute('aria-valuenow',validRaw?raw:0);
  meter.setAttribute('aria-valuetext',validRaw?raw+' / '+(validThreshold?threshold:'—'):'尚無資料');
}

function updateStatus(status){
  var occupied=status&&status.presence==='OCCUPIED';
  var known=occupied||(status&&status.presence==='UNOCCUPIED');
  var label=known?(occupied?'在桌前':'離開'):'未知';
  var stateBox=document.getElementById('state-box'),banner=document.getElementById('status-banner');
  document.getElementById('s-presence').textContent=label;
  document.getElementById('s-presence').className='pill '+(known?(occupied?'on':'off'):'unknown');
  stateBox.className='metric '+(known&&!occupied?'state-off':'');
  banner.className='status-banner '+(known&&!occupied?'state-off':'');
  document.getElementById('banner-presence').textContent=label;
  document.getElementById('s-today').textContent=fmtDuration(status&&status.today_total_seconds);
  document.getElementById('s-segment').textContent=fmtDuration(status&&status.current_segment_seconds);
  document.getElementById('s-count').textContent=(Number(status&&status.today_session_count)||0)+' 次';
  document.getElementById('s-light').textContent=status&&status.light_raw!=null?status.light_raw:'—';
  document.getElementById('s-thresh').textContent=status&&status.threshold!=null?status.threshold:'—';
  document.getElementById('last-change').textContent=status&&status.last_change_ts?dateTimeText(status.last_change_ts):'—';
  var now=status&&Number(status.now_epoch);
  document.getElementById('last-refresh').textContent='最後更新：'+(Number.isFinite(now)&&now>0?timeText(new Date(now*1000).toISOString()):'—');
  updateSensor(status||{});
}

function paginate(rows,page){
  var totalPages=Math.max(1,Math.ceil(rows.length/PAGE_SIZE));
  page=Math.min(Math.max(1,page),totalPages);
  return {rows:rows.slice((page-1)*PAGE_SIZE,page*PAGE_SIZE),page:page,totalPages:totalPages};
}
function updatePagination(prevId,nextId,infoId,page,totalPages){
  document.getElementById(prevId).disabled=page<=1;
  document.getElementById(nextId).disabled=page>=totalPages;
  document.getElementById(infoId).textContent='第 '+page+' / '+totalPages+' 頁';
}
function renderDailyPage(){
  var result=paginate(deskData.daily30.slice().reverse(),dailyPage);dailyPage=result.page;
  var rows=result.rows.map(function(item){
    return '<tr><td>'+esc(item.date)+'</td><td>'+fmtDuration(item.total_seconds)+'</td><td>'+pct(item.total_seconds)+'</td><td>'+(Number(item.session_count)||0)+'</td></tr>';
  }).join('');
  document.getElementById('daily-tbody').innerHTML=rows||'<tr class="empty-row"><td colspan="4">無資料</td></tr>';
  updatePagination('daily-prev','daily-next','daily-page-info',result.page,result.totalPages);
}
function renderSessionsPage(){
  var rows=deskData.sessions.slice().sort(function(a,b){return String(b.start_ts||'').localeCompare(String(a.start_ts||''));});
  var result=paginate(rows,sessionsPage);sessionsPage=result.page;
  var html=result.rows.map(function(session){
    var end=session.end_ts?esc(dateTimeText(session.end_ts)):'<span class="pill on">進行中</span>';
    var duration=session.duration_seconds==null?'—':fmtDuration(session.duration_seconds);
    return '<tr><td>'+esc(dateTimeText(session.start_ts))+'</td><td>'+end+'</td><td>'+duration+'</td></tr>';
  }).join('');
  document.getElementById('sessions-tbody').innerHTML=html||'<tr class="empty-row"><td colspan="3">無紀錄</td></tr>';
  updatePagination('sessions-prev','sessions-next','sessions-page-info',result.page,result.totalPages);
}

function dailyChartRows(data,status){
  var rows=data||[],map={},todayKey=dateKeyFromIso(status&&status.current_date);
  rows.forEach(function(item){var key=dateKeyFromIso(item.date);if(key)map[key]=item;});
  if(!/^\d{8}$/.test(todayKey)){
    var now=new Date();now.setHours(12,0,0,0);todayKey=dateKeyFromDate(now);
  }
  if(status&&/^\d{8}$/.test(todayKey))map[todayKey]={date:dateText(todayKey),total_seconds:Math.max(0,Number(status.today_total_seconds)||0),session_count:Number(status.today_session_count)||0};
  var end=dateFromKey(todayKey),start=new Date(end),result=[];
  start.setDate(end.getDate()-29);
  for(var i=0;i<30;i++){
    var date=new Date(start);date.setDate(start.getDate()+i);
    var key=dateKeyFromDate(date),item=map[key];
    result.push({date:dateText(key),key:key,total_seconds:item?Math.max(0,Number(item.total_seconds)||0):0,session_count:item?Number(item.session_count)||0:0,hasData:!!item});
  }
  return result;
}
function updateDailySummary(rows){
  var recorded=rows.filter(function(item){return item.hasData&&(item.total_seconds>0||item.session_count>0);});
  var sum=rows.reduce(function(total,item){return total+item.total_seconds;},0);
  var max=recorded.reduce(function(best,item){return item.total_seconds>best.total_seconds?item:best;},{date:'',total_seconds:0});
  document.getElementById('avg30').textContent=rows.length?fmtDuration(sum/rows.length):'—';
  document.getElementById('max30').textContent=max.date?max.date+' '+fmtDuration(max.total_seconds):'—';
  document.getElementById('days-count30').textContent=recorded.length;
}
function drawDaily(){
  var fit=fitCanvas(document.getElementById('daily-chart')),g=fit.g,w=fit.w,h=fit.h;
  var rows=dailyChartRows(deskData.daily30,deskData.status),left=44,chartHeight=h-64;
  var ink=chartColor('--ink'),inset=chartColor('--inset'),grid=chartColor('--chart-grid'),muted=chartColor('--muted'),teal=chartColor('--teal');
  g.clearRect(0,0,w,h);g.fillStyle=inset;g.fillRect(0,0,w,h);g.font='12px Consolas,monospace';g.fillStyle=muted;
  for(var i=0;i<=4;i++){
    var y=20+chartHeight*i/4;g.strokeStyle=grid;g.beginPath();g.moveTo(left,y);g.lineTo(w-14,y);g.stroke();g.fillText(24-6*i+'h',8,y+4);
  }
  var barWidth=(w-left-18)/Math.max(1,rows.length);dailyBars=[];
  rows.forEach(function(item,index){
    var seconds=item.total_seconds,barHeight=chartHeight*Math.min(1,seconds/86400),x=left+4+index*barWidth,width=Math.max(3,barWidth-5);
    if(seconds>0){g.fillStyle=teal;g.fillRect(x,h-44-barHeight,width,barHeight);dailyBars.push({x:x,y:h-44-barHeight,w:width,h:barHeight,date:item.date,total_seconds:seconds});}
    if((index%5===0||index===rows.length-1)&&item.key){g.fillStyle=muted;g.font='10px Consolas,monospace';g.textAlign='center';g.fillText(item.key.slice(6,8),x+width/2,h-18);g.textAlign='left';g.font='12px Consolas,monospace';}
  });
  g.fillStyle=ink;g.fillText('最近 30 天每日在桌前時間',left,16);updateDailySummary(rows);
}

function drawBand(g,x,y,width,height,color){g.fillStyle=color;g.fillRect(x,y,Math.max(1,width),height);g.strokeStyle=chartColor('--inset');g.strokeRect(x,y,Math.max(1,width),height);}
function drawTimeline(){
  var fit=fitCanvas(document.getElementById('timeline')),g=fit.g,w=fit.w,h=fit.h;
  var now=Number(deskData.status&&deskData.status.now_epoch)||Math.floor(Date.now()/1000),start=now-86400,x0=70,x1=w-16,top=18,bh=26;
  var inset=chartColor('--inset'),grid=chartColor('--chart-grid'),muted=chartColor('--muted'),ink=chartColor('--ink'),teal=chartColor('--teal'),coral=chartColor('--coral'),unknown=chartColor('--unknown');
  g.clearRect(0,0,w,h);g.fillStyle=inset;g.fillRect(0,0,w,h);g.font='12px Consolas,monospace';g.fillStyle=muted;
  for(var i=0;i<=6;i++){
    var x=x0+(x1-x0)*i/6;g.strokeStyle=grid;g.beginPath();g.moveTo(x,12);g.lineTo(x,48);g.stroke();
    var label=clockText(now-(24-4*i)*3600);g.fillText(label,x-15,h-6);
  }
  drawBand(g,x0,top,x1-x0,bh,unknown);
  var occupied=(deskData.timeline||[]).map(function(session){
    var from=new Date(session.start_ts).getTime()/1000,to=session.end_ts?new Date(session.end_ts).getTime()/1000:now;
    return {from:Math.max(start,from),to:Math.min(now,to)};
  }).filter(function(interval){return Number.isFinite(interval.from)&&Number.isFinite(interval.to)&&interval.to>interval.from;}).sort(function(a,b){return a.from-b.from;});
  var cursor=start;
  occupied.forEach(function(interval){
    if(interval.from>cursor)drawBand(g,x0+(x1-x0)*(cursor-start)/86400,top,(x1-x0)*(interval.from-cursor)/86400,bh,coral);
    drawBand(g,x0+(x1-x0)*(interval.from-start)/86400,top,(x1-x0)*(interval.to-interval.from)/86400,bh,teal);
    cursor=Math.max(cursor,interval.to);
  });
  if(occupied.length&&cursor<now)drawBand(g,x0+(x1-x0)*(cursor-start)/86400,top,(x1-x0)*(now-cursor)/86400,bh,coral);
  g.fillStyle=ink;g.fillText('最近 24 小時',x0,10);
}
function clockText(epoch){
  var value=timeText(new Date(epoch*1000).toISOString());
  return value==='—'?'—':value.slice(0,5);
}

function heatLevel(seconds,hasData){return hasData?Math.max(1,Math.min(4,Math.ceil(Math.max(0,Number(seconds)||0)*4/86400))):0;}
function availableHeatmapYears(history,status){
  var years={},current=String(status&&status.current_date||'');
  if(/^\d{4}-\d{2}-\d{2}$/.test(current))years[current.slice(0,4)]=true;
  (history||[]).forEach(function(item){var key=dateKeyFromIso(item.date),hasData=(Number(item&&item.session_count)||0)>0||(Number(item&&item.total_seconds)||0)>0;if(key&&hasData)years[key.slice(0,4)]=true;});
  return Object.keys(years).sort(function(a,b){return Number(a)-Number(b);});
}
function syncHeatmapControls(){
  var previous=document.getElementById('heatmap-prev'),next=document.getElementById('heatmap-next'),period=document.getElementById('heatmap-period');
  if(heatmapYear!==null&&heatmapYears.indexOf(String(heatmapYear))<0)heatmapYear=null;
  period.textContent=heatmapYear===null?'最近 365 天':heatmapYear+' 年';period.setAttribute('aria-label',period.textContent);
  previous.disabled=heatmapYears.length===0;next.disabled=heatmapYears.length===0;
}
function selectHeatmapYear(year){
  var value=String(year||'');heatmapYear=/^\d{4}$/.test(value)?Number(value):null;syncHeatmapControls();renderHeatmap();
}
function changeHeatmapYear(direction){
  if(!heatmapYears.length)return;
  var index=heatmapYear===null?(direction<0?0:heatmapYears.length-1):heatmapYears.indexOf(String(heatmapYear));
  if(index<0)return;
  var nextIndex=index+direction;
  if(heatmapYear===null||nextIndex<0||nextIndex>=heatmapYears.length){
    if(heatmapYear!==null)selectHeatmapYear(null);else selectHeatmapYear(heatmapYears[direction<0?0:heatmapYears.length-1]);
    return;
  }
  selectHeatmapYear(heatmapYears[nextIndex]);
}
function heatmapDateRows(){
  var history=deskData.dailyHistory||[],map={},status=deskData.status||{},todayKey=/^\d{4}-\d{2}-\d{2}$/.test(status.current_date)?dateKeyFromIso(status.current_date):'';
  history.forEach(function(item){var key=dateKeyFromIso(item.date);if(key)map[key]=item;});
  if(todayKey)map[todayKey]={date:dateText(todayKey),total_seconds:Math.max(0,Number(status.today_total_seconds)||0),session_count:Number(status.today_session_count)||0};
  return map;
}
function renderHeatmapGrid(rows,startKey,dayCount,label){
  var canvas=document.getElementById('heatmap-canvas'),fit=fitCanvas(canvas),g=fit.g,w=fit.w,h=fit.h,map={};
  rows.forEach(function(item){var key=dateKeyFromIso(item.date)||item.key;if(key)map[key]=item;});
  var start=dateFromKey(startKey),startDay=start.getDay(),weeks=Math.floor((dayCount-1+startDay)/7)+1,left=31,top=21,gap=3;
  var cell=Math.max(5,Math.min(14,(w-left-8-(weeks-1)*gap)/weeks));
  var inset=chartColor('--inset'),muted=chartColor('--muted');
  g.clearRect(0,0,w,h);g.fillStyle=inset;g.fillRect(0,0,w,h);g.font='10px Consolas,monospace';g.fillStyle=muted;
  ['日','一','三','五'].forEach(function(day,index){var row=index*2;g.fillText(day,3,top+row*(cell+gap)+cell-1);});
  heatmapCells=[];var lastMonthX=-999;
  for(var offset=0;offset<dayCount;offset++){
    var date=new Date(start);date.setDate(start.getDate()+offset);
    var row=date.getDay(),column=Math.floor((offset+startDay)/7),x=left+column*(cell+gap),y=top+row*(cell+gap),key=dateKeyFromDate(date),item=map[key],seconds=item?Number(item.total_seconds)||0:0,hasData=!!item&&((Number(item.session_count)||0)>0||seconds>0),status=item&&item.status;
    if(date.getDate()===1&&x-lastMonthX>28){g.fillStyle=muted;g.fillText((date.getMonth()+1)+'月',x,11);lastMonthX=x;}
    g.fillStyle=chartColor('--heat-'+(status==='future'?0:heatLevel(seconds,hasData)));g.fillRect(x,y,cell,cell);
    heatmapCells.push({x:x,y:y,w:cell,h:cell,date:key,total_seconds:seconds,hasData:hasData,status:status});
  }
  canvas.setAttribute('aria-label',label+'每日書桌前時間熱力圖');g.fillStyle=chartColor('--ink');g.fillText(label,left,h-3);
  document.getElementById('heatmap-period').textContent=label;
}
function drawRecentHeatmap(){
  var map=heatmapDateRows(),status=deskData.status||{},endKey=dateKeyFromIso(status.current_date);
  if(!endKey){var now=new Date();now.setHours(12,0,0,0);endKey=dateKeyFromDate(now);}
  var end=dateFromKey(endKey),start=new Date(end);start.setDate(end.getDate()-364);
  var rows=[];for(var i=0;i<365;i++){var date=new Date(start);date.setDate(start.getDate()+i);var key=dateKeyFromDate(date);rows.push(Object.assign({date:dateText(key),key:key},map[key]||{}));}
  renderHeatmapGrid(rows,dateKeyFromDate(start),365,'最近 365 天');
}
function drawAnnualHeatmap(payload){
  var days=payload&&payload.days||[],year=Number(payload&&payload.year),dayCount=(new Date(year,1,29,12).getMonth()===1)?366:365;
  var rows=days.map(function(item){return {date:item.date,total_seconds:item.total_seconds,session_count:item.session_count,status:item.status};});
  renderHeatmapGrid(rows,year+'0101',dayCount,year+' 年');
}
function drawHeatmap(){
  syncHeatmapControls();
  if(heatmapYear===null){drawRecentHeatmap();return;}
  if(heatmapCache[heatmapYear]){drawAnnualHeatmap(heatmapCache[heatmapYear]);return;}
  loadAnnualHeatmap(heatmapYear);
}
async function loadAnnualHeatmap(year){
  var sequence=++heatmapRequestSeq;
  try{
    var response=await fetch('/api/desk/heatmap?year='+encodeURIComponent(year));
    if(!response.ok)throw new Error('HTTP '+response.status);
    var payload=await response.json();
    if(sequence!==heatmapRequestSeq||heatmapYear!==year)return;
    heatmapCache[year]=payload;drawAnnualHeatmap(payload);
  }catch(error){
    if(sequence!==heatmapRequestSeq)return;
    showDeskError('年度熱力圖載入失敗：'+error.message);
  }
}

function showTip(event,text){
  var tip=document.getElementById('desk-tip');tip.textContent=text;tip.style.display='block';
  var left=event.clientX+12,top=event.clientY-36;
  tip.style.left=Math.max(6,Math.min(left,window.innerWidth-tip.offsetWidth-6))+'px';tip.style.top=Math.max(6,Math.min(top,window.innerHeight-tip.offsetHeight-6))+'px';
}
function hideTip(){document.getElementById('desk-tip').style.display='none';}
function initChartInteractions(){
  var daily=document.getElementById('daily-chart'),heat=document.getElementById('heatmap-canvas');
  if(daily.dataset.bound!=='true'){
    daily.dataset.bound='true';
    daily.addEventListener('mousemove',function(event){
      var rect=daily.getBoundingClientRect(),mx=event.clientX-rect.left,my=event.clientY-rect.top,found=false;
      dailyBars.forEach(function(bar){if(mx>=bar.x&&mx<=bar.x+bar.w&&my>=bar.y&&my<=bar.y+bar.h){showTip(event,bar.date+' '+fmtDuration(bar.total_seconds));found=true;}});
      if(!found)hideTip();
    });daily.addEventListener('mouseleave',hideTip);
  }
  if(heat.dataset.bound==='true')return;
  heat.dataset.bound='true';
  heat.addEventListener('mousemove',function(event){
    var rect=heat.getBoundingClientRect(),mx=event.clientX-rect.left,my=event.clientY-rect.top,found=false;
    heatmapCells.forEach(function(cell){if(mx>=cell.x&&mx<=cell.x+cell.w&&my>=cell.y&&my<=cell.y+cell.h){var text=cell.status==='future'?dateText(cell.date)+' · 尚未到':dateText(cell.date)+' · '+(cell.hasData?fmtDuration(cell.total_seconds):'尚無資料');showTip(event,text);found=true;}});
    if(!found)hideTip();
  });
  heat.addEventListener('mouseleave',hideTip);
  heat.addEventListener('focus',function(){if(heat._selectedIndex!=null)showHeatmapDay(heat,heat._selectedIndex,true);});
  heat.addEventListener('blur',hideTip);
  heat.addEventListener('keydown',function(event){
    if(!heatmapCells.length)return;
    var index=heat._selectedIndex==null?0:heat._selectedIndex,delta={ArrowLeft:-7,ArrowRight:7,ArrowUp:-1,ArrowDown:1}[event.key];
    if(event.key==='Home')index=0;else if(event.key==='End')index=heatmapCells.length-1;else if(delta==null)return;else index+=delta;
    if(index<0||index>=heatmapCells.length)return;event.preventDefault();showHeatmapDay(heat,index,true);
  });
}
function showHeatmapDay(canvas,index,announce){
  var cell=heatmapCells[index];if(!cell)return;canvas._selectedIndex=index;
  var rect=canvas.getBoundingClientRect(),x=rect.left+cell.x+cell.w/2,y=rect.top+cell.y+cell.h/2;
  var text=cell.status==='future'?dateText(cell.date)+' · 尚未到':dateText(cell.date)+' · '+(cell.hasData?fmtDuration(cell.total_seconds):'尚無資料');
  if(announce)canvas.setAttribute('aria-label',text+'；熱力圖');showTip({clientX:x,clientY:y},text);
}

function showDeskError(message){var box=document.getElementById('desk-error');box.textContent=message;box.classList.remove('is-hidden');}
function clearDeskError(){document.getElementById('desk-error').classList.add('is-hidden');}
async function loadDashboard(){
  if(loading)return;loading=true;
  try{
    var responses=await Promise.all([
      fetch('/api/desk/status'),fetch('/api/desk/timeline'),fetch('/api/desk/daily'),fetch('/api/desk/sessions?limit=40')
    ]);
    responses.forEach(function(response){if(!response.ok)throw new Error('HTTP '+response.status);});
    var payloads=await Promise.all(responses.map(function(response){return response.json();}));
    deskData.status=payloads[0];deskData.timeline=payloads[1].timeline_24h||[];
    deskData.daily30=payloads[2].daily_30d||[];deskData.dailyHistory=payloads[2].daily_history||deskData.daily30;
    deskData.sessions=payloads[3].sessions||[];
    var currentYear=String(deskData.status&&deskData.status.current_date||'').slice(0,4);
    if(/^\d{4}$/.test(currentYear))delete heatmapCache[Number(currentYear)];
    heatmapYears=availableHeatmapYears(deskData.dailyHistory,deskData.status);
    clearDeskError();updateStatus(deskData.status);renderDailyPage();renderSessionsPage();drawDaily();drawTimeline();drawHeatmap();initChartInteractions();
  }catch(error){showDeskError('暫時無法連線：'+error.message);}
  finally{loading=false;}
}

document.getElementById('daily-prev').addEventListener('click',function(){if(dailyPage>1){dailyPage--;renderDailyPage();}});
document.getElementById('daily-next').addEventListener('click',function(){dailyPage++;renderDailyPage();});
document.getElementById('sessions-prev').addEventListener('click',function(){if(sessionsPage>1){sessionsPage--;renderSessionsPage();}});
document.getElementById('sessions-next').addEventListener('click',function(){sessionsPage++;renderSessionsPage();});
document.getElementById('heatmap-prev').addEventListener('click',function(){changeHeatmapYear(-1);});
document.getElementById('heatmap-next').addEventListener('click',function(){changeHeatmapYear(1);});
document.addEventListener('iot-theme-change',function(){drawDaily();drawTimeline();drawHeatmap();});
window.addEventListener('resize',function(){clearTimeout(heatmapResizeTimer);heatmapResizeTimer=setTimeout(function(){drawDaily();drawTimeline();drawHeatmap();},100);});
initChartInteractions();loadDashboard();setInterval(loadDashboard,30000);
</script>
"""


_DESK_HTML = _make_shell(
    "desk",
    "書桌前分析",
    _DESK_CONTENT,
    footer_meta='<span id="last-refresh">最後更新：—</span>',
)
