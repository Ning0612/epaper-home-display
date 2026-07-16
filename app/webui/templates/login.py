import html as _html

from app.webui.templates.theme import (
    _FAVICON_DATA_URI,
    _THEME_CONTROL_SCRIPT,
    _THEME_CSS,
    _THEME_INIT_SCRIPT,
)


_LOGIN_HTML = (
    r"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="description" content="ePaper Home Display 管理介面登入">
  <title>ePaper Home Display / 登入</title>
  <link rel="icon" type="image/svg+xml" href="__FAVICON__">
  <script>__THEME_INIT__</script>
  <style>
    __THEME_CSS__
    body{display:grid;place-items:center;padding:1rem}
    .login-card{width:100%;max-width:22rem;padding:1.35rem}
    .login-brand{display:flex;align-items:center;gap:.7rem;margin-bottom:1.55rem;color:var(--ink)}
    .login-brand .brand-mark{border-color:var(--teal);color:var(--teal)}
    .login-brand .brand-copy{font-size:.8rem}
    .login-brand .brand-sub{color:var(--muted)}
    .login-title{margin:.45rem 0 .3rem;font-size:2rem;line-height:.95;font-weight:400;letter-spacing:-.04em}
    .login-sub{margin:0 0 1.2rem;color:var(--muted);font-size:.88rem;line-height:1.5}
    .login-card .actions{margin-top:.25rem}
    .login-card .actions button{width:100%;min-width:0}
    .login-tools{position:fixed;top:1rem;right:1rem}
  </style>
</head>
<body data-page="login">
  <div class="login-tools">
    <div class="theme-toggle" role="group" aria-label="配色主題切換">
      <button type="button" data-theme-choice="light" aria-pressed="false">LIGHT</button>
      <button type="button" data-theme-choice="dark" aria-pressed="false">DARK</button>
    </div>
  </div>
  <main class="login-wrap">
    <div class="login-brand">
      <span class="brand-mark">EH</span>
      <span class="brand-copy">EPAPER HOME DISPLAY<span class="brand-sub">LOCAL DEVICE / ACCESS CONTROL</span></span>
    </div>
    <section class="card login-card">
      <div class="kicker">01 / access</div>
      <h1 class="login-title">__TITLE__</h1>
      <p class="login-sub">__SUBTITLE__</p>
      __ERROR_HTML__
      <form method="post" action="/login">
        <input type="hidden" name="next" value="__NEXT__">
        <input type="hidden" name="csrf" value="__CSRF__">
        <div class="f"><label for="login-password">管理密碼</label><input id="login-password" type="password" name="password" required autofocus></div>
        __CONFIRM_FIELD__
        <div class="actions"><button type="submit">__BUTTON__</button></div>
      </form>
    </section>
  </main>
  <script>__THEME_CONTROL__</script>
</body>
</html>"""
    .replace("__FAVICON__", _FAVICON_DATA_URI)
    .replace("__THEME_INIT__", _THEME_INIT_SCRIPT)
    .replace("__THEME_CSS__", _THEME_CSS)
    .replace("__THEME_CONTROL__", _THEME_CONTROL_SCRIPT)
)


def _render_login(
    next_url: str = "/settings",
    error: str = "",
    is_setup: bool = False,
    csrf_token: str = "",
) -> str:
    raw_next = next_url if next_url.startswith("/") and not next_url.startswith("//") else "/settings"
    safe_next = _html.escape(raw_next, quote=True)
    safe_csrf = _html.escape(csrf_token, quote=True)
    title = "設定管理密碼" if is_setup else "登入"
    subtitle = "首次設定完成後即可管理裝置。" if is_setup else "輸入密碼以開啟本機控制台。"
    button = "設定密碼" if is_setup else "登入"
    error_html = (
        f'<div class="message error" aria-live="polite">{_html.escape(error)}</div>' if error else ""
    )
    confirm_field = (
        '<div class="f"><label for="login-password-confirm">確認管理密碼</label>'
        '<input id="login-password-confirm" type="password" name="password_confirm" required></div>'
        if is_setup
        else ""
    )
    return (
        _LOGIN_HTML.replace("__TITLE__", title)
        .replace("__SUBTITLE__", subtitle)
        .replace("__BUTTON__", button)
        .replace("__ERROR_HTML__", error_html)
        .replace("__CONFIRM_FIELD__", confirm_field)
        .replace("__NEXT__", safe_next)
        .replace("__CSRF__", safe_csrf)
    )
