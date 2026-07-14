from app.webui.templates.base import _make_shell

_IMAGES_CONTENT = r"""
<style>
  .img-grid2{display:grid;grid-template-columns:repeat(auto-fill,96px);gap:.8rem;justify-content:start;margin-top:.9rem}
  .img-card2{width:96px;display:flex;flex-direction:column;align-items:center}
  .img-thumb2{width:88px;height:141px;background:var(--ink-soft);border-radius:0;overflow:hidden;position:relative;flex-shrink:0;cursor:pointer}
  .img-thumb2 img{width:100%;height:100%;object-fit:cover;image-rendering:pixelated;display:block;transition:filter .15s}
  .img-thumb2:hover>img{filter:brightness(.78)}
  .cur-ribbon{position:absolute;bottom:0;left:0;right:0;background:var(--teal);color:var(--on-dark);font:700 .62rem Consolas,monospace;text-align:center;padding:.18rem 0}
  .img-del-btn{position:absolute;top:4px;right:4px;width:20px;height:20px;border-radius:0;background:var(--coral);border:1px solid var(--coral);color:var(--on-dark);font:700 1rem Consolas,monospace;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:background .15s,border-color .15s;padding:0;line-height:1}
  .img-del-btn:hover{background:var(--coral-dark);border-color:var(--coral-dark)}
  .img-card2-name{font-size:.72rem;font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-top:.35rem;width:96px;text-align:center;color:var(--text)}
  .img-card2-date{font-size:.67rem;color:var(--muted);text-align:center;margin-top:.08rem}
  .empty-state{text-align:center;padding:2rem;color:var(--muted);font-size:.88rem}
  .drop-zone{border:2px dashed var(--line);border-radius:0;padding:2rem;text-align:center;cursor:pointer;transition:border-color .2s,background .2s;color:var(--muted)}
  .drop-zone:hover,.drop-zone.drag-over{border-color:var(--teal);background:var(--surface-2);color:var(--ink)}
  .drop-zone-icon{display:none}
  .drop-zone-text{font-size:.85rem}
  .crop-wrap{display:flex;flex-direction:column;align-items:center;gap:1rem}
  #crop-canvas{max-width:100%;cursor:crosshair;border-radius:0;display:block;touch-action:none}
  .crop-hint{font-size:.78rem;color:var(--muted);text-align:center}
  .transform-bar{display:flex;gap:.45rem;flex-wrap:wrap;justify-content:center;margin:.6rem 0 .2rem}
  .btn-tf{background:var(--surface-2);color:var(--ink);border:1px solid var(--line);border-radius:0;padding:.32rem .65rem;font:700 .78rem Consolas,monospace;cursor:pointer;transition:background .15s;white-space:nowrap}
  .btn-tf:hover{background:var(--ink-soft);color:var(--on-dark)}
  .preview-grid{display:grid;grid-template-columns:1fr 1fr;gap:1.2rem;margin-bottom:1rem}
  .preview-panel{text-align:center}
  .preview-label{font-size:.75rem;color:var(--muted);margin-bottom:.5rem;font-weight:500;text-transform:uppercase;letter-spacing:.05em}
  #crop-mini,#dither-preview{max-width:100%;border-radius:0;border:1px solid var(--line);display:block;margin:0 auto;image-rendering:pixelated}
  .modal-overlay{position:fixed;inset:0;background:rgba(0,0,0,.72);z-index:10000;display:flex;align-items:center;justify-content:center}
  .modal-box{background:var(--surface);border:1px solid var(--ink);border-radius:0;box-shadow:5px 5px 0 var(--line);padding:1.3rem 1.1rem 1rem;display:flex;flex-direction:column;align-items:center;gap:.75rem;position:relative;max-width:90vw}
  .modal-close{position:absolute;top:.5rem;right:.7rem;background:transparent;border:none;color:var(--muted);font-size:1.5rem;cursor:pointer;line-height:1;padding:.1rem .35rem;transition:color .15s}
  .modal-close:hover{color:var(--text)}
  #modal-img{max-height:70vh;max-width:min(560px,85vw);width:auto;height:auto;image-rendering:pixelated;border-radius:0;display:block}
  .modal-fname{font-size:.78rem;color:var(--muted);text-align:center;max-width:320px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  @media(max-width:600px){.preview-grid{grid-template-columns:1fr}}
</style>

<div class="page-wrap">
  <h1 class="page-title">圖片輪播管理</h1>

  <div id="view-gallery">
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
          <label>換圖間隔 <span class="hint">（每幾次刷新，最少 1）</span></label>
          <input type="number" id="c-interval" min="1" max="999" value="10">
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

    <div class="card">
      <div class="card-title">已上傳圖片</div>
      <div id="drop-zone" class="drop-zone" onclick="startUpload()" ondragover="onDragOver(event)" ondragleave="onDragLeave(event)" ondrop="onDrop(event)">
        <div class="drop-zone-icon" aria-hidden="true"></div>
        <div class="drop-zone-text">點擊上傳，或將圖片拖曳至此<br><span style="font-size:.73rem;color:var(--muted)">支援 JPEG、PNG、WebP（最大 15 MB）</span></div>
      </div>
      <input type="file" id="file-input" accept="image/jpeg,image/png,image/webp,image/gif,image/bmp" style="display:none" onchange="onFileSelect(event)">
      <div id="img-grid"></div>
    </div>
  </div>

  <div id="view-crop" style="display:none">
    <div class="card">
      <div class="card-title">裁切圖片 <span style="color:var(--muted);font-size:.75rem;font-weight:400;letter-spacing:0;text-transform:none">— 拖曳選框定位，拖曳角點調整大小（固定 5:8 比例）</span></div>
      <div class="crop-wrap">
        <canvas id="crop-canvas"></canvas>
        <div class="crop-hint">選框比例鎖定為電子紙圖片卡尺寸（280×448）；可拖曳至圖片外側白邊，超出部分顯示為白色</div>
      </div>
      <div class="transform-bar">
        <button class="btn-tf" onclick="doRotate(-90)" title="逆時鐘旋轉 90°">↺ 逆時鐘</button>
        <button class="btn-tf" onclick="doRotate(90)"  title="順時鐘旋轉 90°">↻ 順時鐘</button>
        <button class="btn-tf" onclick="doFlip('x')"   title="水平鏡像（左右翻轉）">↔ 鏡像 X</button>
        <button class="btn-tf" onclick="doFlip('y')"   title="垂直鏡像（上下翻轉）">↕ 鏡像 Y</button>
        <button class="btn-tf" onclick="centerCrop()"  title="將裁切框置中於畫布">⊡ 置中</button>
      </div>
      <div class="btn-row">
        <button class="btn-s" onclick="cancelCrop()">取消</button>
        <button class="btn-p" onclick="requestPreview()">預覽 Dithering 效果 →</button>
      </div>
    </div>
  </div>

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

<div id="img-modal" class="modal-overlay" style="display:none" onclick="closeModal(event)">
  <div class="modal-box">
    <button class="modal-close" onclick="closePreview()">×</button>
    <img id="modal-img" alt="">
    <div id="modal-fname" class="modal-fname"></div>
  </div>
</div>

<script>
let uploadId = null;
let canvasScale = 1;
let imgOffsetX = 0;
let imgOffsetY = 0;
let cropRect = null;
let drag = null;
let srcImg = null;
let transform = {rotate: 0, flipX: false, flipY: false};
const CROP_RATIO = 280 / 448;
const HANDLE_R = 10;
const MIN_CROP_W = 40;
const EXPAND = 2.0;

function showView(name) {
  ['gallery', 'crop', 'preview'].forEach(v => {
    document.getElementById('view-' + v).style.display = v === name ? '' : 'none';
  });
}

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

function initCropView(imgUrl, origW, origH) {
  showView('crop');
  const canvas = document.getElementById('crop-canvas');
  const img = new Image();
  img.onload = () => {
    transform = {rotate: 0, flipX: false, flipY: false};
    srcImg = img;
    reinitCanvas();
    drawCropUI();
    attachCropEvents(canvas);
  };
  img.onerror = () => toast('圖片載入失敗', 'err');
  img.src = imgUrl;
}

function reinitCanvas() {
  const isRotated90 = (transform.rotate % 180 !== 0);
  const tw = isRotated90 ? srcImg.naturalHeight : srcImg.naturalWidth;
  const th = isRotated90 ? srcImg.naturalWidth  : srcImg.naturalHeight;
  const canvas = document.getElementById('crop-canvas');
  const container = canvas.parentElement;
  const maxW = Math.max(200, Math.min(640, container.clientWidth - 32));
  const maxH = Math.max(200, 520);
  const scaleW = maxW / (tw * EXPAND);
  const scaleH = maxH / (th * EXPAND);
  canvasScale = Math.min(scaleW, scaleH, 1);
  const imgPxW = Math.round(tw * canvasScale);
  const imgPxH = Math.round(th * canvasScale);
  canvas.width  = Math.round(imgPxW * EXPAND);
  canvas.height = Math.round(imgPxH * EXPAND);
  imgOffsetX = Math.round((canvas.width  - imgPxW) / 2);
  imgOffsetY = Math.round((canvas.height - imgPxH) / 2);
  cropRect = fitCropRect(canvas.width, canvas.height);
}

function fitCropRect(cw, ch) {
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
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  const imgPxW = Math.round(canvas.width / EXPAND);
  const imgPxH = Math.round(canvas.height / EXPAND);
  ctx.save();
  ctx.translate(imgOffsetX + imgPxW / 2, imgOffsetY + imgPxH / 2);
  ctx.rotate(transform.rotate * Math.PI / 180);
  if (transform.flipY) ctx.scale( 1, -1);
  if (transform.flipX) ctx.scale(-1,  1);
  ctx.drawImage(srcImg,
    -srcImg.naturalWidth  * canvasScale / 2,
    -srcImg.naturalHeight * canvasScale / 2,
     srcImg.naturalWidth  * canvasScale,
     srcImg.naturalHeight * canvasScale);
  ctx.restore();
  const lineColor = getComputedStyle(document.documentElement).getPropertyValue('--line').trim();
  const tealColor = getComputedStyle(document.documentElement).getPropertyValue('--teal').trim();
  const overlayColor = getComputedStyle(document.documentElement).getPropertyValue('--crop-overlay').trim();
  ctx.strokeStyle = lineColor;
  ctx.setLineDash([5, 5]);
  ctx.lineWidth = 1;
  ctx.strokeRect(imgOffsetX + 0.5, imgOffsetY + 0.5, imgPxW - 1, imgPxH - 1);
  ctx.setLineDash([]);
  ctx.fillStyle = overlayColor;
  ctx.fillRect(0, 0, canvas.width, y);
  ctx.fillRect(0, y, x, h);
  ctx.fillRect(x + w, y, canvas.width - x - w, h);
  ctx.fillRect(0, y + h, canvas.width, canvas.height - y - h);
  ctx.globalAlpha = 0.22;
  ctx.strokeStyle = tealColor;
  ctx.lineWidth = 1;
  for (let i = 1; i < 3; i++) {
    ctx.beginPath(); ctx.moveTo(x + i*w/3, y); ctx.lineTo(x + i*w/3, y+h); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(x, y + i*h/3); ctx.lineTo(x+w, y + i*h/3); ctx.stroke();
  }
  ctx.globalAlpha = 1;
  ctx.strokeStyle = tealColor;
  ctx.lineWidth = 2;
  ctx.strokeRect(x, y, w, h);
  ctx.fillStyle = tealColor;
  [[x,y],[x+w,y],[x,y+h],[x+w,y+h]].forEach(([hx,hy]) => {
    ctx.fillRect(hx - 5, hy - 5, 10, 10);
  });
}

document.addEventListener('iot-theme-change', redrawCrop);

function redrawCrop() {
  if (srcImg && cropRect) drawCropUI();
}

function doRotate(deg) {
  transform.rotate = ((transform.rotate + deg) % 360 + 360) % 360;
  reinitCanvas();
  drawCropUI();
}

function doFlip(axis) {
  if (axis === 'x') transform.flipX = !transform.flipX;
  else              transform.flipY = !transform.flipY;
  drawCropUI();
}

function centerCrop() {
  const canvas = document.getElementById('crop-canvas');
  if (!cropRect) return;
  cropRect = {
    x: Math.round((canvas.width  - cropRect.w) / 2),
    y: Math.round((canvas.height - cropRect.h) / 2),
    w: cropRect.w,
    h: cropRect.h
  };
  drawCropUI();
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
  } else {
    w = clamp(o.w - dx, MIN_CROP_W, o.x + o.w);
    h = w / R; if (o.y + h > ch) { h = ch - o.y; w = h * R; }
    nx = o.x + o.w - w; ny = o.y;
  }
  cropRect = { x: Math.round(nx), y: Math.round(ny), w: Math.round(w), h: Math.round(h) };
}

function getOrigCrop() {
  return {
    x: Math.round((cropRect.x - imgOffsetX) / canvasScale),
    y: Math.round((cropRect.y - imgOffsetY) / canvasScale),
    w: Math.round(cropRect.w / canvasScale),
    h: Math.round(cropRect.h / canvasScale)
  };
}

async function requestPreview() {
  if (!uploadId || !cropRect) return;
  toast('生成 dithering 預覽中…', 'info');
  const crop = getOrigCrop();
  let blob;
  try {
    const r = await fetch('/api/images/preview', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ id: uploadId, crop, transform: {rotate: transform.rotate, flip_x: transform.flipX, flip_y: transform.flipY} })
    });
    if (!r.ok) { const e2 = await r.json().catch(()=>({})); toast(e2.detail || '預覽失敗', 'err'); return; }
    blob = await r.blob();
  } catch (e) { toast('網路錯誤', 'err'); return; }
  const url = URL.createObjectURL(blob);
  document.getElementById('dither-preview').src = url;
  const canvas = document.getElementById('crop-canvas');
  const imgPxWc = Math.round(canvas.width / EXPAND);
  const imgPxHc = Math.round(canvas.height / EXPAND);
  const mini = document.getElementById('crop-mini');
  mini.width = 140;
  mini.height = Math.round(140 / CROP_RATIO);
  const mctx = mini.getContext('2d');
  mctx.fillStyle = '#ffffff';
  mctx.fillRect(0, 0, mini.width, mini.height);
  const {x: cx, y: cy, w: cw} = cropRect;
  const scaleM = mini.width / cw;
  const miniCx = (imgOffsetX + imgPxWc / 2 - cx) * scaleM;
  const miniCy = (imgOffsetY + imgPxHc / 2 - cy) * scaleM;
  mctx.save();
  mctx.translate(miniCx, miniCy);
  mctx.rotate(transform.rotate * Math.PI / 180);
  if (transform.flipY) mctx.scale( 1, -1);
  if (transform.flipX) mctx.scale(-1,  1);
  const sw = srcImg.naturalWidth  * canvasScale * scaleM;
  const sh = srcImg.naturalHeight * canvasScale * scaleM;
  mctx.drawImage(srcImg, -sw / 2, -sh / 2, sw, sh);
  mctx.restore();
  showView('preview');
}

async function confirmSave() {
  if (!uploadId || !cropRect) return;
  toast('儲存並套用中…', 'info');
  const crop = getOrigCrop();
  try {
    const r = await fetch('/api/images/' + uploadId + '/confirm', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ crop, transform: {rotate: transform.rotate, flip_x: transform.flipX, flip_y: transform.flipY} })
    });
    if (!r.ok) { const e2 = await r.json().catch(()=>({})); toast(e2.detail || '儲存失敗', 'err'); return; }
  } catch (e) { toast('網路錯誤', 'err'); return; }
  toast('已儲存，已套用到電子紙', 'ok');
  transform = {rotate: 0, flipX: false, flipY: false};
  uploadId = null; srcImg = null; cropRect = null;
  showView('gallery');
  loadGallery();
}

async function cancelCrop() {
  if (uploadId) {
    try { await fetch('/api/images/' + uploadId, { method: 'DELETE' }); } catch (_) {}
    uploadId = null;
  }
  transform = {rotate: 0, flipX: false, flipY: false};
  srcImg = null; cropRect = null;
  showView('gallery');
}

async function deleteImage(id) {
  if (!confirm('確定要刪除這張圖片嗎？')) return;
  try {
    const r = await fetch('/api/images/' + id, { method: 'DELETE' });
    if (!r.ok) { const e2 = await r.json().catch(()=>({})); toast(e2.detail || '刪除失敗', 'err'); return; }
  } catch (e) { toast('網路錯誤', 'err'); return; }
  toast('已刪除', 'ok');
  loadGallery();
}

async function loadCarousel() {
  try {
    const r = await fetch('/api/images/carousel');
    if (!r.ok) return;
    const d = await r.json();
    document.getElementById('c-enabled').checked = d.enabled;
    document.getElementById('c-interval').value = d.interval_refreshes;
    document.getElementById('c-mode').value = d.mode;
  } catch (_) {}
}

async function saveCarousel() {
  const body = {
    enabled: document.getElementById('c-enabled').checked,
    interval_refreshes: parseInt(document.getElementById('c-interval').value) || 10,
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

loadGallery();
loadCarousel();
</script>
"""

_IMAGES_HTML = _make_shell("images", "圖片輪播管理", _IMAGES_CONTENT)
