from app.webui.templates.base import _make_shell

_ENV_CONTENT = r"""
<style>
  .stats-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:.8rem;margin-bottom:1.2rem}
  .stat{background:var(--surface);border:1px solid var(--border);border-radius:var(--r);padding:1rem 1.2rem;box-shadow:var(--sh)}
  .stat-label{font-size:.72rem;color:var(--muted);margin-bottom:.3rem}
  .stat-value{font-size:1.5rem;font-weight:700;line-height:1.2;font-family:'JetBrains Mono',monospace}
  .stat-sub{font-size:.72rem;color:var(--muted);margin-top:.2rem}
  .temp-val{color:#38BDF8}
  .hum-val{color:#34D399}
  .hi-val{color:#FBBF24}
  .lo-val{color:#7dd3fc}
  .chart-wrap{overflow-x:auto;margin-top:.5rem}
  .tab-bar{display:flex;align-items:center;gap:.5rem;margin-bottom:1rem;flex-wrap:wrap}
  .tab-btn{padding:.35rem .9rem;border:1px solid var(--border);border-radius:6px;font-size:.8rem;font-weight:600;background:var(--surface2);color:var(--muted);cursor:pointer;transition:all .15s;font-family:inherit}
  .tab-btn.active{background:var(--primary);color:#060A14;border-color:var(--primary)}
  .tab-btn:hover:not(.active){background:#1C2940;color:var(--text)}
  input[type=date],input[type=month]{width:auto;padding:.3rem .6rem;border:1px solid var(--border);border-radius:6px;font-size:.8rem;color:var(--text);background:var(--bg);outline:none;font-family:'JetBrains Mono',monospace}
  input[type=date]:focus,input[type=month]:focus{border-color:var(--primary)}
  select.ref-year{width:auto;padding:.3rem .6rem;border:1px solid var(--border);border-radius:6px;font-size:.8rem;color:var(--text);background:var(--bg);outline:none;font-family:'JetBrains Mono',monospace}
  .stats-row{display:flex;gap:2rem;flex-wrap:wrap;font-size:.82rem;margin-top:.8rem}
  .stats-row span{white-space:nowrap}
  .refresh-ts{font-size:.72rem;color:var(--muted);text-align:right;margin-top:.3rem}
  .stat-table-wrap{overflow-x:auto;margin-top:.5rem}
  table{width:100%;border-collapse:collapse;font-size:.82rem}
  th{text-align:left;padding:.5rem .7rem;font-size:.72rem;color:var(--muted);font-weight:600;border-bottom:1px solid var(--border)}
  td{padding:.5rem .7rem;border-bottom:1px solid rgba(27,40,66,.5)}
  tr:last-child td{border-bottom:none}
</style>

<div class="page-wrap">
  <div class="page-title">🌡️ 溫溼度分析</div>

  <div class="stats-grid">
    <div class="stat">
      <div class="stat-label">目前溫度</div>
      <div class="stat-value temp-val" id="s-temp">—</div>
      <div class="stat-sub">℃</div>
    </div>
    <div class="stat">
      <div class="stat-label">目前濕度</div>
      <div class="stat-value hum-val" id="s-hum">—</div>
      <div class="stat-sub">%</div>
    </div>
    <div class="stat">
      <div class="stat-label">今日最高溫</div>
      <div class="stat-value hi-val" id="s-temp-max">—</div>
      <div class="stat-sub" id="s-temp-avg"></div>
    </div>
    <div class="stat">
      <div class="stat-label">今日最低溫</div>
      <div class="stat-value lo-val" id="s-temp-min">—</div>
      <div class="stat-sub" id="s-hum-avg"></div>
    </div>
  </div>

  <div class="card">
    <div class="card-title">趨勢圖</div>
    <div class="tab-bar">
      <button class="tab-btn active" data-scale="day"   onclick="setScale('day')">日</button>
      <button class="tab-btn"        data-scale="month" onclick="setScale('month')">月</button>
      <button class="tab-btn"        data-scale="year"  onclick="setScale('year')">年</button>
      <input  type="date"  id="ref-date"  onchange="loadChart()">
      <input  type="month" id="ref-month" style="display:none" onchange="loadChart()">
      <select id="ref-year" class="ref-year" style="display:none" onchange="loadChart()"></select>
    </div>
    <div class="chart-wrap" id="chart-wrap">
      <div style="color:var(--muted);font-size:.85rem;padding:.5rem 0">載入中…</div>
    </div>
    <div class="stats-row" id="chart-stats" style="display:none">
      <span>溫度均值：<b id="st-tavg" class="temp-val">—</b></span>
      <span>溫度最高：<b id="st-tmax" class="hi-val">—</b></span>
      <span>溫度最低：<b id="st-tmin" class="lo-val">—</b></span>
      <span style="border-left:1px solid var(--border);padding-left:2rem">濕度均值：<b id="st-havg" class="hum-val">—</b></span>
      <span>濕度最高：<b id="st-hmax" class="hi-val">—</b></span>
      <span>濕度最低：<b id="st-hmin" class="lo-val">—</b></span>
    </div>
    <div class="refresh-ts" id="chart-refresh"></div>
  </div>

  <div class="card">
    <div class="card-title">統計資訊</div>
    <div class="stat-table-wrap">
      <table id="stats-table">
        <thead>
          <tr>
            <th>項目</th>
            <th class="temp-val">溫度 (℃)</th>
            <th class="hum-val">濕度 (%)</th>
          </tr>
        </thead>
        <tbody id="stats-tbody">
          <tr><td colspan="3" style="color:var(--muted)">載入圖表後顯示</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</div>

<script>
var W=800, CH=160, SVG_H=200;
var PAD={top:12,right:64,bottom:32,left:52};
var PLOT_W=W-PAD.left-PAD.right;
var PLOT_H=CH-PAD.top-PAD.bottom;

var currentScale='day';

function setScale(scale){
  currentScale=scale;
  document.querySelectorAll('.tab-btn').forEach(function(b){
    b.classList.toggle('active', b.dataset.scale===scale);
  });
  document.getElementById('ref-date').style.display  = scale==='day'   ? '' : 'none';
  document.getElementById('ref-month').style.display = scale==='month' ? '' : 'none';
  document.getElementById('ref-year').style.display  = scale==='year'  ? '' : 'none';
  loadChart();
}

function getRef(){
  if(currentScale==='day')   return document.getElementById('ref-date').value;
  if(currentScale==='month') return document.getElementById('ref-month').value;
  return document.getElementById('ref-year').value;
}

function fmtVal(v,unit){return v!=null?v.toFixed(1)+unit:'—';}

function buildBand(pts,xScale,yFn,minKey,maxKey,color){
  if(!pts.length||pts[0][minKey]==null) return '';
  var top=pts.map(function(p,i){return xScale(i)+','+yFn(p[maxKey]);}).join(' ');
  var bot=pts.slice().reverse().map(function(p,i){return xScale(pts.length-1-i)+','+yFn(p[minKey]);}).join(' ');
  return '<polygon points="'+top+' '+bot+'" fill="'+color+'" opacity="0.12"/>';
}

function buildYGrid(min,max,side){
  if(min===max){min-=1;max+=1;}
  var out='';
  for(var i=0;i<=4;i++){
    var v=min+(max-min)*i/4;
    var y=PAD.top+(1-i/4)*PLOT_H;
    out+='<line x1="'+PAD.left+'" y1="'+y+'" x2="'+(W-PAD.right)+'" y2="'+y+'" stroke="#1B2842" stroke-width="1"/>';
    var anchor=side==='left'?'end':'start';
    var x=side==='left'?PAD.left-5:W-PAD.right+5;
    out+='<text x="'+x+'" y="'+(y+4)+'" text-anchor="'+anchor+'" font-size="9" fill="#4E647A">'+v.toFixed(1)+'</text>';
  }
  return out;
}

function buildXLabels(pts,xScale){
  var step=Math.max(1,Math.ceil(pts.length/12));
  var out='';
  pts.forEach(function(p,i){
    if(i%step===0||i===pts.length-1){
      out+='<text x="'+xScale(i)+'" y="'+(SVG_H-4)+'" text-anchor="middle" font-size="9" fill="#4E647A">'+p.label+'</text>';
    }
  });
  return out;
}

function renderChart(data){
  var pts=data.points||[];
  if(!pts.length){
    return '<svg viewBox="0 0 '+W+' '+SVG_H+'" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;min-width:280px">'
      +'<rect width="'+W+'" height="'+SVG_H+'" rx="4" fill="#0C1225"/>'
      +'<text x="'+W/2+'" y="'+SVG_H/2+'" text-anchor="middle" font-size="13" fill="#4E647A">此時段無資料</text></svg>';
  }

  var temps=pts.map(function(p){return p.temp;}).filter(function(v){return v!=null;});
  var hums=pts.map(function(p){return p.hum;}).filter(function(v){return v!=null;});
  var tmins=pts.map(function(p){return p.temp_min;}).filter(function(v){return v!=null;});
  var tmaxs=pts.map(function(p){return p.temp_max;}).filter(function(v){return v!=null;});
  var hmins=pts.map(function(p){return p.hum_min;}).filter(function(v){return v!=null;});
  var hmaxs=pts.map(function(p){return p.hum_max;}).filter(function(v){return v!=null;});

  var allT=temps.concat(tmins,tmaxs);
  var allH=hums.concat(hmins,hmaxs);
  var tMin=Math.min.apply(null,allT.length?allT:[0]);
  var tMax=Math.max.apply(null,allT.length?allT:[1]);
  var hMin=Math.min.apply(null,allH.length?allH:[0]);
  var hMax=Math.max.apply(null,allH.length?allH:[1]);

  var tRange=Math.max(tMax-tMin,0.5);
  var hRange=Math.max(hMax-hMin,0.5);
  tMin-=tRange*0.08; tMax+=tRange*0.08;
  hMin-=hRange*0.08; hMax+=hRange*0.08;

  var xScale=function(i){return PAD.left+(pts.length>1?i/(pts.length-1)*PLOT_W:PLOT_W/2);};
  var yT=function(v){return PAD.top+(1-(v-tMin)/(tMax-tMin))*PLOT_H;};
  var yH=function(v){return PAD.top+(1-(v-hMin)/(hMax-hMin))*PLOT_H;};

  var tempLine=pts.map(function(p,i){return p.temp!=null?xScale(i)+','+yT(p.temp):null;}).filter(Boolean).join(' ');
  var humLine=pts.map(function(p,i){return p.hum!=null?xScale(i)+','+yH(p.hum):null;}).filter(Boolean).join(' ');

  var tempBand=buildBand(pts,xScale,yT,'temp_min','temp_max','#38BDF8');
  var humBand=buildBand(pts,xScale,yH,'hum_min','hum_max','#34D399');
  var tempGrid=buildYGrid(tMin,tMax,'left');
  var humGrid=buildYGrid(hMin,hMax,'right');
  var labels=buildXLabels(pts,xScale);

  return '<svg viewBox="0 0 '+W+' '+SVG_H+'" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;min-width:280px">'
    +'<rect width="'+W+'" height="'+SVG_H+'" rx="4" fill="#0C1225"/>'
    +tempGrid+humGrid
    +tempBand+humBand
    +(tempLine?'<polyline points="'+tempLine+'" fill="none" stroke="#38BDF8" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>'  :'')
    +(humLine ?'<polyline points="'+humLine+'"  fill="none" stroke="#34D399" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>' :'')
    +labels
    +'<rect x="'+(W-130)+'" y="10" width="10" height="10" rx="2" fill="#38BDF8"/>'
    +'<text x="'+(W-115)+'" y="19" font-size="10" fill="#DDE6F0">溫度 °C</text>'
    +'<rect x="'+(W-130)+'" y="26" width="10" height="10" rx="2" fill="#34D399"/>'
    +'<text x="'+(W-115)+'" y="35" font-size="10" fill="#DDE6F0">濕度 %</text>'
    +'</svg>';
}

function renderStats(stats){
  if(!stats){document.getElementById('chart-stats').style.display='none';return;}
  document.getElementById('chart-stats').style.display='';
  document.getElementById('st-tavg').textContent=fmtVal(stats.temp_avg,'°C');
  document.getElementById('st-tmax').textContent=fmtVal(stats.temp_max,'°C');
  document.getElementById('st-tmin').textContent=fmtVal(stats.temp_min,'°C');
  document.getElementById('st-havg').textContent=fmtVal(stats.hum_avg,'%');
  document.getElementById('st-hmax').textContent=fmtVal(stats.hum_max,'%');
  document.getElementById('st-hmin').textContent=fmtVal(stats.hum_min,'%');

  var tbody=document.getElementById('stats-tbody');
  if(!stats.sample_count){
    tbody.innerHTML='<tr><td colspan="3" style="color:var(--muted)">無資料</td></tr>';
    return;
  }
  tbody.innerHTML=[
    ['均值', fmtVal(stats.temp_avg,'°C'), fmtVal(stats.hum_avg,'%')],
    ['最高', fmtVal(stats.temp_max,'°C'), fmtVal(stats.hum_max,'%')],
    ['最低', fmtVal(stats.temp_min,'°C'), fmtVal(stats.hum_min,'%')],
    ['樣本數', stats.sample_count+'筆', stats.sample_count+'筆'],
  ].map(function(r){
    return '<tr><td>'+r[0]+'</td><td style="color:#38BDF8;font-family:\'JetBrains Mono\',monospace">'+r[1]+'</td><td style="color:#34D399;font-family:\'JetBrains Mono\',monospace">'+r[2]+'</td></tr>';
  }).join('');
}

async function loadChart(){
  var ref=getRef();
  var url='/api/env/chart?scale='+currentScale+(ref?'&ref='+encodeURIComponent(ref):'');
  document.getElementById('chart-wrap').innerHTML='<div style="color:var(--muted);font-size:.85rem;padding:.5rem 0">載入中…</div>';
  try{
    var r=await fetch(url);
    var d=await r.json();
    document.getElementById('chart-wrap').innerHTML=renderChart(d);
    renderStats(d.stats||null);
    document.getElementById('chart-refresh').textContent='最後更新：'+new Date().toLocaleTimeString('zh-TW',{hour12:false});
  }catch(e){
    document.getElementById('chart-wrap').innerHTML='<div style="color:var(--red);font-size:.85rem;padding:.5rem 0">資料載入失敗</div>';
    console.error('chart',e);
  }
}

async function loadCurrent(){
  try{
    var r=await fetch('/api/env/current');
    var d=await r.json();
    document.getElementById('s-temp').textContent     = d.temperature!=null ? d.temperature.toFixed(1) : '—';
    document.getElementById('s-hum').textContent      = d.humidity!=null    ? d.humidity.toFixed(1)    : '—';
    var t=d.today||{};
    document.getElementById('s-temp-max').textContent = t.temp_max!=null ? t.temp_max.toFixed(1) : '—';
    document.getElementById('s-temp-min').textContent = t.temp_min!=null ? t.temp_min.toFixed(1) : '—';
    document.getElementById('s-temp-avg').textContent = t.temp_avg!=null ? '今日均 '+t.temp_avg.toFixed(1)+'°C' : '';
    document.getElementById('s-hum-avg').textContent  = t.hum_avg!=null  ? '今日均濕 '+t.hum_avg.toFixed(1)+'%'  : '';
  }catch(e){console.error('current',e);}
}

async function initYears(){
  try{
    var r=await fetch('/api/env/years');
    var d=await r.json();
    var sel=document.getElementById('ref-year');
    (d.years||[]).forEach(function(y){
      var o=document.createElement('option');
      o.value=o.textContent=y;
      sel.appendChild(o);
    });
    if(!sel.value && d.years && d.years.length) sel.value=d.years[0];
  }catch(e){console.error('years',e);}
}

// 初始化
document.getElementById('ref-date').value=new Date().toISOString().slice(0,10);
(function(){
  var now=new Date();
  document.getElementById('ref-month').value=now.getFullYear()+'-'+String(now.getMonth()+1).padStart(2,'0');
})();

initYears();
loadCurrent();
loadChart();
setInterval(loadCurrent,30000);
setInterval(loadChart,300000);
</script>
"""

_ENV_HTML = _make_shell("environment", "溫溼度分析", _ENV_CONTENT)
