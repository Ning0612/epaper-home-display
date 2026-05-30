_IMAGES_HTML = r"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>圖片輪播管理</title>
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
    .topbar-links{display:flex;gap:.6rem}
    .topbar-link{font-size:.8rem;color:var(--primary);text-decoration:none;padding:.3rem .7rem;border:1px solid var(--primary);border-radius:6px;transition:background .15s}
    .topbar-link:hover{background:rgba(56,189,248,.1)}
    .container{max-width:960px;margin:0 auto;padding:1.5rem}
    .card{background:var(--surface);border:1px solid var(--border);border-radius:var(--r);padding:1.3rem;box-shadow:var(--sh);margin-bottom:1.2rem}
    .card-title{font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.07em;color:var(--muted);margin-bottom:1rem}
    /* Image icon grid (Windows-style large icons) */
    .img-grid2{display:grid;grid-template-columns:repeat(auto-fill,96px);gap:.8rem;justify-content:start;margin-top:.9rem}
    .img-card2{width:96px;display:flex;flex-direction:column;align-items:center}
    .img-thumb2{width:88px;height:141px;background:#000;border-radius:6px;overflow:hidden;position:relative;flex-shrink:0;cursor:pointer}
    .img-thumb2 img{width:100%;height:100%;object-fit:cover;image-rendering:pixelated;display:block;transition:filter .15s}
    .img-thumb2:hover>img{filter:brightness(.78)}
    .cur-ribbon{position:absolute;bottom:0;left:0;right:0;background:rgba(56,189,248,.88);color:#080d18;font-size:.62rem;font-weight:700;text-align:center;padding:.18rem 0}
    .img-del-btn{position:absolute;top:4px;right:4px;width:20px;height:20px;border-radius:50%;background:rgba(8,13,24,.78);border:1px solid rgba(248,113,113,.5);color:var(--red);font-size:1rem;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:background .15s,border-color .15s;padding:0;line-height:1}
    .img-del-btn:hover{background:rgba(248,113,113,.28);border-color:var(--red)}
    .img-card2-name{font-size:.72rem;font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-top:.35rem;width:96px;text-align:center;color:var(--text)}
    .img-card2-date{font-size:.67rem;color:var(--muted);text-align:center;margin-top:.08rem}
    .empty-state{text-align:center;padding:2rem;color:var(--muted);font-size:.88rem}
    /* Upload drop zone */
    .drop-zone{border:2px dashed var(--border);border-radius:8px;padding:2rem;text-align:center;cursor:pointer;transition:border-color .2s,background .2s;color:var(--muted)}
    .drop-zone:hover,.drop-zone.drag-over{border-color:var(--primary);background:rgba(56,189,248,.05);color:var(--text)}
    .drop-zone-icon{font-size:2rem;margin-bottom:.5rem}
    .drop-zone-text{font-size:.85rem}
    /* Toggle switch */
    .tog-row{display:flex;align-items:center;justify-content:space-between;padding:.5rem 0}
    .tog-lbl{font-size:.875rem;font-weight:500}
    .tog-desc{font-size:.73rem;color:var(--muted);margin-top:.1rem}
    .sw{position:relative;width:40px;height:22px;flex-shrink:0}
    .sw input{opacity:0;width:0;height:0}
    .sl{position:absolute;inset:0;background:var(--border);border-radius:22px;cursor:pointer;transition:.2s}
    .sl::before{content:'';position:absolute;width:16px;height:16px;left:3px;top:3px;background:#94a3b8;border-radius:50%;transition:.2s;box-shadow:0 1px 3px rgba(0,0,0,.4)}
    input:checked+.sl{background:var(--primary)}
    input:checked+.sl::before{transform:translateX(18px);background:#fff}
    .f{margin-bottom:.9rem}.f:last-of-type{margin-bottom:0}
    label{display:block;font-size:.78rem;font-weight:500;margin-bottom:.3rem}
    .hint{font-weight:400;color:var(--muted);font-size:.72rem;margin-left:.3rem}
    input[type=number],select{width:100%;padding:.45rem .7rem;border:1px solid var(--border);border-radius:6px;font-size:.85rem;color:var(--text);background:var(--bg);transition:border-color .15s;outline:none}
    input:focus,select:focus{border-color:var(--primary);box-shadow:0 0 0 3px rgba(56,189,248,.15)}
    select option{background:var(--surface)}
    :root{color-scheme:dark}
    .row2{display:flex;gap:.65rem}.row2 .f{flex:1;margin-bottom:0}
    .btn-row{display:flex;justify-content:flex-end;gap:.6rem;margin-top:1rem}
    button{padding:.45rem 1.1rem;border:none;border-radius:6px;font-size:.83rem;font-weight:500;cursor:pointer;transition:background .15s}
    .btn-p{background:var(--primary);color:#080d18}
    .btn-p:hover{background:var(--primary-h)}
    .btn-s{background:var(--surface2);color:var(--text);border:1px solid var(--border)}
    .btn-s:hover{background:#243554}
    .btn-d{background:rgba(248,113,113,.15);color:var(--red);border:1px solid rgba(248,113,113,.3)}
    .btn-d:hover{background:rgba(248,113,113,.25)}
    /* Crop view */
    .crop-wrap{display:flex;flex-direction:column;align-items:center;gap:1rem}
    #crop-canvas{max-width:100%;cursor:crosshair;border-radius:6px;display:block;touch-action:none}
    .crop-hint{font-size:.78rem;color:var(--muted);text-align:center}
    /* Preview view */
    .preview-grid{display:grid;grid-template-columns:1fr 1fr;gap:1.2rem;margin-bottom:1rem}
    .preview-panel{text-align:center}
    .preview-label{font-size:.75rem;color:var(--muted);margin-bottom:.5rem;font-weight:500;text-transform:uppercase;letter-spacing:.05em}
    #crop-mini,#dither-preview{max-width:100%;border-radius:6px;border:1px solid var(--border);display:block;margin:0 auto;image-rendering:pixelated}
    /* Toast */
    #toast{position:fixed;bottom:1.5rem;right:1.5rem;padding:.65rem 1.1rem;border-radius:var(--r);font-size:.83rem;font-weight:500;box-shadow:0 4px 12px rgba(0,0,0,.4);opacity:0;transform:translateY(.4rem);transition:opacity .22s,transform .22s;pointer-events:none;z-index:9999}
    #toast.show{opacity:1;transform:none}
    #toast.ok{background:#0a2e1a;color:#34d399;border:1px solid rgba(52,211,153,.3)}
    #toast.err{background:#2e0a0a;color:#f87171;border:1px solid rgba(248,113,113,.3)}
    #toast.info{background:#0a1e2e;color:#7dd3fc;border:1px solid rgba(56,189,248,.3)}
    /* Image preview modal */
    .modal-overlay{position:fixed;inset:0;background:rgba(0,0,0,.8);z-index:10000;display:flex;align-items:center;justify-content:center;backdrop-filter:blur(6px)}
    .modal-box{background:var(--surface);border:1px solid var(--border);border-radius:var(--r);padding:1.3rem 1.1rem 1rem;display:flex;flex-direction:column;align-items:center;gap:.75rem;position:relative;max-width:90vw}
    .modal-close{position:absolute;top:.5rem;right:.7rem;background:transparent;border:none;color:var(--muted);font-size:1.5rem;cursor:pointer;line-height:1;padding:.1rem .35rem;transition:color .15s}
    .modal-close:hover{color:var(--text)}
    #modal-img{max-height:70vh;max-width:min(560px,85vw);width:auto;height:auto;image-rendering:pixelated;border-radius:4px;display:block}
    .modal-fname{font-size:.78rem;color:var(--muted);text-align:center;max-width:320px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
    @media(max-width:600px){
      .container{padding:1rem}
      .topbar{padding:.7rem 1rem}
      .preview-grid{grid-template-columns:1fr}
    }
  </style>
</head>
<body>

<div class="topbar">
  <div class="topbar-title">🖼️ 圖片輪播管理</div>
  <div class="topbar-links">
    <a href="/settings" class="topbar-link">⚙️ 設定</a>
    <a href="/desk" class="topbar-link">📖 書桌</a>
  </div>
</div>

<div class="container">

  <!-- ========== Gallery View ========== -->
  <div id="view-gallery">
    <!-- Carousel Settings -->
    <div class="card">
      <div class="card-title">輪播設定</div>
      <div class="tog-row">
        <div>
          <div class="tog-lbl">啟用輪播</div>
          <div class="tog-desc">自動切換多張圖片顯示在電子紙</div>
        </div>
        <label class="sw">
          <input type="checkbox" id="c-enabled">
          <span class="sl"></span>
        </label>
      </div>
      <div class="row2" style="margin-top:.8rem">
        <div class="f">
          <label>換圖間隔 <span class="hint">（分鐘，最少 1）</span></label>
          <input type="number" id="c-interval" min="1" max="1440" value="30">
        </div>
        <div class="f">
          <label>切換模式</label>
          <select id="c-mode">
            <option value="sequential">循序</option>
            <option value="random">隨機</option>
          </select>
        </div>
      </div>
      <div class="btn-row">
        <button class="btn-s" onclick="advanceCarousel()">立即切換下一張</button>
        <button class="btn-p" onclick="saveCarousel()">儲存輪播設定</button>
      </div>
    </div>

    <!-- Image Gallery -->
    <div class="card">
      <div class="card-title">已上傳圖片</div>
      <div id="drop-zone" class="drop-zone" onclick="startUpload()" ondragover="onDragOver(event)" ondragleave="onDragLeave(event)" ondrop="onDrop(event)">
        <div class="drop-zone-icon">📁</div>
        <div class="drop-zone-text">點擊上傳，或將圖片拖曳至此<br><span style="font-size:.73rem;color:var(--muted)">支援 JPEG、PNG、WebP（最大 15 MB）</span></div>
      </div>
      <input type="file" id="file-input" accept="image/jpeg,image/png,image/webp,image/gif,image/bmp" style="display:none" onchange="onFileSelect(event)">
      <div id="img-grid"></div>
    </div>
  </div>

  <!-- ========== Crop View ========== -->
  <div id="view-crop" style="display:none">
    <div class="card">
      <div class="card-title">裁切圖片 <span style="color:var(--muted);font-size:.75rem;font-weight:400;letter-spacing:0;text-transform:none">— 拖曳選框定位，拖曳角點調整大小（固定 5:8 比例）</span></div>
      <div class="crop-wrap">
        <canvas id="crop-canvas"></canvas>
        <div class="crop-hint">選框比例鎖定為電子紙圖片卡尺寸（280×448）；可拖曳至圖片外側白邊，超出部分顯示為白色</div>
      </div>
      <div class="btn-row">
        <button class="btn-s" onclick="cancelCrop()">取消</button>
        <button class="btn-p" onclick="requestPreview()">預覽 Dithering 效果 →</button>
      </div>
    </div>
  </div>

  <!-- ========== Preview View ========== -->
  <div id="view-preview" style="display:none">
    <div class="card">
      <div class="card-title">確認效果</div>
      <div class="preview-grid">
        <div class="preview-panel">
          <div class="preview-label">裁切預覽</div>
          <canvas id="crop-mini"></canvas>
        </div>
        <div class="preview-panel">
          <div class="preview-label">電子紙效果（280×448，Floyd-Steinberg）</div>
          <img id="dither-preview" alt="dithered preview" width="280" height="448">
        </div>
      </div>
      <div class="btn-row">
        <button class="btn-s" onclick="showView('crop');redrawCrop()">← 重新裁切</button>
        <button class="btn-p" onclick="confirmSave()">確認儲存並顯示</button>
      </div>
    </div>
  </div>

</div>

<div id="toast"></div>

<div id="img-modal" class="modal-overlay" style="display:none" onclick="closeModal(event)">
  <div class="modal-box">
    <button class="modal-close" onclick="closePreview()">×</button>
    <img id="modal-img" alt="">
    <div id="modal-fname" class="modal-fname"></div>
  </div>
</div>

<script>
// ────────────────────────────────────────────────────────
// State
// ────────────────────────────────────────────────────────
let uploadId = null;
let canvasScale = 1;     // canvas px / original image px
let imgOffsetX = 0;      // canvas px where image starts (left edge)
let imgOffsetY = 0;      // canvas px where image starts (top edge)
let cropRect = null;     // {x, y, w, h} in canvas coordinates
let drag = null;         // {type, startX, startY, origCrop}
let srcImg = null;       // Image element loaded for cropping
const CROP_RATIO = 280 / 448;  // e-paper card inner width / height
const HANDLE_R = 10;
const MIN_CROP_W = 40;
const EXPAND = 1.5;      // canvas is EXPAND× the image size; provides white padding around image

// ────────────────────────────────────────────────────────
// View management
// ────────────────────────────────────────────────────────
function showView(name) {
  ['gallery', 'crop', 'preview'].forEach(v => {
    document.getElementById('view-' + v).style.display = v === name ? '' : 'none';
  });
}

// ────────────────────────────────────────────────────────
// Gallery
// ────────────────────────────────────────────────────────
async function loadGallery() {
  try {
    const r = await fetch('/api/images');
    if (!r.ok) return;
    const data = await r.json();
    renderGrid(data.images);
  } catch (e) { /* ignore */ }
}

function renderGrid(images) {
  const grid = document.getElementById('img-grid');
  if (!images || images.length === 0) {
    grid.innerHTML = '<div class="empty-state">尚未上傳任何圖片</div>';
    return;
  }
  grid.innerHTML = '<div class="img-grid2">' + images.map(img => `
    <div class="img-card2">
      <div class="img-thumb2"
           data-id="${esc(img.id)}"
           data-name="${esc(img.filename)}"
           onclick="openPreview(this.dataset.id, this.dataset.name)">
        <img src="/api/images/file/${esc(img.id)}" alt="${esc(img.filename)}" loading="lazy">
        ${img.is_current ? '<div class="cur-ribbon">顯示中</div>' : ''}
        <button class="img-del-btn"
                onclick="event.stopPropagation();deleteImage('${esc(img.id)}')"
                title="刪除">×</button>
      </div>
      <div class="img-card2-name" title="${esc(img.filename)}">${esc(img.filename)}</div>
      <div class="img-card2-date">${fmtDate(img.created_ts)}</div>
    </div>
  `).join('') + '</div>';
}

// ────────────────────────────────────────────────────────
// Upload
// ────────────────────────────────────────────────────────
function startUpload() { document.getElementById('file-input').click(); }

function onDragOver(e) {
  e.preventDefault();
  document.getElementById('drop-zone').classList.add('drag-over');
}
function onDragLeave(e) {
  document.getElementById('drop-zone').classList.remove('drag-over');
}
function onDrop(e) {
  e.preventDefault();
  document.getElementById('drop-zone').classList.remove('drag-over');
  const f = e.dataTransfer.files[0];
  if (f) handleFile(f);
}
function onFileSelect(e) {
  const f = e.target.files[0];
  e.target.value = '';
  if (f) handleFile(f);
}

async function handleFile(file) {
  const MAX = 15 * 1024 * 1024;
  if (file.size > MAX) { toast('圖片過大（最大 15 MB）', 'err'); return; }

  const fd = new FormData();
  fd.append('file', file);
  toast('上傳中…', 'info');

  let data;
  try {
    const r = await fetch('/api/images/upload', { method: 'POST', body: fd });
    if (!r.ok) {
      const e2 = await r.json().catch(() => ({}));
      toast(e2.detail || '上傳失敗', 'err'); return;
    }
    data = await r.json();
  } catch (e) { toast('網路錯誤', 'err'); return; }

  uploadId = data.id;
  initCropView('/api/images/original/' + uploadId, data.orig_w, data.orig_h);
}

// ────────────────────────────────────────────────────────
// Crop view
// ────────────────────────────────────────────────────────
function initCropView(imgUrl, origW, origH) {
  showView('crop');
  const canvas = document.getElementById('crop-canvas');
  const img = new Image();
  img.onload = () => {
    // Scale to fit the card (max 640 wide, 520 tall)
    const container = canvas.parentElement;
    const maxW = Math.max(200, Math.min(640, container.clientWidth - 32));
    const maxH = Math.max(200, 520);
    // Scale so that the expanded canvas (EXPAND× image) fits the container
    const scaleW = maxW / (img.naturalWidth * EXPAND);
    const scaleH = maxH / (img.naturalHeight * EXPAND);
    canvasScale = Math.min(scaleW, scaleH, 1);  // never upscale image beyond 1:1

    const imgPxW = Math.round(img.naturalWidth * canvasScale);
    const imgPxH = Math.round(img.naturalHeight * canvasScale);
    canvas.width = Math.round(imgPxW * EXPAND);
    canvas.height = Math.round(imgPxH * EXPAND);
    imgOffsetX = Math.round((canvas.width - imgPxW) / 2);
    imgOffsetY = Math.round((canvas.height - imgPxH) / 2);

    srcImg = img;
    cropRect = fitCropRect(canvas.width, canvas.height);
    drawCropUI();
    attachCropEvents(canvas);
  };
  img.onerror = () => toast('圖片載入失敗', 'err');
  img.src = imgUrl;
}

function fitCropRect(cw, ch) {
  // Default: largest crop fitting the image area (inside the whitespace padding)
  const imgPxW = Math.round(cw / EXPAND);
  const imgPxH = Math.round(ch / EXPAND);
  let w = imgPxH * CROP_RATIO;
  let h = imgPxH;
  if (w > imgPxW) { w = imgPxW; h = w / CROP_RATIO; }
  return {
    x: Math.round((cw - w) / 2),
    y: Math.round((ch - h) / 2),
    w: Math.round(w),
    h: Math.round(h)
  };
}

function drawCropUI() {
  const canvas = document.getElementById('crop-canvas');
  const ctx = canvas.getContext('2d');
  const {x, y, w, h} = cropRect;

  ctx.clearRect(0, 0, canvas.width, canvas.height);
  // White background (matches e-paper; out-of-bounds crop area becomes white)
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  // Draw image centered in the expanded canvas
  const imgPxW = Math.round(canvas.width / EXPAND);
  const imgPxH = Math.round(canvas.height / EXPAND);
  ctx.drawImage(srcImg, imgOffsetX, imgOffsetY, imgPxW, imgPxH);
  // Subtle dashed border marking the image boundary
  ctx.strokeStyle = 'rgba(100,116,139,0.45)';
  ctx.setLineDash([5, 5]);
  ctx.lineWidth = 1;
  ctx.strokeRect(imgOffsetX + 0.5, imgOffsetY + 0.5, imgPxW - 1, imgPxH - 1);
  ctx.setLineDash([]);

  // Dark overlay outside crop
  ctx.fillStyle = 'rgba(0,0,0,0.55)';
  ctx.fillRect(0, 0, canvas.width, y);
  ctx.fillRect(0, y, x, h);
  ctx.fillRect(x + w, y, canvas.width - x - w, h);
  ctx.fillRect(0, y + h, canvas.width, canvas.height - y - h);

  // Rule of thirds grid
  ctx.strokeStyle = 'rgba(56,189,248,0.22)';
  ctx.lineWidth = 1;
  for (let i = 1; i < 3; i++) {
    ctx.beginPath(); ctx.moveTo(x + i*w/3, y); ctx.lineTo(x + i*w/3, y+h); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(x, y + i*h/3); ctx.lineTo(x+w, y + i*h/3); ctx.stroke();
  }

  // Crop border
  ctx.strokeStyle = '#38bdf8';
  ctx.lineWidth = 2;
  ctx.strokeRect(x, y, w, h);

  // Corner handles
  ctx.fillStyle = '#38bdf8';
  [[x,y],[x+w,y],[x,y+h],[x+w,y+h]].forEach(([hx,hy]) => {
    ctx.fillRect(hx - 5, hy - 5, 10, 10);
  });
}

function redrawCrop() {
  if (srcImg && cropRect) drawCropUI();
}

function hitTest(pos) {
  if (!cropRect) return null;
  const {x, y, w, h} = cropRect;
  const corners = {nw:[x,y], ne:[x+w,y], sw:[x,y+h], se:[x+w,y+h]};
  for (const [name, [hx,hy]] of Object.entries(corners)) {
    if (Math.abs(pos.x - hx) < HANDLE_R && Math.abs(pos.y - hy) < HANDLE_R) return name;
  }
  if (pos.x > x && pos.x < x+w && pos.y > y && pos.y < y+h) return 'move';
  return null;
}

function attachCropEvents(canvas) {
  function getPos(e) {
    const r = canvas.getBoundingClientRect();
    return { x: e.clientX - r.left, y: e.clientY - r.top };
  }

  canvas.style.touchAction = 'none';

  canvas.onpointerdown = e => {
    const pos = getPos(e);
    const hit = hitTest(pos);
    if (hit) {
      drag = { type: hit, startX: pos.x, startY: pos.y, origCrop: {...cropRect} };
      canvas.setPointerCapture(e.pointerId);
      e.preventDefault();
    }
  };

  canvas.onpointermove = e => {
    if (!drag) return;
    const pos = getPos(e);
    updateCrop(pos, canvas.width, canvas.height);
    drawCropUI();
    e.preventDefault();
  };

  canvas.onpointerup = canvas.onpointercancel = () => { drag = null; };
}

function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }

function updateCrop(pos, cw, ch) {
  const dx = pos.x - drag.startX;
  const dy = pos.y - drag.startY;
  const o = drag.origCrop;
  const R = CROP_RATIO;

  if (drag.type === 'move') {
    cropRect = {
      x: clamp(o.x + dx, 0, cw - o.w),
      y: clamp(o.y + dy, 0, ch - o.h),
      w: o.w, h: o.h
    };
    return;
  }

  let w, h, nx, ny;
  if (drag.type === 'se') {
    w = clamp(o.w + dx, MIN_CROP_W, cw - o.x);
    h = w / R; if (o.y + h > ch) { h = ch - o.y; w = h * R; }
    nx = o.x; ny = o.y;
  } else if (drag.type === 'nw') {
    w = clamp(o.w - dx, MIN_CROP_W, o.x + o.w);
    h = w / R; if (h > o.y + o.h) { h = o.y + o.h; w = h * R; }
    nx = o.x + o.w - w; ny = o.y + o.h - h;
  } else if (drag.type === 'ne') {
    w = clamp(o.w + dx, MIN_CROP_W, cw - o.x);
    h = w / R; if (h > o.y + o.h) { h = o.y + o.h; w = h * R; }
    nx = o.x; ny = o.y + o.h - h;
  } else { // sw
    w = clamp(o.w - dx, MIN_CROP_W, o.x + o.w);
    h = w / R; if (o.y + h > ch) { h = ch - o.y; w = h * R; }
    nx = o.x + o.w - w; ny = o.y;
  }

  cropRect = { x: Math.round(nx), y: Math.round(ny), w: Math.round(w), h: Math.round(h) };
}

function getOrigCrop() {
  // x/y can be negative when crop extends into the white padding beyond image edge
  return {
    x: Math.round((cropRect.x - imgOffsetX) / canvasScale),
    y: Math.round((cropRect.y - imgOffsetY) / canvasScale),
    w: Math.round(cropRect.w / canvasScale),
    h: Math.round(cropRect.h / canvasScale)
  };
}

// ────────────────────────────────────────────────────────
// Preview
// ────────────────────────────────────────────────────────
async function requestPreview() {
  if (!uploadId || !cropRect) return;
  toast('生成 dithering 預覽中…', 'info');

  const crop = getOrigCrop();
  let blob;
  try {
    const r = await fetch('/api/images/preview', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ id: uploadId, crop })
    });
    if (!r.ok) { const e2 = await r.json().catch(()=>({})); toast(e2.detail || '預覽失敗', 'err'); return; }
    blob = await r.blob();
  } catch (e) { toast('網路錯誤', 'err'); return; }

  // Draw dithered preview
  const url = URL.createObjectURL(blob);
  document.getElementById('dither-preview').src = url;

  // Draw crop mini preview with white background (handles out-of-bounds white padding)
  const canvas = document.getElementById('crop-canvas');
  const imgPxWc = Math.round(canvas.width / EXPAND);
  const imgPxHc = Math.round(canvas.height / EXPAND);
  const mini = document.getElementById('crop-mini');
  mini.width = 140;
  mini.height = Math.round(140 / CROP_RATIO);
  const mctx = mini.getContext('2d');
  mctx.fillStyle = '#ffffff';
  mctx.fillRect(0, 0, mini.width, mini.height);
  const {x: cx, y: cy, w: cw, h: ch} = cropRect;
  const ix1 = Math.max(cx, imgOffsetX);
  const iy1 = Math.max(cy, imgOffsetY);
  const ix2 = Math.min(cx + cw, imgOffsetX + imgPxWc);
  const iy2 = Math.min(cy + ch, imgOffsetY + imgPxHc);
  if (ix2 > ix1 && iy2 > iy1) {
    const scaleM = mini.width / cw;
    mctx.drawImage(srcImg,
      (ix1 - imgOffsetX) / canvasScale, (iy1 - imgOffsetY) / canvasScale,
      (ix2 - ix1) / canvasScale, (iy2 - iy1) / canvasScale,
      (ix1 - cx) * scaleM, (iy1 - cy) * (mini.height / ch),
      (ix2 - ix1) * scaleM, (iy2 - iy1) * (mini.height / ch)
    );
  }

  showView('preview');
}

// ────────────────────────────────────────────────────────
// Confirm
// ────────────────────────────────────────────────────────
async function confirmSave() {
  if (!uploadId || !cropRect) return;
  toast('儲存並套用中…', 'info');

  const crop = getOrigCrop();
  try {
    const r = await fetch('/api/images/' + uploadId + '/confirm', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ crop })
    });
    if (!r.ok) { const e2 = await r.json().catch(()=>({})); toast(e2.detail || '儲存失敗', 'err'); return; }
  } catch (e) { toast('網路錯誤', 'err'); return; }

  toast('已儲存，已套用到電子紙', 'ok');
  uploadId = null; srcImg = null; cropRect = null;
  showView('gallery');
  loadGallery();
}

// ────────────────────────────────────────────────────────
// Cancel crop
// ────────────────────────────────────────────────────────
async function cancelCrop() {
  if (uploadId) {
    // Delete unconfirmed upload from server
    try { await fetch('/api/images/' + uploadId, { method: 'DELETE' }); } catch (_) {}
    uploadId = null;
  }
  srcImg = null; cropRect = null;
  showView('gallery');
}

// ────────────────────────────────────────────────────────
// Delete image
// ────────────────────────────────────────────────────────
async function deleteImage(id) {
  if (!confirm('確定要刪除這張圖片嗎？')) return;
  try {
    const r = await fetch('/api/images/' + id, { method: 'DELETE' });
    if (!r.ok) { const e2 = await r.json().catch(()=>({})); toast(e2.detail || '刪除失敗', 'err'); return; }
  } catch (e) { toast('網路錯誤', 'err'); return; }
  toast('已刪除', 'ok');
  loadGallery();
}

// ────────────────────────────────────────────────────────
// Carousel settings
// ────────────────────────────────────────────────────────
async function loadCarousel() {
  try {
    const r = await fetch('/api/images/carousel');
    if (!r.ok) return;
    const d = await r.json();
    document.getElementById('c-enabled').checked = d.enabled;
    document.getElementById('c-interval').value = d.interval_minutes;
    document.getElementById('c-mode').value = d.mode;
  } catch (_) {}
}

async function saveCarousel() {
  const body = {
    enabled: document.getElementById('c-enabled').checked,
    interval_minutes: parseInt(document.getElementById('c-interval').value) || 30,
    mode: document.getElementById('c-mode').value
  };
  try {
    const r = await fetch('/api/images/carousel', {
      method: 'PUT', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(body)
    });
    if (!r.ok) { toast('儲存失敗', 'err'); return; }
    toast('輪播設定已儲存', 'ok');
  } catch (_) { toast('網路錯誤', 'err'); }
}

async function advanceCarousel() {
  try {
    const r = await fetch('/api/images/carousel/advance', { method: 'PUT' });
    if (!r.ok) {
      const e2 = await r.json().catch(()=>({}));
      toast(e2.detail || '操作失敗', 'err'); return;
    }
    toast('已切換到下一張', 'ok');
    loadGallery();
  } catch (_) { toast('網路錯誤', 'err'); }
}

// ────────────────────────────────────────────────────────
// Utilities
// ────────────────────────────────────────────────────────
function esc(s) {
  return String(s)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function fmtDate(ts) {
  if (!ts) return '';
  const d = new Date(ts);
  return d.getFullYear() + '/' +
    String(d.getMonth()+1).padStart(2,'0') + '/' +
    String(d.getDate()).padStart(2,'0');
}

let _toastTimer;
function toast(msg, type='ok') {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.className = 'show ' + type;
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(() => { el.className = ''; }, 3000);
}

// ────────────────────────────────────────────────────────
// Init
// ────────────────────────────────────────────────────────
// Image preview modal
// ────────────────────────────────────────────────────────
function openPreview(id, name) {
  document.getElementById('modal-img').src = '/api/images/file/' + id;
  document.getElementById('modal-fname').textContent = name;
  document.getElementById('img-modal').style.display = 'flex';
}

function closePreview() {
  const modal = document.getElementById('img-modal');
  modal.style.display = 'none';
  document.getElementById('modal-img').removeAttribute('src');
}

function closeModal(e) {
  if (e.target === document.getElementById('img-modal')) closePreview();
}

document.addEventListener('keydown', e => {
  if (e.key === 'Escape' && document.getElementById('img-modal').style.display !== 'none') closePreview();
});

// ────────────────────────────────────────────────────────
loadGallery();
loadCarousel();
</script>

</body>
</html>"""
