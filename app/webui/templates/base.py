from app.webui.templates.theme import (
    _CSRF_FETCH_SCRIPT,
    _FAVICON_DATA_URI,
    _THEME_CONTROL_SCRIPT,
    _THEME_CSS,
    _THEME_INIT_SCRIPT,
)


_THEME_CSS += r"""
.page-desc{margin:.35rem 0 1.15rem;color:var(--muted);font:400 .88rem/1.6 Georgia,'Noto Serif TC',serif;max-width:640px}
.summary-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.6rem;margin-bottom:.9rem}
.pagination{display:flex;align-items:center;justify-content:center;gap:.75rem;margin-top:.75rem}
.pagination button{min-width:0;padding:.4rem .75rem}
.pagination button:disabled{opacity:.4;cursor:not-allowed}
.pagination-info{color:var(--muted);font:700 .74rem Consolas,monospace;min-width:5.5rem;text-align:center}
@media(max-width:480px){.summary-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.summary-grid .metric:last-child{grid-column:1/-1}}
"""


_SHELL = (
    r"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="description" content="ePaper Home Display 本機裝置控制台">
  <title>ePaper Home Display / __TITLE__</title>
  <link rel="icon" type="image/svg+xml" href="__FAVICON__">
  <script>__THEME_INIT__</script>
  <style>__THEME_CSS__</style>
  __EXTRA_HEAD__
</head>
<body data-page="__PAGE_ID__">
<header class="topbar">
  <div class="topbar-in">
    <a class="brand" href="/desk" aria-label="返回書桌分析">
      <span class="brand-mark">EH</span>
      <span class="brand-copy">EPAPER HOME DISPLAY<span class="brand-sub">LOCAL DEVICE / HOME DASHBOARD</span></span>
    </a>
    <div class="topbar-actions">
      <nav class="nav" aria-label="主導覽">
        <a class="nav-link __DESK_A__" href="/desk">書桌</a>
        <a class="nav-link __ENV_A__" href="/environment">環境</a>
        <a class="nav-link __IMAGES_A__" href="/images">圖片</a>
        <a class="nav-link __SETTINGS_A__" href="/settings">設定</a>
        <button type="button" class="nav-link danger" data-action="logout">登出</button>
      </nav>
      <div class="theme-toggle" role="group" aria-label="配色主題切換">
        <button type="button" data-theme-choice="light" aria-pressed="false">LIGHT</button>
        <button type="button" data-theme-choice="dark" aria-pressed="false">DARK</button>
      </div>
    </div>
  </div>
</header>
<div id="toast" aria-live="polite"></div>
<main class="main-content">__CONTENT__</main>
<footer class="site-footer">
  <div class="footer-in">
    <div class="footer-repo"><span class="label">SOURCE</span><a href="https://github.com/Ning0612/epaper-home-display">Ning0612/epaper-home-display</a></div>
    <div class="footer-meta">__FOOTER_META__</div>
  </div>
</footer>
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


def _make_shell(
    page_id: str,
    title: str,
    content: str,
    extra_head: str = "",
    footer_meta: str = "FastAPI · Vanilla HTML／CSS／JS · MIT License",
) -> str:
    return (
        _SHELL
        .replace("__TITLE__", title)
        .replace("__PAGE_ID__", page_id)
        .replace("__EXTRA_HEAD__", extra_head)
        .replace("__CONTENT__", content)
        .replace("__FOOTER_META__", footer_meta)
        .replace("__DESK_A__", "active" if page_id == "desk" else "")
        .replace("__ENV_A__", "active" if page_id == "environment" else "")
        .replace("__IMAGES_A__", "active" if page_id == "images" else "")
        .replace("__SETTINGS_A__", "active" if page_id == "settings" else "")
    )
