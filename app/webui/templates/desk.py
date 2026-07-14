from app.webui.templates.base import _make_shell

_DESK_CONTENT = r"""
<style>
  .stats-grid{gap:.6rem;margin-bottom:1.2rem}
  .stat{padding:1rem 1.2rem}
  .stat-label{font-size:.72rem;color:var(--muted);margin-bottom:.3rem}
  .stat-value{font-size:1.5rem;font-weight:700;line-height:1.2;font-family:Consolas,monospace;color:var(--teal)}
  .stat-sub{font-size:.72rem;color:var(--muted);margin-top:.2rem}
  .badge{display:inline-block;padding:.2rem .65rem;border-radius:0;font:700 .68rem Consolas,monospace}
  .badge-green{background:var(--teal);color:var(--on-dark)}
  .badge-gray{background:var(--coral);color:var(--on-dark)}
  .sensor-row{display:flex;align-items:center;gap:1rem;font-size:.85rem;flex-wrap:wrap}
  .sensor-bar-wrap{flex:1;min-width:180px}
  .sensor-bar{height:8px;background:var(--surface-2);border:1px solid var(--line);border-radius:0;position:relative;overflow:visible}
  .sensor-fill{height:100%;background:var(--teal);transition:width .4s}
  .sensor-threshold-line{position:absolute;top:-3px;bottom:-3px;width:2px;background:var(--amber)}
  .chart-wrap{overflow-x:auto}
  table{width:100%;border-collapse:collapse;font-size:.82rem}
  th{text-align:left;padding:.5rem .7rem;font-size:.72rem;color:var(--muted);font-weight:600;border-bottom:1px solid var(--line)}
  td{padding:.5rem .7rem;border-bottom:1px solid var(--line)}
  tr:last-child td{border-bottom:none}
  .badge-occ{background:var(--teal);color:var(--on-dark)}
  .badge-unocc{background:var(--coral);color:var(--on-dark)}
  .refresh-ts{font-size:.72rem;color:var(--muted);text-align:right;margin-top:.3rem}
  .heatmap-header{display:flex;align-items:flex-start;justify-content:space-between;gap:1rem;margin-bottom:.75rem}
  .heatmap-header .card-title{margin:0;padding:0;border:0}
  .heatmap-sub{margin:.35rem 0 0;color:var(--muted);font:400 .74rem/1.45 Consolas,monospace}
  .heatmap-year-controls{display:flex;align-items:center;gap:.35rem;flex-shrink:0}
  .heatmap-year-btn{min-width:0;padding:.45rem .75rem;background:var(--surface);border:1px solid var(--ink);color:var(--ink)}
  .heatmap-year-btn:hover{background:var(--mint);color:var(--on-light)}
  .heatmap-year-btn:disabled{opacity:.4;cursor:not-allowed}
  .heatmap-year-label{min-width:3.5rem;text-align:center;font:700 .82rem Consolas,monospace}
  .heatmap-wrap{overflow-x:auto;padding-bottom:.3rem}
  .heatmap-wrap canvas{display:block;margin:0 auto;max-width:none;background:var(--inset);border:1px solid var(--line)}
  .heatmap-tip{min-height:18px;margin-top:.45rem;color:var(--muted);text-align:center;font:400 .74rem Consolas,monospace}
  .heatmap-summary{margin-top:.35rem;color:var(--muted);font:400 .74rem/1.45 Consolas,monospace}
  .heatmap-details{margin-top:.85rem;border-top:1px solid var(--line);padding-top:.7rem}
  .heatmap-details summary{cursor:pointer;color:var(--teal);font:700 .74rem Consolas,monospace}
  .heatmap-details .table-wrap{margin-top:.65rem;max-height:300px;overflow:auto}
  .heatmap-legend{display:flex;align-items:center;gap:.4rem;margin-top:.6rem;color:var(--muted);font:400 .7rem Consolas,monospace}
  .heatmap-legend canvas{border:0;background:transparent}
  .heatmap-tooltip{position:fixed;z-index:10002;display:none;max-width:240px;padding:.55rem .7rem;background:var(--ink-soft);border:1px solid var(--mint);color:var(--on-dark);font:700 .72rem/1.45 Consolas,monospace;pointer-events:none;box-shadow:5px 5px 0 var(--line)}
  @media(max-width:560px){.heatmap-header{align-items:stretch;flex-direction:column}.heatmap-year-controls{justify-content:flex-end}}
</style>

<div class="page-wrap">
  <h1 class="page-title">書桌前分析</h1>

  <div class="stats-grid" id="stats-grid">
    <div class="stat"><div class="stat-label">目前狀態</div><div class="stat-value" id="s-presence">—</div></div>
    <div class="stat"><div class="stat-label">今日累計</div><div class="stat-value" id="s-today">—</div></div>
    <div class="stat"><div class="stat-label">本次時段</div><div class="stat-value" id="s-segment">—</div><div class="stat-sub" id="s-since"></div></div>
    <div class="stat"><div class="stat-label">今日次數</div><div class="stat-value" id="s-count">—</div></div>
    <div class="stat"><div class="stat-label">光線原始值</div><div class="stat-value" id="s-light">—</div></div>
    <div class="stat"><div class="stat-label">光線閾值</div><div class="stat-value" id="s-thresh">—</div></div>
  </div>

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

  <div class="card">
    <div class="card-title">近 24 小時狀態軸</div>
    <div class="chart-wrap" id="timeline-wrap">
      <div style="color:var(--muted);font-size:.85rem">載入中…</div>
    </div>
  </div>

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

  <div class="card">
    <div class="heatmap-header">
      <div>
        <div class="card-title">年度在席熱力圖</div>
        <p class="heatmap-sub">每格代表一天；以 8 小時書桌前時間作為滿格強度基準。</p>
      </div>
      <div class="heatmap-year-controls" aria-label="年度切換">
        <button type="button" class="heatmap-year-btn" id="heatmap-prev" aria-label="查看上一年">&#8249;</button>
        <span class="heatmap-year-label" id="heatmap-year" aria-live="polite"></span>
        <button type="button" class="heatmap-year-btn" id="heatmap-next" aria-label="查看下一年">&#8250;</button>
      </div>
    </div>
    <div id="heatmap-loading" style="color:var(--muted);font-size:.85rem;text-align:center;padding:1.5rem 0">載入中…</div>
    <div id="heatmap-wrap" class="heatmap-wrap" style="display:none">
      <canvas id="heatmap-canvas" tabindex="0" aria-label="年度每日在席時間熱力圖" aria-describedby="heatmap-summary"></canvas>
    </div>
    <div id="heatmap-tip" class="heatmap-tip" aria-live="polite"></div>
    <div id="heatmap-summary" class="heatmap-summary"></div>
    <div class="heatmap-legend" aria-label="在席時間熱力圖圖例">
      <span>無</span><canvas id="heatmap-legend-canvas" width="90" height="12" aria-hidden="true"></canvas><span>多（≥8h）</span>
    </div>
    <div id="heatmap-tooltip" class="heatmap-tooltip" role="tooltip"></div>
    <details class="heatmap-details">
      <summary>以文字查看每日在席時間</summary>
      <div class="table-wrap">
        <table>
          <thead><tr><th>日期</th><th>在席時間</th><th>時段數</th><th>狀態</th></tr></thead>
          <tbody id="heatmap-tbody"><tr><td colspan="4" style="color:var(--muted)">載入中…</td></tr></tbody>
        </table>
      </div>
    </details>
  </div>

  <div class="card">
    <div class="card-title">每日統計（最近 30 天）</div>
    <div style="overflow-x:auto">
      <table id="daily-table">
        <thead><tr><th>日期</th><th>書桌前時間</th><th>書桌前比例</th></tr></thead>
        <tbody id="daily-tbody"><tr><td colspan="3" style="color:var(--muted)">載入中…</td></tr></tbody>
      </table>
    </div>
  </div>

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

function chartColor(name){return getComputedStyle(document.documentElement).getPropertyValue(name).trim();}

var heatmapYear=new Date().getFullYear(),heatmapCache={},heatmapRequestSeq=0;
var HEATMAP_MIN_CELL=10,HEATMAP_MAX_CELL=22,HEATMAP_GAP=2,HEATMAP_LABEL_WIDTH=22,HEATMAP_LABEL_HEIGHT=18;

function heatmapMetrics(nWeeks){
  var wrap=document.getElementById('heatmap-wrap');
  var available=Math.max(0,wrap.clientWidth-4);
  var fixedWidth=HEATMAP_LABEL_WIDTH+4+(nWeeks-1)*HEATMAP_GAP;
  var cell=Math.max(HEATMAP_MIN_CELL,Math.min(HEATMAP_MAX_CELL,(available-fixedWidth)/nWeeks));
  return {CELL:cell,GAP:HEATMAP_GAP,STEP:cell+HEATMAP_GAP,LW:HEATMAP_LABEL_WIDTH,LH:HEATMAP_LABEL_HEIGHT};
}

function heatmapAlpha(total,reference){
  if(total<=0)return 1;
  var pct=reference>0?total/reference:0;
  return pct>=1?1:pct<.25?.24:pct<.50?.42:pct<.75?.66:.86;
}

function drawHeatmapLegend(reference){
  var canvas=document.getElementById('heatmap-legend-canvas'),dpr=window.devicePixelRatio||1,w=90,h=12;
  canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);canvas.style.width=w+'px';canvas.style.height=h+'px';
  var ctx=canvas.getContext('2d'),teal=chartColor('--teal'),surface2=chartColor('--surface-2');
  ctx.setTransform(dpr,0,0,dpr,0,0);
  [
    {color:surface2,alpha:1},
    {color:teal,alpha:.24},{color:teal,alpha:.42},{color:teal,alpha:.66},{color:teal,alpha:.86},{color:teal,alpha:1}
  ].forEach(function(item,index){
    ctx.fillStyle=item.color;ctx.globalAlpha=item.alpha;ctx.fillRect(index*14,0,12,h);ctx.globalAlpha=1;
  });
}

function renderHeatmapTable(days){
  var tbody=document.getElementById('heatmap-tbody');tbody.replaceChildren();
  var labels={future:'尚未到',empty:'無記錄',recorded:'有記錄',ongoing:'進行中'};
  days.forEach(function(day){
    var row=document.createElement('tr');
    [day.date,fmtDuration(Number(day.total_seconds)||0),String(day.session_count||0),labels[day.status]||'—'].forEach(function(value){
      var cell=document.createElement('td');cell.textContent=value;row.appendChild(cell);
    });
    tbody.appendChild(row);
  });
}

function drawHeatmap(payload,refreshTable){
  var year=payload.year,days=payload.days||[],reference=payload.reference_seconds||28800;
  var heatmapWrap=document.getElementById('heatmap-wrap');
  heatmapWrap.style.display='';
  var canvas=document.getElementById('heatmap-canvas'),previousMeta=canvas._hm;
  var jan1=new Date(year,0,1),startWd=(jan1.getDay()+6)%7,nDays=days.length;
  var nWeeks=Math.ceil((startWd+nDays)/7),metrics=heatmapMetrics(nWeeks);
  var CELL=metrics.CELL,STEP=metrics.STEP,LW=metrics.LW,LH=metrics.LH;
  var dpr=window.devicePixelRatio||1;
  var cw=LW+nWeeks*STEP+4,ch=LH+7*STEP+4;
  canvas.width=Math.max(1,Math.round(cw*dpr));canvas.height=Math.max(1,Math.round(ch*dpr));
  canvas.style.width=cw+'px';canvas.style.height=ch+'px';
  var ctx=canvas.getContext('2d'),colors={
    teal:chartColor('--teal'),surface2:chartColor('--surface-2'),muted:chartColor('--muted'),line:chartColor('--line'),inset:chartColor('--inset')
  };
  ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,cw,ch);
  ctx.fillStyle=colors.inset;ctx.fillRect(0,0,cw,ch);
  ctx.font='700 10px Consolas,monospace';ctx.fillStyle=colors.muted;ctx.textAlign='left';
  for(var d=0;d<nDays;d++){
    var dateObj=new Date(year,0,d+1);
    if(d===0||dateObj.getDate()===1){
      var monthX=LW+Math.floor((startWd+d)/7)*STEP;
      ctx.fillText(String(dateObj.getMonth()+1).padStart(2,'0')+'月',monthX,11);
    }
  }
  ['一','三','五'].forEach(function(label,row){
    ctx.textAlign='right';ctx.fillText(label,LW-4,LH+(row*2)*STEP+CELL-1);
  });
  for(var dayIndex=0;dayIndex<nDays;dayIndex++){
    var grid=startWd+dayIndex,col=Math.floor(grid/7),row=grid%7;
    var x=LW+col*STEP,y=LH+row*STEP,day=days[dayIndex],total=Number(day.total_seconds)||0;
    ctx.fillStyle=total<=0?colors.surface2:colors.teal;ctx.globalAlpha=day.status==='future'?.55:heatmapAlpha(total,reference);ctx.fillRect(x,y,CELL,CELL);ctx.globalAlpha=1;
  }
  canvas._hm={year:year,nDays:nDays,startWd:startWd,LW:LW,LH:LH,STEP:STEP,CELL:CELL,days:days,reference:reference,selectedIndex:previousMeta&&previousMeta.year===year?Math.min(previousMeta.selectedIndex||0,nDays-1):0};
  var activeDays=payload.active_days==null?days.filter(function(day){return Number(day.total_seconds)>0;}).length:payload.active_days;
  var totalYear=payload.total_seconds==null?days.reduce(function(sum,day){return sum+(Number(day.total_seconds)||0);},0):payload.total_seconds;
  canvas.setAttribute('aria-label',year+' 年每日在席時間熱力圖，共 '+activeDays+' 天有紀錄');
  document.getElementById('heatmap-summary').textContent=year+' 年累計 '+fmtDuration(totalYear)+'，'+activeDays+' 天有在席記錄';
  if(refreshTable!==false)renderHeatmapTable(days);
  document.getElementById('heatmap-loading').style.display='none';
  document.getElementById('heatmap-year').textContent=String(year);
  drawHeatmapLegend(reference);
}

function clearHeatmapTip(){
  document.getElementById('heatmap-tip').textContent='';
  document.getElementById('heatmap-tooltip').style.display='none';
}

function showHeatmapTip(canvas,clientX,clientY,announce){
  var meta=canvas._hm;if(!meta)return;
  var rect=canvas.getBoundingClientRect(),mx=clientX-rect.left,my=clientY-rect.top;
  var col=Math.floor((mx-meta.LW)/meta.STEP),row=Math.floor((my-meta.LH)/meta.STEP);
  if(mx<meta.LW||my<meta.LH||col<0||row<0||row>=7||((mx-meta.LW)%meta.STEP)>meta.CELL||((my-meta.LH)%meta.STEP)>meta.CELL){clearHeatmapTip();return;}
  var dayIndex=col*7+row-meta.startWd;
  if(dayIndex<0||dayIndex>=meta.nDays){clearHeatmapTip();return;}
  canvas._hm.selectedIndex=dayIndex;
  var day=meta.days[dayIndex],total=Number(day.total_seconds)||0,pct=meta.reference>0?Math.round(total/meta.reference*100):0;
  var message=day.status==='future'?day.date+' · 尚未到':day.date+' · '+fmtDuration(total)+(total?'（'+pct+'% / 8h，'+(day.session_count||0)+' 次）':' · 無在席記錄');
  if(announce)document.getElementById('heatmap-tip').textContent=message;
  var tooltip=document.getElementById('heatmap-tooltip');tooltip.textContent=message;tooltip.style.display='block';
  var left=Math.min(clientX+12,window.innerWidth-tooltip.offsetWidth-8),top=Math.min(clientY+12,window.innerHeight-tooltip.offsetHeight-8);
  tooltip.style.left=Math.max(8,left)+'px';tooltip.style.top=Math.max(8,top)+'px';
}

function showHeatmapDay(canvas,dayIndex,announce){
  var meta=canvas._hm;if(!meta||dayIndex<0||dayIndex>=meta.nDays)return;
  var col=Math.floor((meta.startWd+dayIndex)/7),row=(meta.startWd+dayIndex)%7,rect=canvas.getBoundingClientRect();
  showHeatmapTip(canvas,rect.left+meta.LW+col*meta.STEP+meta.CELL/2,rect.top+meta.LH+row*meta.STEP+meta.CELL/2,announce);
}

function bindHeatmapPointer(){
  var canvas=document.getElementById('heatmap-canvas');
  canvas.addEventListener('pointermove',function(event){showHeatmapTip(canvas,event.clientX,event.clientY,false);});
  canvas.addEventListener('pointerdown',function(event){showHeatmapTip(canvas,event.clientX,event.clientY,true);});
  canvas.addEventListener('pointerleave',clearHeatmapTip);
  canvas.addEventListener('focus',function(){
    if(canvas._hm){
      showHeatmapDay(canvas,canvas._hm.selectedIndex||0,true);
    }
  });
  canvas.addEventListener('keydown',function(event){
    if(!canvas._hm)return;
    var index=canvas._hm.selectedIndex||0,delta={ArrowLeft:-1,ArrowRight:1,ArrowUp:-7,ArrowDown:7}[event.key];
    if(event.key==='Home')index=0;
    else if(event.key==='End')index=canvas._hm.nDays-1;
    else if(delta==null)return;
    if(delta!=null)index+=delta;
    if(index<0||index>=canvas._hm.nDays)return;
    event.preventDefault();showHeatmapDay(canvas,index,true);
  });
  canvas.addEventListener('blur',clearHeatmapTip);
}

async function loadHeatmap(year){
  var seq=++heatmapRequestSeq,currentYear=new Date().getFullYear();
  document.getElementById('heatmap-year').textContent=String(year);
  document.getElementById('heatmap-prev').disabled=year<=2000;
  document.getElementById('heatmap-next').disabled=year>=currentYear;
  if(heatmapCache[year]){drawHeatmap(heatmapCache[year]);clearHeatmapTip();return;}
  var canvas=document.getElementById('heatmap-canvas'),hadPrevious=!!canvas._hm;
  if(!hadPrevious){document.getElementById('heatmap-loading').style.display='';document.getElementById('heatmap-wrap').style.display='none';}
  try{
    var response=await fetch('/api/desk/heatmap?year='+encodeURIComponent(year));
    if(!response.ok)throw new Error('HTTP '+response.status);
    var payload=await response.json();
    if(seq!==heatmapRequestSeq)return;
    if(year<currentYear)heatmapCache[year]=payload;
    drawHeatmap(payload);clearHeatmapTip();
  }catch(error){
    if(seq!==heatmapRequestSeq)return;
    document.getElementById('heatmap-tip').textContent=hadPrevious?'更新失敗，保留上次資料':'熱力圖載入失敗，請稍後再試';
    if(!hadPrevious){document.getElementById('heatmap-loading').style.display='';document.getElementById('heatmap-loading').textContent='熱力圖載入失敗，請稍後再試';}
    console.error('heatmap',error);
  }
}

function renderTimeline(sessions){
  var now=Date.now();
  var start24=now-86400000;
  var W=800, H=48;
  var bars='',teal=chartColor('--teal'),muted=chartColor('--muted'),line=chartColor('--line'),inset=chartColor('--inset');
  sessions.forEach(function(s){
    var x1=Math.max(0,(new Date(s.start_ts).getTime()-start24)/86400000*W);
    var endMs=s.end_ts?new Date(s.end_ts).getTime():now;
    var x2=Math.min(W,(endMs-start24)/86400000*W);
    var w=Math.max(2,x2-x1);
    var opacity=s.end_ts?'0.75':'0.95';
    bars+='<rect x="'+x1+'" y="6" width="'+w+'" height="36" fill="'+teal+'" opacity="'+opacity+'"/>';
  });
  var labels='';
  for(var h=0;h<=24;h+=6){
    var x=h/24*W;
    var t=new Date(start24+h*3600000);
    var lbl=String(t.getHours()).padStart(2,'0')+':00';
    var anchor=h===0?'start':h===24?'end':'middle';
    labels+='<text x="'+x+'" y="'+H+'" text-anchor="'+anchor+'" font-size="10" fill="'+muted+'">'+lbl+'</text>';
    labels+='<line x1="'+x+'" y1="44" x2="'+x+'" y2="47" stroke="'+line+'" stroke-width="1"/>';
  }
  return '<svg viewBox="0 0 '+W+' '+(H+2)+'" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;min-width:320px">'
    +'<rect width="'+W+'" height="48" fill="'+inset+'" stroke="'+line+'"/>'
    +bars+labels+'</svg>';
}

function renderBarChart(daily30d){
  var W=800, bH=140, svgH=170;
  var maxSec=Math.max.apply(null,daily30d.map(function(d){return d.total_seconds;}));
  if(maxSec===0) maxSec=3600;
  var bW=W/30-2;
  var bars='',labels='',teal=chartColor('--teal'),muted=chartColor('--muted'),line=chartColor('--line'),inset=chartColor('--inset');
  daily30d.forEach(function(d,i){
    var x=i*(W/30);
    var h=Math.max(2,d.total_seconds/maxSec*bH);
    var y=bH-h;
    var opacity=d.total_seconds>0?'0.75':'0.2';
    bars+='<rect x="'+(x+1)+'" y="'+y+'" width="'+bW+'" height="'+h+'" fill="'+teal+'" opacity="'+opacity+'"/>';
    if(i%7===0||i===29){
      var lbl=d.date.slice(5);
      labels+='<text x="'+(x+bW/2)+'" y="'+(svgH-2)+'" text-anchor="middle" font-size="9" fill="'+muted+'">'+lbl+'</text>';
    }
  });
  return '<svg viewBox="0 0 '+W+' '+svgH+'" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;min-width:320px">'
    +'<rect width="'+W+'" height="'+svgH+'" fill="'+inset+'" stroke="'+line+'"/>'
    +bars+labels+'</svg>';
}

async function loadStats(){
  try{
    var r=await fetch('/api/desk/stats');
    if(!r.ok)throw new Error('HTTP '+r.status);
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
    if(!r.ok)throw new Error('HTTP '+r.status);
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
    if(!r.ok)throw new Error('HTTP '+r.status);
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

document.getElementById('heatmap-prev').addEventListener('click',function(){
  if(heatmapYear>2000){heatmapYear--;loadHeatmap(heatmapYear);}
});
document.getElementById('heatmap-next').addEventListener('click',function(){
  var currentYear=new Date().getFullYear();
  if(heatmapYear<currentYear){heatmapYear++;loadHeatmap(heatmapYear);}
});
bindHeatmapPointer();
loadStats(); loadHistory(); loadSessions(); loadHeatmap(heatmapYear);
setInterval(loadStats, 30000);
setInterval(function(){loadHistory();loadSessions();if(heatmapYear===new Date().getFullYear())loadHeatmap(heatmapYear);}, 300000);
document.addEventListener('iot-theme-change',loadHistory);
document.addEventListener('iot-theme-change',function(){
  var canvas=document.getElementById('heatmap-canvas'),meta=canvas._hm;
  if(meta)drawHeatmap({year:meta.year,days:meta.days,active_days:meta.days.filter(function(day){return Number(day.total_seconds)>0;}).length,reference_seconds:meta.reference},false);
});
var heatmapResizeTimer;
window.addEventListener('resize',function(){
  clearTimeout(heatmapResizeTimer);
  heatmapResizeTimer=setTimeout(function(){
    var canvas=document.getElementById('heatmap-canvas'),meta=canvas._hm;
    if(meta&&document.getElementById('heatmap-wrap').style.display!=='none')
      drawHeatmap({year:meta.year,days:meta.days,active_days:meta.days.filter(function(day){return Number(day.total_seconds)>0;}).length,reference_seconds:meta.reference},false);
  },100);
});
</script>
"""

_DESK_HTML = _make_shell("desk", "書桌前分析", _DESK_CONTENT)
