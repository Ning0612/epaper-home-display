from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from passlib.context import CryptContext
from starlette.requests import Request

from app.webui.config_helpers import _save_to_config
from app.webui.templates.login import _render_login

if TYPE_CHECKING:
    from app.config import Settings

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_auth_router(settings: "Settings") -> APIRouter:
    router = APIRouter()

    @router.get("/login", response_class=HTMLResponse)
    async def login_page(next: str = "/settings"):
        is_setup = not bool(settings.webui.password_hash)
        return HTMLResponse(_render_login(next_url=next, is_setup=is_setup))

    @router.post("/login", response_class=HTMLResponse)
    async def login_post(
        request: Request,
        password: str = Form(...),
        password_confirm: str = Form(""),
        next: str = Form("/settings"),
    ):
        is_setup = not bool(settings.webui.password_hash)
        safe_next = next if next.startswith("/") and not next.startswith("//") else "/settings"

        if is_setup:
            if len(password) < 8:
                return HTMLResponse(
                    _render_login(safe_next, "密碼長度至少 8 個字元", is_setup=True), status_code=400
                )
            if password != password_confirm:
                return HTMLResponse(
                    _render_login(safe_next, "兩次密碼不一致", is_setup=True), status_code=400
                )
            new_hash = _pwd_ctx.hash(password)
            if settings.webui.password_hash:
                is_setup = False
            else:
                _save_to_config({"webui": {"password_hash": new_hash}})
                settings.webui.password_hash = new_hash
                request.session["authenticated"] = True
                return RedirectResponse(url=safe_next, status_code=302)

        if not _pwd_ctx.verify(password, settings.webui.password_hash):
            return HTMLResponse(
                _render_login(safe_next, "密碼錯誤", is_setup=False), status_code=401
            )
        request.session["authenticated"] = True
        return RedirectResponse(url=safe_next, status_code=302)

    @router.get("/logout")
    async def logout(request: Request):
        request.session.clear()
        return RedirectResponse(url="/login", status_code=302)

    return router
