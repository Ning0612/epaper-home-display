import html as _html

_LOGIN_HTML = r"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>登入 — ePaper Home Display</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,600;9..40,700&family=DM+Mono:wght@400;500&display=swap">
  <style>
    *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
    :root{
      --bg:#080d18;--surface:#0f172a;--border:#1e3a5f;
      --primary:#38bdf8;--primary-h:#0ea5e9;--text:#e2e8f0;--muted:#64748b;
      --err-bg:rgba(248,113,113,.08);--err-border:rgba(248,113,113,.3);--r:10px
    }
    body{background:var(--bg);color:var(--text);min-height:100vh;display:flex;align-items:center;justify-content:center;font-family:'DM Sans',system-ui,sans-serif}
    .card{background:var(--surface);border:1px solid var(--border);border-top:2px solid var(--primary);border-radius:var(--r);padding:2rem;width:100%;max-width:360px;box-shadow:0 4px 32px rgba(0,0,0,.5)}
    .logo{text-align:center;font-size:2rem;margin-bottom:.4rem}
    .title{text-align:center;font-size:1.05rem;font-weight:600;margin-bottom:.25rem}
    .sub{text-align:center;font-size:.78rem;color:var(--muted);margin-bottom:1.5rem}
    .err{background:var(--err-bg);border:1px solid var(--err-border);color:#f87171;border-radius:6px;padding:.55rem .9rem;font-size:.82rem;margin-bottom:1rem}
    label{display:block;font-size:.78rem;font-weight:500;margin-bottom:.3rem}
    input[type=password]{width:100%;padding:.55rem .75rem;border:1px solid var(--border);border-radius:6px;font-size:.9rem;color:var(--text);background:var(--bg);outline:none;transition:border-color .15s,box-shadow .15s}
    input[type=password]:focus{border-color:var(--primary);box-shadow:0 0 0 3px rgba(56,189,248,.15)}
    .f{margin-bottom:.9rem}
    button{width:100%;padding:.6rem;background:var(--primary);color:#080d18;border:none;border-radius:6px;font-size:.9rem;font-weight:600;cursor:pointer;margin-top:.5rem;transition:background .15s}
    button:hover{background:var(--primary-h)}
  </style>
</head>
<body>
<div class="card">
  <div class="logo">🖥️</div>
  <div class="title">ePaper Home Display</div>
  <div class="sub">__SUBTITLE__</div>
  __ERROR_HTML__
  <form method="post" action="/login">
    <input type="hidden" name="next" value="__NEXT__">
    <div class="f">
      <label>密碼</label>
      <input type="password" name="password" required autofocus placeholder="輸入密碼">
    </div>
    __CONFIRM_FIELD__
    <button type="submit">__BUTTON__</button>
  </form>
</div>
</body>
</html>"""


def _render_login(next_url: str = "/settings", error: str = "", is_setup: bool = False) -> str:
    raw_next = next_url if next_url.startswith("/") and not next_url.startswith("//") else "/settings"
    safe_next = _html.escape(raw_next, quote=True)
    subtitle = "首次設定 — 請設定登入密碼" if is_setup else "請輸入密碼以登入"
    button = "設定密碼" if is_setup else "登入"
    error_html = f'<div class="err">{_html.escape(error)}</div>' if error else ""
    confirm_field = (
        '<div class="f"><label>確認密碼</label>'
        '<input type="password" name="password_confirm" required placeholder="再次輸入密碼"></div>'
        if is_setup else ""
    )
    return (
        _LOGIN_HTML
        .replace("__SUBTITLE__", subtitle)
        .replace("__BUTTON__", button)
        .replace("__ERROR_HTML__", error_html)
        .replace("__CONFIRM_FIELD__", confirm_field)
        .replace("__NEXT__", safe_next)
    )
